import asyncio
import datetime
import json
import os
import re
import sys
from collections.abc import Callable, Collection, Iterable
from itertools import takewhile
from typing import Any, Literal, NotRequired, TypedDict, TypeVar, Unpack

import aiohttp
import discord
import structlog
from dotenv import load_dotenv
from frozendict import frozendict
from PIL import Image


# Someone not in the role assigner role tried to assign/unassign a role
class NotRoleAssigner(Exception):
    pass
# Tried to manage a role that doesn't match the bot's ROLE_PATTERN below
class DisallowedRole(Exception):
    pass

spirit_names = (
'Behemoth',
'Breath',
'Bringer',
'Covets',
'Downpour',
'Earth',
'Earthquakes',
'Eyes',
'Fangs',
'Finder',
'Fractured',
'Gaze',
'Green',
'Heat',
'Keeper',
'Lightning',
'Lure',
'Memory',
'Minds',
'Mist',
'Mud',
'Ocean',
'River',
'Roots',
'Rot',
'Serpent',
'Shadows',
'Starlight',
'Stone',
'Teeth',
'Thunderspeaker',
'Trickster',
'Vengeance',
'Vigil',
'Voice',
'Volcano',
'Waters',
'Whirlwind',
'Wildfire',
)
spirit_disambig = frozendict({
    'Earth': 'Vital.*Earth', # just "Earth" is ambiguous (Earthquakes)
    'Stone': 'Stones?(Unyielding|.*Defiance)', # just "Stone" is ambiguous (Rising Heat of Stone and Sand)
})

resolved_spirit_emoji: dict[str, discord.Emoji] = {}
energy_to_discord_map: dict[str, str] = {}

load_dotenv()

if '--fake-discord' in sys.argv:
    class Client:
        class User:
            def __init__(self) -> None:
                self.name = 'fake discord bot'

        class Guild:
            def __init__(self, id: int = 0) -> None:
                self.id = id
                self.name = 'fake discord guild'
                self.emojis: tuple[discord.Emoji, ...] = ()

        class Channel:
            def __init__(self, id: int) -> None:
                self.id = id

            async def send(self, msg: str, file: discord.File | None = None) -> None:
                if file:
                    print(f"send {self.id}: {msg} file: {file.filename}")
                else:
                    print(f"send {self.id}: {msg}")

        def __init__(self) -> None:
            self.user = self.User()
            self.guilds = [self.Guild()]

        T = TypeVar('T')
        def event(self, f: T) -> T:
            return f

        def run(self, key: str) -> None:
            async def fakebot() -> None:
                await setup_hook()
                await on_ready()
                while True:
                    await asyncio.sleep(60)
            print(f"fake client (key has {len(key)} characters)")
            asyncio.run(fakebot())

        async def wait_until_ready(self) -> None:
            pass

        def get_channel(self, id: int) -> Channel:
            return self.Channel(id)

    class Tree:
        T = TypeVar('T')
        def command(self, guild: discord.Object | None) -> Callable[[T], T]:
            T = TypeVar('T')
            def dc(f: T) -> T:
                return f
            return dc

        async def sync(self, guild: discord.Object | None = None) -> None:
            pass

    client: discord.client.Client = Client() #type: ignore[assignment]
    tree: discord.app_commands.CommandTree = Tree() #type: ignore[assignment]
else:
    intents = discord.Intents.default()
    intents.members = True

    client = discord.Client(intents=intents)
    tree = discord.app_commands.CommandTree(client)

list_guilds = '--list-guilds' in sys.argv

LOG = structlog.get_logger()

DISCORD_KEY = os.getenv('DISCORD_KEY', '')
DJANGO_HOST = os.getenv('DJANGO_HOST', 'localhost')
DJANGO_PORT = int(os.getenv('DJANGO_PORT', 8000))
MANAGED_CHANNEL_PATTERN = re.compile(os.getenv('DISCORD_MANAGED_CHANNEL_PATTERN', r'\A\d+-?(up|dc)'))
NON_UPDATE_CHANNEL_PATTERN = re.compile(os.getenv('DISCORD_NON_UPDATE_CHANNEL_PATTERN', r'\A\d+-?dc'))
ROLE_CHANNEL = int(os.getenv('DISCORD_ROLE_CHANNEL', 846584074943725599))
ROLE_PATTERN = re.compile(os.getenv('DISCORD_ROLE_PATTERN', r'\A\d+-pbp\Z'))
ROLE_ASSIGNER_ROLE = int(os.getenv('DISCORD_ROLE_ASSIGNER_ROLE', 1195873293622857789))
ROLE_ASSIGNER_ADMIN_ROLE = int(os.getenv('DISCORD_ROLE_ASSIGNER_ADMIN_ROLE', 925206661528948736))
ROLE_CREATOR_ROLE = int(os.getenv('DISCORD_ROLE_CREATOR_ROLE', 925206661528948736))
GAME_URL = os.getenv('GAME_URL', 'si.bitcrafter.net')
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID', 846580409050857493))

