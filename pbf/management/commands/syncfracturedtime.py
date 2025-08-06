from django.core.management.base import BaseCommand
from pbf.models import GamePlayer, Presence

class Command(BaseCommand):
    help = 'set Fractured Days spirit-specific resource to number of Time discs they have'

    def add_arguments(self, parser):
        parser.add_argument('--save', action='store_true', help='save')

    def handle(self, *args, **options):
        fractured_days = GamePlayer.objects.filter(spirit__name='Fractured').all()
        change = []
        for frac in fractured_days:
            time = frac.presence_set.filter(opacity=1.0, left__lte=300).count()
            if time != frac.spirit_specific_resource:
                change.append((frac.spirit_specific_resource, frac))
                frac.spirit_specific_resource = time
        print(f"change {len(change)}/{len(fractured_days)} Fractured Days")
        if options['save']:
            GamePlayer.objects.bulk_update((f for (_, f) in change), ['spirit_specific_resource'])
        else:
            for (old, frac) in change:
                print(f"{frac.id}: {old} -> {frac.spirit_specific_resource}")
