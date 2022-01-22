from django.shortcuts import get_object_or_404
from typing import List
from ninja import NinjaAPI
from ninja import ModelSchema

from .models import Game, GameLog

api = NinjaAPI()

class GameSchema(ModelSchema):
    class Config:
        model = Game
        model_fields = ['id', 'turn', 'name']

class GameLogSchema(ModelSchema):
    class Config:
        model = GameLog
        model_fields = ['id', 'date', 'text']

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
