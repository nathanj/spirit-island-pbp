import traceback
import os
import discord
import random
import requests
import aiohttp
import asyncio
import datetime
import textwrap
import json
import structlog
import asyncio
import async_timeout
import aioredis
from collections import defaultdict
from dotenv import load_dotenv
from PIL import Image

load_dotenv()
client = discord.Client()

LOG = structlog.get_logger()
debug = os.environ.get('DEBUG', None) == 'yes'

def combine_images(filenames):
    images = []

    for infile in filenames:
        images.append(Image.open(infile))
        images[-1].resize((300, 420))

    out = Image.new('RGB', (len(images)*300, 420))

    for i, img in enumerate(images):
        out.paste(img, (i*300, 0))

    out.save('out.jpg')

@client.event
async def on_ready():
    print(f'We have logged in as {client}')

async def get_games(session):
    async with session.get('http://localhost:8000/api/game') as response:
        if response.status == 200:
            return await response.json()
    return []

async def get_game_log(session, id, latest):
    LOG.msg("getting log", id=id, latest=latest)
    async with session.get(f'http://localhost:8000/api/game/{id}/log?after={latest}') as response:
        if response.status == 200:
            return await response.json()
    return []

async def relay_game(channel_id, log):
    channel = client.get_channel(channel_id)
    combined_text = []
    for entry in log:
        print(entry)
        if 'images' in entry:
            if len(combined_text) > 0:
                await channel.send(embed=discord.Embed(description='\n'.join(combined_text)))
                combined_text = []
            images = entry['images']
            filenames = images.split(',')
            print(filenames)
            if len(filenames) > 1:
                combine_images(filenames)
                await channel.send(embed=discord.Embed(description=entry['text']), file=discord.File('out.jpg'))
            else:
                await channel.send(embed=discord.Embed(description=entry['text']), file=discord.File(filenames[0]))
        else:
            combined_text.append(entry['text'])

    if len(combined_text) > 0:
        await channel.send(embed=discord.Embed(description='\n'.join(combined_text)))
        combined_text = []

# Buffer up the log so we can send a group of related log messages together.
game_log_buffer = {}

async def logger():
    redis = await aioredis.from_url("redis://localhost", decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.psubscribe("log-relay:*")

    while True:
        try:
            async with async_timeout.timeout(5):
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                LOG.msg("got message", message=message)
                if message is not None:
                    channel_id = int(message['channel'].split(':')[1])
                    print(channel_id)
                    if channel_id in game_log_buffer:
                        game_log_buffer[channel_id]['timestamp'] = datetime.datetime.utcnow()
                    else:
                        game_log_buffer[channel_id] = {'timestamp': datetime.datetime.utcnow(), 'logs': []}
                    game_log_buffer[channel_id]['logs'].append(json.loads(message['data']))

                LOG.msg("buffer", game_log_buffer=game_log_buffer)
                keys = list(game_log_buffer.keys())
                for channel_id in keys:
                    LOG.msg("now", now=datetime.datetime.utcnow())
                    LOG.msg("sending at", send=(game_log_buffer[channel_id]['timestamp'] + datetime.timedelta(minutes=1)))
                    if game_log_buffer[channel_id]['timestamp'] + datetime.timedelta(seconds=10) < datetime.datetime.utcnow():
                        print('actually sending data!')
                        await relay_game(channel_id, game_log_buffer[channel_id]['logs'])
                        del game_log_buffer[channel_id]
                await asyncio.sleep(1)
        except asyncio.TimeoutError:
            print('timeout')
            pass

    #await asyncio.sleep(10)

client.loop.create_task(logger())
client.run(os.environ['DISCORD_KEY'])

