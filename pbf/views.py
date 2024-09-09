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

class GameForm2(ModelForm):
    class Meta:
        model = Game
        fields = ['screenshot2']

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

# Base energy gain per turn when no presence has been removed from tracks.
# NOT to be used to indicate how much energy the spirit has at setup;
# use spirit_setup_energy for that.
#
# Note that as of Nature Incarnate, there is no aspect that modifies the tracks.
# (Immense and Spreading Hostility are handled in get_gain_energy)
# Therefore, only spirit names are in this dictionary,
# and code that looks up from this dictionary only uses spirit name,
# ignoring aspects.
#
# If a future expansion adds an aspect that modifies an energy gain track,
# the code that looks up from this dictionary needs to be modified,
# so that it can include aspect in its lookup.
spirit_base_energy_per_turn = {
        'Bringer': 2,
        'Exploratory Bringer': 2,
        'Downpour': 1,
        'Earth': 2,
        'Fangs': 1,
        'Finder': 0,
        'Fractured': 1,
        'Green': 0,
        'Lightning': 1,
        'Keeper': 2,
        'Vengeance': 1,
        'Lure': 1,
        'Minds': 0,
        'Mist': 0,
        'Ocean': 0,
        'River': 1,
        'Shadows': 0,
        'Shifting': 0,
        'Starlight': 1,
        'Stone': 2,
        'Thunderspeaker': 1,
        'Trickster': 1,
        'Volcano': 1,
        'Wildfire': 0,
        'Serpent': 1,
        'Teeth': 2,
        'Eyes': 1,
        'Mud': 1,
        'Heat': 1,
        'Whirlwind': 1,
        'Voice': 0,
        'Roots': 1,
        'Gaze': 1,
        'Vigil': 0,
        'Behemoth': 0,
        'Earthquakes': 1,
        'Breath': 1,
        'Waters': 0,
        }

# Note that both spirit and aspect are used in this lookup,
# so e.g. specifying "River" here will only affect base River.
spirit_setup_energy = {
        'River - Sunshine': 1,
        'Keeper - Spreading Hostility': 1,
        'Bringer - Violence': 1,
        'Vigil': 1,
        'Waters': 4,
        }

