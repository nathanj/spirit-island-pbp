import json
from random import shuffle

from django.db import transaction
from django.forms import ModelForm
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from .models import *

import redis

redis_client = redis.StrictRedis(host='localhost', port=6379, db=1)

def add_log_msg(game, text, images=None):
    game.gamelog_set.create(text=text, images=images)
    if len(game.discord_channel) > 0:
        j = {'text': text}
        if images is not None:
            j['images'] = images
        redis_client.publish(f'log-relay:{game.discord_channel}', json.dumps(j))

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
        'Bringer': ((452,155,1.0), (522,155,1.0), (592,155,1.0), (662,155,1.0), (732,155,1.0), (802,155,1.0),
            (452,255,1.0), (522,255,1.0), (592,255,1.0), (662,255,1.0), (732,255,1.0)),
        'Downpour': ((434,205,1.0), (506,205,1.0), (578,205,1.0), (650,205,1.0), (720,205,1.0), (790,205,1.0), (860,205,1.0),
            (430,295,1.0), (500,295,1.0), (575,295,1.0), (645,295,1.0), (720,295,1.0)),
        'Earth': ((447,158,1.0), (513,158,1.0), (582,158,1.0), (649,158,1.0), (719,158,1.0),
            (445,253,1.0), (515,253,1.0), (580,253,1.0), (650,253,1.0), (720,253,1.0)),
        'Fangs': ((447,158,1.0), (513,158,1.0), (582,158,1.0), (649,158,1.0), (719,158,1.0), (789,158,1.0),
            (445,253,1.0), (515,253,1.0), (580,253,1.0), (650,253,1.0), (720,253,1.0)),
        'Finder': ((450,146,1.0), (582,146,1.0), (717,146,1.0), (849,146,1.0),
            (519,208,1.0), (649,208,1.0), (779,208,1.0),
            (449,273,1.0), (583,273,1.0), (716,273,1.0), (848,273,1.0)),
        'Fractured': ((447,203,1.0), (518,203,1.0), (592,203,1.0), (664,203,1.0), (739,203,1.0),
            (447,293,1.0), (521,293,1.0), (593,293,1.0), (665,293,1.0), (740,293,1.0),
            (0,0,0.0), (60,0,0.0), (120,0,0.0), (180,0,0.0), (240,0,0.0),
            (0,60,0.0), (60,60,0.0), (120,60,0.0), (180,60,0.0), (240,60,0.0),
            ),
        'Green': ((447,163,1.0), (513,163,1.0), (582,163,1.0), (649,163,1.0), (719,163,1.0), (789,163,1.0),
            (445,258,1.0), (515,258,1.0), (580,258,1.0), (650,258,1.0), (720,258,1.0)),
        'Lightning': ((445,156,1.0), (511,156,1.0), (580,156,1.0), (647,156,1.0), (715,156,1.0), (783,156,1.0), (851,156,1.0),
            (443,253,1.0), (513,253,1.0), (578,253,1.0), (648,253,1.0)),
        'Keeper': ((445,156,1.0), (511,156,1.0), (580,156,1.0), (647,156,1.0), (715,156,1.0), (783,156,1.0), (851,156,1.0),
            (443,253,1.0), (513,253,1.0), (578,253,1.0), (648,253,1.0), (718,253,1.0)),
        'Vengeance': ((447,146,1.0), (518,146,1.0), (592,146,1.0), (664,146,1.0),
            (447,250,1.0), (521,250,1.0), (592,250,1.0), (666,250,1.0), (738,250,1.0), (810,250,1.0)),
        'Lure': ((447,148,1.0), (517,148,1.0), (590,148,1.0), (661,148,1.0), (743,148,1.0),
            (447,248,1.0), (519,248,1.0), (590,248,1.0), (664,248,1.0), (736,248,1.0)),
        'Minds': ((448,148,1.0), (519,148,1.0), (593,148,1.0), (665,148,1.0), (738,148,1.0), (811,148,1.0),
            (448,251,1.0), (520,251,1.0), (591,251,1.0), (665,251,1.0), (737,251,1.0), (809,251,1.0), ),
        'Mist': ((431,148,1.0), (502,148,1.0), (576,148,1.0), (648,148,1.0),
            (431,251,1.0), (503,251,1.0), (574,251,1.0), (648,251,1.0), (720,251,1.0), (792,251,1.0), (865,251,1.0), ),
        'Ocean': ((445,233,1.0), (513,233,1.0), (580,233,1.0), (648,233,1.0), (718,233,1.0), (788,233,1.0),
            (445,318,1.0), (513,318,1.0), (584,318,1.0), (648,318,1.0), (718,318,1.0)),
        'River': ((437,158,1.0), (503,158,1.0), (572,158,1.0), (639,158,1.0), (707,158,1.0), (775,158,1.0),
            (435,253,1.0), (505,253,1.0), (570,253,1.0), (640,253,1.0), (708,253,1.0), (776,253,1.0)),
        'Shadows': ((447,158,1.0), (513,158,1.0), (582,158,1.0), (649,158,1.0), (717,158,1.0),
            (445,253,1.0), (515,253,1.0), (580,253,1.0), (650,253,1.0), (718,253,1.0)),
        'Shifting': ((430,150,1.0), (501,150,1.0), (573,150,1.0), (642,150,1.0), (713,150,1.0), (783,150,1.0), (853,150,1.0),
            (431,246,1.0), (502,246,1.0), (569,246,1.0), (641,246,1.0)),
        'Starlight': (
            (305,111,1.0),(385,111,0.0),(485,111,0.0),(565,111,0.0),
            (305,193,1.0),(385,193,0.0),(485,193,0.0),(565,193,0.0),
            (292,263,1.0),(366,263,1.0),(443,263,0.0),(517,263,0.0),(577,263,0.0),
            (292,353,1.0),(366,353,1.0),(443,353,0.0),(517,353,0.0),(577,353,0.0),
            (363,450,1.0),(435,450,1.0),(507,450,1.0),(579,450,1.0),
            (363,536,1.0),(435,536,1.0),(507,536,1.0),(579,536,1.0),

            ),
        'Stone': ((450,148,1.0), (523,148,1.0), (596,148,1.0), (669,148,1.0), (742,148,1.0), (815,148,1.0),
            (450,250,1.0), (523,250,1.0), (596,250,1.0), (669,250,1.0), (742,250,1.0)),
        'Thunderspeaker': ((443,155,1.0), (512,155,1.0), (583,155,1.0), (650,155,1.0), (719,155,1.0),
            (444,245,1.0), (513,245,1.0), (583,245,1.0), (650,245,1.0), (719,245,1.0), (787,245,1.0)),
        'Trickster': ((446,138,1.0), (518,138,1.0), (592,138,1.0), (663,138,1.0), (736,138,1.0),
            (447,227,1.0), (519,227,1.0), (592,227,1.0), (663,227,1.0), (736,227,1.0), (808,227,1.0)),
        'Volcano': ((428,140,1.0), (500,140,1.0), (574,140,1.0), (645,140,1.0), (718,140,1.0),
            (429,227,1.0), (501,227,1.0), (574,227,1.0), (645,227,1.0), (718,227,1.0), (790,227,1.0), (862,227,1.0)),
        'Wildfire': ((444,155,1.0), (513,155,1.0), (584,155,1.0), (653,155,1.0), (725,155,1.0),
            (443,253,1.0), (513,253,1.0), (584,253,1.0), (653,253,1.0), (724,253,1.0)),
        'Serpent': ((442,151,1.0), (512,151,1.0), (582,151,1.0), (717,151,1.0), (787,151,1.0), (857,151,1.0),
            (652,201,1.0), 
            (442,251,1.0), (512,251,1.0), (582,251,1.0), (727,251,1.0), (797,251,1.0),
            (68,480,0.0), (138,480,0.0), (208,480,0.0),
            (35,540,0.0), (105,540,0.0), (175,540,0.0)),
        }