match os.getenv('IPC_METHOD', 'redis'):
    case 'socket':
        import socket
        SOCKET_PATH = os.getenv('SOCKET_PATH', 'si.sock')
    case 'redis':
        # for type-checking, this code path is statically checked regardless of IPC_METHOD,
        # and we don't want to force type-checking to install redis
        import redis.asyncio as redis  #type: ignore[import-not-found]

        REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
        REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
        SOCKET_PATH = None #type: ignore[assignment]
    case _:
        raise ValueError('unknown IPC method')

command_test_guild = discord.Object(id=GUILD_ID)
command_scope = None
# for testing, since guild-specific commands update immediately:
# command_scope = command_test_guild

relay_task = None

def combine_images(filenames: Iterable[str]) -> None:
    images = []

    for infile in filenames:
        images.append(Image.open(infile).resize((300, 420)))

    out = Image.new('RGB', (len(images)*300, 420))

    for i, img in enumerate(images):
        out.paste(img, (i*300, 0))

    out.save('out.jpg')

@client.event
async def setup_hook() -> None:
    global relay_task
    LOG.msg(f'We have logged in as {client.user.name if client.user else 'nobody???'}')
    # Important that we create this task in setup_hook, not on_ready.
    # setup_hook is guaranteed to be called only once,
    # while on_ready may be called multiple times if the bot reconnects.
    # If we set this task up in on_ready,
    # the bot will start sending duplicate messages for each reconnect.
    #
    # We only want to create the task, not await the creation.
    # The task contains a wait_until_ready,
    # and awaiting wait_until_ready in setup_hook will deadlock,
    # as pointed out by the documentation of setup_hook.
    relay_task = asyncio.create_task(logger())

@client.event
async def on_ready() -> None:
    LOG.msg(f'We have logged in as {client.user.name if client.user else 'nobody???'}, a member of {len(client.guilds)} guilds')

    # while other instances of the bot are welcome,
    # we also want to avoid duplicate commands on the main guild.
    # The below user ID is NOT read from an environment variable because the main bot instance is not a configuration option.
    main_bot = client.user and client.user.id == 932806700761743362

    # similarly, the main guild's ID is NOT a configuration option, even if it is the default value of GUILD_ID
    if main_bot or (command_test_guild and command_test_guild.id != 846580409050857493):
        # main bot syncs guild-scoped commands to main guild to clear duplicates when transitioning from guild to global
        # or, any bot can sync guild-scoped commands to their own guild as long as it's not the main guild
        await tree.sync(guild=command_test_guild)
        LOG.msg("guild tree synced")
    else:
        LOG.msg("not syncing commands to main guild, as this is not the main bot. to fix this, change the DISCORD_GUILD_ID environment variable.")

    if main_bot:
        await tree.sync()
        LOG.msg("global tree synced")

    #await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, status="a movie"))

def match_game_url(s: str) -> str | None:
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

type AnyDiscordChannel = discord.TextChannel | discord.StageChannel | discord.VoiceChannel | discord.Thread | discord.DMChannel | discord.GroupChannel | discord.PartialMessageable

async def link_channel_to_game(after: AnyDiscordChannel, guid: str) -> bool:
    LOG.msg(f'found guid: {guid}, linking to channel: {after.id}')
    # TODO: we could try to keep this session across multiple requests,
    # but it hasn't been necessary yet
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f'http://{DJANGO_HOST}:{DJANGO_PORT}/api/game/{guid}/link/{after.id}') as resp:
                LOG.msg(resp)
                status = resp.status
        except Exception as e:
            await after.send(f"Couldn't link the channel to the game ({type(e).__name__}). The bot owner needs to check the logs for the site API and/or bot")
            raise
    if status == 200:
        await after.send(f'Now relaying game log for {guid} to this channel. Good luck!')
        return True
    await after.send(f"Couldn't link the channel to the game ({status}). The bot owner needs to check the logs for the site API and/or bot")
    return False

@client.event
async def on_guild_channel_update(before: discord.abc.GuildChannel, after: discord.abc.GuildChannel) -> None:
    LOG.msg(f'channel update #{after.name}')
    if (isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel)):
        LOG.msg(f'id: {after.id}')
        LOG.msg(f'before topic: {before.topic}')
        LOG.msg(f'after  topic: {after.topic}')
        if before.topic == after.topic:
            return
        guid = after.topic and match_game_url(after.topic)
        if not guid:
            return
        if re.search(NON_UPDATE_CHANNEL_PATTERN, after.name):
            LOG.msg('skip non-update channel')
            return
        await link_channel_to_game(after, guid)

