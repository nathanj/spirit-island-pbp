import os
import sys
import discord
import requests
import asyncio
import datetime
import json
import structlog
import async_timeout
import re
from dotenv import load_dotenv
from PIL import Image
import redis.asyncio as redis

spirit_emoji_map = {
'Behemoth': 'SpiritEmberEyedBehemothEEB',
'Breath': 'SpiritBreathOfDarknessBoDDYS',
'Bringer': 'SpiritBringerDreamNightmareBoDaN',
'Downpour': 'SpiritDownpourDrenchesWorld',
'Earthquakes': 'SpiritDancesUpEarthquakesDUE',
'Earth': 'SpiritVitalStrengthEarth',
'Exploratory Bringer': 'SpiritBringerDreamNightmareBoDaN',
'Eyes': 'SpiritEyesWatchTrees',
'Fangs': 'SpiritSharpFangsLeaves',
'Finder': 'SpiritFinderPathsUnseen',
'Fractured': 'SpiritFracturedDaysSplitSky',
'Gaze': 'SpiritRelentlessGazeOfSun',
'Green': 'SpiritSpreadRampantGreen',
'Heat': 'SpiritRisingHeatStoneSand',
'Keeper': 'SpiritKeeperForbiddenWilds',
'Lightning': 'SpiritLightningSwiftStrike',
'Lure': 'SpiritLureDeepWilderness',
'Minds': 'SpiritManyMindsMoveOneMMMAO',
'Mist': 'SpiritShroudSilentMist',
'Mud': 'SpiritOtterFathomlessMud',
'Ocean': 'SpiritOceanHungryGrasp',
'River': 'SpiritRiverSurgesSunlight',
'Roots': 'SpiritToweringRoots',
'Serpent': 'SpiritSerpentSlumberingSnek',
'Shadows': 'SpiritShadowsFlickerFlame',
'Shifting': 'SpiritShiftingMemoryAges',
'Starlight': 'SpiritStarlightSeeksForm',
'Stone': 'SpiritStoneUnyieldingDefiance',
'Teeth': 'SpiritChompDevouringTeeth',
'Thunderspeaker': 'SpiritThunderspeaker',
'Trickster': 'SpiritGrinningTrickster',
'Vengeance': 'SpiritVengeanceBurningPlague',
'Vigil': 'SpiritHearthVigil',
'Voice': 'SpiritWanderingVoice',
'Volcano': 'SpiritVolcanoLoomingHigh',
'Waters': 'SpiritWoundedWaters',
'Whirlwind': 'SpiritKittySunBrightWhirlwind',
'Wildfire': 'SpiritHeartWildfire',
}

emoji_to_discord_map = {}
energy_to_discord_map = {}

load_dotenv()

if '--fake-discord' in sys.argv:
    class Client:
        class Guild:
            def __init__(self):
                self.emojis = {}

        class Channel:
            def __init__(self, id):
                self.id = id

            async def send(self, msg, file=None):
                if file:
                    print(f"send {self.id}: {msg} file: {file.filename}")
                else:
                    print(f"send {self.id}: {msg}")

        def event(self, f):
            return f

        def run(self, guild):
            print(f"fake client for {guild}")
            asyncio.run(on_ready())

        async def wait_until_ready(self):
            pass

        def get_guild(self, _):
            return self.Guild()

        def get_channel(self, id):
            return self.Channel(id)

    client = Client()
else:
    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

LOG = structlog.get_logger()
debug = os.environ.get('DEBUG', None) == 'yes'

DISCORD_KEY = os.getenv('DISCORD_KEY')
DJANGO_HOST = os.getenv('DJANGO_HOST', 'localhost')
DJANGO_PORT = int(os.getenv('DJANGO_PORT', 8000))
GAME_URL = os.getenv('GAME_URL', 'si.bitcrafter.net')
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID', 846580409050857493))
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

def combine_images(filenames):
    images = []

    for infile in filenames:
        images.append(Image.open(infile).resize((300, 420)))

    out = Image.new('RGB', (len(images)*300, 420))

    for i, img in enumerate(images):
        out.paste(img, (i*300, 0))

    out.save('out.jpg')

@client.event
async def on_ready():
    LOG.msg(f'We have logged in as {client}')
    #await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, status="a movie"))
    await asyncio.create_task(logger())

