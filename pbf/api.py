from django.shortcuts import get_object_or_404
from ninja import NinjaAPI
from ninja import Field, ModelSchema
import os
import ipaddress
from .models import Card, Game, GameLog, GamePlayer, GamePlayerImpendingWithEnergy, Presence, Spirit

api = NinjaAPI()

class SpiritSchema(ModelSchema):
    class Meta:
        model = Spirit
        fields = ['id', 'name']

class CardSchema(ModelSchema):
    class Meta:
        model = Card
        fields = ['id', 'name']

class ImpendingSchema(ModelSchema):
    card: CardSchema
    class Meta:
        model = GamePlayerImpendingWithEnergy
        fields = ['energy', 'in_play', 'this_turn']

class PresenceSchema(ModelSchema):
    class Meta:
        model = Presence
        fields = ['opacity', 'energy', 'elements']

class GamePlayerSchema(ModelSchema):
    spirit: SpiritSchema
    hand: list[CardSchema] = []
    discard: list[CardSchema] = []
    play: list[CardSchema] = []
    selection: list[CardSchema] = []
    days: list[CardSchema] = []
    scenario: list[CardSchema] = []
    healing: list[CardSchema] = []
    impending: list[ImpendingSchema] = Field([], alias="gameplayerimpendingwithenergy_set")
    presence: list[PresenceSchema] = Field([], alias="presence_set")
    class Meta:
        model = GamePlayer
        fields = [
                'name', 'color', 'aspect',
                'ready', 'paid_this_turn', 'gained_this_turn',
                'energy', 'last_unready_energy', 'last_ready_energy',
                'bargain_paid_this_turn', 'bargain_cost_per_turn',
                'temporary_sun', 'temporary_moon', 'temporary_fire', 'temporary_air', 'temporary_water', 'temporary_earth', 'temporary_plant', 'temporary_animal',
                'permanent_sun', 'permanent_moon', 'permanent_fire', 'permanent_air', 'permanent_water', 'permanent_earth', 'permanent_plant', 'permanent_animal',
                'spirit_specific_resource', 'spirit_specific_per_turn_flags',
                ]

class GameSchema(ModelSchema):
    class Meta:
        model = Game
        fields = ['id', 'name', 'discord_channel', 'scenario']

class GameDetailSchema(ModelSchema):
    players: list[GamePlayerSchema] = Field([], alias="gameplayer_set")
    minor_deck: list[CardSchema] = []
    major_deck: list[CardSchema] = []
    discard_pile: list[CardSchema] = []
    class Meta:
        model = Game
        # we've not exported the screenshots, because it's not obvious how we would do it.
        fields = ['id', 'name', 'discord_channel', 'scenario', 'always_suffix_screenshot']

class GameLogSchema(ModelSchema):
    class Meta:
        model = GameLog
        fields = ['id', 'date', 'text', 'spoiler_text', 'images']

class InvalidIP(Exception):
    pass

def get_ip(request):
    if 'HTTP_X_FORWARDED_FOR' in request.META:
        return request.META["HTTP_X_FORWARDED_FOR"]
    else:
        return request.META["REMOTE_ADDR"]

@api.exception_handler(InvalidIP)
def on_invalid_ip(request, exc):
    ip = get_ip(request)
    return api.create_response(request, {"detail": f"Unauthenticated source IP: {ip}"}, status=401)

def ip_whitelist(request):
    ALLOWED_IPS = (os.getenv('ALLOWED_IPS') or '127.0.0.1,::1').split(',')
    ip_networks = [ipaddress.ip_network(allowed_ip.strip()) for allowed_ip in ALLOWED_IPS]
    ip = get_ip(request)
    for network in ip_networks:
        if ipaddress.ip_address(ip) in network:
            return ip
    raise InvalidIP

@api.get("/ip", auth=ip_whitelist)
def ip(request):
    return f"Authenticated client, IP = {request.auth}"

@api.post("/game/{game_id}/link/{channel_id}", auth=ip_whitelist)
def game_link(request, game_id, channel_id):
    game = get_object_or_404(Game, pk=game_id)
    Game.objects.filter(discord_channel=channel_id).update(discord_channel='')
    game.discord_channel = channel_id
    game.save()
    return "ok"

@api.get("/game", response=list[GameSchema])
def game_list(request):
    return Game.objects.all()

@api.get("/game/{game_id}", response=GameDetailSchema)
def game(request, game_id):
    return get_object_or_404(Game, pk=game_id)

@api.get("/game/{game_id}/log", response=list[GameLogSchema])
def gamelogs(request, game_id, after: int | None = None):
    game = get_object_or_404(Game, pk=game_id)
    if after is None:
        return game.gamelog_set.all()
    else:
        return game.gamelog_set.filter(pk__gt=after)