@tree.command(guild=command_scope)
@discord.app_commands.describe(topic="what you want help on")
async def help(interaction: discord.Interaction, topic: Literal['general', 'admin', 'role'] | None = None) -> None:
    """Help for PBP bot"""
    match topic:
        case "admin":
            text = "\n".join(( #noqa: FLY002
                "/createrole N to create the role N-pbp",
                "$host/$unhost to add/remove hosts (hosts can can add/remove players to/from PBP roles)",
            ))
        case "role":
            text = "\n".join(( #noqa: FLY002
                "### Add yourself",
                "in the commands channel: /roleme 99",
                "### Add other players",
                "in the game channel: /role @player1 @player2 @player3",
                "### Remove a player",
                "in the game channel: /unrole @player",
                "### Remove all players",
                "in the game channel: /unroleall",
                "",
            ))
        case _:
            text = "\n".join(( #noqa: FLY002
                "[Github link](<https://github.com/nathanj/spirit-island-pbp>)",
                "",
                "`/topic new topic` to set the channel topic (set an update channel's topic to a game link to start sending updates to that channel)",
                "`/follow gameurl` for forum posts (where it's not possible to set a topic)",
                "`/delete messageID` to delete a message (only messages posted by the bot)",
                "`/rename new name` to set the channel name",
                "`/roleme rolenum` to add yourself to a role",
                "`/role` and `/unrole` to add/remove other players to/from a role",
                "`/unroleall` to remove all players from a role",
                "`/help role` for more detailed help on roles",
                "`/help admin` to show admin-only commands",
            ))
    await interaction.response.send_message(text)

@tree.command(guild=command_scope)
@discord.app_commands.describe(game_url=f"game URL, looks like https://{GAME_URL}/game/abcd1234...")
async def follow(interaction: discord.Interaction, game_url: str) -> None:
    """manually follow a game (only use in forum threads, not regular channels)"""
    guid = match_game_url(game_url)
    if not guid:
        await interaction.response.send_message(f"That doesn't look like a game URL. Did you provide the full URL https://{GAME_URL}/game/abcd1234... ?")
        return

    if not isinstance(interaction.channel, AnyDiscordChannel.__value__):
        await interaction.response.send_message(f"I can't follow games in this kind of channel ({type(interaction.channel).__name__})")
        return

    if not await link_channel_to_game(interaction.channel, guid):
        return

    v = await interaction.response.send_message(f"https://{GAME_URL}/game/{guid}")
    if isinstance(v.resource, discord.InteractionMessage):
        try:
            await v.resource.pin(reason=f"{interaction.user.display_name} ({interaction.user.name}, ID {interaction.user.id}) requested")
        except discord.Forbidden:
            await interaction.channel.send("I don't have permission to pin messages, so you'll have to pin the link yourself, but I'll still relay game logs.")
        except discord.HTTPException:
            await interaction.channel.send("Failed to pin the message due to an HTTP error, so you'll have to pin the link yourself, but I'll still relay game logs.")

@tree.command(guild=command_scope)
async def unpinall(interaction: discord.Interaction) -> None:
    """unpin all messages in this channel"""
    if not interaction.channel or isinstance(interaction.channel, (discord.ForumChannel, discord.CategoryChannel)):
        await interaction.response.send_message(f"this kind of channel ({type(interaction.channel).__name__}) doesn't have any pins")
        return

    num_unpinned = 0
    try:
        async for to_unpin in interaction.channel.pins():
            if not await act_on_message(interaction, to_unpin, 'unpin'):
                return
            num_unpinned += 1
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to get the pinned messages")
        return
    await interaction.response.send_message(f"{interaction.user.mention} unpinned {num_unpinned} messages")

@tree.command(guild=command_scope)
@discord.app_commands.describe(message_id="ID of the message to delete (17-20 digit number)")
# can't use int, because int only supports int53, but message IDs can be up to 64 bits
async def delete(interaction: discord.Interaction, message_id: str) -> None:
    """delete the message with the specified ID (bot's messages only)"""
    if not interaction.channel or isinstance(interaction.channel, (discord.ForumChannel, discord.CategoryChannel)):
        await interaction.response.send_message("couldn't find a message with that ID in this channel (need to be in the same channel)")
        return

    try:
        message_id_int = int(message_id)
    except Exception: # noqa: BLE001
        await interaction.response.send_message(f"invalid message ID (needs to be a number between 1 and {2 ** 64 - 1})")
        return

    try:
        message_to_delete = await interaction.channel.fetch_message(message_id_int)
    except discord.errors.NotFound:
        await interaction.response.send_message("couldn't find a message with that ID in this channel (need to be in the same channel)")
        return
    except discord.errors.Forbidden:
        await interaction.response.send_message("I don't have permission to get past messages")
        return

    if message_to_delete.author != client.user:
        await interaction.response.send_message("I only delete my own messages")
        return
    if message_to_delete.mentions or message_to_delete.interaction_metadata:
        await interaction.response.send_message("This message seems to mention some users, which means it may be an audit message. Deleting it may be unsafe.")
        return

    # delete doesn't accept a reason argument
    # doesn't matter anyway since we're deleting our own message,
    # which doesn't create an audit log entry
    if await act_on_message(interaction, message_to_delete, 'delete', reason=False):
        await interaction.response.send_message(f"{interaction.user.mention} deleted the message I sent at {message_to_delete.created_at}")

