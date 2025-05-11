import json
from random import sample, shuffle
import os

from django.db import transaction
from django.forms import ModelForm
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from .models import *

import redis

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=1)

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
    return redirect(reverse('game_setup', args=[game.id]))

def edit_players(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    players = zip(request.POST.getlist('id'), request.POST.getlist('name'), request.POST.getlist('color'))
    for (id, name, color) in players:
        game.gameplayer_set.filter(id=id).update(name=name, color=color)

    return redirect(reverse('game_setup', args=[game.id]))

def game_setup(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    spirits_by_expansion = {
        # Short name, full name, aspects (if any)
        # Within an expansion, sorted alphabetically
        #
        # Should we sort by complexity?
        # Don't think so; not everyone knows the complexities by heart,
        # and so the ordering would look haphazard to those who don't know them.
        #
        # Similarly, aspects are going to be grouped with their spirit
        # regardless of which expansion the aspect was released in,
        # because not everyone is going to know which expansion has which aspects.
        'Spirit Island (base)': [
            ('Bringer', 'Bringer of Dreams and Nightmares', ('Enticing', 'Violence')),
            ('Lightning', "Lightning's Swift Strike", ('Immense', 'Pandemonium', 'Sparking', 'Wind')),
            ('Ocean', "Ocean's Hungry Grasp", ('Deeps',)),
            ('River', 'River Surges in Sunlight', ('Haven', 'Sunshine', 'Travel')),
            ('Shadows', 'Shadows Flicker Like Flame', ('Amorphous', 'Dark Fire', 'Foreboding', 'Madness', 'Reach')),
            ('Green', 'A Spread of Rampant Green', ('Regrowth', 'Tangles')),
            ('Thunderspeaker', 'Thunderspeaker', ('Tactician', 'Warrior')),
            ('Earth', 'Vital Strength of the Earth', ('Might', 'Resilience', 'Nourishing')),
        ],
        'Branch & Claw': [
            ('Keeper', 'Keeper of the Forbidden Wilds', ('Spreading Hostility',)),
            ('Fangs', 'Sharp Fangs Behind the Leaves', ('Encircle', 'Unconstrained')),
        ],
        'Jagged Earth': [
            ('Fractured', 'Fractured Days Split the Sky', ()),
            ('Trickster', 'Grinning Trickster Stirs Up Trouble', ()),
            ('Lure', 'Lure of the Deep Wilderness', ('Lair',)),
            ('Minds', 'Many Minds Move as One', ()),
            ('Shifting', 'Shifting Memory of Ages', ('Intensify', 'Mentor')),
            ('Mist', 'Shroud of Silent Mist', ('Stranded',)),
            ('Starlight', 'Starlight Seeks Its Form', ()),
            ('Stone', "Stone's Unyielding Defiance", ()),
            ('Vengeance', 'Vengeance as a Burning Plague', ()),
            ('Volcano', 'Volcano Looming High', ()),
        ],
        'Feather & Flame': [
            ('Downpour', 'Downpour Drenches the World', ()),
            ('Finder', 'Finder of Paths Unseen', ()),
            ('Wildfire', 'Heart of the Wildfire', ('Transforming',)),
            ('Serpent', 'Serpent Slumbering Beneath the Island', ('Locus',)),
        ],
        'Horizons of Spirit Island': [
            ('Teeth', 'Devouring Teeth Lurk Underfoot', ()),
            ('Eyes', 'Eyes Watch from the Trees', ()),
            ('Mud', 'Fathomless Mud of the Swamp', ()),
            ('Heat', 'Rising Heat of Stone and Sand', ()),
            ('Whirlwind', 'Sun-Bright Whirlwind', ()),
        ],
        'Nature Incarnate': [
            ('Breath', 'Breath of Darkness Down Your Spine', ()),
            ('Earthquakes', 'Dances Up Earthquakes', ()),
            ('Behemoth', 'Ember-Eyed Behemoth', ()),
            ('Vigil', 'Hearth-Vigil', ()),
            ('Gaze', 'Relentless Gaze of the Sun', ()),
            ('Roots', 'Towering Roots of the Jungle', ()),
            ('Voice', 'Wandering Voice Keens Delirium', ()),
            ('Waters', 'Wounded Waters Bleeding', ()),
        ],
        'Apocrypha': [
            ('Covets', 'Covets Gleaming Shards of Earth v1.2.1 [Apocrypha]', ()),
            ('Rot', 'Spreading Rot Renews the Earth [Apocrypha]', ('Round Down',)),
        ],
        'Exploratory Testing': [
            # Note that the template has logic to not show the base spirit for this category,
            # because the base spirit is assumed to be in a different expansion.
            # In other words, this category only shows aspects.
            ('Shadows', 'Shadows Flicker Like Flame', ('Exploratory', )),
            ('Bringer', 'Bringer of Dreams and Nightmares', ('Exploratory', )),
        ],
    }
    spirits_present = [spirit for (expansion, spirits) in spirits_by_expansion.items() for (spirit, _, _) in spirits]
    spirits = [s.name for s in Spirit.objects.order_by('name').all()]

    # These messages are useful while in development;
    # we expect that they do not get printed in production.
    missing_spirits = set(spirits) - set(spirits_present)
    if missing_spirits:
        print(f"Warning: missing spirits {missing_spirits}")
    unknown_spirits = set(spirits_present) - set(spirits)
    if unknown_spirits:
        print(f"Warning: unknown spirits {unknown_spirits}")

    return render(request, 'setup.html', { 'game': game, 'spirits_by_expansion': spirits_by_expansion })

def change_game_name(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    game.name = request.POST['name']
    game.save()
    return redirect(reverse('game_setup', args=[game.id]))

def change_scenario(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    game.scenario = request.POST['scenario']
    game.save()
    return redirect(reverse('game_setup', args=[game.id]))

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
        'Rot': 2,
        'Covets': 0,
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
                (445,147,1.0),(522,147,1.0,'2'),(599,147,1.0),(676,147,1.0,'3'),(753,147,1.0,'Impend2'),(830,147,1.0,'4'),
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
        'Rot': (
                (441,158,1.0,'','Water,Rot'), (512,158,1.0,'3'), (582,158,1.0,'','Plant,Rot'), (654,158,1.0,'','Earth,Rot'), (725,158,1.0,'4'),
                (441,254,1.0), (512,254,1.0,'','Rot'), (582,254,1.0), (654,254,1.0,'','Moon'), (724,254,1.0), (796,254,1.0),
                ),
        'Covets': (
                (441,158,1.0,'1'), (512,158,1.0), (582,158,1.0,'3'), (654,158,1.0,'','Earth'), (725,158,1.0,'','Fire,Animal'), (796,158,1.0,'5'),
                (441,279,1.0,'','Air'), (512,279,1.0,''), (582,279,1.0,'','Sun'), (654,244,1.0,'','Fire'), (654,314,1.0,'','Animal'), (724,279,1.0),
                # hoard one-time bonuses
                (176,700,0.0), (176,815,0.0),
                # hoard forms (passive bonuses)
                (368,700,0.0), (332,815,0.0), (332,950,0.0),
                # hoard innates
                (605,700,0.0), (605,855,0.0), (605,1005,0.0),
                # hoard any element spaces
                (11,991,0.0), (11,1061,0.0), (159,991,0.0), (159,1061,0.0), (307,1061,0.0),
                # hoard treasure
                (13,1146,1.0), (83,1146,1.0), (153,1146,1.0), (223,1146,1.0), (293,1146,1.0), (363,1146,1.0), (433,1146,1.0), (503,1146,1.0), (573,1146,1.0), (643,1146,1.0), (713,1146,1.0), (783,1146,1.0), (853,1146,1.0),
                ),
        }

spirit_additional_cards = {
    'Dark FireShadows': ['Unquenchable Flames'],
    'NourishingEarth': ['Voracious Growth'],
    'SparkingLightning': ['Smite the Land with Fulmination'],
    'TanglesGreen': ['Belligerent and Aggressive Crops'],
    'ViolenceBringer': ['Bats Scout for Raids by Darkness'],
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
    'SunshineRiver': ['Boon of Vigor'],
    }

def add_player(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    colors = [c for (c, freq, _) in game.color_freq() if freq == 0]
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
    name = request.POST.get('name', '')
    # as noted above in the comment of spirit_base_energy_per_turn,
    # only spirit name (and not aspect) is considered in energy gain per turn.
    gp = GamePlayer(game=game, name=name, spirit=spirit, color=color, aspect=aspect, energy=setup_energy, starting_energy=spirit_base_energy_per_turn[spirit.name])
    gp.init_spirit()
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

    return redirect(reverse('game_setup', args=[game.id]))

def view_game(request, game_id, spirit_spec=None):
    game = get_object_or_404(Game, pk=game_id)
    if request.method == 'POST':
        if 'spirit_spec' in request.POST:
            spirit_spec = request.POST['spirit_spec']
        if 'screenshot' in request.FILES:
            form = GameForm(request.POST, request.FILES, instance=game)
            if form.is_valid():
                form.save()
                add_log_msg(game, text=f'New screenshot uploaded.', images='.' + game.screenshot.url)
                return redirect(reverse('view_game', args=[game.id, spirit_spec] if spirit_spec else [game.id]))
        if 'screenshot2' in request.FILES:
            form = GameForm2(request.POST, request.FILES, instance=game)
            if form.is_valid():
                form.save()
                add_log_msg(game, text=f'New screenshot uploaded.', images='.' + game.screenshot2.url)
                return redirect(reverse('view_game', args=[game.id, spirit_spec] if spirit_spec else [game.id]))

    tab_id = try_match_spirit(game, spirit_spec) or (game.gameplayer_set.first().id if game.gameplayer_set.exists() else None)
    logs = reversed(game.gamelog_set.order_by('-date').all()[:30])
    return render(request, 'game.html', { 'game': game, 'logs': logs, 'tab_id': tab_id, 'spirit_spec': spirit_spec })

def try_match_spirit(game, spirit_spec):
    if not spirit_spec:
        return None

    if spirit_spec.isnumeric():
        spirit_spec = int(spirit_spec)
        player_ids = game.gameplayer_set.values_list('id', flat=True)
        if 1 <= spirit_spec <= len(player_ids):
            return player_ids[spirit_spec - 1]
        elif spirit_spec in player_ids:
            return spirit_spec
    else:
        aspect_match = game.gameplayer_set.filter(aspect__iexact=spirit_spec)
        if aspect_match.exists():
            return aspect_match.first().id
        # prefer the base spirit if they search for a spirit name,
        # in case there is one base and one aspected spirit in the same game.
        base_spirit_match = game.gameplayer_set.filter(spirit__name__iexact=spirit_spec, aspect=None)
        if base_spirit_match.exists():
            return base_spirit_match.first().id
        spirit_match = game.gameplayer_set.filter(spirit__name__iexact=spirit_spec)
        if spirit_match.exists():
            return spirit_match.first().id

        # look for an exact match first, in case someone's name is a substring of another
        # on the other hand, if someone's name is exactly a spirit or aspect's name, not much we can do!
        player_exact_match = game.gameplayer_set.filter(name__iexact=spirit_spec)
        if player_exact_match.exists():
            return player_exact_match.first().id
        player_match = game.gameplayer_set.filter(name__icontains=spirit_spec)
        if player_match.exists():
            return player_match.first().id

def draw_cards(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    cards_needed = int(request.POST['num_cards'])
    type = request.POST['type']
    if cards_needed <= 0:
        return render(request, 'host_draw.html', {'msg': f"Can't draw {cards_needed} cards"})

    cards_drawn = cards_from_deck(game, cards_needed, type)
    game.discard_pile.add(*cards_drawn)

    draw_result = f"drew {len(cards_drawn)} {type} power card{'s' if len(cards_drawn) != 1 else ''}"
    draw_result_explain = "" if len(cards_drawn) == cards_needed else f" (there were not enough cards to draw all {cards_needed})"
    card_names = ', '.join(card.name for card in cards_drawn)

    add_log_msg(game, text=f'Host {draw_result}: {card_names}', images=",".join('./pbf/static' + card.url() for card in cards_drawn))

    return render(request, 'host_draw.html', {'msg': f"You {draw_result}{draw_result_explain}: {card_names}", 'cards': cards_drawn})

def cards_from_deck(game, cards_needed, type):
    if type == 'minor':
        deck = game.minor_deck
    elif type == 'major':
        deck = game.major_deck
    else:
        raise ValueError(f"can't draw from {type} deck")

    cards_have = deck.count()

    if cards_have >= cards_needed:
        cards_drawn = sample(list(deck.all()), cards_needed)
        deck.remove(*cards_drawn)
    else:
        # reshuffle needed, but first draw all the cards we do have
        cards_drawn = list(deck.all())
        cards_remain = cards_needed - cards_have
        deck.clear()
        reshuffle_discard(game, type)
        if deck.count() >= cards_remain:
            new_cards = sample(list(deck.all()), cards_remain)
            cards_drawn.extend(new_cards)
            deck.remove(*new_cards)
        else:
            cards_drawn.extend(list(deck.all()))
            deck.clear()

    return cards_drawn

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

def take_powers(request, player_id, type, num):
    player = get_object_or_404(GamePlayer, pk=player_id)

    taken_cards = cards_from_deck(player.game, num, type)
    player.hand.add(*taken_cards)

    if num == 1:
        card = taken_cards[0]
        add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} takes a {type} power: {card.name}', images='./pbf/static' + card.url())
    else:
        # There's a bit of tension between the function's name/functionality and game terminology.
        #
        # As used in code, take_powers is being used when we don't go through the selection process
        # (the spirit gets all the cards directly into their hand).
        # It's natural to use this for Mentor Shifting Memory of Ages,
        # since the number of cards they get to keep is equal to the number of cards they look at.
        #
        # However, we do want to use the word "gain" in the log message, not "take",
        # because Mentor still needs to forget a power card.
        #
        # The alternative is to special-case gain_power to not use selection if it's Mentor and num == 2.
        # Either way we have to make some special cases,
        # and doing it here at least matches in mechanism better.
        card_names = ', '.join(card.name for card in taken_cards)
        add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} gains {num} {type} powers: {card_names}', images=",".join('./pbf/static' + card.url() for card in taken_cards))

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player, 'taken_cards': taken_cards}))

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

    selection = cards_from_deck(player.game, num, type)
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

