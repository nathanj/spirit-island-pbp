from django.shortcuts import get_object_or_404
from typing import List
from ninja import NinjaAPI
from ninja import ModelSchema

from .models import Game, GameLog

api = NinjaAPI()

class GameSchema(ModelSchema):
    class Config:
        model = Game
        model_fields = ['id', 'turn', 'name', 'discord_channel']

class GameLogSchema(ModelSchema):
    class Config:
        model = GameLog
        model_fields = ['id', 'date', 'text', 'images']

def get_ip(request):
    if 'HTTP_X_FORWARDED_FOR' in request.META:
        return request.META["HTTP_X_FORWARDED_FOR"]
    else:
        return request.META["REMOTE_ADDR"]

def ip_whitelist(request):
    if get_ip(request) == "127.0.0.1":
        return "127.0.0.1"

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

@api.get("/game", response=List[GameSchema])
def game(request):
    return Game.objects.all()

@api.get("/game/{game_id}", response=GameSchema)
def game(request, game_id):
    return get_object_or_404(Game, pk=game_id)

@api.get("/game/{game_id}/log", response=List[GameLogSchema])
def gamelogs(request, game_id, after: int = None):
    game = get_object_or_404(Game, pk=game_id)
    if after is None:
        return game.gamelog_set.all()
    else:
        return game.gamelog_set.filter(pk__gt=after)
