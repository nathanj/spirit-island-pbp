import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.conf import settings
from django.db import transaction
from pbf.models import *
from pbf.views import spirit_presence

class Command(BaseCommand):
    help = 'Fixup presence'

    def add_arguments(self, parser):
        # parser.add_argument('poll_ids', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        serpent = GamePlayer.objects.get(pk=8)
        bringer = GamePlayer.objects.get(pk=9)
        stone = GamePlayer.objects.get(pk=10)

        serpent.color = '#715dff'
        bringer.color = '#d15a01'
        stone.color = '#e67bfe'
        serpent.save()
        bringer.save()
        stone.save()

        for presence in spirit_presence['Serpent']:
            serpent.presence_set.create(left=presence[0], top=presence[1], opacity=presence[2])
        for presence in spirit_presence['Bringer']:
            bringer.presence_set.create(left=presence[0], top=presence[1], opacity=presence[2])
        for presence in spirit_presence['Stone']:
            stone.presence_set.create(left=presence[0], top=presence[1], opacity=presence[2])