async def act_on_message(interaction: discord.Interaction, message_to_modify: discord.Message, verb: str, reason: bool = True) -> bool:
    try:
        kwargs = {'reason': f"{interaction.user.display_name} ({interaction.user.name}) requested"} if reason else {}
        await getattr(message_to_modify, verb)(**kwargs)
        return True
    except discord.Forbidden:
        await interaction.response.send_message(f"I don't have permission to {verb} messages.")
    except discord.HTTPException:
        await interaction.response.send_message(f"Failed to {verb} the message due to an HTTP error.")
    return False

@tree.command(guild=command_scope)
@discord.app_commands.describe(new_topic="new topic, or empty to clear the topic")
async def topic(interaction: discord.Interaction, new_topic: str = "") -> None:
    """change the topic of this channel (PBP channels only) automatically follow game for update channels"""
    if not isinstance(interaction.channel, discord.TextChannel):
        if isinstance(interaction.channel, discord.StageChannel):
            await interaction.response.send_message(f"This bot only supports setting the topic of text channels, not {type(interaction.channel).__name__}s")
        else:
            # ForumChannel have a topic in the API, but they are guidelines in the UI
            # Everything else doesn't have a topic at all.
            await interaction.response.send_message(f"{type(interaction.channel).__name__}s don't have a topic")
        return
    try:
        # Expected (and so far observed) behaviour:
        # the bot will get an on_guild_channel_update for its own update,
        # thereby automatically following a game linked in the topic
        # (if present and the channel doesn't match NON_UPDATE_CHANNEL_PATTERN),
        # without needing to explicitly call link_channel_to_game here.
        await edit_channel(interaction, interaction.channel, 'changed the channel topic', topic=new_topic)
    except discord.Forbidden:
        await interaction.followup.send("I don't have permission to set the channel topic")

@tree.command(guild=command_scope)
@discord.app_commands.describe(new_name="new channel name, or empty to clear the name. DO NOT include the NNup- or NNdc- prefix")
async def rename(interaction: discord.Interaction, new_name: str = "") -> None:
    """rename this channel (PBP channels only) DO NOT include the NNup- or NNdc- prefix"""
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message(f"This bot only supports renaming text channels, not {type(interaction.channel).__name__}s")
        return

    existing_name = interaction.channel.name
    verb = 'renamed the channel'

    if not new_name:
        # no argument given: try to clear the channel name.
        if '-' in existing_name:
            new_name = existing_name[:existing_name.index('-')]
        else:
            await interaction.response.send_message("channel already had no name")
            return
    else:
        # TODO: Too specific to one guild's naming conventions?
        # Consider the first dash-separated word of the channel name.
        # Always keep this the same.
        # But don't duplicate the prefix if the user specifies it again.
        # Given a channel currently named either 1up or 1up-aaa,
        # requesting the following names will have these results:
        #
        # Requested name | Resulting name
        # ---------------|---------------
        # 1up            | 1up
        # bbb            | 1up-bbb
        # 1up-bbb        | 1up-bbb (and tell them they don't need to include 1up)
        # hello-world    | 1up-hello-world
        # (a request to rename 1up-aaa to 1up-1up will behave oddly, but this shouldn't normally happen)
        existing_prefix = existing_name[:existing_name.index('-')] if '-' in existing_name else existing_name
        new_suffix = new_name
        if '-' in new_suffix and new_suffix[:new_suffix.index('-')] == existing_prefix:
            verb = f"You don't need to include the {existing_prefix}- prefix; it's automatically added. {interaction.user.mention} {verb}"
            new_suffix = new_suffix[new_suffix.index('-') + 1:]
        new_name = existing_prefix if new_suffix == existing_prefix else f"{existing_prefix}-{new_suffix}"

    try:
        await edit_channel(interaction, interaction.channel, verb, name=new_name)
    except discord.Forbidden:
        await interaction.followup.send("I don't have permission to rename the channel")

class ChannelChanges(TypedDict):
    name: NotRequired[str]
    topic: NotRequired[str]