spirit_presence = {
        'Bringer': ((452,155,1.0,'','Air'), (522,155,1.0,'3'), (592,155,1.0,'','Moon'), (662,155,1.0,'4'), (732,155,1.0), (802,155,1.0,'5'),
            (452,255,1.0), (522,255,1.0), (592,255,1.0), (662,255,1.0), (732,255,1.0)),
        'Exploratory Bringer': ((452,155,1.0,'','Air'), (522,155,1.0,'3'), (592,155,1.0,'','Moon'), (662,155,1.0,'4'), (732,155,1.0), (802,155,1.0,'5'),
            (452,255,1.0), (522,255,1.0), (592,255,1.0), (662,255,1.0), (732,255,1.0)),
        'Downpour': ((434,205,1.0,'','Water'), (506,205,1.0,'','Plant'), (578,205,1.0,'','Water'), (650,205,1.0,'2','Air'), (720,205,1.0,'','Water'), (790,205,1.0,'','Earth'), (860,205,1.0,'','Water,Water'),
            (430,295,1.0), (500,295,1.0,'','Water'), (575,295,1.0), (645,295,1.0), (720,295,1.0)),
        'Earth': ((447,158,1.0,'3'), (513,158,1.0,'4'), (582,158,1.0,'6'), (649,158,1.0,'7'), (719,158,1.0,'8'),
            (445,253,1.0), (515,253,1.0), (580,253,1.0), (650,253,1.0), (720,253,1.0)),
        'Fangs': ((447,158,1.0,'','Animal'), (513,158,1.0,'','Plant'), (582,158,1.0,'2'), (649,158,1.0,'','Animal'), (719,158,1.0,'3'), (789,158,1.0,'4'),
            (445,253,1.0), (515,253,1.0), (580,253,1.0), (650,253,1.0), (720,253,1.0)),
        'Finder': ((450,146,1.0,'','Sun'), (582,146,1.0,'2','Water'), (717,146,1.0,'+2'), (849,146,1.0,'+1'),
            (519,208,1.0,'1','Moon'), (649,208,1.0,'','Air'), (779,208,1.0,'+1'),
            (449,273,1.0,'','Earth'), (583,273,1.0), (716,273,1.0), (848,273,1.0)),
        'Fractured': ((447,203,1.0,'1'), (518,203,1.0,'2'), (592,203,1.0,'2'), (664,203,1.0,'2'), (739,203,1.0,'3'),
            (447,293,1.0), (521,293,1.0), (593,293,1.0), (665,293,1.0), (740,293,1.0),
            (0,0,0.0), (60,0,0.0), (120,0,0.0), (180,0,0.0), (240,0,0.0),
            (0,60,0.0), (60,60,0.0), (120,60,0.0), (180,60,0.0), (240,60,0.0),
            ),
        'Green': ((447,163,1.0,'1'), (513,163,1.0,'','Plant'), (582,163,1.0,'2'), (649,163,1.0,'2'), (719,163,1.0,'','Plant'), (789,163,1.0,'3'),
            (445,258,1.0), (515,258,1.0), (580,258,1.0), (650,258,1.0), (720,258,1.0)),
        'Lightning': ((445,156,1.0,'1'), (511,156,1.0,'2'), (580,156,1.0,'2'), (647,156,1.0,'3'), (715,156,1.0,'4'), (783,156,1.0,'4'), (851,156,1.0,'5'),
            (443,253,1.0), (513,253,1.0), (578,253,1.0), (648,253,1.0)),
        'Keeper': ((445,156,1.0,'','Sun'), (511,156,1.0,'4'), (580,156,1.0,'5'), (647,156,1.0,'','Plant'), (715,156,1.0,'7'), (783,156,1.0,'8'), (851,156,1.0,'9'),
            (443,253,1.0), (513,253,1.0), (578,253,1.0), (648,253,1.0), (718,253,1.0)),
        'Vengeance': ((447,146,1.0,'2'), (518,146,1.0,'','Animal'), (592,146,1.0,'3'), (664,146,1.0,'4'),
            (447,250,1.0), (521,250,1.0,'','Fire'), (592,250,1.0), (666,250,1.0), (738,250,1.0), (810,250,1.0)),
        'Lure': ((447,148,1.0,'2'), (517,148,1.0,'','Moon'), (590,148,1.0,'3','Plant'), (661,148,1.0,'4','Air'), (743,148,1.0,'5'),
            (447,248,1.0), (519,248,1.0,'','Animal'), (590,248,1.0), (664,248,1.0), (736,248,1.0)),
        'Minds': ((448,148,1.0,'1'), (519,148,1.0,'','Air'), (593,148,1.0,'2'), (665,148,1.0,'','Animal'), (738,148,1.0,'3'), (811,148,1.0,'4'),
            (448,251,1.0), (520,251,1.0), (591,251,1.0), (665,251,1.0), (737,251,1.0), (809,251,1.0), ),
        'Mist': ((431,148,1.0,'1'), (502,148,1.0,'','Water'), (576,148,1.0,'2'), (648,148,1.0,'','Air'),
            (431,251,1.0), (503,251,1.0), (574,251,1.0,'','Moon'), (648,251,1.0), (720,251,1.0), (792,251,1.0), (865,251,1.0), ),
        'Ocean': ((445,233,1.0,'','Moon'), (513,233,1.0,'','Water'), (580,233,1.0,'1'), (648,233,1.0,'','Earth'), (718,233,1.0,'','Water'), (788,233,1.0,'2'),
            (445,318,1.0), (513,318,1.0), (584,318,1.0), (648,318,1.0), (718,318,1.0)),
        'River': ((437,158,1.0,'2'), (503,158,1.0,'2'), (572,158,1.0,'3'), (639,158,1.0,'4'), (707,158,1.0,'4'), (775,158,1.0,'5'),
            (435,253,1.0), (505,253,1.0), (570,253,1.0), (640,253,1.0), (708,253,1.0), (776,253,1.0)),
        'Shadows': ((447,158,1.0,'1'), (513,158,1.0,'3'), (582,158,1.0,'4'), (649,158,1.0,'5'), (717,158,1.0,'6'),
            (445,253,1.0), (515,253,1.0), (580,253,1.0), (650,253,1.0), (718,253,1.0)),
        'Shifting': ((430,150,1.0,'1'), (501,150,1.0,'2'), (573,150,1.0,'3'), (642,150,1.0,'4'), (713,150,1.0), (783,150,1.0,'5'), (853,150,1.0,'6'),
            (431,246,1.0), (502,246,1.0), (569,246,1.0), (641,246,1.0)),
        'Starlight': (
            (305,111,1.0),(385,111,0.0),(485,111,0.0),(565,111,0.0),
            (305,193,1.0),(385,193,0.0),(485,193,0.0),(565,193,0.0),
            (292,263,1.0),(366,263,1.0),(443,263,0.0),(517,263,0.0),(577,263,0.0),
            (292,353,1.0),(366,353,1.0),(443,353,0.0),(517,353,0.0),(577,353,0.0),
            (363,450,0.0,'1'),(435,450,1.0,'2'),(507,450,1.0),(579,450,1.0,'4'),
            (363,536,0.0),(435,536,1.0),(507,536,1.0),(579,536,1.0),

            ),
        'Stone': ((450,148,1.0,'3'), (523,148,1.0), (596,148,1.0,'4'), (669,148,1.0), (742,148,1.0,'6'), (815,148,1.0),
            (450,250,1.0,'','Earth'), (523,250,1.0,'','Earth'), (596,250,1.0,'','Earth'), (669,250,1.0,'','Earth'), (742,250,1.0,'','Earth')),
        'Thunderspeaker': ((443,155,1.0,'','Air'), (512,155,1.0,'2'), (583,155,1.0,'','Fire'), (650,155,1.0,'','Sun'), (719,155,1.0,'3'),
            (444,245,1.0), (513,245,1.0), (583,245,1.0), (650,245,1.0), (719,245,1.0), (787,245,1.0)),
        'Trickster': ((446,138,1.0,'','Moon'), (518,138,1.0,'2'), (592,138,1.0), (663,138,1.0,'','Fire'), (736,138,1.0,'3'),
            (447,227,1.0), (519,227,1.0), (592,227,1.0), (663,227,1.0), (736,227,1.0,'','Air'), (808,227,1.0)),
        'Volcano': ((428,140,1.0,'2'), (500,140,1.0,'','Earth'), (574,140,1.0,'3'), (645,140,1.0,'4'), (718,140,1.0,'5'),
            (429,227,1.0,'','Fire'), (501,227,1.0,'','Earth'), (574,227,1.0), (645,227,1.0,'','Air'), (718,227,1.0), (790,227,1.0,'','Fire'), (862,227,1.0)),
        'Wildfire': ((444,155,1.0,'','Fire'), (513,155,1.0,'1'), (584,155,1.0,'2'), (653,155,1.0,'','Fire,Plant'), (725,155,1.0,'3'),
            (443,253,1.0,'','Fire'), (513,253,1.0), (584,253,1.0), (653,253,1.0,'','Fire'), (724,253,1.0)),
        'Serpent': ((442,151,1.0,'','Fire'), (512,151,1.0), (582,151,1.0), (717,151,1.0,'6'), (787,151,1.0), (857,151,1.0,'12'),
            (652,201,1.0,'','Earth'), 
            (442,251,1.0,'','Moon'), (512,251,1.0), (582,251,1.0,'','Water'), (727,251,1.0), (797,251,1.0),
            (68,480,0.0), (138,480,0.0), (208,480,0.0),
            (35,540,0.0), (105,540,0.0), (175,540,0.0)),
        'Teeth': ((450,146,1.0,'','Fire'),(523,146,1.0,'3'),(596,146,1.0,'4'),(669,146,1.0,'','Animal'),(742,146,1.0,'6'),(815,146,1.0,'7'),
                (450,240,1.0),(523,240,1.0,'','Animal'),(596,240,1.0,'','Fire'),(669,240,1.0),(742,240,1.0,'','Earth'),(815,240,1.0)),
        'Eyes': ((450,146,1.0,'1'),(523,146,1.0,'2'),(596,146,1.0,'','Plant'),(669,146,1.0,'3'),(742,146,1.0,'','Moon'),(815,146,1.0,'4'),
                (450,240,1.0),(523,240,1.0,'','Air'),(596,240,1.0),(669,240,1.0,'','Plant'),(742,240,1.0)),
        'Mud': ((450,146,1.0,'','Plant'),(523,146,1.0,'2'),(596,146,1.0,'3'),(669,146,1.0,'','Water'),(742,146,1.0,'4'),(815,146,1.0,'5'),
                (450,240,1.0),(523,240,1.0,'','Earth'),(596,240,1.0),(669,240,1.0,'','Moon'),(742,240,1.0)),
        'Heat': ((450,146,1.0,'','Earth'),(523,146,1.0,'2'),(596,146,1.0,'3'),(669,146,1.0,'','Fire'),(742,146,1.0,'4'),(815,146,1.0,'5'),
                (450,240,1.0),(523,240,1.0),(596,240,1.0),(669,240,1.0),(742,240,1.0,'','Fire')),
        'Whirlwind': ((450,146,1.0,'2'),(523,146,1.0,'','Sun'),(596,146,1.0,'3'),(669,146,1.0,'4','Air'),(742,146,1.0,'6'),
                (450,240,1.0),(523,240,1.0),(596,240,1.0,'','Air'),(669,240,1.0),(742,240,1.0,'','Sun')),
        'Behemoth': (
                (445,232,1.0,'1'),(522,232,1.0,'2','Fire'),(599,232,1.0,'3'),(676,232,1.0,'','Earth'),(753,232,1.0,'4','Plant'),(830,232,1.0,'5','Fire'),
                (445,326,1.0),(522,326,1.0),(599,326,1.0),(676,326,1.0,'','Fire'),(753,326,1.0),
                ),
        'Breath': (
                (445,204,1.0,'2'),(522,204,1.0,'','Moon'),(599,204,1.0,'3'),(676,204,1.0),(753,204,1.0,'4','Animal'),(830,204,1.0,'5','Air'),
                (445,303,1.0),(522,303,1.0),(599,303,1.0,'','Moon'),(676,303,1.0),(753,303,1.0,'','Air'),
                ),
        'Earthquakes': (
                (445,147,1.0),(522,147,1.0,'2'),(599,147,1.0),(676,147,1.0,'3'),(753,147,1.0),(830,147,1.0,'4'),
                (445,246,1.0),(522,246,1.0,'','Moon,Fire'),(599,246,1.0),(676,246,1.0,'','Earth'),(753,246,1.0),(833,246,1.0),
                ),
        'Gaze': (
                (445,167,1.0,'2','Sun'),(522,167,1.0,'3','Fire'),(599,167,1.0,'','Sun'),(676,167,1.0,'4'),(753,167,1.0,'5'),
                (445,266,1.0),(522,266,1.0),(599,266,1.0,'','Sun'),(676,266,1.0),(753,266,1.0),(833,266,1.0),
                ),
        'Roots': (
                (445,217,1.0,'2'),(522,217,1.0,'','Earth'),(599,217,1.0,'4'),(676,217,1.0,'','Plant'),(753,217,1.0,'6'),
                (445,316,1.0),(522,316,1.0,'','Sun'),(599,316,1.0),(676,316,1.0,'','Plant'),(753,316,1.0),
                ),
        'Vigil': (
                (515,132,1.0,'1','Sun'), (591,132,1.0,'2'), (667,132,1.0,'3','Animal'), (743,132,1.0,'4'), (819,132,1.0,'5','Sun'),
                (515,232,1.0), (591,232,1.0,'','Air'), (667,232,1.0), (743,232,1.0,'','Animal'), (819,232,1.0),
                ),
        'Voice': (
                (445,142,1.0,'1'),(522,142,1.0),(599,142,1.0,'2'),(676,142,1.0,'','Air'),(753,142,1.0,'4'),(828,142,1.0),
                (445,245,1.0),(522,245,1.0),(599,245,1.0),(676,245,1.0),(753,245,1.0),
                ),
        'Waters': (
                (452,255,1.0),
                (527,255,1.0),
                (604,255,1.0,'1'),
                (679,210,1.0,'3'),
                (757,210,1.0,'4'),
                (832,210,1.0,'5'),
                (682,308,1.0),
                (757,308,1.0),
                (835,308,1.0),
                ),
        }

