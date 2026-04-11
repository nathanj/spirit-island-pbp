import os
import sys
import discord
import requests
import asyncio
import datetime
import json
import structlog
import re
from dotenv import load_dotenv
from PIL import Image
from typing import Any, Callable, Iterable, NotRequired, TypeVar, TypedDict, Unpack

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
spirit_disambig = {
    'Earth': 'Vital.*Earth', # just "Earth" is ambiguous (Earthquakes)
    'Stone': 'Stones?(Unyielding|.*Defiance)', # just "Stone" is ambiguous (Rising Heat of Stone and Sand)
}

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

    client: discord.client.Client = Client() #type: ignore[assignment]
else:
    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

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
ROLE_CREATOR_ROLE = int(os.getenv('DISCORD_ROLE_CREATOR_ROLE', 925206661528948736))
GAME_URL = os.getenv('GAME_URL', 'si.bitcrafter.net')
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID', 846580409050857493))

match os.getenv('IPC_METHOD', 'redis'):
    case 'socket':
        import socket
        import threading
        SOCKET_PATH = os.getenv('SOCKET_PATH', 'si.sock')
    case 'redis':
        # for type-checking, this code path is statically checked regardless of IPC_METHOD,
        # and we don't want to force type-checking to install redis
        import redis.asyncio as redis #type: ignore[import-not-found]

        REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
        REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
        SOCKET_PATH = None #type: ignore[assignment]
    case _:
        raise ValueError('unknown IPC method')

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
    try:
        r = requests.post(f'http://{DJANGO_HOST}:{DJANGO_PORT}/api/game/{guid}/link/{after.id}')
    except Exception as e:
        await after.send(f"Couldn't link the channel to the game ({type(e).__name__}). The bot owner needs to check the logs for the site API and/or bot")
        raise
    LOG.msg(r)
    if r.status_code == 200:
        await after.send(f'Now relaying game log for {guid} to this channel. Good luck!')
        return True
    await after.send(f"Couldn't link the channel to the game ({r.status_code}). The bot owner needs to check the logs for the site API and/or bot")
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

