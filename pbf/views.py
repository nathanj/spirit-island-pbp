import json
import itertools
import random
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

# If player is set, the text will be prefixed with their colour and spirit name.
#
# If cards is set:
# * The log message will automatically have a : and the card names appended to it.
# * The images will automatically be set to the images of the cards.
#
# Setting spoiler to True will hide the card names (if any) and the image.
#
# It's an error to set both cards and images.
# images may be set by itself if there are images not associated with a card (example: screenshot)
def add_log_msg(game, *, text, player=None, cards=None, images=None, spoiler=False):
    if player:
        text = f'{player.circle_emoji} {player.spirit.name} {text}'
    if cards and images:
        raise TypeError("specified both cards and images, but cards would overwrite images")
    card_names = cards and ', '.join(card.name for card in cards)
    if cards:
        images = ','.join('./pbf/static' + card.url() for card in cards)
    if spoiler and cards:
        # We only need to spoiler certain information.
        # For the things we're spoilering (gain power, take power),
        # that's just the card names (it's okay not to spoiler who gains the card).
        discord_text = f"{text}: ||{card_names}||"
        game.gamelog_set.create(text=f"{text}:", spoiler_text=card_names, images=images)
    else:
        if cards:
            text += ': ' + card_names
        discord_text = text
        game.gamelog_set.create(text=text, images=images)
    if len(game.discord_channel) > 0:
        j = {'text': discord_text}
        if images is not None:
            j['images'] = images
        if spoiler:
            j['spoiler'] = True
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
    return render(request, 'index.html')

# For use in development only, not production.
def view_screenshot(request, game_id=None, filename=None):
    with open(os.path.join(*[s for s in ['screenshot', game_id, filename] if s]), mode='rb') as f:
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
    GamePlayer.objects.bulk_update([GamePlayer(id=id, name=name, color=color) for id, name, color in players], ['name', 'color'])

    return redirect(reverse('game_setup', args=[game.id]))

