from django.db import migrations, models

def retroactively_label_covets_v11(apps, schema_editor):
    Spirit = apps.get_model('pbf', 'Spirit')
    Presence = apps.get_model('pbf', 'Presence')
    GamePlayer = apps.get_model('pbf', 'GamePlayer')
    covets = Spirit.objects.get(name='Covets')

    players110 = Presence.objects.filter(left=512, top=123, elements='Fire', energy='', game_player__spirit=covets).values_list('game_player_id', flat=True)
    GamePlayer.objects.filter(id__in=players110).update(aspect='v1.1')

def label_covets_v121(apps, schema_editor):
    Spirit = apps.get_model('pbf', 'Spirit')
    Presence = apps.get_model('pbf', 'Presence')
    GamePlayer = apps.get_model('pbf', 'GamePlayer')
    covets = Spirit.objects.get(name='Covets')

    players121 = Presence.objects.filter(left=512, top=158, elements='', energy='', game_player__spirit=covets).values_list('game_player_id', flat=True)
    GamePlayer.objects.filter(id__in=players121).update(aspect='v1.2.1')

def unlabel_covets_v121(apps, schema_editor):
    Spirit = apps.get_model('pbf', 'Spirit')
    Presence = apps.get_model('pbf', 'Presence')
    GamePlayer = apps.get_model('pbf', 'GamePlayer')
    covets = Spirit.objects.get(name='Covets')

    players121 = Presence.objects.filter(left=512, top=158, elements='', energy='', game_player__spirit=covets).values_list('game_player_id', flat=True)
    GamePlayer.objects.filter(id__in=players121).update(aspect='')

def covets_uniques_v121_rename(apps, schema_editor):
    Card = apps.get_model('pbf', 'Card')

    for name in ('Melt Earth to Slag', 'Petition for Smoldering Wrath', 'Favors of Steel and Bone'):
        Card.objects.filter(name=name).update(name=f"{name} v1.2.1", spirit=None)

def covets_uniques_v121_unrename(apps, schema_editor):
    Card = apps.get_model('pbf', 'Card')
    Spirit = apps.get_model('pbf', 'Spirit')
    covets = Spirit.objects.get(name='Covets')

    for name in ('Melt Earth to Slag', 'Petition for Smoldering Wrath', 'Favors of Steel and Bone'):
        Card.objects.filter(name=f"{name} v1.2.1").update(name=name, spirit=covets)

def covets_add_v13_uniques(apps, schema_editor):
    Card = apps.get_model('pbf', 'Card')
    Spirit = apps.get_model('pbf', 'Spirit')
    covets = Spirit.objects.get(name='Covets')

    unique = 2
    fast = 1
    slow = 2

    Card(name="Favors of Steel and Bone",      cost=1, type=unique, speed=fast, spirit=covets, elements="Sun,Earth,Animal").save()
    Card(name="Melt Earth to Slag",            cost=1, type=unique, speed=slow, spirit=covets, elements="Sun,Moon,Fire,Earth").save()
    Card(name="Petition for Smoldering Wrath", cost=2, type=unique, speed=fast, spirit=covets, elements="Moon,Fire,Air,Earth").save()

def covets_rm_v13_uniques(apps, schema_editor):
    Card = apps.get_model('pbf', 'Card')

    for name in ('Melt Earth to Slag', 'Petition for Smoldering Wrath', 'Favors of Steel and Bone'):
        Card.objects.get(name=name).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('pbf', '0055_gameplayer_bargain_cost_and_paid'),
    ]

    operations = [
        migrations.RunPython(retroactively_label_covets_v11, migrations.RunPython.noop),
        migrations.RunPython(label_covets_v121, unlabel_covets_v121),
        migrations.RunPython(covets_uniques_v121_rename, covets_uniques_v121_unrename),
        migrations.RunPython(covets_add_v13_uniques, covets_rm_v13_uniques),
    ]
