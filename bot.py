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
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()
client = discord.Client()

log = structlog.get_logger()
debug = os.environ.get('DEBUG', None) == 'yes'

@client.event
async def on_ready():
    print(f'We have logged in as {client}')

async def get_games(session):
    async with session.get('http://localhost:8000/api/game') as response:
        if response.status == 200:
            return await response.json()
    return []

async def get_game_log(session, id, latest):
    log.msg("getting log", id=id, latest=latest)
    async with session.get(f'http://localhost:8000/api/game/{id}/log?after={latest}') as response:
        if response.status == 200:
            return await response.json()
    return []

async def logger():
    game_log_latest = defaultdict(lambda: -1)
    await asyncio.sleep(10)
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                games = await get_games(session)
                for g in games:
                    id = g['id']
                    channel_id = g['discord_channel']
                    latest = game_log_latest[id]
                    log = await get_game_log(session, id, latest)
                    if latest != -1 and len(log) > 0:
                        text = '\n'.join([entry['text'] for entry in log])
                        if debug:
                            print(text)
                        elif len(channel_id) > 0:
                            channel = client.get_channel(int(channel_id))
                            await channel.send(embed=discord.Embed(description=text))
                    if latest == -1:
                        game_log_latest[id] = 0
                    game_log_latest[id] = max([entry['id'] for entry in log], default=game_log_latest[id])
            except Exception as ex:
                print(ex)
            await asyncio.sleep(60)

client.loop.create_task(logger())
client.run(os.environ['DISCORD_KEY'])