def game_setup(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    spirits_by_expansion = {
        # Short name, full name, aspects (if any)
        # Within an expansion, sorted alphabetically
        # Base is automatically included, unless the first element of aspects is 'NO BASE'
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
            ('Covets', 'Covets Gleaming Shards of Earth [Apocrypha]', ('NO BASE', 'v1.3')),
            ('Rot', 'Spreading Rot Renews the Earth [Apocrypha]', ('Round Down',)),
        ],
        'Exploratory Testing': [
            ('Shadows', 'Shadows Flicker Like Flame', ('NO BASE', 'Exploratory', )),
            ('Bringer', 'Bringer of Dreams and Nightmares', ('NO BASE', 'Exploratory', )),
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
                (441,158,1.0,'1'), (512,158,1.0,'','Fire'), (582,158,1.0,'2','Animal'), (654,158,1.0,'3','Earth'), (725,158,1.0,'4'), (796,158,1.0), (867,158,1.0,'5'),
                (441,279,1.0,'','Sun'), (512,279,1.0,''), (582,279,1.0,'','Air'), (654,279,1.0,'','Animal'), (724,279,1.0),
                # hoard one-time bonuses
                (176,700,0.0), (176,815,0.0),
                # hoard forms (passive bonuses)
                (332,700,0.0), (332,815,0.0), (332,950,0.0),
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
        color = random.choice(colors)
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
    gp = GamePlayer(game=game, name=name, spirit=spirit, color=color, aspect=aspect, energy=setup_energy, base_energy_per_turn=spirit_base_energy_per_turn[spirit.name])
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

    make_initial_hand(gp)

    return redirect(reverse('game_setup', args=[game.id]))

def make_initial_hand(gp, remove_from_decks=True):
    game = gp.game
    gp.hand.set(Card.objects.filter(spirit=gp.spirit))
    if gp.full_name() in spirit_additional_cards:
        cards = [Card.objects.get(name=name) for name in spirit_additional_cards[gp.full_name()]]
        gp.hand.add(*cards)
        # Iterates over cards twice, but cards is currently small for all spirits, so not an issue yet.
        game.minor_deck.remove(*[card for card in cards if card.type == Card.MINOR])
        game.major_deck.remove(*[card for card in cards if card.type == Card.MAJOR])
    if gp.full_name() in spirit_remove_cards:
        gp.hand.remove(*[Card.objects.get(name=name) for name in spirit_remove_cards[gp.full_name()]])

def import_game(request):
    def cards_with_name(cards):
        # Cards can be specified as either:
        # - just their name as a string
        # - or a dict with key "name"
        # (it is an error to provide something other than a string or dict)
        names = {(card if isinstance(card, str) else card['name']) for card in cards}
        exact_name_matches = Card.objects.filter(name__in=names)
        if exact_name_matches.count() == len(cards):
            return exact_name_matches

        # TODO: Is there a way to do a case-insensitive match on a set?
        # maybe not: https://stackoverflow.com/questions/2667524/django-query-case-insensitive-list-match
        remaining_names_needed = names - {card.name for card in exact_name_matches}
        remaining_cards = [Card.objects.get(name__iexact=name) for name in remaining_names_needed]
        if len(remaining_cards) == len(remaining_names_needed):
            return list(exact_name_matches) + remaining_cards
        # TODO: This feedback needs to be shown in UI
        still_not_matched = remaining_names_needed - {card.name for card in remaining_cards}
        raise ValueError(f"Couldn't find cards {still_not_matched}")

    # The general strategy of the importer is that it will allow most fields to be optional,
    # using a reasonable default for any field not defined.
    #
    # Really, this should be unnecessary for games that were exported from the API,
    # as they should have all the fields,
    # but it doesn't seem to hurt to be permissive here.

    to_import = json.load(request.FILES['json'])
    game = Game(
            name=to_import.get('name', 'Untitled Imported Game'),
            scenario=to_import.get('scenario', ''),
            always_suffix_screenshot=to_import.get('always_suffix_screenshot', False),
            )
    # we are not importing the discord_channel,
    # because it's not yet been proven to be desirable to automatically do this.
    game.save()

    if 'discard_pile' in to_import:
        game.discard_pile.set(discards := cards_with_name(to_import['discard_pile']))
        cards_in_game = {card.id for card in discards}
    else:
        cards_in_game = set()

    # set minor/major decks after we've imported players,
    # because we may want to exclude cards players are holding.

    # if any player doesn't have colour defined,
    # we need to assign an unused colour,
    # not duplicating a player that does have a colour defined
    colours = {color for (color, _) in GamePlayer.COLORS}
    used_colours = {player.get('color', '') for player in to_import.get('players', [])}
    available_colours = colours - used_colours
    if not available_colours:
        available_colours = colours

    # the API shows the last-added player first, as does the UI (last-added player farthest to the left).
    # to preserve the right ordering we have to import players in the reverse order!
    for player in reversed(to_import.get('players', [])):
        elts = (temp_or_perm + "_" + elt for temp_or_perm in ("temporary", "permanent") for elt in ("sun", "moon", "fire", "air", "water", "earth", "plant", "animal"))
        # if these basic attributes aren't set, we'll rely on the database defaults
        basic_attrs = {attr: player[attr] for attr in (
            'name', 'aspect', 'energy',
            'ready', 'paid_this_turn', 'gained_this_turn',
            'last_unready_energy', 'last_ready_energy',
            'bargain_paid_this_turn', 'bargain_cost_per_turn',
            'spirit_specific_resource', 'spirit_specific_per_turn_flags',
            *elts,
            ) if attr in player}

        # Spirit can be specified as either:
        # - just their name as a string
        # - or a dict with key "name"
        # Error if they don't have a spirit defined.
        spirit_name = player['spirit'] if isinstance(player['spirit'], str) else player['spirit']['name']
        gp = GamePlayer(
                game=game,
                **basic_attrs,
                color=player.get('color', next(iter(available_colours))),
                spirit=Spirit.objects.get(name__iexact=spirit_name),
                base_energy_per_turn=spirit_base_energy_per_turn[spirit_name],
                )
        if gp.color in available_colours:
            available_colours.remove(gp.color)
            # if there are no colours left, we'll just have to repopulate.
            if not available_colours:
                available_colours = {color for (color, _) in GamePlayer.COLORS}
        gp.save()

        for (i, (expected_presence, import_presence)) in enumerate(zip(spirit_presence[spirit_name], itertools.chain(player.get('presence', []), itertools.repeat(None)))):
            expected_energy = expected_presence[3] if 3 < len(expected_presence) else ''
            expected_elements = expected_presence[4] if 4 < len(expected_presence) else ''

            if import_presence:
                # limitation: This will cause the import to fail if we change the order of spirits' presences.
                # maybe it's better to also import the top/left coordinates.
                # we aren't doing this yet because the API doesn't export them.
                if import_presence['energy'] != expected_energy:
                    raise ValueError(f"presence at {expected_presence[0]}, {expected_presence[1]} should have {expected_energy} energy but had {import_presence['energy']}")
                if import_presence['elements'] != expected_elements:
                    raise ValueError(f"presence at {expected_presence[0]}, {expected_presence[1]} should have {expected_elements} elements but had {import_presence['elements']}")
                gp.presence_set.create(left=expected_presence[0], top=expected_presence[1], opacity=import_presence['opacity'], energy=import_presence['energy'], elements=import_presence['elements'])
            else:
                expected_opacity = 0.0 if gp.aspect == 'Locus' and i == 0 else expected_presence[2]
                gp.presence_set.create(left=expected_presence[0], top=expected_presence[1], opacity=expected_opacity, energy=expected_energy, elements=expected_elements)

        if 'hand' in player:
            gp.hand.set(hand := cards_with_name(player['hand']))
            cards_in_game |= {card.id for card in hand}
        else:
            # We haven't made the major/minor decks yet
            # (because we need to know what cards to exclude from it)
            # so we should not remove cards from it yet,
            # only record the cards so that we remove them when the decks are made.
            make_initial_hand(gp, remove_from_decks=False)
            if gp.full_name() in spirit_additional_cards:
                cards_in_game |= {Card.objects.get(name=card).id for card in spirit_additional_cards[gp.full_name()]}

        for name in ('discard', 'play', 'selection', 'days', 'healing'):
            if name in player:
                getattr(gp, name).set(cards := cards_with_name(player[name]))
                cards_in_game |= {card.id for card in cards}
        if 'impending' in player:
            for impending in player['impending']:
                card = Card.objects.get(name__iexact=impending['card'] if isinstance(impending['card'], str) else impending['card']['name'])
                GamePlayerImpendingWithEnergy(
                        gameplayer=gp,
                        card=card,
                        **{attr: impending[attr] for attr in ('in_play', 'energy', 'this_turn') if attr in impending},
                        ).save()
                cards_in_game.add(card.id)

    for (name, type) in (('minor_deck', Card.MINOR), ('major_deck', Card.MAJOR)):
        deck = getattr(game, name)
        if name in to_import:
            deck.set(cards_with_name(to_import[name]))
        else:
            # if someone imports a discard pile and not a major/minor deck,
            # exclude discarded cards and cards being held by any player
            deck.set(Card.objects.filter(type=type).exclude(id__in=cards_in_game))

    return redirect(reverse('view_game', args=[game.id]))

def view_game(request, game_id, spirit_spec=None):
    game = get_object_or_404(Game, pk=game_id)
    if request.method == 'POST':
        if 'spirit_spec' in request.POST:
            spirit_spec = request.POST['spirit_spec']

        def without_suffix(ss):
            name, ext = os.path.splitext(os.path.basename(ss.url))
            if len(name) >= 8 and name[-8] == '_':
                return f"{name[:-8]}{ext}"
        existing_files = [without_suffix(ss) for ss in [game.screenshot, game.screenshot2] if ss]

        for key, form_class in (('screenshot', GameForm), ('screenshot2', GameForm2)):
            if key not in request.FILES:
                continue

            # Some hosts always use the same filename for their uploads.
            # Django's behaviour is to try to use that filename,
            # but suffix it with random characters if it already exists.
            #
            # Because we use django_cleanup, which deletes previous files,
            # every other file will be stored at the same location:
            # name, name_suffix1, name, name_suffix2, name, name_suffix3...
            #
            # If this happens, browsers may use the cached version of the unsuffixed file,
            # so players will see the cached version from a previous upload.
            #
            # We can try to control this by setting the max age on the cache (web server config),
            # but it's not clear what value we should use,
            # and ultimately the behaviour would be at the browser's discretion.
            #
            # Overall it seems best to detect when a game is reusing the same filenames,
            # and add a suffix ourselves if necessary.
            #
            # if the existing screenshot has filename e.g. name_abc1234.png,
            # detect when they upload the file name.png
            if not game.always_suffix_screenshot and request.FILES[key].name in existing_files:
                from django.utils.crypto import get_random_string
                name, ext = os.path.splitext(request.FILES[key].name)
                request.FILES[key].name = f"{name}_{get_random_string(7)}{ext}"

            form = form_class(request.POST, request.FILES, instance=game)
            if form.is_valid():
                form.save()
                add_log_msg(game, text=f'New screenshot uploaded.', images='.' + getattr(game, key).url)

        return redirect(reverse('view_game', args=[game.id, spirit_spec] if spirit_spec else [game.id]))

    tab_id = try_match_spirit(game, spirit_spec) or game.gameplayer_set.values_list('id', flat=True).first()
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
        aspect_match = game.gameplayer_set.filter(aspect__iexact=spirit_spec).values_list('id', flat=True).first()
        if aspect_match:
            return aspect_match
        # prefer the base spirit if they search for a spirit name,
        # in case there is one base and one aspected spirit in the same game.
        base_spirit_match = game.gameplayer_set.filter(spirit__name__iexact=spirit_spec, aspect=None).values_list('id', flat=True).first()
        if base_spirit_match:
            return base_spirit_match
        spirit_match = game.gameplayer_set.filter(spirit__name__iexact=spirit_spec).values_list('id', flat=True).first()
        if spirit_match:
            return spirit_match

        # look for an exact match first, in case someone's name is a substring of another
        # on the other hand, if someone's name is exactly a spirit or aspect's name, not much we can do!
        player_exact_match = game.gameplayer_set.filter(name__iexact=spirit_spec).values_list('id', flat=True).first()
        if player_exact_match:
            return player_exact_match
        player_match = game.gameplayer_set.filter(name__icontains=spirit_spec).values_list('id', flat=True).first()
        if player_match:
            return player_match

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

    add_log_msg(game, text=f'Host {draw_result}', cards=cards_drawn)

    card_names = ', '.join(card.name for card in cards_drawn)
    return with_log_trigger(render(request, 'host_draw.html', {'msg': f"You {draw_result}{draw_result_explain}: {card_names}", 'cards': cards_drawn}))

def cards_from_deck(game, cards_needed, type):
    if type == 'minor':
        deck = game.minor_deck
    elif type == 'major':
        deck = game.major_deck
    else:
        raise ValueError(f"can't draw from {type} deck")

    cards_have = deck.count()

    if cards_have >= cards_needed:
        cards_drawn = random.sample(list(deck.all()), cards_needed)
        deck.remove(*cards_drawn)
    else:
        # reshuffle needed, but first draw all the cards we do have
        cards_drawn = list(deck.all())
        cards_remain = cards_needed - cards_have
        deck.clear()
        reshuffle_discard(game, type)
        if deck.count() >= cards_remain:
            new_cards = random.sample(list(deck.all()), cards_remain)
            cards_drawn.extend(new_cards)
            deck.remove(*new_cards)
        else:
            cards_drawn.extend(list(deck.all()))
            deck.clear()

    return cards_drawn

def reshuffle_discard(game, type):
    if type == 'minor':
        minors = game.discard_pile.filter(type=Card.MINOR).all()
        game.discard_pile.remove(*minors)
        game.minor_deck.add(*minors)
    elif type == 'major':
        majors = game.discard_pile.filter(type=Card.MAJOR).all()
        game.discard_pile.remove(*majors)
        game.major_deck.add(*majors)
    else:
        raise ValueError(f"can't reshuffle {type} deck")

    add_log_msg(game, text=f'Re-shuffling {type} power deck')

def take_powers(request, player_id, type, num):
    player = get_object_or_404(GamePlayer, pk=player_id)
    spoiler = request.GET.get('spoiler_power_gain', False)

    taken_cards = cards_from_deck(player.game, num, type)
    player.hand.add(*taken_cards)

    if num == 1:
        add_log_msg(player.game, player=player, text=f'takes a {type} power', cards=taken_cards, spoiler=spoiler)
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
        add_log_msg(player.game, player=player, text=f'gains {num} {type} powers', cards=taken_cards, spoiler=spoiler)

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

    return render(request, 'player.html', {'player': player})

def gain_power(request, player_id, type, num):
    player = get_object_or_404(GamePlayer, pk=player_id)
    spoiler = request.GET.get('spoiler_power_gain', False)

    selection = cards_from_deck(player.game, num, type)
    player.selection.set(selection)

    # TODO: Should we set a flag on the player, such that when they actually select the card, it is also spoilered?
    add_log_msg(player.game, player=player, text=f'gains a {type} power. Choices', cards=selection, spoiler=spoiler)

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

    add_log_msg(game, text=f'{card.name} returned to the deck')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

def choose_from_discard(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.game.discard_pile, pk=card_id)
    player.hand.add(card)
    player.game.discard_pile.remove(card)

    add_log_msg(player.game, player=player, text=f'takes {card.name} from the power discard pile')

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

    add_log_msg(player.game, player=player, text=f'sends {card.name} to the Days That Never Were')

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
        player.game.discard_pile.add(*player.selection.all())
        player.selection.clear()

    add_log_msg(player.game, player=player, text=f'gains {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

def undo_gain_card(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    game = player.game

    to_remove = []
    minors = []
    majors = []
    for sel in player.selection.all():
        # we don't remove from player.selection immediately,
        # as that would modify the selection we're iterating over,
        # plus we want to add/remove all at once.
        if sel.type == Card.MINOR:
            minors.append(sel)
            to_remove.append(sel)
        elif sel.type == Card.MAJOR:
            majors.append(sel)
            to_remove.append(sel)
        elif sel.is_healing():
            to_remove.append(sel)
        # If it's not any of these types, we'll leave it in selection, as something's gone wrong.

    game.minor_deck.add(*minors)
    game.major_deck.add(*majors)
    player.selection.remove(*to_remove)

    return with_log_trigger(render(request, 'player.html', {'player': player}))

def choose_healing_card(request, player, card):
    if card.name.startswith('Waters'):
        player.healing.remove(player.healing.filter(name__startswith='Waters').first())
    else:
        player.healing.clear()
    player.healing.add(card)
    player.selection.clear()

    add_log_msg(player.game, player=player, text=f'claims {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

def choose_days(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.days, pk=card_id)
    player.hand.add(card)
    player.days.remove(card)

    add_log_msg(player.game, player=player, text=f'gains {card.name} from the Days That Never Were')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

def create_days(request, player_id, num):
    player = get_object_or_404(GamePlayer, pk=player_id)
    game = player.game

    for (deck, name) in [(game.minor_deck, 'minor'), (game.major_deck, 'major')]:
        days = random.sample(list(deck.all()), num)
        deck.remove(*days)
        player.days.add(*days)
        add_log_msg(player.game, player=player, text=f'starts with {num} {name} powers in the Days That Never Were', cards=days)

    return with_log_trigger(render(request, 'player.html', {'player': player}))

def gain_energy_on_impending(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    to_gain = player.impending_energy()
    # You only gain energy on cards made impending on previous turns.
    impendings = player.gameplayerimpendingwithenergy_set.filter(this_turn=False)
    for impending in impendings:
        # Let's cap the energy at the cost of the card.
        # There's no real harm in letting it exceed the cost
        # (the UI will still let you play it),
        # it's just that undoing it will require extra clicks on the -1.
        impending.energy += to_gain
        if impending.energy >= impending.cost_with_scenario:
            impending.energy = impending.cost_with_scenario
            impending.in_play = True
    GamePlayerImpendingWithEnergy.objects.bulk_update(impendings, ['energy', 'in_play'])
    player.spirit_specific_per_turn_flags |= GamePlayer.SPIRIT_SPECIFIC_INCREMENTED_THIS_TURN
    player.save()

    return render(request, 'player.html', {'player': player})

def impend_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.hand, pk=card_id)
    player.impending_with_energy.add(card)
    player.hand.remove(card)

    return render(request, 'player.html', {'player': player})

def unimpend_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.impending_with_energy, pk=card_id)
    player.impending_with_energy.remove(card)
    player.hand.add(card)

    return render(request, 'player.html', {'player': player})

def add_energy_to_impending(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.impending_with_energy, pk=card_id)
    impending_with_energy = get_object_or_404(GamePlayerImpendingWithEnergy, gameplayer=player, card=card)
    if not impending_with_energy.in_play and impending_with_energy.energy < impending_with_energy.cost_with_scenario:
        impending_with_energy.energy += 1
        impending_with_energy.save()

    return render(request, 'player.html', {'player': player})

def remove_energy_from_impending(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.impending_with_energy, pk=card_id)
    impending_with_energy = get_object_or_404(GamePlayerImpendingWithEnergy, gameplayer=player, card=card)
    if not impending_with_energy.in_play and impending_with_energy.energy > 0:
        impending_with_energy.energy -= 1
        impending_with_energy.save()

    return render(request, 'player.html', {'player': player})

def play_from_impending(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.impending_with_energy, pk=card_id)
    impending_with_energy = get_object_or_404(GamePlayerImpendingWithEnergy, gameplayer=player, card=card)
    if not impending_with_energy.in_play and impending_with_energy.energy >= impending_with_energy.cost_with_scenario:
        impending_with_energy.in_play = True
        impending_with_energy.save()

    return render(request, 'player.html', {'player': player})

def unplay_from_impending(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.impending_with_energy, pk=card_id)
    impending_with_energy = get_object_or_404(GamePlayerImpendingWithEnergy, gameplayer=player, card=card)
    if impending_with_energy.in_play:
        impending_with_energy.in_play = False
        impending_with_energy.save()

    return render(request, 'player.html', {'player': player})

def play_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.hand, pk=card_id)
    player.play.add(card)
    player.hand.remove(card)

    # no log message but deciding to keep with_log_trigger anyway as they could affect what cards the player wants to play
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def unplay_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.play, pk=card_id)
    player.hand.add(card)
    player.play.remove(card)

    # no log message but deciding to keep with_log_trigger anyway as they could affect what cards the player wants to play
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

    add_log_msg(player.game, player=player, text=f'forgets {card.name}')

    return with_log_trigger(render(request, 'player.html', {'player': player}))


def reclaim_card(request, player_id, card_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    card = get_object_or_404(player.discard, pk=card_id)
    player.hand.add(card)
    player.discard.remove(card)

    # no log message but deciding to keep with_log_trigger anyway as they could affect what cards the player wants to play
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def reclaim_all(request, player_id, element=None):
    player = get_object_or_404(GamePlayer, pk=player_id)
    if element:
        # just validate that it's an element, don't need to keep the value
        _ = Elements[element.capitalize()]
        with_element = player.discard.filter(elements__contains=element.capitalize())
        player.hand.add(*with_element)
        player.discard.remove(*with_element)
    else:
        player.hand.add(*player.discard.all())
        player.discard.clear()

    # no log message but deciding to keep with_log_trigger anyway as they could affect what cards the player wants to play
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def discard_all(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    # if we used the cached property cards_in_play here, we'd have to clear it,
    # so let's just not use it.
    player.discard.add(*player.play.all())

    if player.spirit.name == 'Earthquakes':
        played_impending = player.gameplayerimpendingwithenergy_set.filter(in_play=True)
        player.discard.add(*played_impending.values_list('card_id', flat=True))
        played_impending.delete()
        player.gameplayerimpendingwithenergy_set.update(this_turn=False)

    player.play.clear()
    player.ready = False
    player.last_unready_energy = player.energy
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
    player.bargain_paid_this_turn = 0
    player.spirit_specific_per_turn_flags = 0
    player.save()

    # no log message but deciding to keep with_log_trigger anyway as an update is useful at the end of the turn
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

    # no log message but deciding to keep with_log_trigger anyway as they could affect what cards the player wants to play
    return with_log_trigger(render(request, 'player.html', {'player': player}))

def ready(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.ready = True
    player.last_ready_energy = player.energy
    player.save()

    if player.gained_this_turn:
        add_log_msg(player.game, player=player, text=f'gains {player.get_gain_energy()} energy')
    for card in player.cards_in_play:
        add_log_msg(player.game, player=player, text=f'plays {card.name}')
    if player.spirit.name == 'Earthquakes':
        add_impending_log_msgs(player)
    if player.paid_this_turn:
        add_log_msg(player.game, player=player, text=f'pays {player.get_play_cost()} energy')
    add_log_msg(player.game, player=player, text=f'started with {player.last_unready_energy_friendly} energy and now has {player.energy} energy')
    if player.has_spirit_specific_resource():
        add_spirit_specific_resource_msgs(player)
    add_log_msg(player.game, player=player, text=f'is ready')

    if player.game.gameplayer_set.filter(ready=False).count() == 0:
        add_log_msg(player.game, text=f'All spirits are ready!')

    return with_log_trigger(render(request, 'player.html', {'player': player}))

def add_impending_log_msgs(player):
    for impended_card_with_energy in player.gameplayerimpendingwithenergy_set.all().prefetch_related('card'):
        card = impended_card_with_energy.card
        if impended_card_with_energy.this_turn:
            add_log_msg(player.game, player=player, text=f'impends {card.name}')
        elif impended_card_with_energy.in_play:
            add_log_msg(player.game, player=player, text=f'plays {card.name} from impending')
        else:
            add_log_msg(player.game, player=player, text=f'adjusts energy on impended card {card.name} ({impended_card_with_energy.energy}/{impended_card_with_energy.cost_with_scenario})')

def add_spirit_specific_resource_msgs(player):
    # TODO: Add support for logging spirit-specific elements for Memory and Wounded Waters
    if player.spirit_specific_resource_elements() is None:
        add_log_msg(player.game, player=player, text=f'has {player.spirit_specific_resource} {player.spirit_specific_resource_name()}')

def change_energy(request, player_id, amount):
    amount = int(amount)
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.energy += amount
    player.save()

    return render(request, 'energy.html', {'player': player})

def pay_energy(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    amount = player.get_play_cost()
    player.energy -= amount
    player.paid_this_turn = True
    player.save()

    return render(request, 'energy.html', {'player': player})

def gain_energy(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    amount = player.get_gain_energy()
    player.gain_energy_or_pay_debt(amount)
    player.gained_this_turn = True
    player.save()

    # no log message but deciding to keep with_log_trigger anyway as they could affect what cards the player wants to play
    return with_log_trigger(render(request, 'energy.html', {'player': player}))

def change_bargain_cost_per_turn(request, player_id, amount):
    amount = int(amount)
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.bargain_cost_per_turn = max(0, player.bargain_cost_per_turn + amount)
    # what if they adjust bargain_cost_per_turn to be less than bargain_paid_this_turn?
    # should we adjust bargain_paid_this_turn down?
    # let's say no for now, because the player may need to adjust their energy count
    player.save()
    return render(request, 'energy_and_spirit_resource.html' if player.spirit_specific_resource_gives_energy else 'energy.html', {'player': player})

def change_bargain_paid_this_turn(request, player_id, amount):
    amount = int(amount)
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.bargain_paid_this_turn = max(0, min(player.bargain_paid_this_turn + amount, player.bargain_cost_per_turn))
    player.save()
    return render(request, 'energy_and_spirit_resource.html' if player.spirit_specific_resource_gives_energy else 'energy.html', {'player': player})

def change_spirit_specific_resource(request, player_id, amount):
    amount = int(amount)
    player = get_object_or_404(GamePlayer, pk=player_id)
    # no known spirit's spirit-specific-resource can go below 0
    player.spirit_specific_resource = max(player.spirit_specific_resource + amount, 0)
    if amount > 0:
        player.spirit_specific_per_turn_flags |= GamePlayer.SPIRIT_SPECIFIC_INCREMENTED_THIS_TURN
    elif amount < 0:
        player.spirit_specific_per_turn_flags |= GamePlayer.SPIRIT_SPECIFIC_DECREMENTED_THIS_TURN
    player.save()

    if player.spirit.name == 'Fractured':
        player.sync_time_discs_with_resource()
        # Have to render the spirit panel to show the change in discs.
        return render(request, 'player.html', {'player': player})

    return render(request, 'spirit_specific_resource.html', {'player': player})

def gain_rot(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    player.spirit_specific_resource += player.rot_gain()
    player.spirit_specific_per_turn_flags |= GamePlayer.ROT_GAINED_THIS_TURN
    player.save()

    return render(request, 'spirit_specific_resource.html', {'player': player})

def convert_rot(request, player_id):
    player = get_object_or_404(GamePlayer, pk=player_id)
    # be sure to change energy before rot,
    # because energy gain is based on rot.
    player.gain_energy_or_pay_debt(player.energy_from_rot())
    player.spirit_specific_resource -= player.rot_loss()
    player.spirit_specific_per_turn_flags |= GamePlayer.ROT_CONVERTED_THIS_TURN
    player.save()

    return render(request, 'energy_and_spirit_resource.html', {'player': player})

def toggle_presence(request, player_id, left, top):
    player = get_object_or_404(GamePlayer, pk=player_id)
    presence = get_object_or_404(player.presence_set, left=left, top=top)
    presence.opacity = abs(1.0 - presence.opacity)
    presence.save()
    if player.spirit.name == 'Fractured' and left <= Presence.FRACTURED_DAYS_TIME_X:
        # See sync_time_discs_with_resource on GamePlayer model for the sync in the other direction,
        # and reasoning why we do this.
        # You'd think we could just +/- 1 depending on the new opacity,
        # But we do have to handle the case where they had more Time than discs (10).
        player.spirit_specific_resource = player.presence_set.filter(opacity=1.0, left__lte=Presence.FRACTURED_DAYS_TIME_X).count()
        player.save(update_fields=['spirit_specific_resource'])

    return render(request, 'player.html', {'player': player})

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
    if element == 'moonfire': player.temporary_moon += 1
    player.save()

    return render(request, 'player.html', {'player': player})

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
    if element == 'moonfire':
        if player.temporary_moon > 0:
            player.temporary_moon -= 1
        elif player.temporary_fire > 0:
            player.temporary_fire -= 1
    player.save()

    return render(request, 'player.html', {'player': player})

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
    if element == 'moonfire': player.permanent_moon += 1
    player.save()

    return render(request, 'player.html', {'player': player})

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
    if element == 'moonfire':
        if player.permanent_moon > 0:
            player.permanent_moon -= 1
        elif player.permanent_fire > 0:
            player.permanent_fire -= 1
    player.save()

    return render(request, 'player.html', {'player': player})

def tab(request, game_id, player_id):
    game = get_object_or_404(Game, pk=game_id)
    player = get_object_or_404(GamePlayer, pk=player_id)
    return render(request, 'tabs.html', {'game': game, 'player': player})

def game_logs(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    logs = reversed(game.gamelog_set.order_by('-date').all()[:30])
    return render(request, 'logs.html', {'game': game, 'logs': logs})