async def edit_channel(interaction: discord.Interaction, channel: discord.TextChannel, action: str, **changes: Unpack[ChannelChanges]) -> None:
    # Ideally the guild uses permissions to restrict what the bot can do,
    # but defence in depth is desirable for such sensitive operations.
    if not re.search(MANAGED_CHANNEL_PATTERN, channel.name):
        await interaction.response.send_message("I only manage PBP channels, which this channel doesn't appear to be")
        return

    edit_task = asyncio.create_task(channel.edit(**changes, reason=f"{interaction.user.display_name} ({interaction.user.name}, ID {interaction.user.id}) requested"))

    async def check_task_completion() -> None:
        await asyncio.sleep(3)
        # Didn't find a way to introspect the channel edit task to see its status (time left to wait)
        # so best we can do is check whether it's done.
        if edit_task.done():
            return
        await channel.send("Got rate-limited by Discord (Discord limits the bot to 2 changes to the same channel within 10 minutes), automatically retrying when possible. Thanks for your patience.")

    check_task = asyncio.create_task(check_task_completion())
    await interaction.response.defer(thinking=True)
    await edit_task
    await interaction.followup.send(f"{interaction.user.mention} {action}")
    await check_task

@tree.command(guild=command_scope)
@discord.app_commands.describe(role="role to add yourself to")
async def roleme(interaction: discord.Interaction, role: discord.Role) -> None:
    """add yourself to a given PBP role"""
    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("you have to be a member to be given a role")
        return
    await mod_players_and_roles(interaction, (interaction.user, ), role, "add", "to")

@tree.command(guild=command_scope)
async def role(interaction: discord.Interaction, player1: discord.Member, player2: discord.Member | None = None, player3: discord.Member | None = None, player4: discord.Member | None = None, player5: discord.Member | None = None, player6: discord.Member | None = None) -> None:
    """add players to this channel's PBP role"""
    role = await role_from_channel(interaction)
    if not role:
        return
    players = [p for p in [player1, player2, player3, player4, player5, player6] if p]
    await mod_players_and_roles(interaction, players, role, "add", "to")

@tree.command(guild=command_scope)
async def unrole(interaction: discord.Interaction, player1: discord.Member, player2: discord.Member | None = None, player3: discord.Member | None = None, player4: discord.Member | None = None, player5: discord.Member | None = None, player6: discord.Member | None = None) -> None:
    """remove players from this channel's PBP role"""
    role = await role_from_channel(interaction)
    if not role:
        return
    players = [p for p in [player1, player2, player3, player4, player5, player6] if p]
    await mod_players_and_roles(interaction, players, role, "remove", "from")

@tree.command(guild=command_scope)
async def unroleall(interaction: discord.Interaction) -> None:
    """remove all players from this channel's PBP role"""
    role = await role_from_channel(interaction)
    if not role:
        return
    if not client.intents.members and interaction.channel and not isinstance(interaction.channel, (discord.CategoryChannel, discord.ForumChannel)):
        await interaction.channel.send("The Server Members intent isn't enabled, so `unroleall` probably won't work. Check with the bot's owner to see if they are willing to enable it.")
        # OK not to return and just try it; maybe a future change makes the Server Members intent not required.
    await mod_players_and_roles(interaction, role.members, role, "remove", "from")

async def role_from_channel(interaction: discord.Interaction) -> discord.Role | None:
    tip = "You have to use this command in a numbered PBP channel like #NNup- or #NNdc-, otherwise I don't know what role to use. Did you mean to use /roleme to add yourself to a specific role?"
    if not interaction.channel or not interaction.guild or isinstance(interaction.channel, discord.DMChannel) or not interaction.channel.name:
        await interaction.response.send_message(tip)
        return None
    if re.search(MANAGED_CHANNEL_PATTERN, interaction.channel.name):
        channelnum = int(''.join(takewhile(lambda x: x.isnumeric(), interaction.channel.name)))
        candidates = (role for role in interaction.guild.roles if role.name == f"{channelnum}-pbp")
        role = next(candidates, None)
        if not role:
            await interaction.response.send_message(f"There doesn't seem to be any role matching the number of this PBP channel ({channelnum}). Check with a PBP admin to get one created")
            return None
        if excess := sum(1 for _ in candidates):
            await interaction.response.send_message(f"There seem to be multiple ({1 + excess}) roles matching the number of this PBP channel ({channelnum}). Check with a server admin to fix this.")
            return None
        return role
    await interaction.response.send_message(tip)
    return None

