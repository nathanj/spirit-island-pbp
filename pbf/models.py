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
        counter[Elements.Sun] += self.temporary_sun
        counter[Elements.Moon] += self.temporary_moon
        counter[Elements.Fire] += self.temporary_fire
        counter[Elements.Air] += self.temporary_air
        counter[Elements.Water] += self.temporary_water
        counter[Elements.Earth] += self.temporary_earth
        counter[Elements.Plant] += self.temporary_plant
        counter[Elements.Animal] += self.temporary_animal
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