def match_game_url(s):
    """
    Match a game url returning the guid on a match.

    >>> match_game_url('https://si.bitcrafter.net/game/573a76ed-b9ed-45b1-8e14-04bfacb90a21')
    '573a76ed-b9ed-45b1-8e14-04bfacb90a21'
    >>> match_game_url('stuff')
    """
    match = re.search(GAME_URL + r'''/game/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})''', s)
    if match is not None:
        return match[1]
    return None

async def updatethings(after,topic):
    guid = match_game_url(topic)
    if guid is not None:
        LOG.msg(f'found guid: {guid}, linking to channel: {after.id}')
        r = requests.post(f'http://{DJANGO_HOST}:{DJANGO_PORT}/api/game/{guid}/link/{after.id}')
        LOG.msg(r)
        if r.status_code == 200:
            await after.send(f'Now relaying game log for {guid} to this channel. Good luck!')
        return r.status_code

@client.event
async def on_guild_channel_update(before, after):
    LOG.msg(f'channel update #{after.name}')
    if (isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel)) or \
    (isinstance(before, discord.Thread) and isinstance(after, discord.Thread)):
        LOG.msg(f'id: {after.id}')
        LOG.msg(f'before topic: {before.topic}')
        LOG.msg(f'after  topic: {after.topic}')
        if before.topic != after.topic:
            status = await updatethings(after, after.topic)
            if status and status != 200:
                await after.send(f"Couldn't link the channel to the game ({status}). The bot owner needs to check the logs for the site API and/or bot")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    parts = message.content.split()
    if len(parts) >= 2 and parts[0] == '$follow':
        argument = parts[1]
        status = await updatethings(message.channel, argument)
        if not status:
            await message.channel.send(f"That doesn't look like a game URL. Did you provide the full URL https://{GAME_URL}/game/abcd1234... ?")
            return
        elif status != 200:
            await message.channel.send(f"Couldn't link the channel to the game ({status}). The bot owner needs to check the logs for the site API and/or bot")
            return
        try:
            await message.pin(reason=f"{message.author.display_name} ({message.author.name}) requested")
        except discord.Forbidden:
            await message.channel.send("I don't have permission to pin messages, so you'll have to pin the link yourself, but I'll still relay game logs.")
        except discord.HTTPException:
            await message.channel.send("Failed to pin the message due to an HTTP error, so you'll have to pin the link yourself, but I'll still relay game logs.")
    if message.content.startswith('$help'):
        # The message starts with the specified word
        LOG.msg(f'$help called')
        text = "\n".join((
            "[Github link](<https://github.com/nathanj/spirit-island-pbp>)",
            "",
            "Use `$follow (yourgameurl)` to start",
            "Use `$pin` (reply to message) to pin the message",
            "Use `$unpin` (reply to message) to unpin the message, or `$unpin N` to unpin the last N messages",
            "Use `$delete` (reply to message) to delete a message (only messages posted by the bot)",
            "Use `$topic (new topic)` to set the channel topic",
        ))
        await message.channel.send(text)
    if message.content.startswith('$pin'):
        message_to_pin = await referenced_message(message, 'pin')
        # OK not to check if the message is already pinned, since pinning is idempotent.
        if message_to_pin and await act_on_message(message, message_to_pin, 'pin'):
            await report_success(message, 'pinned')
    elif message.content.startswith('$unpin'):
        if message.reference:
            message_to_unpin = await referenced_message(message, 'unpin')
            # OK not to check that the message is pinned, since unpinning is idempotent.
            if message_to_unpin and await act_on_message(message, message_to_unpin, 'unpin'):
                await report_success(message, 'unpinned')
        elif len(parts) >= 2 and parts[1].isnumeric() and (num_to_unpin := int(parts[1])) > 0:
            try:
                pinned = await message.channel.pins()
            except discord.Forbidden:
                await message.channel.send("I don't have permission to get the pinned messages")
                return
            for to_unpin in pinned[:num_to_unpin]:
                if not await act_on_message(message, to_unpin, 'unpin'):
                    return
            if pinned:
                await report_success(message, 'unpinned')
            else:
                await message.channel.send("There were no pinned messages to unpin")
        else:
            await message.channel.send(f"You need to reply to a message or specify a number of messages to unpin to use $unpin")
    elif message.content.startswith('$delete'):
        message_to_delete = await referenced_message(message, 'delete')
        if not message_to_delete:
            return
        if message_to_delete.author != client.user:
            await message.channel.send("I only delete my own messages")
            return
        # delete doesn't accept a reason argument
        # doesn't matter anyway since we're deleting our own message,
        # which doesn't create an audit log entry
        if await act_on_message(message, message_to_delete, 'delete', reason=False):
            await report_success(message, 'deleted')
    elif message.content.startswith('$topic'):
        try:
            await message.channel.edit(topic=" ".join(parts[1:]), reason=f"{message.author.display_name} ({message.author.name}) requested")
            await report_success(message, 'set as topic')
        except discord.Forbidden:
            await message.channel.send("I don't have permission to set the channel topic")