async def mod_players_and_roles(interaction: discord.Interaction, members: Collection[discord.Member], role: discord.Role, verb: str, direction: str) -> None:
    if not (interaction.channel and interaction.channel.id == ROLE_CHANNEL) and not (isinstance(interaction.channel, discord.TextChannel) and re.search(MANAGED_CHANNEL_PATTERN, interaction.channel.name)):
        await interaction.response.send_message("For auditability reasons, please keep role commands to PBP game channels or the bot channel, thanks!")
        return

    try:
        assert_allowed_role_manager(interaction.user, role)
    except NotRoleAssigner:
        await interaction.response.send_message("You need to be a PBP host to assign roles")
        return
    except DisallowedRole:
        await interaction.response.send_message("I only manage roles related to PBP, which that role doesn't appear to be")
        return

    try:
        for member in members:
            # This should have been asserted above for a friendlier message,
            # but intentionally asserting it a second time in case a refactor accidentally removes the above assert or makes it no longer exit.
            assert_allowed_role_manager(interaction.user, role)
            await getattr(member, f"{verb}_roles")(role, reason=f"{interaction.user.display_name} ({interaction.user.name}, ID {interaction.user.id}) requested {verb}")
    except discord.Forbidden:
        if role.is_assignable():
            await interaction.response.send_message("I don't have permission to manage roles on this server")
        else:
            await interaction.response.send_message("I don't have permission to manage that role (it outranks me)")
        return

    suffix = "d" if verb[-1] == "e" else "ed"
    name_list = ', '.join(member.display_name for member in members)
    await interaction.response.send_message(f"{interaction.user.mention} {verb}{suffix} {len(members)} player{'' if len(members) == 1 else 's'} {direction} {role.name}: {name_list}")

def assert_allowed_role_manager(user_or_member: discord.User | discord.Member, role: discord.Role) -> None:
    if not isinstance(user_or_member, discord.Member):
        # User has no roles (left the guild, or message isn't in a guild)
        raise NotRoleAssigner()
    if not any(role.id == ROLE_ASSIGNER_ROLE or role.id == ROLE_ASSIGNER_ADMIN_ROLE for role in user_or_member.roles):
        # assigner admin is okay too because they can assign themselves assigner
        raise NotRoleAssigner()
    if not re.search(ROLE_PATTERN, role.name):
        raise DisallowedRole()

@tree.command(guild=command_scope)
# it's okay to raise the rolenum limit,
# but keep in mind that there's a limit of 250 roles,
# so allowing higher numbers implies having non-contiguous channel numbers.
# OK if that's desired in the future, just not the case right now.
# https://support.discord.com/hc/en-us/articles/33694251638295-Discord-Account-Caps-Server-Caps-and-More
async def createrole(interaction: discord.Interaction, rolenum: discord.app_commands.Range[int, 1, 255]) -> None:
    """create PBP role of the given number (PBP admin only)"""
    new_role_name = f"{rolenum}-pbp"
    if not isinstance(interaction.user, discord.Member) or not any(role.id == ROLE_CREATOR_ROLE for role in interaction.user.roles):
        await interaction.response.send_message("You need to be a PBP admin to create roles")
        return
    if not interaction.guild:
        await interaction.response.send_message("Can't create a role without a server")
        return
    if any(role.name == new_role_name for role in interaction.guild.roles):
        # Discord's API and UI do allow multiple roles with the same name.
        # So we are choosing to add this additional limitation to avoid confusion.
        await interaction.response.send_message("A role with that name already exists")
        return

    if not (interaction.channel and interaction.channel.id == ROLE_CHANNEL) and not (isinstance(interaction.channel, discord.TextChannel) and re.search(MANAGED_CHANNEL_PATTERN, interaction.channel.name)):
        await interaction.response.send_message("For auditability reasons, please keep role commands to PBP game channels or the bot channel, thanks!")
        return

    try:
        await interaction.guild.create_role(name=new_role_name, mentionable=True, reason=f"{interaction.user.display_name} ({interaction.user.name}, ID {interaction.user.id}) requested")
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to create roles")
        return
    except discord.HTTPException:
        await interaction.response.send_message("Creating the role failed for some reason")
        return
    await interaction.response.send_message(f"{interaction.user.mention} created role {new_role_name}")

@tree.command(guild=command_scope)
async def host(interaction: discord.Interaction, member: discord.Member) -> None:
    """make the given member a PBP host (PBP admin only)"""
    await mod_hosts(interaction, member, 'add', 'to')

@tree.command(guild=command_scope)
async def unhost(interaction: discord.Interaction, member: discord.Member) -> None:
    """make the given member no longer a PBP host (PBP admin only)"""
    await mod_hosts(interaction, member, 'remove', 'from')

