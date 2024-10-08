from django.db import models, migrations

def load_spreading_rot(apps, schema_editor):
    Spirit = apps.get_model("pbf", "Spirit")
    Card = apps.get_model("pbf", "Card")
    rot = Spirit(name="Rot")
    rot.save()
    Card(name="Land of Deadfall and Rot", cost=1, type=2, spirit=rot, elements="Water,Earth,Plant").save()
    Card(name="Infesting Spores", cost=2, type=2, spirit=rot, elements="Fire,Plant,Animal").save()
    Card(name="Worms and Bugs Enrich the Soil", cost=1, type=2, spirit=rot, elements="Moon,Water,Earth,Animal").save()
    Card(name="Exaltation of the Re-Forming Land", cost=0, type=2, spirit=rot, elements="Sun,Moon,Water,Plant").save()

def delete_spreading_rot(apps, schema_editor):
    Spirit = apps.get_model("pbf", "Spirit")
    Card = apps.get_model("pbf", "Card")
    Card.objects.filter(spirit=Spirit.objects.get(name="Rot")).delete()
    Spirit.objects.get(name="Rot").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('pbf', '0038_gameplayer_spirit_specific_per_turn_flag'),
    ]

    operations = [
        migrations.RunPython(load_spreading_rot, delete_spreading_rot),
    ]
