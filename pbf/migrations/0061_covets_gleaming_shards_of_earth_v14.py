from django.db import migrations, models

def covets_uniques_v13_rename(apps, schema_editor):
    Card = apps.get_model('pbf', 'Card')

    for name in ('Melt Earth to Slag', 'Favors of Steel and Bone'):
        Card.objects.filter(name=name).update(name=f"{name} v1.3", spirit=None)

def covets_uniques_v13_unrename(apps, schema_editor):
    Card = apps.get_model('pbf', 'Card')
    Spirit = apps.get_model('pbf', 'Spirit')
    covets = Spirit.objects.get(name='Covets')

    for name in ('Melt Earth to Slag', 'Favors of Steel and Bone'):
        Card.objects.filter(name=f"{name} v1.3").update(name=name, spirit=covets)

def covets_add_v14_uniques(apps, schema_editor):
    Card = apps.get_model('pbf', 'Card')
    Spirit = apps.get_model('pbf', 'Spirit')
    covets = Spirit.objects.get(name='Covets')

    unique = 2
    fast = 1
    slow = 2

    Card(name="Favors of Steel and Bone", cost=1, type=unique, speed=fast, spirit=covets, elements="Sun,Earth,Animal").save()
    Card(name="Melt Earth to Slag",       cost=1, type=unique, speed=slow, spirit=covets, elements="Sun,Moon,Fire,Earth").save()

def covets_rm_v14_uniques(apps, schema_editor):
    Card = apps.get_model('pbf', 'Card')

    for name in ('Melt Earth to Slag', 'Favors of Steel and Bone'):
        Card.objects.get(name=name).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('pbf', '0060_remove_gameplayer_base_energy_per_turn'),
    ]

    operations = [
        migrations.RunPython(covets_uniques_v13_rename, covets_uniques_v13_unrename),
        migrations.RunPython(covets_add_v14_uniques, covets_rm_v14_uniques),
    ]