@client.event
async def on_message(message: discord.Message) -> None:
    if message.author == client.user:
        return
    parts = message.content.split()
    if len(parts) >= 2 and parts[0] == '$follow':
        argument = parts[1]
        guid = match_game_url(argument)
        if not guid:
            await message.channel.send(f"That doesn't look like a game URL. Did you provide the full URL https://{GAME_URL}/game/abcd1234... ?")
            return
        if not await link_channel_to_game(message.channel, guid):
            return
        try:
            await message.pin(reason=f"{message.author.display_name} ({message.author.name}) requested")
        except discord.Forbidden:
            await message.channel.send("I don't have permission to pin messages, so you'll have to pin the link yourself, but I'll still relay game logs.")
        except discord.HTTPException:
            await message.channel.send("Failed to pin the message due to an HTTP error, so you'll have to pin the link yourself, but I'll still relay game logs.")
    if message.content.startswith('$help'):
        LOG.msg('$help called')
        if 'role' in message.content:
            text = "\n".join((
                "Roles and players can be specified by either @mentioning them or replying to a message that does.",
                "### Example 1",
                "message 1: $role @99-pbp @player1 @player2 @player3 @player4 you were randomly selected as the players for my game",
                "message 2 (reply to message 1): $unrole",
                "### Example 2 (specifying the role separately from the players by replying to the message)",
                "message 1: @player1 @player2 @player3 @player4 you were randomly selected as the players for my game",
                "message 2 (reply to message 1, the list of players): $role @99-pbp",
                "message 3 (reply to message 1, the list of players): $unrole @99-pbp",
                "### Example 3 (using $unrole as a reply to a reply so that you don't have to specify the role a second time)",
                "message 1: @player1 @player2 @player3 @player4 you were randomly selected as the players for my game",
                "message 2 (reply to message 1, the list of players): $role @99-pbp",
                "message 3 (reply to message 2, the $role message): $unrole",
            ))
            await message.channel.send(text)
            return
        elif 'admin' in message.content:
            text = "\n".join((
                "`$createrole N` to create the role N-pbp",
            ))
            await message.channel.send(text)
            return
        text = "\n".join((
            "[Github link](<https://github.com/nathanj/spirit-island-pbp>)",
            "",
            "Use `$topic (new topic)` to set the channel topic (set an update channel's topic to a game link to start sending updates to that channel)",
            "Use `$follow (yourgameurl)` for forum posts (where it's not possible to set a topic)",
            "Use `$unpin N` to unpin the last N messages",
            "Use `$delete` (reply to message) to delete a message (only messages posted by the bot)",
            "Use `$rename (new name)` to set the channel name",
            "Use `$role/$unrole` to add/remove players to/from a role (specify role and players by either @mentioning them or replying to a message that does)",
            "(aliases $addrole, $addplayer, $derole, $rmrole, $rmplayer, $removeplayer)",
            "`$help role` for more detailed help on roles",
            "`$help admin` to show admin-only commands",
        ))
        await message.channel.send(text)
    if message.content.startswith('$pin'):
        # Deprecated command, as hosts can now pin messages themselves.
        # For an unspecified transitionary period, still pin the message,
        # but educate hosts that they should do it themselves.
        # TODO: Remove command
        message_to_pin = await referenced_message(message, 'pin')
        # OK not to check if the message is already pinned, since pinning is idempotent.
        if message_to_pin and await act_on_message(message, message_to_pin, 'pin'):
            await report_success(message, 'pinned')
        await reply(message, 'The $pin command is deprecated and may be removed in the future. Hosts should pin messages themselves instead of using this command.')
    elif message.content.startswith('$unpin'):
        # Automatically unpinning a number of messages may be more convenient than manually unpinning each.
        # So, even after $pin is removed, we would still want to keep this $unpin N command.
        if len(parts) >= 2 and parts[1].isnumeric() and (num_to_unpin := int(parts[1])) > 0:
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
            await reply(message, 'You need to tell me how many messages to unpin, like $unpin 1 or $unpin 99')
    elif message.content.startswith('$delete'):
        message_to_delete = await referenced_message(message, 'delete')
        if not message_to_delete:
            return
        if message_to_delete.author != client.user:
            await message.channel.send("I only delete my own messages")
            return
        if message_to_delete.mentions:
            await message.channel.send("This message seems to mention some users, which means it may be an audit message. Deleting it may be unsafe.")
            return
        # delete doesn't accept a reason argument
        # doesn't matter anyway since we're deleting our own message,
        # which doesn't create an audit log entry
        if await act_on_message(message, message_to_delete, 'delete', reason=False):
            await report_success(message, 'deleted')
    elif message.content.startswith('$topic'):
        if not isinstance(message.channel, discord.TextChannel):
            if isinstance(message.channel, discord.StageChannel):
                await message.channel.send(f"This bot only supports setting the topic of text channels, not {type(message.channel).__name__}s")
            else:
                # ForumChannel have a topic in the API, but they are guidelines in the UI
                # Everything else doesn't have a topic at all.
                await message.channel.send(f"{type(message.channel).__name__}s don't have a topic")
            return
        try:
            # Expected (and so far observed) behaviour:
            # the bot will get an on_guild_channel_update for its own update,
            # thereby automatically following a game linked in the topic
            # (if present and the channel doesn't match NON_UPDATE_CHANNEL_PATTERN),
            # without needing to explicitly call link_channel_to_game here.
            await edit_channel(message, message.channel, 'Topic set', topic=" ".join(parts[1:]))
        except discord.Forbidden:
            await message.channel.send("I don't have permission to set the channel topic")
    elif message.content.startswith('$rename'):
        if not isinstance(message.channel, discord.TextChannel):
            await message.channel.send(f"This bot only supports renaming text channels, not {type(message.channel).__name__}s")
            return

        existing_name = message.channel.name

        if len(parts) == 1:
            # no argument given: try to clear the channel name.
            if '-' in existing_name:
                new_name = existing_name[:existing_name.index('-')]
            else:
                # this would result in no change, so no need to try editing
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
            # rename a b c becomes a-b-c
            new_suffix = '-'.join(parts[1:])
            if '-' in new_suffix and new_suffix[:new_suffix.index('-')] == existing_prefix:
                try:
                    await reply(message, f"You don't need to include the {existing_prefix}- prefix; it's automatically added")
                except discord.Forbidden:
                    # even if we don't have permission to send the message,
                    # we might still have permission to set the channel name, so still try that.
                    pass
                new_suffix = new_suffix[new_suffix.index('-') + 1:]
            new_name = existing_prefix if new_suffix == existing_prefix else f"{existing_prefix}-{new_suffix}"

        try:
            await edit_channel(message, message.channel, 'Channel renamed', name=new_name)
        except discord.Forbidden:
            await message.channel.send("I don't have permission to rename the channel")
    elif message.content.startswith('$role') or message.content.startswith('$addrole') or message.content.startswith('$addplayer'):
        await mod_players_and_roles(message, "add", "to", max_depth=1)
    elif message.content.startswith('$unrole') or message.content.startswith('$derole') or message.content.startswith('$rmrole') or message.content.startswith('$rmplayer') or message.content.startswith('$removeplayer'):
        # max depth 2 to allow this pattern:
        # message 1: @player1 @player2 @player3 are the players for this game
        # message 2 (reply to 1) $role @1-pbp
        # message 3 (reply to 2) $unrole
        await mod_players_and_roles(message, "remove", "from", max_depth=2)
    elif message.content.startswith('$createrole'):
        if len(parts) >= 2 and parts[1].isnumeric() and (rolenum := int(parts[1])) > 0:
            new_role_name = f"{rolenum}-pbp"
            if not isinstance(message.author, discord.Member) or not any(role.id == ROLE_CREATOR_ROLE for role in message.author.roles):
                await reply(message, "You aren't allowed to create roles")
                return
            if not message.guild:
                await message.channel.send("Can't create a role without a server")
                return
            if any(role.name == new_role_name for role in message.guild.roles):
                # Discord's API and UI do allow multiple roles with the same name.
                # So we are choosing to add this additional limitation to avoid confusion.
                await message.channel.send("A role with that name already exists")
                return

            if message.channel.id != ROLE_CHANNEL and not (isinstance(message.channel, discord.TextChannel) and re.search(MANAGED_CHANNEL_PATTERN, message.channel.name)):
                await message.channel.send("For auditability reasons, please keep role commands to PBP game channels or the bot channel, thanks!")
                return

            try:
                await message.guild.create_role(name=new_role_name, mentionable=True, reason=f"{message.author.display_name} ({message.author.name}) requested")
            except discord.Forbidden:
                await message.channel.send("I don't have permission to create roles")
                return
            except discord.HTTPException:
                await message.channel.send("Creating the role failed for some reason")
                return
            await message.channel.send(f"<@{message.author.id}> created role {new_role_name}")
        else:
            await reply(message, 'You need to tell me just the number of the role to create, no suffixes or any characters other than numbers')