@transaction.atomic
def add_player(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    colors = ['blue', 'green', 'orange', 'purple', 'red', 'yellow']
    for player in game.gameplayer_set.all():
        colors.remove(player.color)
    # Remove yellow unless this is the last color. Yellow is easy to mix up
    # with dahan.
    if len(colors) > 1:
        colors.remove('yellow')
    shuffle(colors)
    spirit_id = int(request.POST['spirit'])
    spirit = get_object_or_404(Spirit, pk=spirit_id)
    gp = GamePlayer(game=game, spirit=spirit, notes="You can add notes here...\ntop:1 bottom:1", color=colors[0])
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
            form.save()
            add_log_msg(game, text=f'New screenshot uploaded.', images='.' + game.screenshot.url)
            return redirect(reverse('view_game', args=[game.id]))
    else:
        form = GameForm(instance=game)

    spirits = Spirit.objects.order_by('name').all()
    logs = reversed(game.gamelog_set.order_by('-date').all()[:30])
    return render(request, 'game.html', { 'game': game, 'form': form, 'spirits': spirits, 'logs': logs })

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

    add_log_msg(game, text=f'Host drew {card.name}')

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
    images = ",".join(['./pbf/static' + card.url() for card in selection])
    add_log_msg(player.game, text=f'{player.spirit.name} gains a {type} power. Choices: {cards_str}',
            images=images)

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def choose_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.selection, pk=card_id)
    player.selection.clear()
    player.hand.add(card)

    add_log_msg(player.game, text=f'{player.spirit.name} gains {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def choose_card2(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.selection, pk=card_id)
    player.selection.remove(card)
    player.hand.add(card)

    add_log_msg(player.game, text=f'{player.spirit.name} gains {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def play_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.hand, pk=card_id)
    player.play.add(card)
    player.hand.remove(card)

    add_log_msg(player.game, text=f'{player.spirit.name} plays {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def unplay_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.play, pk=card_id)
    player.hand.add(card)
    player.play.remove(card)

    add_log_msg(player.game, text=f'{player.spirit.name} unplays {card.name}')

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

    add_log_msg(player.game, text=f'{player.spirit.name} forgets {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))


@transaction.atomic
def reclaim_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.discard, pk=card_id)
    player.hand.add(card)
    player.discard.remove(card)

    add_log_msg(player.game, text=f'{player.spirit.name} reclaims {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def reclaim_all(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    cards = list(player.discard.all())
    for card in cards:
        player.hand.add(card)
    player.discard.clear()

    add_log_msg(player.game, text=f'{player.spirit.name} reclaims all')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def discard_all(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    cards = list(player.play.all())
    for card in cards:
        player.discard.add(card)
    player.play.clear()

    add_log_msg(player.game, text=f'{player.spirit.name} discards all')

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

    add_log_msg(player.game, text=f'{player.spirit.name} discards {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

@transaction.atomic
def ready(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.ready = not player.ready
    player.save()

    if player.ready:
        add_log_msg(player.game, text=f'{player.spirit.name} is ready')
    else:
        add_log_msg(player.game, text=f'{player.spirit.name} is not ready')

    if player.game.gameplayer_set.filter(ready=False).count() == 0:
        add_log_msg(player.game, text=f'All spirits are ready!')

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

    add_log_msg(player.game, text=f'All spirits marked not ready')

    return redirect(reverse('view_game', args=[game.id]))

@transaction.atomic
def time_passes(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    for player in game.gameplayer_set.all():
        player.ready = False
        player.save()
    game.turn += 1
    game.save()

    add_log_msg(player.game, text=f'Time passes...')
    add_log_msg(player.game, text=f'-- Turn {game.turn} --')

    return redirect(reverse('view_game', args=[game.id]))


@transaction.atomic
def change_energy(request, player_id, amount):
    amount = int(amount)
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.energy += amount
    player.save()

    if amount > 0:
        add_log_msg(player.game, text=f'{player.spirit.name} gains {amount} energy (now: {player.energy})')
    else:
        add_log_msg(player.game, text=f'{player.spirit.name} pays {-amount} energy (now: {player.energy})')

    return with_log_trigger(render(request, 'energy.html', {'player': player}))

@transaction.atomic
def pay_energy(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    amount = player.get_play_cost()
    player.energy -= amount
    player.save()

    add_log_msg(player.game, text=f'{player.spirit.name} pays {amount} energy (now: {player.energy})')

    return with_log_trigger(render(request, 'energy.html', {'player': player}))

@transaction.atomic
def toggle_presence(request, player_id, left, top):
    player = get_object_or_404(GamePlayer, pk=player_id)
    presence = get_object_or_404(player.presence_set, left=left, top=top)
    presence.opacity = abs(1.0 - presence.opacity)
    presence.save()

    return with_log_trigger(render(request, 'player-with-image.html', {'player': player}))

@transaction.atomic
def add_element(request, player_id, element):
    player = get_object_or_404(GamePlayer, pk=player_id)
    if element == 'sun': player.temporary_sun += 1
    if element == 'moon': player.temporary_moon += 1
    if element == 'fire': player.temporary_fire += 1
    if element == 'air': player.temporary_air += 1
    if element == 'water': player.temporary_water += 1
    if element == 'earth': player.temporary_earth += 1
    if element == 'plant': player.temporary_plant += 1
    if element == 'animal': player.temporary_animal += 1
    player.save()

    return with_log_trigger(render(request, 'elements.html', {'player': player}))

@transaction.atomic
def remove_element(request, player_id, element):
    player = get_object_or_404(GamePlayer, pk=player_id)
    if element == 'sun': player.temporary_sun = 0
    if element == 'moon': player.temporary_moon = 0
    if element == 'fire': player.temporary_fire = 0
    if element == 'air': player.temporary_air = 0
    if element == 'water': player.temporary_water = 0
    if element == 'earth': player.temporary_earth = 0
    if element == 'plant': player.temporary_plant = 0
    if element == 'animal': player.temporary_animal = 0
    player.save()

    return with_log_trigger(render(request, 'elements.html', {'player': player}))


def tab(request, game_id, player_id):
    game = get_object_or_404(Game, pk=game_id)
    player = get_object_or_404(GamePlayer, pk=player_id)
    return render(request, 'tabs.html', {'game': game, 'player': player})

def game_logs(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    logs = reversed(game.gamelog_set.order_by('-date').all()[:30])
    return render(request, 'logs.html', {'game': game, 'logs': logs})