spirit_additional_cards = {
    'DarkFireShadows': ['Unquenchable Flames'],
    'NourishingEarth': ['Voracious Growth'],
    'SparkingLightning': ['Smite the Land with Fulmination'],
    'TanglesGreen': ['Belligerent and Aggressive Crops'],
    'ViolenceBringer': ['Bats Scout For Raids By Darkness'],
    'WarriorThunderspeaker': ['Call to Bloodshed'],
    'LocusSerpent': ['Pull Beneath the Hungry Earth'],
    }

spirit_remove_cards = {
    'NourishingEarth': ['A Year of Perfect Stillness'],
    'SparkingLightning': ['Raging Storm'],
    'TanglesGreen': ['Gift of Proliferation'],
    'ViolenceBringer': ['Dreams of the Dahan'],
    'WarriorThunderspeaker': ['Manifestation of Power and Glory'],
    'LocusSerpent': ['Elemental Aegis'],
    }

def add_player(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    colors = game.available_colors()
    color = request.POST['color']
    # this automatically handles random by virtue of random not being in colors.
    # TODO: maybe consider showing an error if they select a color already in use?
    if color not in colors:
        shuffle(colors)
        color = colors[0]
    spirit_name = request.POST['spirit']
    spirit_and_aspect = spirit_name
    aspect = None
    if '-' in spirit_name:
        spirit_name, aspect = spirit_name.split(' - ')
    spirit = get_object_or_404(Spirit, name=spirit_name)
    setup_energy = spirit_setup_energy.get(spirit_and_aspect, 0)
    # as noted above in the comment of spirit_base_energy_per_turn,
    # only spirit name (and not aspect) is considered in energy gain per turn.
    gp = GamePlayer(game=game, spirit=spirit, color=color, aspect=aspect, energy=setup_energy, starting_energy=spirit_base_energy_per_turn[spirit.name])
    gp.init_permanent_elements()
    gp.save()
    try:
        for presence in spirit_presence[spirit.name]:
            try: energy = presence[3]
            except: energy = ''
            try: elements = presence[4]
            except: elements = ''
            gp.presence_set.create(left=presence[0], top=presence[1], opacity=presence[2], energy=energy, elements=elements)

        # remove 1 presence from top track for Serpent Locus setup
        if aspect == 'Locus':
            bonus_presence = spirit_presence[spirit.name][0]
            toggle_presence(request, player_id=gp.pk, left=bonus_presence[0], top=bonus_presence[1])
    except Exception as ex:
        print(ex)
        pass
    gp.hand.set(Card.objects.filter(spirit=spirit))
    if gp.full_name() in spirit_additional_cards:
        additional_starting_cards = spirit_additional_cards[gp.full_name()]
        for card_name in additional_starting_cards:
            card = Card.objects.get(name=card_name)
            gp.hand.add(card)
            if card.type == Card.MINOR:
                game.minor_deck.remove(card)
            elif card.type == Card.MAJOR:
                game.major_deck.remove(card)
    if gp.full_name() in spirit_remove_cards:
        remove_cards = spirit_remove_cards[gp.full_name()]
        for card_name in remove_cards:
            card = Card.objects.get(name=card_name)
            card = gp.hand.remove(card)

    return redirect(reverse('view_game', args=[game.id]))

def view_game(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    if request.method == 'POST':
        if 'screenshot' in request.FILES:
            form = GameForm(request.POST, request.FILES, instance=game)
            if form.is_valid():
                form.save()
                add_log_msg(game, text=f'New screenshot uploaded.', images='.' + game.screenshot.url)
                return redirect(reverse('view_game', args=[game.id]))
        if 'screenshot2' in request.FILES:
            form = GameForm2(request.POST, request.FILES, instance=game)
            if form.is_valid():
                form.save()
                add_log_msg(game, text=f'New screenshot uploaded.', images='.' + game.screenshot2.url)
                return redirect(reverse('view_game', args=[game.id]))

    spirits = [s.name for s in Spirit.objects.order_by('name').all()]
    spirits.append('Lightning - Immense')
    spirits.append('Lightning - Pandemonium')
    spirits.append('Lightning - Wind')
    spirits.append('River - Sunshine')
    spirits.append('River - Travel')
    spirits.append('River - Haven')
    spirits.append('Earth - Might')
    spirits.append('Earth - Resilence')
    spirits.append('Earth - Nourishing')
    spirits.append('Shadows - Amorphous')
    spirits.append('Shadows - DarkFire')
    spirits.append('Shadows - Foreboding')
    spirits.append('Shadows - Madness')
    spirits.append('Shadows - Reach')
    spirits.append('Fangs - Encircle')
    spirits.append('Bringer - Enticing')
    spirits.append('Shifting - Intensify')
    spirits.append('Shifting - Mentor')
    spirits.append('Lure - Lair')
    spirits.append('Green - Regrowth')
    spirits.append('Lightning - Sparking')
    spirits.append('Keeper - Spreading Hostility')
    spirits.append('Mist - Stranded')
    spirits.append('Thunderspeaker - Tactician')
    spirits.append('Green - Tangles')
    spirits.append('Wildfire - Transforming')
    spirits.append('Fangs - Unconstrained')
    spirits.append('Bringer - Violence')
    spirits.append('Thunderspeaker - Warrior')
    spirits.append('Ocean - Deeps')
    spirits.append('Serpent - Locus')
    spirits.sort()
    logs = reversed(game.gamelog_set.order_by('-date').all()[:30])
    return render(request, 'game.html', { 'game': game, 'spirits': spirits, 'logs': logs })

def draw_card(request, game_id, type):
    game = get_object_or_404(Game, pk=game_id)
    if type == 'minor':
        deck = game.minor_deck
    else:
        deck = game.major_deck

    cards = list(deck.all())
    if not cards:
        # deck was empty
        reshuffle_discard(game, type)
        cards = list(deck.all())
    shuffle(cards)
    card = cards[0]
    deck.remove(card)
    game.discard_pile.add(card)

    add_log_msg(game, text=f'Host drew {card.name}', images='./pbf/static/' + card.url())

    return redirect(reverse('view_game', args=[game.id]))

def reshuffle_discard(game, type):
    if type == 'minor':
        minors = game.discard_pile.filter(type=Card.MINOR).all()
        for card in minors:
            game.discard_pile.remove(card)
            game.minor_deck.add(card)
    else:
        majors = game.discard_pile.filter(type=Card.MAJOR).all()
        for card in majors:
            game.discard_pile.remove(card)
            game.major_deck.add(card)

    add_log_msg(game, text=f'Re-shuffling {type} power deck')

def take_power(request, player_id, type):
    player = get_object_or_404(GamePlayer, pk=player_id)
    if type == 'minor':
        deck = player.game.minor_deck
    else:
        deck = player.game.major_deck

    cards = list(deck.all())
    if not cards:
        # deck was empty
        reshuffle_discard(player.game, type)
        cards = list(deck.all())
    shuffle(cards)
    card = cards[0]
    player.hand.add(card)
    deck.remove(card)

    add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} takes {card.name}')

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def gain_healing(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    selection = [
            Card.objects.get(name="Serene Waters"),
            Card.objects.get(name="Waters Renew"),
            Card.objects.get(name="Roiling Waters"),
            Card.objects.get(name="Waters Taste of Ruin")
            ]

    player.selection.set(selection)

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

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

    # handle power deck running out
    if len(selection) != num:
        reshuffle_discard(player.game, type)

        cards = list(deck.all())
        shuffle(cards)
        selection2 = cards[:num-len(selection)]
        for c in selection2:
            deck.remove(c)
        selection += selection2

    player.selection.set(selection)

    cards_str = ", ".join([str(card) for card in selection])
    images = ",".join(['./pbf/static' + card.url() for card in selection])
    add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} gains a {type} power. Choices: {cards_str}',
            images=images)

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def minor_deck(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    return render(request, 'power_deck.html', {'name': 'Minor', 'cards': game.minor_deck.all()})

def major_deck(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    return render(request, 'power_deck.html', {'name': 'Major', 'cards': game.major_deck.all()})

def discard_pile(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    return render(request, 'discard_pile.html', { 'player': player })

def choose_from_discard(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.game.discard_pile, pk=card_id)
    player.hand.add(card)
    player.game.discard_pile.remove(card)

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def send_days(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    for location in [player.selection, player.game.discard_pile]:
        try:
            card = get_object_or_404(location, pk=card_id)
            player.days.add(card)
            location.remove(card)
            break
        except:
            pass

    add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} sends {card.name} to the Days That Never Were')

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def choose_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.selection, pk=card_id)

    if card.name in ("Serene Waters", "Waters Renew", "Roiling Waters", "Waters Taste of Ruin"):
        return choose_healing_card(request, player, card)

    player.hand.add(card)
    player.selection.remove(card)
    for discard in player.selection.all():
        player.game.discard_pile.add(discard)
    player.selection.clear()

    add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} gains {card.name}')

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def choose_healing_card(request, player, card):
    player.healing.add(card)
    player.selection.clear()

    add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} claims {card.name}')

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def choose_days(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.days, pk=card_id)
    player.hand.add(card)
    player.days.remove(card)

    add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} gains {card.name} from the Days That Never Were')

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def create_days(request, player_id, num):
    player = get_object_or_404(GamePlayer, pk=player_id)
    game = player.game

    for deck in [game.minor_deck, game.major_deck]:
        cards = list(deck.all())
        shuffle(cards)
        for c in cards[:num]:
            deck.remove(c)
            player.days.add(c)

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def compute_card_thresholds(player):
    equiv_elements = player.equiv_elements()
    player.play_cards = []
    for card in player.play.all():
        card.computed_thresholds = card.thresholds(player.elements, equiv_elements)
        player.play_cards.append(card)
    player.hand_cards = []
    for card in player.hand.all():
        card.computed_thresholds = card.thresholds(player.elements, equiv_elements)
        player.hand_cards.append(card)
    player.selection_cards = []
    for card in player.selection.all():
        card.computed_thresholds = card.thresholds(player.elements, equiv_elements)
        player.selection_cards.append(card)

