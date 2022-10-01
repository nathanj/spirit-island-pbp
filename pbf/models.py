import uuid
from enum import Enum
from collections import Counter, defaultdict

from django.db import models

class Elements(Enum):
    Sun = 1
    Moon = 2
    Fire = 3
    Air = 4
    Water = 5
    Earth = 6
    Plant = 7
    Animal = 8

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

    name = models.CharField(max_length=255, blank=False)
    TYPES = (
        (MINOR, 'Minor'),
        (MAJOR, 'Major'),
        (UNIQUE, 'Unique'),
    )
    type = models.IntegerField(choices=TYPES)
    spirit = models.ForeignKey(Spirit, null=True, on_delete=models.CASCADE)
    cost = models.IntegerField()
    elements = models.CharField(max_length=255, blank=False)

    def __str__(self):
        return self.name

    def url(self):
        return '/pbf/' + self.name.replace(",", '').replace("-", '').replace("'", '').replace(' ', '_').lower() + '.jpg'

    def get_elements(self):
        counter = Counter()
        for e in self.elements.split(','):
            if len(e) > 0:
                counter[Elements[e]] = 1
        return counter

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
    CHANNELS = (
        ('957389286834057306', '#pbp1-updates'),
        ('883019769937268816', '#pbp2-updates'),
        ('1022258668428865586', '#pbp3-updates'),
        ('1025502499387478127', '#pbp4-updates'),
        ('1010285070680072192', '#pbp-allspirit-updates'),
        ('703767917854195733', '#bot-testing'),
    )
    discord_channel = models.CharField(max_length=255, default="", blank=True, choices=CHANNELS)

    def __str__(self):
        return str(self.id)


colors_to_circle_color_map = {
        'blue': '#715dff',
        'green': '#0d9501',
        'orange': '#d15a01',
        'purple': '#e67bfe',
        'red': '#fc3b5a',
        'yellow': '#ffd585',
        }

colors_to_emoji_map = {
        'blue': '🔵',
        'green': '🟢',
        'orange': '🟠',
        'purple': '🟣',
        'red': '🔴',
        'yellow': '🟡',
        }

class GamePlayer(models.Model):
    class Meta:
        ordering = ('-id', )

    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    spirit = models.ForeignKey(Spirit, blank=False, on_delete=models.CASCADE)
    hand = models.ManyToManyField(Card, related_name='hand', blank=True)
    discard = models.ManyToManyField(Card, related_name='discard', blank=True)
    play = models.ManyToManyField(Card, related_name='play', blank=True)
    selection = models.ManyToManyField(Card, related_name='selection', blank=True)
    days = models.ManyToManyField(Card, related_name='days', blank=True)
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
    starting_energy = models.IntegerField(default=0)

    def __str__(self):
        return str(self.game.id) + ' - ' + str(self.spirit.name)

    def aspect_url(self):
        return f'pbf/aspect-{self.aspect.lower()}.jpg'

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
        for card in self.play.all():
            counter += card.get_elements()
        for presence in self.presence_set.all():
            counter += presence.get_elements()
        return defaultdict(int, counter)

    def sun(self): return self.elements[Elements.Sun]
    def moon(self): return self.elements[Elements.Moon]
    def fire(self): return self.elements[Elements.Fire]
    def air(self): return self.elements[Elements.Air]
    def water(self): return self.elements[Elements.Water]
    def earth(self): return self.elements[Elements.Earth]
    def plant(self): return self.elements[Elements.Plant]
    def animal(self): return self.elements[Elements.Animal]

    def get_play_cost(self):
        return sum([card.cost for card in self.play.all()])

    def get_gain_energy(self):
        amount = max([self.starting_energy] + [p.get_energy() for p in self.presence_set.all()]) + sum([p.get_plus_energy() for p in self.presence_set.all()])
        if self.aspect == 'Immense':
            return amount * 2
        else:
            return amount

    def days_ordered(self):
        return self.days.order_by('type', 'cost')

    def chunk(self, str, n):
        return [str[i:i+n] for i in range(0, len(str), n)]

    def check_elements(self, elements, desired):
        if type(desired) == type([]):
            return any([self.check_elements(elements, d) for d in desired])

        chunks = self.chunk(desired, 2)
        for c in chunks:
            amt = int(c[0])
            e = c[1]
            if e == 'S' and elements[Elements.Sun] < amt: return False
            if e == 'M' and elements[Elements.Moon] < amt: return False
            if e == 'F' and elements[Elements.Fire] < amt: return False
            if e == 'A' and elements[Elements.Air] < amt: return False
            if e == 'W' and elements[Elements.Water] < amt: return False
            if e == 'E' and elements[Elements.Earth] < amt: return False
            if e == 'P' and elements[Elements.Plant] < amt: return False
            if e == 'N' and elements[Elements.Animal] < amt: return False
        return True

    def thresholds(self):
        elements = self.elements
        thresholds = []
        name = self.spirit.name
        if self.aspect:
            name = self.aspect + name
        if name in spirit_thresholds:
            for t in spirit_thresholds[name]:
                thresholds.append(Threshold(t[0], t[1], self.check_elements(elements, t[2])))
        return thresholds

spirit_thresholds = {
        'Bringer': [
            (360, 450, '2M2A'),
            (360, 515, '3M'),
            (650, 450, '1M1A'),
            (650, 490, '2M1A1N'),
            (650, 530, '3M2A1N'),
            ],
        'Exploratory Bringer': [
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
        'Fangs': [
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
        'Green': [
            (365, 440, '1M2P'),
            (365, 480, '2M3P'),
            (365, 520, '3M4P'),
            (645, 440, '1W3P'),
            (645, 480, '2W4P'),
            (645, 520, '3W1E5P'),
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
        'Mist': [
            (360, 435, '1M2A1W'),
            (360, 480, '2M3A2W'),
            (360, 525, '4M4A3W'),
            (360, 560, '5M6A4W'),
            (650, 435, '1A2W'),
            (650, 475, '2A3W'),
            (650, 515, '3A4W'),
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
        'Wildfire': [
            (360, 445, '1P'),
            (360, 475, '3P'),
            (360, 510, '4F2A'),
            (360, 570, '7F'),
            (640, 445, '4F1P'),
            (640, 485, '4F2P'),
            (640, 525, '5F2P2E'),
            ],
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
            if self.energy[0] != '+':
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

    def get_elements(self):
        counter = Counter()
        if self.opacity == 1.0:
            return counter
        for e in self.elements.split(','):
            if len(e) > 0:
                counter[Elements[e]] += 1
        return counter

class GameLog(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True, blank=True)
    text = models.CharField(max_length=255, blank=False)
    images = models.CharField(max_length=1024, blank=True, null=True)