async def mod_players_and_roles(message: discord.Message, verb: str, direction: str, max_depth: int = 1) -> None:
    if message.channel.id != ROLE_CHANNEL and not (isinstance(message.channel, discord.TextChannel) and re.search(MANAGED_CHANNEL_PATTERN, message.channel.name)):
        await message.channel.send("For auditability reasons, please keep role commands to PBP game channels or the bot channel, thanks!")
        return

    # players: take the union of all them
    # role: message shallower in the chain wins
    players = set()
    role = None
    for (user_mentions, maybe_role_mention) in await chain_mentioned_users_and_roles(message, max_depth=max_depth):
        players.update(user_mentions)
        if not role and maybe_role_mention:
            role = maybe_role_mention

    if not players:
        if message.reference:
            await message.channel.send(f"The message you replied to didn't @mention any players to {verb}")
        else:
            await message.channel.send(f"You need to @mention the player(s) to {verb}, OR reply to a message that @mentions the players")
        return

    if not role:
        if not message.role_mentions:
            await message.channel.send(f"You need to @mention a role to {verb} players {direction}, OR reply to a message that @mentions the role")
        else:
            # This message is only shown if the command message has > 1 role,
            # which means it will miss any replies with > 1 role.
            # This is probably fine.
            await message.channel.send(f"You need to specify only one role to {verb} players {direction}, not multiple")
        return

    try:
        assert_allowed_role_manager(message, role)
    except NotRoleAssigner:
        await reply(message, "You aren't allowed to manage roles (ask a PBP admin to give you the role that allows it)")
        return
    except DisallowedRole:
        await reply(message, "I only manage roles related to PBP, which that role doesn't appear to be")
        return

    if not message.guild:
        await message.channel.send("Assigning roles doesn't work outside of a server")
        return

    try:
        # For referenced messages, there may be Users instead of Members, so we need to convert them all to Members,
        # as only Member has add_role / remove_role
        members = await resolve_members(message.guild, players)
    except discord.Forbidden:
        await message.channel.send("I don't have permission to determine the players in that message (if this error happens, try @mentioning the players directly in the message rather than replying to a message)")
        return
    except (discord.HTTPException, TypeError):
        await message.channel.send("Something went wrong when determining the players in that message (if this error happens, try @mentioning the players directly in the message rather than replying to a message)")
        return

    try:
        # role.members is always empty unless we have the members intent
        # previously_in_role = len(role.members)
        for member in members:
            # This should have been asserted above for a friendlier message,
            # but intentionally asserting it a second time in case a refactor accidentally removes the above assert or makes it no longer exit.
            assert_allowed_role_manager(message, role)
            await getattr(member, f"{verb}_roles")(role, reason=f"{message.author.display_name} ({message.author.name}) requested {verb}")
    except discord.Forbidden:
        if role.is_assignable():
            await reply(message, "I don't have permission to manage roles on this server")
        else:
            await reply(message, "I don't have permission to manage that role (it outranks me)")
        return

    suffix = "d" if verb[-1] == "e" else "ed"
    name_list = ', '.join(member.display_name for member in members)
    await message.channel.send(f"<@{message.author.id}> {verb}{suffix} {len(members)}/{len(players)} player{'' if len(players) == 1 else 's'} {direction} {role.name}: {name_list}")