def impend_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.hand, pk=card_id)
    player.impending.add(card)
    player.hand.remove(card)

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def play_from_impending(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.impending, pk=card_id)
    player.play.add(card)
    player.impending.remove(card)

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def play_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.hand, pk=card_id)
    player.play.add(card)
    player.hand.remove(card)

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def unplay_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.play, pk=card_id)
    player.hand.add(card)
    player.play.remove(card)

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def forget_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)

    for location in [player.hand, player.play, player.discard]:
        try:
            card = location.get(pk=card_id)
            location.remove(card)
            player.game.discard_pile.add(card)
            break
        except:
            pass

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))


def reclaim_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.discard, pk=card_id)
    player.hand.add(card)
    player.discard.remove(card)

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def reclaim_all(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    cards = list(player.discard.all())
    for card in cards:
        player.hand.add(card)
    player.discard.clear()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def discard_all(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    cards = list(player.play.all())
    for card in cards:
        player.discard.add(card)
    player.play.clear()
    player.ready = False
    player.gained_this_turn = False
    player.paid_this_turn = False
    player.temporary_sun = 0
    player.temporary_moon = 0
    player.temporary_fire = 0
    player.temporary_air = 0
    player.temporary_water = 0
    player.temporary_earth = 0
    player.temporary_plant = 0
    player.temporary_animal = 0
    player.save()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

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

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def ready(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.ready = not player.ready
    player.save()

    if player.ready:
        if player.gained_this_turn:
            add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} gains {player.get_gain_energy()} energy')
        for card in player.play.all():
            add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} plays {card.name}')
        if player.paid_this_turn:
            add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} pays {player.get_play_cost()} energy')
        add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} is ready')
    else:
        add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} is not ready')

    if player.game.gameplayer_set.filter(ready=False).count() == 0:
        add_log_msg(player.game, text=f'All spirits are ready!')

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def unready(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    for player in game.gameplayer_set.all():
        player.ready = False
        player.save()

    add_log_msg(player.game, text=f'All spirits marked not ready')

    return redirect(reverse('view_game', args=[game.id]))

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


def change_energy(request, player_id, amount):
    amount = int(amount)
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.energy += amount
    player.save()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'energy.html', {'player': player}))

