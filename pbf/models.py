import uuid
from enum import Enum
from collections import Counter, defaultdict

from django.db import models

def chunk(str, n):
    return [str[i:i+n] for i in range(0, len(str), n)]

def check_elements(elements, desired, equiv_elements=None):
    if type(desired) == type([]):
        return any([check_elements(elements, d) for d in desired])

    chunks = chunk(desired, 2)
    if equiv_elements:
        threshold = sum(int(c[0]) for c in chunks if c[1] in equiv_elements)
        in_play = sum(elements[Elements.from_char(e)] for e in equiv_elements)
        if in_play < threshold: return False
        chunks = [c for c in chunks if c[1] not in equiv_elements]

    for c in chunks:
        amt = int(c[0])
        e = Elements.from_char(c[1])
        if e and elements[e] < amt: return False
    return True


class Elements(Enum):
    Sun = 1
    Moon = 2
    Fire = 3
    Air = 4
    Water = 5
    Earth = 6
    Plant = 7
    Animal = 8

    @staticmethod
    def from_char(c):
        if c == 'S': return Elements.Sun
        if c == 'M': return Elements.Moon
        if c == 'F': return Elements.Fire
        if c == 'A': return Elements.Air
        if c == 'W': return Elements.Water
        if c == 'E': return Elements.Earth
        if c == 'P': return Elements.Plant
        if c == 'N': return Elements.Animal
        return None

class Threshold():
    def __init__(self, x, y, achieved):
        self.x = x
        self.y = y
        self.achieved = achieved

    def __repr__(self):
        return f'{self.achieved} - {self.x}, {self.y}'

class Spirit(models.Model):
    name = models.CharField(max_length=255, blank=False)

    def __str__(self):
        return self.name

    def starting_hand(self):
        return Card.objects.filter(spirit_id=self.id)

    def url(self):
        return '/pbf/' + self.name.replace(' ', '-').lower() + '.jpg'

class Card(models.Model):
    class Meta:
        ordering = ('name', )

    MINOR = 0
    MAJOR = 1
    UNIQUE = 2
    SPECIAL = 3

    name = models.CharField(max_length=255, blank=False)
    TYPES = (
        (MINOR, 'Minor'),
        (MAJOR, 'Major'),
        (UNIQUE, 'Unique'),
        (SPECIAL, 'Special'),
    )
    type = models.IntegerField(choices=TYPES)
    spirit = models.ForeignKey(Spirit, null=True, on_delete=models.CASCADE)
    cost = models.IntegerField()
    elements = models.CharField(max_length=255, blank=False)

    FAST = 1
    SLOW = 2
    speed = models.IntegerField(choices=[(0, 'Unknown'), (FAST, 'Fast'), (SLOW, 'Slow')])

    def __str__(self):
        return self.name

    def can_return_to_deck(self):
        return self.type in (self.MINOR, self.MAJOR)

    HEALING_NAMES = frozenset(('Serene Waters', 'Waters Renew', 'Roiling Waters', 'Waters Taste of Ruin'))
    def is_healing(self):
        return self.name in self.HEALING_NAMES

    def url(self):
        return '/pbf/' + self.name.replace(",", '').replace("-", '').replace("'", '').replace(' ', '_').lower() + '.jpg'

    def get_elements(self):
        counter = Counter()
        for e in self.elements.split(','):
            if len(e) > 0:
                counter[Elements[e]] = 1
        return counter

    def thresholds(self, elements, equiv_elements=None):
        thresholds = []
        for t in card_thresholds.get(self.name, []):
            thresholds.append(Threshold(t[0], t[1], check_elements(elements, t[2], equiv_elements)))
        return thresholds

    def healing_thresholds(self, num_healing_cards, healing_markers):
        elements = {elt: n for (_, _, n, elt) in healing_markers}
        total_elements = sum(elements.values())
        if self.name.startswith('Waters'):
            y, elt = (80, 'animal') if self.name == 'Waters Taste of Ruin' else (74, 'water')
            return [Threshold(2, y, total_elements >= 5 and elements[elt] >= 3)]
        else:
            y, elt = (65, 'animal') if self.name == 'Roiling Waters' else (68, 'water')
            return [
                Threshold(2, y, total_elements >= 3 and elements[elt] >= 2),
                Threshold(2, y + 8, num_healing_cards == 0),
            ]