# players and roles referenced in a potential message chain, up to the maximum depth (number of references to follow from the original)
# 0 means just the message passed, 1 means the message passed and its reference, etc.
# No error if the chain has fewer references than the max.
async def chain_mentioned_users_and_roles(message: discord.Message, max_depth: int = 1) -> list[tuple[list[discord.User | discord.Member], discord.Role | None]]:
    result = [(message.mentions, message.role_mentions[0] if len(message.role_mentions) == 1 else None)] if max_depth >= 0 else []
    if max_depth <= 0:
        return result

    if message.reference and max_depth >= 1:
        if isinstance(message.reference.resolved, discord.Message):
            refmsg = message.reference.resolved
        elif isinstance(message.reference.resolved, discord.DeletedReferencedMessage):
            # Silently ignore because it's okay to reply to a reply to a deleted message.
            return result
        else:
            try:
                if not message.reference.message_id:
                    # see docs for when this can be None:
                    # https://discordpy.readthedocs.io/en/latest/api.html#discord.MessageReference.message_id
                    return result
                refmsg = await message.channel.fetch_message(message.reference.message_id)
            except discord.Forbidden:
                await message.channel.send("I don't have permission to read previous messages")
                return result
        # TODO: O(N^2) because each level extends itself with all the info from the lower ones.
        # okay for now because of small N, but consider deque for larger N
        result.extend(await chain_mentioned_users_and_roles(refmsg, max_depth - 1))
    return result

async def resolve_members(guild: discord.Guild, players: Iterable[discord.User | discord.Member]) -> list[discord.Member]:
    resolved = []
    for player in players:
        if isinstance(player, discord.Member):
            resolved.append(player)
        elif isinstance(player, discord.User):
            try:
                resolved.append(await guild.fetch_member(player.id))
            except discord.NotFound:
                # e.g. if the member has left the guild since they were mentioned in the message.
                pass
        else:
            raise TypeError(f"{player} neither a member nor a user")
    return resolved

def assert_allowed_role_manager(message: discord.Message, role: discord.Role) -> None:
    if not isinstance(message.author, discord.Member):
        # author can be User or Member; User has no roles (left the guild, or message isn't in a guild)
        raise NotRoleAssigner()
    if not any(role.id == ROLE_ASSIGNER_ROLE for role in message.author.roles):
        raise NotRoleAssigner()
    if not re.search(ROLE_PATTERN, role.name):
        raise DisallowedRole()

class ChannelChanges(TypedDict):
    name: NotRequired[str]
    topic: NotRequired[str]

async def edit_channel(message: discord.Message, channel: discord.TextChannel, success_msg: str, **changes: Unpack[ChannelChanges]) -> None:
    # Ideally the guild uses permissions to restrict what the bot can do,
    # but defence in depth is desirable for such sensitive operations.
    if not re.search(MANAGED_CHANNEL_PATTERN, channel.name):
        await reply(message, "I only manage PBP channels, which this channel doesn't appear to be")
        return

    edit_task = asyncio.create_task(channel.edit(**changes, reason=f"{message.author.display_name} ({message.author.name}) requested"))

    async def check_task_completion() -> None:
        await asyncio.sleep(3)
        # Didn't find a way to introspect the channel edit task to see its status (time left to wait)
        # so best we can do is check whether it's done.
        if edit_task.done():
            return
        await reply(message, "Got rate-limited by Discord (Discord limits the bot to 2 changes to the same channel within 10 minutes), automatically retrying when possible. Thanks for your patience.")

    check_task = asyncio.create_task(check_task_completion())
    await edit_task
    await report_success(message, success_msg, noun=None)
    await check_task

