import json
from random import shuffle

from django.db import transaction
from django.forms import ModelForm
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from .models import *

class GameForm(ModelForm):
    class Meta:
        model = Game
        fields = ['screenshot']

def with_log_trigger(response):
    response['HX-Trigger'] = 'newLog'
    return response

def home(request):
    games = Game.objects.all()
    return render(request, 'index.html', { 'games': games })

def view_screenshot(request, filename):
    with open(f'screenshot/{filename}', mode='rb') as f:
        return HttpResponse(f.read(), content_type='image/jpeg')

def new_game(request):
    game = Game(name='My Game')
    game.save()
    game.minor_deck.set(Card.objects.filter(type=Card.MINOR))
    game.major_deck.set(Card.objects.filter(type=Card.MAJOR))
    return redirect(reverse('view_game', args=[game.id]))

spirit_presence = {
        'Bringer': ((465,160,1.0), (535,160,1.0), (605,160,1.0), (675,160,1.0), (745,160,1.0), (815,160,1.0), (465,260,1.0), (535,260,1.0), (605,260,1.0), (675,260,1.0), (745,260,1.0)),
        'Stone': ((465,155,1.0), (538,155,1.0), (611,155,1.0), (684,155,1.0), (757,155,1.0), (830,155,1.0), (465,257,1.0), (538,257,1.0), (611,257,1.0), (684,257,1.0), (757,257,1.0)),
        'Serpent': ((457,158,1.0), (527,158,1.0), (597,158,1.0), (732,158,1.0), (802,158,1.0), (872,158,1.0),
            (667,208,1.0), 
            (457,258,1.0), (527,258,1.0), (597,258,1.0), (742,258,1.0), (812,258,1.0),
            (83,487,1.0), (153,487,1.0), (223,487,1.0),
            (50,547,1.0), (120,547,1.0), (190,547,1.0),
            ),
        }


