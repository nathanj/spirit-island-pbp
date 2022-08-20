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
import re
from collections import defaultdict
from dotenv import load_dotenv
from PIL import Image

spirit_emoji_map = {
'Bringer': 'SpiritBodanBringerDreamsNightmar',
'Exploratory Bringer':  'SpiritBodanBringerDreamsNightmar',
'Downpour': 'SpiritDownpourDrenchesWorld',
'Earth': 'SpiritVitalStrengthEarth',
'Fangs': 'SpiritSharpFangsLeaves',
'Finder': 'SpiritFinderPathsUnseen',
'Fractured': 'SpiritFracturedDaysSplitSky',
'Green': 'SpiritSpreadRampantGreen',
'Keeper': 'SpiritKeeperForbiddenWilds',
'Lightning': 'SpiritLightningSwiftStrike',
'Lure': 'SpiritLureDeepWilderness',
'Minds': 'SpiritManyMindsMoveOne',
'Mist': 'SpiritShroudSilentMist',
'Ocean': 'SpiritOceanHungryGrasp',
'River': 'SpiritRiverSurgesSunlight',
'Serpent': 'SpiritSnekSerpentSlumbering',
'Shadows': 'SpiritShadowsFlickerFlame',
'Shifting': 'SpiritShiftingMemoryAges',
'Starlight': 'SpiritStarlightSeeksForm',
'Stone': 'SpiritStoneUnyieldingDefiance',
'Thunderspeaker': 'SpiritThunderspeaker',
'Trickster': 'SpiritGrinningTricksterStirsTrou',
'Vengeance': 'SpiritVengeanceBurningPlague',
'Volcano': 'SpiritVolcanoLoomingHigh',
'Wildfire': 'SpiritHeartWildfire',
}

emoji_to_discord_map = {}
energy_to_discord_map = {}

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
    LOG.msg(f'We have logged in as {client}')

@client.event
async def on_guild_channel_update(before, after):
    LOG.msg(f'channel update #{after.name}')
    if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
        LOG.msg(f'id: {after.id}')
        if after.id in (957389286834057306, 883019769937268816, 703767917854195733, 1010285070680072192):
            LOG.msg(f'before topic: {before.topic}')
            LOG.msg(f'after  topic: {after.topic}')
            if before.topic != after.topic:
                match = re.search(r'''[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}''', after.topic)
                if match is not None:
                    guid = match[0]
                    LOG.msg(f'found guid: {guid}, linking to channel: {after.id}')
                    r = requests.post(f'http://localhost:8000/api/game/{guid}/link/{after.id}')
                    LOG.msg(r)
                    if r.status_code == 200:
                        await after.send(f'Now relaying game log for {guid} to this channel. Good luck!')

def load_emojis():
    guild = client.get_guild(846580409050857493)
    for e in guild.emojis:
        if e.name in spirit_emoji_map.values():
            emoji_to_discord_map[e.name] = str(e)
        if e.name == '4Energy1':
            energy_to_discord_map[e.name] = str(e)
        if e.name == '4Energy2':
            energy_to_discord_map[e.name] = str(e)
        if e.name == '4Energy3':
            energy_to_discord_map[e.name] = str(e)

def adjust_msg(msg):
    for spirit in spirit_emoji_map:
        msg = re.sub(f'^(.) {spirit}', '\\1 ' + emoji_to_discord_map[spirit_emoji_map[spirit]], msg)
    match = re.search(r'''(\d+) energy''', msg)
    if match is not None:
        new_msg = ''
        value = int(match[1])
        while value >= 3:
            new_msg += energy_to_discord_map['4Energy3']
            value -= 3
        while value >= 2:
            new_msg += energy_to_discord_map['4Energy2']
            value -= 2
        while value >= 1:
            new_msg += energy_to_discord_map['4Energy1']
            value -= 1
        if len(new_msg) > 0:
            msg = re.sub(r'''(\d+) energy''', new_msg, msg)
    return msg

async def relay_game(channel_id, log):
    channel = client.get_channel(channel_id)
    combined_text = []
    for entry in log:
        msg = adjust_msg(entry['text'])
        if 'images' in entry:
            if len(combined_text) > 0:
                await channel.send('\n'.join(combined_text))
                combined_text = []
            images = entry['images']
            filenames = images.split(',')
            if len(filenames) > 1:
                combine_images(filenames)
                await channel.send(msg, file=discord.File('out.jpg'))
            else:
                await channel.send(msg, file=discord.File(filenames[0]))
        else:
            combined_text.append(msg)

    if len(combined_text) > 0:
        await channel.send('\n'.join(combined_text))
        combined_text = []

# Buffer up the log so we can send a group of related log messages together.
game_log_buffer = {}

async def logger():
    await client.wait_until_ready()
    load_emojis()

    redis = await aioredis.from_url("redis://localhost", decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.psubscribe("log-relay:*")

    while True:
        try:
            async with async_timeout.timeout(30):
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message is not None:
                    LOG.msg("got message", message=message)
                    channel_id = int(message['channel'].split(':')[1])
                    if channel_id in game_log_buffer:
                        game_log_buffer[channel_id]['timestamp'] = datetime.datetime.utcnow()
                    else:
                        game_log_buffer[channel_id] = {'timestamp': datetime.datetime.utcnow(), 'logs': []}
                    game_log_buffer[channel_id]['logs'].append(json.loads(message['data']))

                keys = list(game_log_buffer.keys())
                for channel_id in keys:
                    if game_log_buffer[channel_id]['timestamp'] + datetime.timedelta(seconds=20) < datetime.datetime.utcnow():
                        LOG.msg('sending', channel_id=channel_id)
                        logs = game_log_buffer[channel_id]['logs']
                        del game_log_buffer[channel_id]
                        await relay_game(channel_id, logs)
                await asyncio.sleep(1)
        except asyncio.TimeoutError:
            LOG.msg('timeout')
            pass
        except Exception as ex:
            LOG.msg(ex)
            pass

client.loop.create_task(logger())
client.run(os.environ['DISCORD_KEY'])