def return_to_deck(request, player_id, card_id):
    # this doesn't actually manipulate the player in any way,
    # except to return to their tab after the operation is done
    player = get_object_or_404(GamePlayer, pk=player_id)
    game = player.game
    card = get_object_or_404(game.discard_pile, pk=card_id)
    game.discard_pile.remove(card)

    if card.type == card.MINOR:
        game.minor_deck.add(card)
    elif card.type == card.MAJOR:
        game.major_deck.add(card)
    else:
        raise ValueError(f"Can't return {card}")

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def choose_from_discard(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.game.discard_pile, pk=card_id)
    player.hand.add(card)
    player.game.discard_pile.remove(card)

    add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} takes {card.name} from the power discard pile')

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

    if card.is_healing():
        return choose_healing_card(request, player, card)

    player.hand.add(card)
    player.selection.remove(card)
    # if there are 5 minor cards left in their selection,
    # we assume this was a Boon of Reimagining (draw 6 and gain 2)
    # so we do not send the cards to the discard in that case.
    # Also, Boon of Reimagining on Mentor Shifting Memory of Ages will draw 4 and gain 3.
    # Otherwise, we do discard the cards.
    # (It has to be minors because Covets Gleaming Shards of Earth can draw 6 majors)
    #
    # For now it works to make this decision solely based on the number of cards drawn.
    # If there's ever another effect that does draw 6 gain N with N != 2,
    # we would have to redo this in some way,
    # perhaps by adding a field to GamePlayer indicating the number of cards that are to be gained.
    cards_left = player.selection.count()
    can_keep_selecting = card.type == Card.MINOR and (cards_left == 5 or player.aspect == 'Mentor' and cards_left > 1)
    if not can_keep_selecting:
        for discard in player.selection.all():
            player.game.discard_pile.add(discard)
        player.selection.clear()

    add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} gains {card.name}')

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def undo_gain_card(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    game = player.game

    to_remove = []
    for sel in player.selection.all():
        if sel.type == Card.MINOR:
            game.minor_deck.add(sel)
            # we don't remove from player.selection immediately,
            # as that would modify the selection we're iterating over.
            to_remove.append(sel)
        elif sel.type == Card.MAJOR:
            game.major_deck.add(sel)
            to_remove.append(sel)
        elif sel.is_healing():
            to_remove.append(sel)
        # If it's not any of these types, we'll leave it in selection, as something's gone wrong.

    for rem in to_remove:
        player.selection.remove(rem)

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def choose_healing_card(request, player, card):
    if card.name.startswith('Waters'):
        player.healing.remove(player.healing.filter(name__startswith='Waters').first())
    else:
        player.healing.clear()
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
        if card.is_healing():
            card.computed_thresholds.extend(card.healing_thresholds(player.healing.count(), player.spirit_specific_resource_elements()))
        player.selection_cards.append(card)
    # we could just unconditionally set this, but I guess we'll save a database query if they're not Dances Up Earthquakes.
    player.computed_impending = player.gameplayerimpendingwithenergy_set.all() if player.spirit.name == 'Earthquakes' else []
    for imp in player.computed_impending:
        imp.card.computed_thresholds = imp.card.thresholds(player.elements, equiv_elements)

def gain_energy_on_impending(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    to_gain = player.impending_energy()
    for impending in player.gameplayerimpendingwithenergy_set.all():
        if impending.this_turn:
            # You only gain energy on cards made impending on previous turns.
            continue
        # Let's cap the energy at the cost of the card.
        # There's no real harm in letting it exceed the cost
        # (the UI will still let you play it),
        # it's just that undoing it will require extra clicks on the -1.
        impending.energy += to_gain
        if impending.energy >= impending.cost_with_scenario:
            impending.energy = impending.cost_with_scenario
            impending.in_play = True
        impending.save()
    player.spirit_specific_per_turn_flags |= GamePlayer.SPIRIT_SPECIFIC_INCREMENTED_THIS_TURN
    player.save()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def impend_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.hand, pk=card_id)
    player.impending_with_energy.add(card)
    player.hand.remove(card)

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def unimpend_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.impending_with_energy, pk=card_id)
    player.impending_with_energy.remove(card)
    player.hand.add(card)

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def add_energy_to_impending(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.impending_with_energy, pk=card_id)
    impending_with_energy = get_object_or_404(GamePlayerImpendingWithEnergy, gameplayer=player, card=card)
    if not impending_with_energy.in_play and impending_with_energy.energy < impending_with_energy.cost_with_scenario:
        impending_with_energy.energy += 1
        impending_with_energy.save()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def remove_energy_from_impending(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.impending_with_energy, pk=card_id)
    impending_with_energy = get_object_or_404(GamePlayerImpendingWithEnergy, gameplayer=player, card=card)
    if not impending_with_energy.in_play and impending_with_energy.energy > 0:
        impending_with_energy.energy -= 1
        impending_with_energy.save()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def play_from_impending(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.impending_with_energy, pk=card_id)
    impending_with_energy = get_object_or_404(GamePlayerImpendingWithEnergy, gameplayer=player, card=card)
    if not impending_with_energy.in_play and impending_with_energy.energy >= impending_with_energy.cost_with_scenario:
        impending_with_energy.in_play = True
        impending_with_energy.save()

    compute_card_thresholds(player)
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def unplay_from_impending(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.impending_with_energy, pk=card_id)
    impending_with_energy = get_object_or_404(GamePlayerImpendingWithEnergy, gameplayer=player, card=card)
    if impending_with_energy.in_play:
        impending_with_energy.in_play = False
        impending_with_energy.save()

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

    for location in [player.hand, player.play, player.discard, player.impending_with_energy]:
        try:
            card = location.get(pk=card_id)
            location.remove(card)
            player.game.discard_pile.add(card)
            break
        except:
            pass

    add_log_msg(player.game, text=f'{player.circle_emoji} {player.spirit.name} forgets {card.name}')

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

    if player.spirit.name == 'Earthquakes':
        played_impending = GamePlayerImpendingWithEnergy.objects.filter(gameplayer=player, in_play=True)
        for i in played_impending.all():
            player.discard.add(i.card)
        played_impending.delete()
        player.gameplayerimpendingwithenergy_set.update(this_turn=False)

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
    player.spirit_specific_per_turn_flags = 0
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

    return with_log_trigger(render(request, 'energy.html', {'player': player}))

