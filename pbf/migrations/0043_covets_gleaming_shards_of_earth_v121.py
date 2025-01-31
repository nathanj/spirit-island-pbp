from django.db import migrations

def covets_121_remove_earth(apps, schema_editor):
    Card = apps.get_model('pbf', 'Card')
    card = Card.objects.get(name='Petition for Smoldering Wrath')
    card.elements = 'Moon,Fire,Air'
    card.save()

def covets_110_add_earth(apps, schema_editor):
    Card = apps.get_model('pbf', 'Card')
    card = Card.objects.get(name='Petition for Smoldering Wrath')
    card.elements = 'Moon,Fire,Air,Earth'
    card.save()

class Migration(migrations.Migration):
    dependencies = [
        ('pbf', '0042_gameplayer_color_white'),
    ]

    operations = [
        migrations.RunPython(covets_121_remove_earth, covets_110_add_earth),
    ]