async def mod_hosts(interaction: discord.Interaction, member: discord.Member, verb: str, direction: str) -> None:
    if not isinstance(interaction.user, discord.Member) or not any(role.id == ROLE_ASSIGNER_ADMIN_ROLE for role in interaction.user.roles):
        await interaction.response.send_message(f"You need to be a PBP admin to {verb} players {direction} the host role")
        return
    if not (interaction.channel and interaction.channel.id == ROLE_CHANNEL) and not (isinstance(interaction.channel, discord.TextChannel) and re.search(MANAGED_CHANNEL_PATTERN, interaction.channel.name)):
        await interaction.response.send_message("For auditability reasons, please keep role commands to PBP game channels or the bot channel, thanks!")
        return
    if not interaction.guild:
        await interaction.response.send_message("Assigning roles doesn't work outside of a server")
        return
    if not (role := interaction.guild.get_role(ROLE_ASSIGNER_ROLE)):
        await interaction.response.send_message("Couldn't find the host role. Is the bot configured correctly?")
        return

    suffix = "d" if verb[-1] == "e" else "ed"

    if member.bot and direction == "add":
        await interaction.response.send_message("Bots cannot be hosts")
        return
    if member.system and direction == "add":
        await interaction.response.send_message("System users cannot be hosts")
        return

    try:
        await getattr(member, f"{verb}_roles")(role, reason=f"{interaction.user.display_name} ({interaction.user.name}, ID {interaction.user.id}) requested {verb}")
    except discord.Forbidden:
        if role.is_assignable():
            await interaction.response.send_message("I don't have permission to manage roles on this server")
        else:
            await interaction.response.send_message("I don't have permission to manage that role (it outranks me)")
        return
    except discord.HTTPException:
        await interaction.response.send_message(f"Something went wrong when trying to {verb} {direction} the role")
        return
    await interaction.response.send_message(f"{interaction.user.mention} {verb}{suffix} {member.mention} {direction} {role.name}")

def load_emojis(emojis: Iterable[discord.Emoji]) -> None:
    for e in emojis:
        if e.name in ('Energy1', 'Energy2', 'Energy3'):
            energy_to_discord_map[e.name] = str(e)
    for spirit in spirit_names:
        # wrap inner pattern in () so that something like A|B doesn't result in ^SpiritA|B (can match just B)
        # but also compile the inner pattern separately so that invalid syntax like )( doesn't suddenly become valid when wrapped
        r = re.compile(f'^Spirit.*({re.compile(spirit_disambig[spirit]).pattern if spirit in spirit_disambig else spirit})')
        possible_match = [e for e in emojis if r.match(e.name)]
        if len(possible_match) == 1:
            resolved_spirit_emoji[spirit] = possible_match[0]
        elif possible_match:
            LOG.warning(f'too many possible emoji for {spirit}, please disambiguate between {possible_match}')
        else:
            LOG.warning(f'missing emoji for {spirit}')

def adjust_msg(msg: str) -> str:
    if len(words := msg.split()) > 1:
        spirit_name = words[1]
        # we check that the first word is a heart because of potential message like:
        # Accelerated Rot returned to the deck
        # second word should not be replaced with Spreading Rot Renews the Earth's emoji
        heart = words[0] == '❤️' or len(words[0]) == 1 and words[0] != 'A'
        if heart and (spirit_emoji := resolved_spirit_emoji.get(spirit_name)):
            # replace only one occurrence (consider Earth playing Rumbling Earthquakes)
            msg = msg.replace(spirit_name, str(spirit_emoji), 1)
    try:
        # For now, don't want to replace the "started with N energy and now has M energy" messages,
        # because the message may be excessively long if the spirit has a lot.
        # so restricting it to gains/pays
        # With Blitz, you might pay negative energy. That's fine.
        match = re.search(r'''(?:gains|pays) -?(\d+) energy''', msg)
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

class GameLogEntry(TypedDict):
    text: str
    images: str
    spoiler: bool

async def relay_game(channel_id: int, log: Iterable[GameLogEntry]) -> None:
    channel = client.get_channel(channel_id)
    if not isinstance(channel, discord.abc.Messageable):
        LOG.warning(f"channel {channel_id} is {type(channel).__name__}, not sendable")
        return

    # https://docs.discord.com/developers/resources/message#create-message
    # content: "up to 2000 characters"
    maxlen = 2000

    combined_text: list[str] = []
    for entry in log:
        msg = adjust_msg(entry['text'])
        if len(msg) > maxlen:
            too_long = "... (message too long for Discord)"
            msg = msg[:maxlen - len(too_long)] + too_long
        if 'images' in entry:
            if len(combined_text) > 0:
                await channel.send('\n'.join(combined_text))
                combined_text = []
            images = entry['images']
            filenames = images.split(',')
            try:
                if len(filenames) > 1:
                    combine_images(filenames)
                    file_to_send = 'out.jpg'
                else:
                    file_to_send = filenames[0]
                if 'spoiler' in entry:
                    await channel.send(msg, file=discord.File(file_to_send, spoiler=entry['spoiler']))
                else:
                    await channel.send(msg, file=discord.File(file_to_send))
            except discord.Forbidden:
                await channel.send(msg + "\nCouldn't send the image. Make sure I have permission to attach files.")
            except FileNotFoundError:
                # If the host uploads two screenshots to the same slot before a message has been sent,
                # because we use django_cleanup, the first message's image will have been deleted by now.
                # We don't want the FileNotFoundError to prevent further messages in this batch from being sent.
                # TODO: After we've confirmed this is in fact what's happening
                #       we can probably delete this message, and just pass here.
                # Players probably don't need to be informed of this, so we can just pass.
                await channel.send(msg + " (the image has since been deleted)")
        else:
            if sum(len(m) + 1 for m in combined_text) + len(msg) > maxlen:
                # adding the new message would make the combined message too long
                await channel.send('\n'.join(combined_text))
                combined_text = []
            combined_text.append(msg)

    if len(combined_text) > 0:
        await channel.send('\n'.join(combined_text))
        combined_text = []