async def referenced_message(message, command):
    if message.reference:
        try:
            return await message.channel.fetch_message(message.reference.message_id)
        except discord.Forbidden:
            await message.channel.send("I don't have permission to read previous messages")
            return
    await message.channel.send(f"You need to reply to a message to use ${command}")

async def act_on_message(command_message, message_to_modify, verb, reason=True):
    try:
        kwargs = {'reason': f"{command_message.author.display_name} ({command_message.author.name}) requested"} if reason else {}
        await getattr(message_to_modify, verb)(**kwargs)
        return True
    except discord.Forbidden:
        await command_message.channel.send(f"I don't have permission to {verb} messages.")
    except discord.HTTPException:
        await command_message.channel.send(f"Failed to {verb} the message due to an HTTP error.")

async def report_success(command_message, verb):
    try:
        await command_message.add_reaction('✅')
    except discord.Forbidden:
        await command_message.channel.send(f"Message {verb}!")

def load_emojis(emojis):
    for e in emojis:
        #LOG.msg(f'found emoji = {e.name} {str(e)}')
        if e.name in spirit_emoji_map.values():
            emoji_to_discord_map[e.name] = str(e)
        if e.name == 'Energy1':
            energy_to_discord_map[e.name] = str(e)
        if e.name == 'Energy2':
            energy_to_discord_map[e.name] = str(e)
        if e.name == 'Energy3':
            energy_to_discord_map[e.name] = str(e)
    for spirit in spirit_emoji_map:
        if spirit_emoji_map[spirit] not in emoji_to_discord_map:
            LOG.warn(f'missing emoji for {spirit}')

def adjust_msg(msg):
    try:
        for spirit in spirit_emoji_map:
            try:
                # searches for keys from spirit_emoji_map and replaces with correct Discord emoji
                # \\S+ matches the emoji representing the spirit; (.) does not successfully match ❤️
                msg = re.sub(f'^(\\S+) {spirit} ', '\\1 ' + emoji_to_discord_map[spirit_emoji_map[spirit]] + ' ', msg)
            except KeyError:
                pass
        match = re.search(r'''(\d+) energy''', msg)
        if match is not None:
            new_msg = ''
            value = int(match[1])
            while value >= 3:
                new_msg += energy_to_discord_map['Energy3']
                value -= 3
            while value >= 2:
                new_msg += energy_to_discord_map['Energy2']
                value -= 2
            while value >= 1:
                new_msg += energy_to_discord_map['Energy1']
                value -= 1
            if len(new_msg) > 0:
                msg = re.sub(r'''(\d+) energy''', new_msg, msg)
    except KeyError:
        pass
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

# The bot has been sending duplicate messages after running for some time.
# We don't know the reason for this yet.
# As a short-term solution we could de-duplicate before we send them,
# but it'd be better to find the root of the problem and solve that instead.
last_message = {}

async def logger():
    await client.wait_until_ready()

    correct_guild = False
    for guild in client.guilds:
        if guild.id == GUILD_ID:
            load_emojis(guild.emojis)
            correct_guild = True
    if not correct_guild:
        LOG.warn("Not in the correct guild! Won't be able to use any spirit emojis!")

    redis_obj = await redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)
    pubsub = redis_obj.pubsub()
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

                    if last_message.get(channel_id) == message['data']:
                        LOG.msg('drop duplicate message')
                    else:
                        game_log_buffer[channel_id]['logs'].append(json.loads(message['data']))
                        last_message[channel_id] = message['data']

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
            LOG.exception(ex)
            pass

if __name__ == '__main__':
    #combine_images(["./pbf/static/pbf/settle_into_huntinggrounds.jpg","./pbf/static/pbf/flocking_redtalons.jpg","./pbf/static/pbf/vigor_of_the_breaking_dawn.jpg","./pbf/static/pbf/vengeance_of_the_dead.jpg"])
    client.run(DISCORD_KEY)