class Game(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    turn = models.IntegerField(default=1)
    name = models.CharField(max_length=255, blank=False)
    minor_deck = models.ManyToManyField(Card, related_name='minor_deck', blank=True)
    major_deck = models.ManyToManyField(Card, related_name='major_deck', blank=True)
    discard_pile = models.ManyToManyField(Card, related_name='discard_pile', blank=True)
    screenshot = models.ImageField(upload_to='screenshot', blank=True)
    screenshot2 = models.ImageField(upload_to='screenshot', blank=True)
    scenario = models.CharField(max_length=255, blank=True)
    #CHANNELS = (
    #    ('957389286834057306', '#pbp1-updates'),
    #    ('883019769937268816', '#pbp2-updates'),
    #    ('1022258668428865586', '#pbp3-updates'),
    #    ('1025502499387478127', '#pbp4-updates'),
    #    ('1010285070680072192', '#pbp-allspirit-updates'),
    #    ('1090363335888863375', '#pbp5-updates'),
    #    ('703767917854195733', '#bot-testing'),
    #)
    discord_channel = models.CharField(max_length=255, default="", blank=True)

    def __str__(self):
        return str(self.id)

    def color_freq(self):
        colors = ['red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'purple', 'pink', 'brown', 'white']
        player_colors = Counter(self.gameplayer_set.values_list('color', flat=True))
        return [(c, player_colors[c], colors_to_circle_color_map[c]) for c in colors]


colors_to_circle_color_map = {
        'blue': '#705dff',
        'green': '#0d9501',
        'orange': '#d15a01',
        'purple': '#af58ed',
        'red': '#fc3b5a',
        'yellow': '#ffd585',
        'cyan': '#58edde',
        'brown': '#cc9054',
        'pink': '#ed93e4',
        'white': '#eaeaeb',
        }

colors_to_emoji_map = {
        'blue': '💙',
        'green': '💚',
        'orange': '🧡',
        'purple': '💜',
        'red': '❤️',
        'yellow': '💛',
        'cyan': '🩵',
        'brown': '🤎',
        'pink': '🩷',
        'white': '🤍',
        }

# eight elements to fit in a 32-bit integer: each element can have four bits
# (so can store values from 0 to 15 inclusive)
ELEMENT_WIDTH = 4
ELEMENT_MASK = (1 << ELEMENT_WIDTH) - 1

class GamePlayer(models.Model):
    class Meta:
        ordering = ('-id', )

    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True)
    spirit = models.ForeignKey(Spirit, blank=False, on_delete=models.CASCADE)
    hand = models.ManyToManyField(Card, related_name='hand', blank=True)
    discard = models.ManyToManyField(Card, related_name='discard', blank=True)
    play = models.ManyToManyField(Card, related_name='play', blank=True)
    selection = models.ManyToManyField(Card, related_name='selection', blank=True)
    days = models.ManyToManyField(Card, related_name='days', blank=True)
    # had to rename from "impending" to enable ManyToManyField migration
    impending_with_energy = models.ManyToManyField(Card, through='GamePlayerImpendingWithEnergy', related_name='impending_with_energy', blank=True)
    healing = models.ManyToManyField(Card, related_name='healing', blank=True)
    ready = models.BooleanField(default=False)
    paid_this_turn = models.BooleanField(default=False)
    gained_this_turn = models.BooleanField(default=False)
    energy = models.IntegerField(default=0)
    COLORS = (
        ('blue', 'blue'),
        ('green', 'green'),
        ('orange', 'orange'),
        ('purple', 'purple'),
        ('red', 'red'),
        ('yellow', 'yellow'),
        ('cyan', 'cyan'),
        ('brown', 'brown'),
        ('pink', 'pink'),
        ('white', 'white'),
    )
    color = models.CharField(max_length=255, blank=True, choices=COLORS)
    temporary_sun = models.IntegerField(default=0)
    temporary_moon = models.IntegerField(default=0)
    temporary_fire = models.IntegerField(default=0)
    temporary_air = models.IntegerField(default=0)
    temporary_water = models.IntegerField(default=0)
    temporary_earth = models.IntegerField(default=0)
    temporary_plant = models.IntegerField(default=0)
    temporary_animal = models.IntegerField(default=0)
    permanent_sun = models.IntegerField(default=0)
    permanent_moon = models.IntegerField(default=0)
    permanent_fire = models.IntegerField(default=0)
    permanent_air = models.IntegerField(default=0)
    permanent_water = models.IntegerField(default=0)
    permanent_earth = models.IntegerField(default=0)
    permanent_plant = models.IntegerField(default=0)
    permanent_animal = models.IntegerField(default=0)
    aspect = models.CharField(max_length=255, default=None, null=True, blank=True)
    # starting_energy denotes the base energy gain PER TURN,
    # when no presence has been removed from the tracks.
    # It DOES NOT denote energy that the spirit starts with at setup
    # (simply set the energy at creation time for this).
    # It would be best to rename starting_energy to base_energy_per_turn,
    # but this will need a database change.
    starting_energy = models.IntegerField(default=0)
    # A number of spirits have a resource that's specific to them.
    # Rather than have separate fields + endpoints that can modify each of them,
    # we'll use a single field for this purpose,
    # with the main motivation of avoiding repetitive code.
    # (and a secondary motivation of having fewer columns in the database)
    #
    # To see the list of spirits that use this field, see spirit_specific_resource_name below.
    spirit_specific_resource = models.IntegerField(default=0)
    # some spirits allow you to do something to their spirit-specific resource,
    # but only once per turn.
    # again, to reduce some repetitive code, we'll use one field for all of these.
    spirit_specific_per_turn_flags = models.PositiveIntegerField(default=0)

    # Meanings for specific bits in the spirit-specific per-turn flags:
    # It's okay for different spirits to assign different meanings to the same bits.
    # But do note that no spirit should assign a different meaning to these generic ones:
    # (these can be useful for e.g. Unconstrained Sharp Fangs Behind the Leaves)
    SPIRIT_SPECIFIC_INCREMENTED_THIS_TURN = 1 << 0
    SPIRIT_SPECIFIC_DECREMENTED_THIS_TURN = 1 << 1
    # Spirit-specific bits:
    # Spreading Rot Renews the Earth:
    ROT_GAINED_THIS_TURN = 1 << 2 # Whether they've gained from their track (NOT incrementing using the +1 button)
    ROT_CONVERTED_THIS_TURN = 1 << 3

    def spirit_specific_incremented_this_turn(self):
        return self.spirit_specific_per_turn_flags & GamePlayer.SPIRIT_SPECIFIC_INCREMENTED_THIS_TURN

    def spirit_specific_decremented_this_turn(self):
        return self.spirit_specific_per_turn_flags & GamePlayer.SPIRIT_SPECIFIC_DECREMENTED_THIS_TURN

    def rot_gained_this_turn(self):
        return self.spirit_specific_per_turn_flags & GamePlayer.ROT_GAINED_THIS_TURN

    def rot_converted_this_turn(self):
        return self.spirit_specific_per_turn_flags & GamePlayer.ROT_CONVERTED_THIS_TURN

    def __str__(self):
        return str(self.game.id) + ' - ' + str(self.spirit.name)

    def spirit_specific_resource_name(self):
        d = {
            'Rot': 'Rot',
            'Round DownRot': 'Rot',
            'Covets': 'Metal',
            'UnconstrainedFangs': 'Prepared Beasts',
            'Shifting': 'Prepared Elements',
            'IntensifyShifting': 'Prepared Elements',
            'MentorShifting': 'Prepared Elements',
            'Waters': 'Healing Markers',
        }
        return d.get(self.full_name())

    # these spirits use the spirit-specific resource field to store a number of markers of each element.
    # since the integer field is only guaranteed to be 32 bits wide and there are eight elements,
    # we can use four bits per element (a max of 15 of each).
    def spirit_specific_resource_elements(self):
        d = {
            'Shifting': ('sun', 'moon', 'fire', 'air', 'water', 'earth', 'plant', 'animal'),
            'Waters': ('water', 'animal'),
        }
        # Currently doesn't change based on aspect, so just uses spirit name instead of spirit + aspect
        elts = d.get(self.spirit.name)
        if not elts:
            return elts
        # for each element return a 4-tuple:
        # amount to add to spirit_specific_resource to increment the count of that element
        # same but for decrementing
        # current amount of that element
        # the element's name
        # (have to do it this way because it's not clear how to make the template perform these calculations)
        return [(
            1 << i,
            -(1 << i),
            (self.spirit_specific_resource >> i) & ELEMENT_MASK,
            e,
        ) for (i, e) in zip(range(0, ELEMENT_WIDTH * len(elts), ELEMENT_WIDTH), elts)]

    # If true, it makes sense to +1/-1 the spirit-specific resource
    # Assumed to be true unless a spirit specifically specifies not.
    # (also has no effect for spirits using spirit_specific_resource_elements)
    def increment_decrement_specific_resource(self):
        d = {
        }
        return d.get(self.full_name(), True)

    def aspect_url(self):
        return f'pbf/aspect-{self.aspect.replace(" ", "_").lower()}.jpg'

    def aspect_left(self):
        if self.aspect == 'Immense':
            return 650
        elif self.aspect == 'Pandemonium':
            return 370
        elif self.aspect == 'Sunshine':
            return 700
        else:
            return 0

    def aspect_top(self):
        if self.aspect == 'Immense':
            return 360
        elif self.aspect == 'Pandemonium':
            return 360
        elif self.aspect == 'Sunshine':
            return 360
        else:
            return 400

    def disk_url(self):
        return 'pbf/disk_' + self.color + '.png'

    def circle_color(self):
        return colors_to_circle_color_map[self.color]

    @property
    def circle_emoji(self):
        return colors_to_emoji_map[self.color]

    @property
    def elements(self):
        counter = Counter()
        counter[Elements.Sun] += self.temporary_sun + self.permanent_sun
        counter[Elements.Moon] += self.temporary_moon + self.permanent_moon
        counter[Elements.Fire] += self.temporary_fire + self.permanent_fire
        counter[Elements.Air] += self.temporary_air + self.permanent_air
        counter[Elements.Water] += self.temporary_water + self.permanent_water
        counter[Elements.Earth] += self.temporary_earth + self.permanent_earth
        counter[Elements.Plant] += self.temporary_plant + self.permanent_plant
        counter[Elements.Animal] += self.temporary_animal + self.permanent_animal

        if self.aspect in ('Dark Fire', 'Intensify'):
            counter[Elements.Moon] += 1

        for card in self.play.all():
            counter += card.get_elements()
        if self.spirit.name == 'Earthquakes':
            played_impending = self.impending_with_energy.filter(gameplayerimpendingwithenergy__in_play=True)
            for card in played_impending.all():
                counter += card.get_elements()
        for presence in self.presence_set.all():
            counter += presence.get_elements()
        return defaultdict(int, counter)

    def equiv_elements(self):
        if self.aspect == 'Dark Fire': return "MF"
        return None

    def sun(self): return self.elements[Elements.Sun]
    def moon(self): return self.elements[Elements.Moon]
    def fire(self): return self.elements[Elements.Fire]
    def air(self): return self.elements[Elements.Air]
    def water(self): return self.elements[Elements.Water]
    def earth(self): return self.elements[Elements.Earth]
    def plant(self): return self.elements[Elements.Plant]
    def animal(self): return self.elements[Elements.Animal]

    # Any code that creates a GamePlayer is expected to (manually) call this function once after creating it,
    # (currently add_player in views)
    # so it is suitable for any one-time setup.
    # why not override __init__? Django docs indicate doing so is *not* preferred:
    # https://docs.djangoproject.com/en/5.1/ref/models/instances/
    def init_spirit(self):
        if self.spirit.name == "Shifting":
            for e in (Elements.Moon, Elements.Air, Elements.Earth):
                # Prepare one of each.
                self.spirit_specific_resource += 1 << (ELEMENT_WIDTH * (e.value - 1))

    def full_name(self):
        name = self.spirit.name
        if self.aspect:
            name = self.aspect + name
        return name

    def get_play_cost(self):
        blitz = self.game.scenario == 'Blitz'
        return sum([card.cost - (1 if blitz and card.speed == Card.FAST else 0) for card in self.play.all()])

    def get_gain_energy(self):
        amount = max([self.starting_energy] + [p.get_energy() for p in self.presence_set.all()]) + sum([p.get_plus_energy() for p in self.presence_set.all()])
        if self.aspect == 'Immense':
            return amount * 2
        elif self.aspect == 'Spreading Hostility':
            return amount // 2 + amount % 2
        elif self.aspect == 'Exploratory' and self.spirit.name == 'Shadows':
            return amount + 1
        else:
            return amount

    def impending_energy(self):
        return max(1, max(p.impending_energy() for p in self.presence_set.all()))

    def rot_gain(self):
        return sum(p.rot() for p in self.presence_set.all())

    def rot_loss(self):
        return (self.spirit_specific_resource + (0 if self.aspect == 'Round Down' else 1)) // 2

    def energy_from_rot(self):
        return (self.rot_loss() + (0 if self.aspect == 'Round Down' else 1)) // 2

    def days_ordered(self):
        return self.days.order_by('type', 'cost')

    def thresholds(self):
        elements = self.elements
        thresholds = []
        name = self.full_name()
        equiv_elements = self.equiv_elements()
        if (name == 'Waters'):
            if self.healing.all().contains(Card.objects.get(name='Waters Renew')):
                name += ' - Renew'
            elif self.healing.all().contains(Card.objects.get(name='Waters Taste of Ruin')):
                name += ' - Ruin'
        if name == 'Earthquakes':
            # Show additional threshold indicators for whether enough cards are in play.
            #
            # We are keeping these separate from the elements threshold indicators to avoid surprise:
            # Most other threshold indicators are only counting elements,
            # so it would be too surprising if the ones for Earth Shudders, Buildings Fall also counted card plays.
            #
            # Therefore, it seems the least-surprising thing is just to show separate indicators.
            # They are placed right over the icon for card plays.
            cards_in_play = self.play.count() + self.impending_with_energy.filter(gameplayerimpendingwithenergy__in_play=True).count()
            for (y, n) in ((475, 3), (525, 5), (580, 7)):
                thresholds.append(Threshold(737, y, cards_in_play >= n))
        if name in spirit_thresholds:
            for t in spirit_thresholds[name]:
                thresholds.append(Threshold(t[0], t[1], check_elements(elements, t[2], equiv_elements)))
        return thresholds

class GamePlayerImpendingWithEnergy(models.Model):
    gameplayer = models.ForeignKey(GamePlayer, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    energy = models.IntegerField(default=0)
    in_play = models.BooleanField(default=False)
    this_turn = models.BooleanField(default=True)

    class Meta:
        db_table = "pbf_gameplayer_impending_with_energy"

    @property
    def cost_with_scenario(self):
        return self.card.cost - (1 if self.card.speed == Card.FAST and self.gameplayer.game.scenario == 'Blitz' else 0)

spirit_thresholds = {
        'EnticingBringer': [
            (360, 450, '2M2A'),
            (360, 515, '3M'),
            (635, 450, '2M1A'),
            (635, 480, '2M2N'),
            (635, 525, '3M2A1N'),
            (635, 565, '4M3A2N'),
            ],
        'ViolenceBringer': [
            (650, 450, '1M1A'),
            (650, 490, '2M1A1N'),
            (650, 530, '3M2A1N'),
            ],
        'Bringer': [
            (360, 450, '2M2A'),
            (360, 515, '3M'),
            (650, 450, '1M1A'),
            (650, 490, '2M1A1N'),
            (650, 530, '3M2A1N'),
            ],
        'ExploratoryBringer': [
            (360, 450, '2M2A'),
            (360, 535, '3M'),
            (650, 450, '1M1A'),
            (650, 490, '2M1A1N'),
            (650, 530, '3M2A1N'),
            ],
        'Downpour': [
            (360, 480, '1A3W'),
            (360, 530, '5W1E'),
            (360, 580, '3A9W2E'),
            (650, 480, '3W2P'),
            (650, 530, '5W1E2P'),
            (650, 580, '7W2E3P'),
            ],
        'Earth': [
            (370, 440, '1S2E2P'),
            (370, 480, '2S3E2P'),
            (370, 520, '2S4E3P'),
            ],
        'NourishingEarth': [
            (0, 530, '1W1P'),
            (0, 550, '1W2P'),
            (0, 575, '1W1E2P'),
            (370, 440, '1S2E2P'),
            (370, 480, '2S3E2P'),
            (370, 520, '2S4E3P'),
            ],
        'ResilenceEarth': [
            (370, 440, '1S2E2P'),
            (370, 480, '2S3E2P'),
            (370, 520, '2S4E3P'),
            ],
        'MightEarth': [
            (370, 440, '1S2E2P'),
            (370, 480, '2S3E2P'),
            (370, 520, '2S4E3P'),
            (-5, 493, '1P'),
            (-5, 535, '1S2E'),
            (-5, 565, '2P3E'),
            (-5, 595, '1S3P'),
            ],
        'EncircleFangs': [
            (360, 450, '1P2N'),
            (360, 505, '1M3N'),
            (360, 570, '1M2P4N'),
            (625, 440, '1M1F4N'),
            (625, 480, '1M2F5N'),
            ],
        'Fangs': [
            (360, 440, '2N'),
            (360, 480, '2P3N'),
            (360, 520, '2N'),
            (625, 440, '1M1F4N'),
            (625, 480, '1M2F5N'),
            ],
        'UnconstrainedFangs': [
            (360, 440, '2N'),
            (360, 480, '2P3N'),
            (360, 520, '2N'),
            (625, 440, '1M1F4N'),
            (625, 480, '1M2F5N'),
            ],
        'Finder': [
            (360, 455, '2M2A'),
            (360, 495, '2S2A'),
            (360, 535, '2M4A3W'),
            (648, 465, '1A2W'),
            (648, 505, '2A2E'),
            (648, 545, '3A2P'),
            ],
        'Fractured': [
            (360, 495, '3M1A'),
            (360, 540, '2S2M'),
            (360, 595, '3S2A'),
            (640, 470, '1S2M2A'),
            (640, 555, '2S3M2A'),
            ],
        'RegrowthGreen': [
            (365, 440, '1M2P'),
            (365, 480, '2M3P'),
            (365, 520, '3M4P'),
            (645, 450, '2W3P'),
            (645, 490, '1W3P'),
            (645, 530, '2W4P'),
            (645, 580, '3W5P'),
            ],
        'TanglesGreen': [
            (365, 445, '1S2P'),
            (365, 485, '2S3P'),
            (365, 525, '2S4P'),
            (365, 565, '3S5P'),
            (645, 440, '1W3P'),
            (645, 480, '2W4P'),
            (645, 520, '3W1E5P'),
            ],
        'Green': [
            (365, 440, '1M2P'),
            (365, 480, '2M3P'),
            (365, 520, '3M4P'),
            (645, 440, '1W3P'),
            (645, 480, '2W4P'),
            (645, 520, '3W1E5P'),
            ],
        'Spreading HostilityKeeper': [
            (365, 440, '2S1F2P'),
            (365, 480, '2S2F3P'),
            (365, 520, '4P'),
            (635, 440, '2S'),
            (635, 480, '1P'),
            (635, 520, '3P'),
            (635, 560, '1A'),
            ],
        'Keeper': [
            (365, 440, '2S1F2P'),
            (365, 480, '2S2F3P'),
            (365, 520, '4P'),
            (635, 440, '2S'),
            (635, 480, '1P'),
            (635, 520, '3P'),
            (635, 560, '1A'),
            ],
        'Lightning': [
            (363, 440, '3F2A'),
            (363, 475, '4F3A'),
            (363, 510, '5F4A1W'),
            (363, 545, '5F5A2W'),
            ],
        'SparkingLightning': [
            (355, 445, '2S5F3A'),
            (355, 520, '2F2A'),
            (355, 550, '1S3F2A'),
            ],
        'ImmenseLightning': [
            (363, 440, '3F2A'),
            (363, 475, '4F3A'),
            (363, 510, '5F4A1W'),
            (363, 545, '5F5A2W'),
            ],
        'PandemoniumLightning': [
            (363, 450, '3F2A'),
            (363, 475, '4F3A'),
            (363, 500, '5F4A1M'),
            (363, 525, '5F5A2M'),
            ],
        'WindLightning': [
            (363, 440, '3F2A'),
            (363, 475, '4F3A'),
            (363, 510, '5F4A1W'),
            (363, 545, '5F5A2W'),
            (0, 490, '1A'),
            (0, 520, '3A'),
            (0, 550, '4A1W'),
            (0, 580, '5A2W'),
            ],
        'LairLure': [
            (360, 463, '1M'),
            (360, 510, '3M1A'),
            (360, 565, '4M1A'),
            (650, 470, '1F3P'),
            (650, 500, '2P'),
            (650, 530, '4P1N'),
            (650, 560, '6P'),
            ],
        'Lure': [
            (360, 480, '2M'),
            (360, 510, '2M1A'),
            (360, 540, '3M2A1N'),
            (360, 570, '4A'),
            (650, 470, '1F3P'),
            (650, 500, '2P'),
            (650, 530, '4P1N'),
            (650, 560, '6P'),
            ],
        'Minds': [
            (360, 435, '2A1N'),
            (360, 475, '3A1W2N'),
            (360, 515, '1F4A2N'),
            (640, 450, '1A2N'),
            (640, 490, '2A3N'),
            (640, 530, '3A4N'),
            (640, 570, '4A1E5N'),
            ],
        'StrandedMist': [
            (360, 435, '1M2A1W'),
            (360, 480, '2M3A2W'),
            (360, 525, '4M4A3W'),
            (360, 560, '5M6A4W'),
            (650, 435, '1A2W'),
            (650, 475, '2A3W'),
            (650, 515, '3A4W'),
            ],
        'Mist': [
            (360, 435, '1M2A1W'),
            (360, 480, '2M3A2W'),
            (360, 525, '4M4A3W'),
            (360, 560, '5M6A4W'),
            (650, 435, '1A2W'),
            (650, 475, '2A3W'),
            (650, 515, '3A4W'),
            ],
        'DeepsOcean': [
            (360, 475, '2W'),
            (360, 500, '4W2E'),
            (360, 585, '2M3W'),
            (640, 485, '2W'),
            (640, 515, '3W'),
            (640, 565, '3M4W3E'),
            ],
        'Ocean': [
            (370, 495, '1M1A2W'),
            (370, 535, '2M1A3W'),
            (370, 570, '3M2A4W'),
            (645, 495, '2W1E'),
            (645, 535, '3W2E'),
            (645, 570, '4W3E'),
            ],
        'River': [
            (365, 440, '1S2W'),
            (365, 480, '2S3W'),
            (365, 520, '3S4W1E'),
            ],
        'HavenRiver': [
            (365, 460, '1S1W'),
            (365, 490, '1S2W1E'),
            (365, 530, '1S1N'),
            (365, 570, '1S1W2P'),
            ],
        'TravelRiver': [
            (365, 440, '1S2W'),
            (365, 480, '2S3W'),
            (365, 520, '3S4W1E'),
            ],
        'SunshineRiver': [
            (365, 440, '1S2W'),
            (365, 480, '2S3W'),
            (365, 520, '3S4W1E'),
            (698, 450, '2S'),
            (698, 478, '3S1W'),
            (698, 505, '4S2W'),
            ],
        'LocusSerpent': [
            (360, 445, '2W1E'),
            (360, 550, '2M2E1P'),
            (638, 440, '1F1E'),
            (638, 495, '2M2E'),
            (638, 555, '5M6F6E'),
            ],
        'Serpent': [
            (360, 440, '2F1W1P'),
            (360, 500, '2W3E2P'),
            (360, 560, '3F3W3E3P'),
            (638, 440, '1F1E'),
            (638, 495, '2M2E'),
            (638, 555, '5M6F6E'),
            ],
        'Shadows': [
            (365, 440, '2M1F'),
            (365, 475, '3M2F'),
            (365, 515, '4M3F2A'),
            ],
        'Dark FireShadows': [
            (365, 440, '2M1F'),
            (365, 475, '3M2F'),
            (365, 515, '4M3F2A'),
            ],
        'ReachShadows': [
            (365, 440, '2M1F'),
            (365, 475, '3M2F'),
            (365, 515, '4M3F2A'),
            ],
        'MadnessShadows': [
            (365, 440, '2M1F'),
            (365, 475, '3M2F'),
            (365, 515, '4M3F2A'),
            ],
        'AmorphousShadows': [
            (365, 440, '2M1F'),
            (365, 475, '3M2F'),
            (365, 515, '4M3F2A'),
            ],
        'ForebodingShadows': [
            (365, 440, '2M1F'),
            (365, 475, '3M2F'),
            (365, 515, '4M3F2A'),
            (-5, 490, '2A'),
            (-5, 525, '1M'),
            (-5, 560, '2F'),
            (-5, 580, '2M4A'),
            ],
        'ExploratoryShadows': [
            (365, 440, '2M1F'),
            (365, 475, '3M2F'),
            (365, 515, '4M3F2A'),
            ],
        'IntensifyShifting': [
            (365, 430, '2E'),
            (365, 465, '1A2E'),
            (365, 500, '2M3A4E'),
            (645, 430, '1M'),
            (645, 465, '2M1A'),
            ],
        'MentorShifting': [
            (365, 430, '2E'),
            (365, 465, '1A2E'),
            (365, 500, '2M3A4E'),
            (645, 440, '1A'),
            (645, 477, '3A2E'),
            (645, 520, '1S4A3E'),
            (645, 575, '1A'),
            ],
        'Shifting': [
            (365, 430, '2E'),
            (365, 465, '1A2E'),
            (365, 500, '2M3A4E'),
            (645, 430, '1M'),
            (645, 465, '2M1A'),
            ],
        'Starlight': [
            (655, 90, '3A'),
            (655, 120, '3E'),
            (655, 210, '3F'),
            (655, 240, '3W'),
            (655, 330, '3P'),
            (655, 360, '3N'),
            (655, 445, '2M'),
            (655, 475, '3M'),
            (655, 575, '4S'),
            ],
        'Stone': [
            (363, 435, '2E'),
            (363, 495, '4E'),
            (363, 530, '6E1P'),
            (650, 465, '3E'),
            (650, 505, '5E'),
            (650, 545, '7E2S'),
            ],
        'WarriorThunderspeaker': [
            (370, 425, '4A'),
            (370, 455, '1N'),
            (630, 508, '1S2F'),
            (630, 545, '3S3F'),
            ],
        'TacticianThunderspeaker': [
            (370, 425, '4A'),
            (370, 455, '1N'),
            (640, 425, '4A'),
            (640, 455, '2S1F'),
            (640, 495, '4S3F'),
            ],
        'Thunderspeaker': [
            (370, 425, '4A'),
            (370, 455, '1N'),
            (640, 425, '4A'),
            (640, 455, '2S1F'),
            (640, 495, '4S3F'),
            ],
        'Trickster': [
            (360, 415, '1M1F2A'),
            (360, 565, '2M1F2A'),
            (650, 415, '3M'),
            (650, 450, '3A'),
            (650, 490, ['3S', '3F']),
            (650, 530, '3N'),
            ],
        'Vengeance': [
            (360, 455, '1F3N'),
            (360, 495, '1W2F4N'),
            (360, 545, '3W3F5N'),
            (650, 430, '3A'),
            (650, 465, '3F1N'),
            (650, 505, '4F2N'),
            (650, 545, '5F2A2N'),
            ],
        'Volcano': [
            (360, 455, '2F2E'),
            (360, 495, '3F3E'),
            (360, 530, '4F2A4E'),
            (360, 580, '5F3A5E'),
            (653, 408, '3E'),
            (653, 445, '3F'),
            (653, 485, '4E4F'),
            (653, 525, '5F'),
            ],
        'TransformingWildfire': [
            (360, 445, '1P'),
            (360, 475, '3P'),
            (360, 510, '4F2A'),
            (360, 570, '7F'),
            (640, 495, '4F1P'),
            (640, 525, '3F1E2P'),
            (640, 560, '1S3F1N'),
            ],
        'Wildfire': [
            (360, 445, '1P'),
            (360, 475, '3P'),
            (360, 510, '4F2A'),
            (360, 570, '7F'),
            (640, 445, '4F1P'),
            (640, 485, '4F2P'),
            (640, 525, '5F2P2E'),
            ],
        'Teeth': [
            (360, 430, '1F1N'),
            (360, 465, '2F1E2N'),
            (360, 500, '3F1E3N'),
            (360, 535, '4F2E5N'),
            ],
        'Eyes': [
            (360, 430, '1M2P'),
            (360, 465, '2M3P'),
            (360, 500, '2M2A4P'),
            (360, 535, '3M3A5P'),
            ],
        'Mud': [
            (360, 425, '1W'),
            (360, 460, '1M2W1E'),
            (360, 495, '2M3W2E'),
            (360, 530, '3M4W3E2P'),
            ],
        'Heat': [
            (360, 425, '2F2A'),
            (360, 460, '3F2E'),
            (360, 495, '4F1A3E'),
            (360, 530, '5F2A3E'),
            ],
        'Whirlwind': [
            (360, 425, '1S2A'),
            (360, 460, '2S3A'),
            (360, 495, '2S4A'),
            (360, 530, '3S5A'),
            ],
        'Behemoth': [
            (358, 508, '2F1E'),
            (358, 540, '3F1E1P'),
            (358, 572, '4F2E1P'),
            (358, 604, '5F2E2P'),
            ],
        'Breath': [
            (356, 492, '2M1N'),
            (356, 528, '3M1A1N'),
            (356, 564, '4M2A2N'),
            (356, 600, '5M2A3N'),
            (650, 510, '2M1A'),
            (650, 560, '4M3A'),
            (650, 600, '3M2N'),
            ],
        'Earthquakes': [
            (350, 460, '1E'),
            (350, 500, '1M1E'),
            (350, 540, '1M2E'),
            (350, 580, '2M3E'),
            (630, 475, '2F3E'),
            (630, 525, '3F4E'),
            (630, 580, '4F5E'),
            ],
        'Gaze': [
            (350, 470, '2S'),
            (350, 510, '3S1F'),
            (350, 550, '4S2F1A'),
            (350, 590, '5S3F2A'),
            (650, 472, '3S1M'),
            (650, 512, '3S1W'),
            (650, 552, '3S1P'),
            (650, 592, '3S1W1P'),
            ],
        'Roots': [
            (350, 508, '1S1P'),
            (350, 538, '1S1E2P'),
            (350, 568, '2S1E3P'),
            (350, 598, '3S2E4P'),
            (650, 508, '1S1M2P'),
            (650, 538, '2S1M3P'),
            (650, 568, '2S2M4P'),
            ],
        'Vigil': [
            (350, 415, '2S1E'),
            (350, 490, '3S1E'),
            (350, 538, '4S2E'),
            (350, 590, '5S3E'),
            (655, 415, '1N'),
            (655, 460, '1S2A3N'),
            (655, 530, '2S3A4N'),
            ],
        'Voice': [
            (350, 475, '1A'),
            (350, 505, '3A'),
            (350, 538, '5A'),
            (350, 574, '2M1F4A1P'),
            (655, 445, '1M2A'),
            (655, 485, '1S2A'),
            (655, 535, '1S1M4A'),
            ],
        'Waters': [
            (355, 492, '2W'),
            (355, 535, '3W1N'),
            (355, 580, '5W2P2N'),
            (655, 492, '2N'),
            (655, 535, '1W3N'),
            (655, 580, '2F2W5N'),
            ],
        'Waters - Renew': [
            (355, 492, '2W'),
            (355, 535, '3W1N'),
            (355, 580, '5W2P2N'),
            (655, 480, '1W'),
            (655, 510, '2W1P'),
            (655, 540, '3W1P'),
            (655, 570, '1S4W2P'),
            ],
        'Waters - Ruin': [
            (353, 480, '1N'),
            (353, 510, '1F3N'),
            (353, 540, '1S2F4N'),
            (353, 590, '1F2N'),
            (655, 492, '2N'),
            (655, 535, '1W3N'),
            (655, 580, '2F2W5N'),
            ],
        'Rot': [
            (356, 450, '1M1W2P'),
            (356, 485, '1E2P'),
            (356, 530, '3P'),
            (356, 565, '2W2E4P'),
            (645, 450, '2M3W1N'),
            (645, 485, '1M3W1P'),
            (645, 520, '1M2W'),
            (645, 555, '2W'),
            (645, 590, '4W3P'),
            ],
        'Round DownRot': [
            (356, 450, '1M1W2P'),
            (356, 485, '1E2P'),
            (356, 530, '3P'),
            (356, 565, '2W2E4P'),
            (645, 450, '2M3W1N'),
            (645, 485, '1M3W1P'),
            (645, 520, '1M2W'),
            (645, 555, '2W'),
            (645, 590, '4W3P'),
            ],
        'Covets': [
            (360, 487, '1E'),
            (360, 522, '1F2A2E'),
            (360, 580, '2S2F3E'),
            (638, 501, '2S2E2N'),
            (638, 560, '4E'),
            (667, 750, '1F1E'),
            (667, 779, '3F2E'),
            (667, 807, '3F2A3E'),
            (667, 902, '1A1E1N'),
            (667, 931, '3A1E2N'),
            (667, 960, '3A3E3N'),
            (667, 1052, '1S1E1N'),
            (667, 1081, '3S1E2N'),
            (667, 1110, '3S2E3N'),
            ],
        }

card_thresholds = {
# Unique
"Blinding Glare": [ (40, 72, '5S') ],
"Blooming of the Rocks and Trees": [ (40, 80, '3P') ],
"Flash-Fires": [ (40, 79, '2A') ],
"Shape the Self Anew": [ (40, 75, '4M') ],
"Share Secrets of Survival": [ (40, 79, '3A') ],
"Swallowed by the Endless Dark": [ (35, 80, '3M3A') ],

# Minor
"Absorb Corruption": [ (42, 78, '2P') ],
"Call of the Dahan Ways": [ (40, 76, '2M') ],
"Carapaced Land": [ (40, 78, '2E') ],
"Domesticated Animals Go Berserk": [ (40, 77, '3M') ],
"Drought": [ (40, 79, '3S') ],
"Favor of the Sun and Star-Lit Dark": [ (40, 78, '2S') ],
"Inflame the Fires of Life": [ (40, 79, '3N') ],
"Nature's Resilience": [ (40, 78, '2W') ],
"Renewing Rain": [ (40, 78, '3P') ],
"Sap the Strength of Multitudes": [ (40, 76, '1A') ],
"Savage Mawbeasts": [ (40, 79, '3N') ],
"Scour the Land": [ (40, 78, '3A') ],
"Steam Vents": [ (41, 79, '3E') ],
"Strong and Constant Currents": [ (40, 80, '2W') ],
"Unquenchable Flames": [ (35, 78, '2F') ],
"Visions of Fiery Doom": [ (40, 78, '2F') ],

# Major
"Accelerated Rot": [ (30, 78, '3S2W3P') ],
"Angry Bears": [ (35, 76, '2F3N') ],
"Bargains of Power and Protection": [ (30, 82, '3S2W2E') ],
"Blazing Renewal": [ (30, 80, '3F3E2P') ],
"Bloodwrack Plague": [ (35, 74, '2E4N') ],
"Cast Down into the Briny Deep": [ (25, 70, '2S2M4W4E') ],
"Cleansing Floods": [ (38, 80, '4W') ],
"Death Falls Gently from Open Blossoms": [ (35, 73, '3A3P') ],
"Dissolve the Bonds of Kinship": [ (30, 76, '2F2W3N') ],
"Dream of the Untouched Land": [ (23, 65, '3M2W3E2P') ],
"Entwined Power": [ (35, 77, '2W4P') ],
"Fire and Flood": [ (38, 73, '3F'), (38, 83, '3W') ],
"Flow like Water, Reach like Air": [ (36, 76, '2A2W') ],
"Focus the Land's Anguish": [ (38, 80, '3S') ],
"Forests of Living Obsidian": [ (30, 80, '2S3F3E') ],
"Grant Hatred a Ravenous Form": [ (36, 80, '4M2F') ],
"Indomitable Claim": [ (34, 72, '2S3E') ],
"Infestation of Venomous Spiders": [ (30, 76, '2A2E3N') ],
"Infinite Vitality": [ (40, 75, '4E') ],
"Insatiable Hunger of the Swarm": [ (35, 80, '2A4N') ],
"Instruments of Their Own Ruin": [ (32, 70, '4S2F2N') ],
"Irresistible Call": [ (28, 76, '2S3A2P') ],
"Manifest Incarnation": [ (35, 76, '3S3M') ],
"Melt Earth into Quicksand": [ (28, 78, '2M4W2E') ],
"Mists of Oblivion": [ (30, 79, '2M3A2W') ],
"Paralyzing Fright": [ (35, 78, '2A3E') ],
"Pent-Up Calamity": [ (30, 78, '2M3F') ],
"Pillar of Living Flame": [ (38, 80, '4F') ],
"Poisoned Land": [ (30, 76, '3E2P2N') ],
"Powerstorm": [ (30, 76, '2S2F3A') ],
"Pyroclastic Flow": [ (30, 79, '2F3A2E') ],
'Savage Transformation': [ (38, 76, '2M3N') ],
"Sea Monsters": [ (30, 80, '3W3N') ],
"Settle into Hunting-Grounds": [ (35, 76, '2P3N') ],
"Sleep and Never Waken": [ (28, 74, '3M2A2N') ],
"Smothering Infestation": [ (36, 80, '2W2P') ],
"Spill Bitterness into the Earth": [ (33, 76, '3F3W') ],
"Storm-Swath": [ (28, 68, '2F3A2W') ],
"Strangling Firevine": [ (35, 76, '2F3P') ],
"Sweep into the Sea": [ (35, 80, '3S2W') ],
"Talons of Lightning": [ (35, 76, '3F3A') ],
"Terrifying Nightmares": [ (38, 78, '4M') ],
"The Jungle Hungers": [ (33, 76, '2M3P') ],
"The Land Thrashes in Furious Pain": [ (35, 71, '3M3E') ],
"The Trees and Stones Speak of War": [ (30, 76, '2S2E2P') ],
"The Wounded Wild Turns on Its Assailants": [ (30, 73, '2F3P2N') ],
"Thickets Erupt with Every Touch of Breeze": [ (38, 80, '3P') ],
"Tigers Hunting": [ (30, 76, '2S2M3N') ],
"Transform to a Murderous Darkness": [ (30, 78, '3M2F2A') ],
"Trees Radiate Celestial Brilliance": [ (28, 80, '3S2M2P') ],
"Tsunami": [ (33, 72, '3W2E') ],
"Twisted Flowers Murmur Ultimatums": [ (30, 76, '3M2A3P') ],
"Unleash a Torrent of the Self's Own Essence": [ (33, 80, '2S3F') ],
"Unlock the Gates of Deepest Power": [ (18, 72, '2S2M2F2A2W2E2P2N') ],
"Unrelenting Growth": [ (33, 72, '3S3P') ],
"Utter a Curse of Dread and Bone": [ (35, 76, '3M2N') ],
"Vanish Softly Away, Forgotten by All": [ (35, 78, '3M3A') ],
"Vengeance of the Dead": [ (38, 76, '3N') ],
"Vigor of the Breaking Dawn": [ (36, 72, '3S2N') ],
"Voice of Command": [ (35, 78, '3S2A') ],
"Volcanic Eruption": [ (35, 72, '4F3E') ],
"Walls of Rock and Thorn": [ (35, 72, '2E2P') ],
"Weave Together the Fabric of Place": [ (42, 80, '4A') ],
"Winds of Rust and Atrophy": [ (30, 80, '3A3W2N') ],
"Wrap in Wings of Sunlight": [ (30, 76, '2S2A2N') ],

"Bargain of Coursing Paths": [ (30, 80, '3A2W2E') ],
"Bombard with Boulders and Stinging Seeds": [ (30, 75, '2A2E3P') ],
"Exaltation of the Incandescent Sky": [ (25, 78, '3S3F4A2W') ],
"Flocking Red-Talons": [ (30, 75, '2A2P3N') ],
"Fragments of Yesteryear": [ (30, 68, '3S'), (30, 78, '3M') ],
"Inspire the Release of Stolen Lands": [ (30, 70, '3S3W2N') ],
"Plague Ships Sail to Distant Ports": [ (30, 68, '2F2W2N') ],
"Ravaged Undergrowth Slithers Back to Life": [ (33, 73, '3W2P') ],
"Rumbling Earthquakes": [ (33, 77, '4E') ],
"Solidify Echoes of Majesty Past": [ (30, 75, '2S2M2E') ],
"Transformative Sacrifice": [ (30, 75, '2M3F2P') ],
"Unearth a Beast of Wrathful Stone": [ (30, 73, '2M3E3N') ],
}


class Presence(models.Model):
    game_player = models.ForeignKey(GamePlayer, on_delete=models.CASCADE)
    left = models.IntegerField()
    top = models.IntegerField()
    opacity = models.FloatField(default=1.0)
    energy = models.CharField(max_length=255, blank=True)
    elements = models.CharField(max_length=255, blank=True)

    def get_energy(self):
        if self.opacity == 1.0:
            return 0
        try:
            if self.energy[0].isdigit():
                return int(self.energy)
        except:
            pass
        return 0

    def get_plus_energy(self):
        if self.opacity == 1.0:
            return 0
        try:
            if self.energy[0] == '+':
                return int(self.energy)
        except:
            pass
        return 0

    def impending_energy(self):
        if self.opacity == 1.0:
            return 0
        if self.energy and self.energy.startswith("Impend"):
            return int(self.energy[6:])
        return 0

    def get_elements(self):
        counter = Counter()
        if self.opacity == 1.0:
            return counter
        for e in self.elements.split(','):
            # Kind of hacky: storing Rot in the same field as elements.
            # Making a new field for Rot just seemed sort of wasteful.
            if e == 'Rot':
                continue
            if len(e) > 0:
                counter[Elements[e]] += 1
        return counter

    def rot(self):
        if self.opacity == 1.0:
            return 0
        # no presence grants > 1 rot, so just check `in` rather than count
        return 1 if 'Rot' in self.elements.split(',') else 0

class GameLog(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True, blank=True)
    text = models.CharField(max_length=255, blank=False)
    images = models.CharField(max_length=1024, blank=True, null=True)
