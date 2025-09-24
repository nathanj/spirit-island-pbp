from django.core.management.base import BaseCommand
from pbf.models import GamePlayer, Presence
import pbf.views

class Command(BaseCommand):
    help = 'Recreates the presence for the player, based on their spirit. Intended only for use when testing changes to presence positions; not intended to be available via web'

    def add_arguments(self, parser):
        parser.add_argument("player_ids", nargs="+", type=int)

    def handle(self, *args, **options):
        for playerid in options['player_ids']:
            player = GamePlayer.objects.get(id=playerid)

            # key: (left, top), value: (opacity, energy, elements)
            new_presences = {(left, top): (opacity, rest[0] if rest else '', rest[1] if len(rest) > 1 else '') for (left, top, opacity, *rest) in pbf.views.spirit_presence[player.spirit.name]}
            # locus:
            if player.aspect == 'Locus':
                (left, top, *_) = pbf.views.spirit_presence[player.spirit.name][0]
                pos = (left, top)
                new_presences[pos] = (0.0, new_presences[pos][1], new_presences[pos][2])

            current_presences = {(p.left, p.top): (p.opacity, p.energy, p.elements) for p in player.presence_set.all()}

            add = 0
            change = 0
            delete = 0
            for k in new_presences.keys() | current_presences.keys():
                if k in new_presences and k not in current_presences:
                    print(f"add presence {k} {new_presences[k]}")
                    add += 1
                elif k not in new_presences and k in current_presences:
                    print(f"delete presence {k} {current_presences[k]}")
                    delete += 1
                elif k in new_presences and k in current_presences:
                    if new_presences[k] != current_presences[k]:
                        print(f"change presence {k}: {current_presences[k]} -> {new_presences[k]}")
                        change += 1
                    pass
                else:
                    raise Exception("impossible for it to be in neither")

            print(f"{playerid}: add {add}, change {change}, delete {delete}")

            if add == 0 and change == 0 and delete == 0:
                print(f"no changes needed for {playerid}")
                continue

            if input(f'OK for {playerid}? you must type yes in all caps: ') == 'YES':
                Presence.objects.filter(game_player=player).delete()
                pbf.views.make_presence(player)
            else:
                print('you did not type yes in all caps, no changes made')