def pay_energy(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    amount = player.get_play_cost()
    player.energy -= amount
    player.paid_this_turn = True
    player.save()

    return with_log_trigger(render(request, 'energy.html', {'player': player}))

def gain_energy(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    amount = player.get_gain_energy()
    player.energy += amount
    player.gained_this_turn = True
    player.save()

    return with_log_trigger(render(request, 'energy.html', {'player': player}))

def change_spirit_specific_resource(request, player_id, amount):
    amount = int(amount)
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.spirit_specific_resource += amount
    if amount > 0:
        player.spirit_specific_per_turn_flags |= GamePlayer.SPIRIT_SPECIFIC_INCREMENTED_THIS_TURN
    elif amount < 0:
        player.spirit_specific_per_turn_flags |= GamePlayer.SPIRIT_SPECIFIC_DECREMENTED_THIS_TURN
    player.save()

    # The spirit-specific resource is displayed in energy.html,
    # because some of them can change simultaneously with energy (e.g. Rot).
    return with_log_trigger(render(request, 'energy.html', {'player': player}))

def gain_rot(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.spirit_specific_resource += player.rot_gain()
    player.spirit_specific_per_turn_flags |= GamePlayer.ROT_GAINED_THIS_TURN
    player.save()

    return with_log_trigger(render(request, 'energy.html', {'player': player}))

def convert_rot(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    # be sure to change energy before rot,
    # because energy gain is based on rot.
    player.energy += player.energy_from_rot()
    player.spirit_specific_resource -= player.rot_loss()
    player.spirit_specific_per_turn_flags |= GamePlayer.ROT_CONVERTED_THIS_TURN
    player.save()

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

def tab(request, game_id, player_id):
    game = get_object_or_404(Game, pk=game_id)
    player = get_object_or_404(GamePlayer, pk=player_id)
    compute_card_thresholds(player)
    return render(request, 'tabs.html', {'game': game, 'player': player})

def game_logs(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    logs = reversed(game.gamelog_set.order_by('-date').all()[:30])
    return render(request, 'logs.html', {'game': game, 'logs': logs})

