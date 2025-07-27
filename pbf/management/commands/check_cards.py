from django.core.management.base import BaseCommand
from pbf.models import Card

class Command(BaseCommand):
    help = 'check card speed and elements'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        for card in Card.objects.all():
            if not card.elements and card.name not in ('Elemental Boon', "Gift of Nature's Connection", 'Draw Towards a Consuming Void') and not card.is_healing():
                print(f"{card.name} no elements {card.elements}")

            elements = card.elements.split(',')
            if len(elements) != len(set(elements)):
                print(f"{card.name} duplicate elements {card.elements}")

            if card.speed not in (Card.FAST, Card.SLOW) and not card.is_healing():
                print(f"Unknown speed {card.name}")

        print(f"{Card.objects.count()} cards")
