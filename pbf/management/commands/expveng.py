from django.core.management.base import BaseCommand
from pbf.models import Card, Game

class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        expl = Card.objects.get(name='Vengeance of the Dead exploratory')

        for (games, name) in ((expl.major_deck, 'major deck'), (expl.discard_pile, 'discard pile')):
            print(f"{games.count()} {name}s: {games.first()}... {games.last()}")

        # Player-specific locations, minus impending
        # Not healing because Vengeance of the Dead can't end up there
        for loc in ('hand', 'discard', 'play', 'selection', 'days'):
            players = getattr(expl, loc)
            print(f"{players.count()} player {loc}s: {players.first()}... {players.last()}")

        impends = expl.gameplayerimpendingwithenergy_set.values_list('gameplayer__game__id', flat=True)
        print(f"{impends.count()} impending: {impends.first()}... {impends.last()}")