class GameLogBufferEntry(TypedDict):
    timestamp: datetime.datetime
    logs: list[GameLogEntry]

# Buffer up the log so we can send a group of related log messages together.
game_log_buffer: dict[int, GameLogBufferEntry] = {}

# We keep the last message sent to each channel,
# which helped us drop duplicate messages when the bot had a bug that would send them.
# This shouldn't be necessary now that we make sure to only create one relay_task,
# but we'll keep it in case there are other causes of duplicate messages.
last_message: dict[int, Any] = {}

class SIDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, enqueue: Callable[[int, str, Callable[[str], GameLogEntry]], None]):
        self.enqueue = enqueue

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, _addr: tuple[Any, int]) -> None:
        message = data.decode()
        LOG.msg("got message (socket)", message=message)
        j = json.loads(message)
        channel_id = int(j['channel'])
        self.enqueue(channel_id, message, lambda _: j)

async def logger() -> None:
    await client.wait_until_ready()

    correct_guild = False
    for guild in client.guilds:
        if list_guilds:
            LOG.msg(f"{guild.id} {guild.name}")
        if guild.id == GUILD_ID:
            load_emojis(guild.emojis)
            correct_guild = True
    if not correct_guild:
        LOG.warning("Not in the correct guild! Won't be able to use any spirit emojis!")

    T = TypeVar('T')
    def enqueue(channel_id: int, raw: T, parse: Callable[[T], GameLogEntry]) -> None:
        if channel_id in game_log_buffer:
            # our usage is:
            # * internal (entirely contained in bot.py)
            # * relative (we don't care about absolute times, only that a certain amount of time has passed)
            # therefore, we do not care to create timezone-aware datetime objects.
            # If ruff DTZ005 ever becomes enabled by default, we can ignore it.
            game_log_buffer[channel_id]['timestamp'] = datetime.datetime.now()
        else:
            game_log_buffer[channel_id] = {'timestamp': datetime.datetime.now(), 'logs': []}

        if last_message.get(channel_id) == raw:
            LOG.msg('drop duplicate message')
        else:
            game_log_buffer[channel_id]['logs'].append(parse(raw))
            last_message[channel_id] = raw

    async def dequeue() -> None:
        keys = list(game_log_buffer.keys())
        for channel_id in keys:
            if game_log_buffer[channel_id]['timestamp'] + datetime.timedelta(seconds=20) < datetime.datetime.now():
                LOG.msg('sending', channel_id=channel_id)
                logs = game_log_buffer[channel_id]['logs']
                del game_log_buffer[channel_id]
                await relay_game(channel_id, logs)

    if SOCKET_PATH:
        loop = asyncio.get_running_loop()

        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
        LOG.msg("trying to create", socket_path=SOCKET_PATH)
        _transport, _protocol = await loop.create_datagram_endpoint(
            lambda: SIDatagramProtocol(enqueue),
            local_addr=SOCKET_PATH,
            family=socket.AF_UNIX,
        )
        LOG.msg("listening", socket_path=SOCKET_PATH)

        while True:
            try:
                await dequeue()
                await asyncio.sleep(1)
            except Exception:
                LOG.exception("exception while dequeueing (socket)")

    else:
        redis_obj = await redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)
        pubsub = redis_obj.pubsub()
        await pubsub.psubscribe("log-relay:*")

        while True:
            try:
                async with asyncio.timeout(30):
                    message = await pubsub.get_message(ignore_subscribe_messages=True)
                    if message is not None:
                        LOG.msg("got message (Redis)", message=message)
                        channel_id = int(message['channel'].split(':')[1])
                        enqueue(channel_id, message, lambda msg: json.loads(msg['data']))

                    await dequeue()

                    await asyncio.sleep(1)
            except TimeoutError:
                LOG.msg('timeout')
            except Exception:
                LOG.exception("exception while dequeueing (Redis)")

if __name__ == '__main__':
    #combine_images(["./pbf/static/pbf/settle_into_huntinggrounds.jpg","./pbf/static/pbf/flocking_redtalons.jpg","./pbf/static/pbf/vigor_of_the_breaking_dawn.jpg","./pbf/static/pbf/vengeance_of_the_dead.jpg"])
    client.run(DISCORD_KEY)