@transaction.atomic
def add_player(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    colors = {
            'red': '#fc3b5a',
            'peach': '#ffd585',
            'purple': '#715dff',
            'pink': '#e67bfe',
            'orange': '#d15a01',
            'green': '#0d9501',
            }
    color_values = list(colors.values())
    for player in game.gameplayer_set.all():
        color_values.remove(player.color)
    shuffle(color_values)
    spirit_id = int(request.POST['spirit'])
    spirit = get_object_or_404(Spirit, pk=spirit_id)
    gp = GamePlayer(game=game, spirit=spirit, notes="You can add notes here...\ntop:1 bottom:1", color=color_values[0])
    gp.save()
    try:
        for presence in spirit_presence[spirit.name]:
            gp.presence_set.create(left=presence[0], top=presence[1], opacity=presence[2])
    except:
        pass
    gp.hand.set(Card.objects.filter(spirit=spirit))
    return redirect(reverse('view_game', args=[game.id]))

def view_game(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    old_screenshot = game.screenshot
    if request.method == 'POST':
        form = GameForm(request.POST, request.FILES, instance=game)
        if form.is_valid():
            # file is saved
            form.save()
            #if old_screenshot is None:
            game.gamelog_set.create(text=f'New screenshot uploaded.')
            #else:
            #    game.gamelog_set.create(text=f'New screenshot uploaded. Old: {old_screenshot}')
            return redirect(reverse('view_game', args=[game.id]))
    else:
        form = GameForm(instance=game)

    spirits = Spirit.objects.order_by('name').all()
    return render(request, 'game.html', { 'game': game, 'form': form, 'spirits': spirits })

@transaction.atomic
def draw_card(request, game_id, type):
    game = get_object_or_404(Game, pk=game_id)
    if type == 'minor':
        deck = game.minor_deck
    else:
        deck = game.major_deck

    cards = list(deck.all())
    shuffle(cards)
    card = cards[0]
    deck.remove(card)

    game.gamelog_set.create(text=f'Host drew {card.name}')

    return redirect(reverse('view_game', args=[game.id]))

@transaction.atomic
def gain_power(request, player_id, type, num):
    player = get_object_or_404(GamePlayer, pk=player_id)
    if type == 'minor':
        deck = player.game.minor_deck
    else:
        deck = player.game.major_deck

    cards = list(deck.all())
    shuffle(cards)
    selection = cards[:num]
    for c in selection:
        deck.remove(c)

    player.selection.set(selection)

    cards_str = ", ".join([str(card) for card in selection])
    player.game.gamelog_set.create(text=f'{player.spirit.name} gains a {type} power. Choices: {cards_str}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def choose_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.selection, pk=card_id)
    player.selection.clear()
    player.hand.add(card)

    player.game.gamelog_set.create(text=f'{player.spirit.name} gains {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def choose_card2(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.selection, pk=card_id)
    player.selection.remove(card)
    player.hand.add(card)

    player.game.gamelog_set.create(text=f'{player.spirit.name} gains {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def play_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.hand, pk=card_id)
    player.play.add(card)
    player.hand.remove(card)

    player.game.gamelog_set.create(text=f'{player.spirit.name} plays {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def unplay_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.play, pk=card_id)
    player.hand.add(card)
    player.play.remove(card)

    player.game.gamelog_set.create(text=f'{player.spirit.name} unplays {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def forget_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    try:
        card = player.hand.get(pk=card_id)
        player.hand.remove(card)
    except:
        pass
    try:
        card = player.play.get(pk=card_id)
        player.play.remove(card)
    except:
        pass
    try:
        card = player.discard.get(pk=card_id)
        player.discard.remove(card)
    except:
        pass

    player.game.gamelog_set.create(text=f'{player.spirit.name} forgets {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))


@transaction.atomic
def reclaim_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.discard, pk=card_id)
    player.hand.add(card)
    player.discard.remove(card)

    player.game.gamelog_set.create(text=f'{player.spirit.name} reclaims {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def reclaim_all(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    cards = list(player.discard.all())
    for card in cards:
        player.hand.add(card)
    player.discard.clear()

    player.game.gamelog_set.create(text=f'{player.spirit.name} reclaims all')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def discard_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    try:
        card = player.play.get(pk=card_id)
        player.discard.add(card)
        player.play.remove(card)
    except:
        pass
    try:
        card = player.hand.get(pk=card_id)
        player.discard.add(card)
        player.hand.remove(card)
    except:
        pass

    player.game.gamelog_set.create(text=f'{player.spirit.name} discards {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def ready(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.ready = not player.ready
    player.save()

    if player.ready:
        player.game.gamelog_set.create(text=f'{player.spirit.name} is ready')
    else:
        player.game.gamelog_set.create(text=f'{player.spirit.name} is not ready')

    if player.game.gameplayer_set.filter(ready=False).count() == 0:
        player.game.gamelog_set.create(text=f'All spirits are ready!')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def notes(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.notes = request.POST['notes']
    player.save()

    return HttpResponse("")

@transaction.atomic
def unready(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    for player in game.gameplayer_set.all():
        player.ready = False
        player.save()

    player.game.gamelog_set.create(text=f'All spirits marked not ready')

    return redirect(reverse('view_game', args=[game.id]))

@transaction.atomic
def time_passes(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    for player in game.gameplayer_set.all():
        cards = player.play.all()
        for card in cards:
            player.discard.add(card)
        player.play.clear()
        player.ready = False
        player.save()
    game.turn += 1
    game.save()

    player.game.gamelog_set.create(text=f'Time passes...')
    player.game.gamelog_set.create(text=f'-- Turn {game.turn} --')

    return redirect(reverse('view_game', args=[game.id]))


@transaction.atomic
def change_energy(request, player_id, amount):
    amount = int(amount)
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.energy += amount
    player.save()

    if amount > 0:
        player.game.gamelog_set.create(text=f'{player.spirit.name} gains {amount} energy ({player.energy})')
    else:
        player.game.gamelog_set.create(text=f'{player.spirit.name} pays {-amount} energy ({player.energy})')

    return with_log_trigger(render(request, 'energy.html', {'player': player}))

@transaction.atomic
def toggle_presence(request, player_id):
    j = json.loads(request.body)
    print(j)
    player = get_object_or_404(GamePlayer, pk=player_id)
    presence = get_object_or_404(player.presence_set, left=j['left'], top=j['top'])
    presence.opacity = abs(1.0 - presence.opacity)
    presence.save()

    return HttpResponse("")


def tab(request, game_id, player_id):
    game = get_object_or_404(Game, pk=game_id)
    player = get_object_or_404(GamePlayer, pk=player_id)
    return render(request, 'tabs.html', {'game': game, 'player': player})

def game_logs(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    return render(request, 'logs.html', {'game': game})