def pay_energy(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    amount = player.get_play_cost()
    player.energy -= amount
    player.paid_this_turn = True
    player.save()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'energy.html', {'player': player}))

def gain_energy(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    amount = player.get_gain_energy()
    player.energy += amount
    player.gained_this_turn = True
    player.save()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'energy.html', {'player': player}))

def toggle_presence(request, player_id, left, top):
    player = get_object_or_404(GamePlayer, pk=player_id)
    presence = get_object_or_404(player.presence_set, left=left, top=top)
    presence.opacity = abs(1.0 - presence.opacity)
    presence.save()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

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

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def remove_element(request, player_id, element):
    player = get_object_or_404(GamePlayer, pk=player_id)
    if element == 'sun': player.temporary_sun -= 1
    if element == 'moon': player.temporary_moon -= 1
    if element == 'fire': player.temporary_fire -= 1
    if element == 'air': player.temporary_air -= 1
    if element == 'water': player.temporary_water -= 1
    if element == 'earth': player.temporary_earth -= 1
    if element == 'plant': player.temporary_plant -= 1
    if element == 'animal': player.temporary_animal -= 1
    player.save()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def add_element_permanent(request, player_id, element):
    player = get_object_or_404(GamePlayer, pk=player_id)
    if element == 'sun': player.permanent_sun += 1
    if element == 'moon': player.permanent_moon += 1
    if element == 'fire': player.permanent_fire += 1
    if element == 'air': player.permanent_air += 1
    if element == 'water': player.permanent_water += 1
    if element == 'earth': player.permanent_earth += 1
    if element == 'plant': player.permanent_plant += 1
    if element == 'animal': player.permanent_animal += 1
    player.save()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def remove_element_permanent(request, player_id, element):
    player = get_object_or_404(GamePlayer, pk=player_id)
    if element == 'sun': player.permanent_sun -= 1
    if element == 'moon': player.permanent_moon -= 1
    if element == 'fire': player.permanent_fire -= 1
    if element == 'air': player.permanent_air -= 1
    if element == 'water': player.permanent_water -= 1
    if element == 'earth': player.permanent_earth -= 1
    if element == 'plant': player.permanent_plant -= 1
    if element == 'animal': player.permanent_animal -= 1
    player.save()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def change_name(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.name = request.POST['name']
    player.save()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'name.html', {'player': player, 'success': True}))

def tab(request, game_id, player_id):
    game = get_object_or_404(Game, pk=game_id)
    player = get_object_or_404(GamePlayer, pk=player_id)
    compute_card_thresholds(player)
    return render(request, 'tabs.html', {'game': game, 'player': player})

def game_logs(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    logs = reversed(game.gamelog_set.order_by('-date').all()[:30])
    return render(request, 'logs.html', {'game': game, 'logs': logs})

