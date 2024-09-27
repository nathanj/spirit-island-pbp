from django.db import models, migrations

def load_covets_gleaming_shards(apps, schema_editor):
    Spirit = apps.get_model("pbf", "Spirit")
    Card = apps.get_model("pbf", "Card")
    covets = Spirit(name="Covets")
    covets.save()
    Card(name="Favors of Steel and Bone", cost=1, type=2, spirit=covets, elements="Sun,Earth,Animal").save()
    Card(name="Melt Earth to Slag", cost=2, type=2, spirit=covets, elements="Sun,Fire,Earth").save()
    Card(name="Petition for Smoldering Wrath", cost=1, type=2, spirit=covets, elements="Moon,Fire,Air,Earth").save()
    Card(name="Unnerving Attention", cost=1, type=2, spirit=covets, elements="Air,Earth,Animal").save()

def delete_covets_gleaming_shards(apps, schema_editor):
    Spirit = apps.get_model("pbf", "Spirit")
    Card = apps.get_model("pbf", "Card")
    Card.objects.filter(spirit=Spirit.objects.get(name="Covets")).delete()
    Spirit.objects.get(name="Covets").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('pbf', '0036_gameplayer_spirit_specific_resource'),
    ]

    operations = [
        migrations.RunPython(load_covets_gleaming_shards, delete_covets_gleaming_shards),
    ]