async def referenced_message(message: discord.Message, command: str) -> discord.Message | None:
    if message.reference:
        try:
            if not message.reference.message_id:
                # https://discordpy.readthedocs.io/en/latest/api.html#discord.MessageReference.message_id
                await message.channel.send(f"Can't {command} that kind of message")
                return None
            return await message.channel.fetch_message(message.reference.message_id)
        except discord.Forbidden:
            await message.channel.send("I don't have permission to read previous messages")
            return None
    await message.channel.send(f"You need to reply to a message to use ${command}")
    return None

# note that since the bot refuses to delete its own messages that mention a user
# (as they may be audit messages),
# and a reply mentions the user,
# using reply will prevent the bot from deleting this message.
# Thus, generally we prefer to use it only in situations where:
# * the user did something they're not allowed to
#   (the record of this should not be deleted)
# * they did something but it's important to notify them they can do it a better way
#   (it'd be okay to delete these,
#   but the worth of notifying them exceeds the cost of making them undeletable)
async def reply(message: discord.Message, response: str) -> None:
    try:
        await message.reply(response)
    except discord.Forbidden:
        # reply requires View Message Log, which this bot may not have permission to.
        # Try to send a message to the channel, as we may have permission to do that instead.
        await message.channel.send(response)
        # That may in turn raise discord.Forbidden if we're not allowed to send a message either,
        # but if this is the case, there's not much that can be done.

async def act_on_message(command_message: discord.Message, message_to_modify: discord.Message, verb: str, reason: bool = True) -> bool:
    try:
        kwargs = {'reason': f"{command_message.author.display_name} ({command_message.author.name}) requested"} if reason else {}
        await getattr(message_to_modify, verb)(**kwargs)
        return True
    except discord.Forbidden:
        await command_message.channel.send(f"I don't have permission to {verb} messages.")
    except discord.HTTPException:
        await command_message.channel.send(f"Failed to {verb} the message due to an HTTP error.")
    return False

async def report_success(command_message: discord.Message, verb: str, noun: str | None = 'Message') -> None:
    try:
        await command_message.add_reaction('✅')
    except discord.Forbidden:
        await command_message.channel.send(f"{noun} {verb}!" if noun else f"{verb}!")

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
            LOG.warn(f'too many possible emoji for {spirit}, please disambiguate between {possible_match}')
        else:
            LOG.warn(f'missing emoji for {spirit}')

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
        LOG.warn(f"channel {channel_id} is {type(channel).__name__}, not sendable")
        return

    combined_text: list[str] = []
    for entry in log:
        msg = adjust_msg(entry['text'])
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
                if 'spoiler' in entry.keys():
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
        self.msgbuflock = threading.Lock()
        self.enqueue = enqueue

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, _addr: tuple[Any, int]) -> None:
        message = data.decode()
        LOG.msg("got message (socket)", message=message)
        j = json.loads(message)
        channel_id = int(j['channel'])
        with self.msgbuflock:
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
        LOG.warn("Not in the correct guild! Won't be able to use any spirit emojis!")

    T = TypeVar('T')
    def enqueue(channel_id: int, raw: T, parse: Callable[[T], GameLogEntry]) -> None:
        if channel_id in game_log_buffer:
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
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: SIDatagramProtocol(enqueue),
            local_addr=SOCKET_PATH,
            family=socket.AF_UNIX,
        )
        LOG.msg("listening", socket_path=SOCKET_PATH)

        while True:
            try:
                with protocol.msgbuflock:
                    await dequeue()
                await asyncio.sleep(1)
            except Exception as ex:
                LOG.exception(ex)

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
            except asyncio.TimeoutError:
                LOG.msg('timeout')
            except Exception as ex:
                LOG.exception(ex)

if __name__ == '__main__':
    #combine_images(["./pbf/static/pbf/settle_into_huntinggrounds.jpg","./pbf/static/pbf/flocking_redtalons.jpg","./pbf/static/pbf/vigor_of_the_breaking_dawn.jpg","./pbf/static/pbf/vengeance_of_the_dead.jpg"])
    client.run(DISCORD_KEY)
