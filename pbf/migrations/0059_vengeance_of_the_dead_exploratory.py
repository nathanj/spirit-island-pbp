from django.db import models, migrations

def add_vengeance_of_the_dead_exploratory(apps, schema_editor):
    Card = apps.get_model("pbf", "Card")
    type_major = 1
    speed_fast = 1
    Card(name="Vengeance of the Dead exploratory", cost=3, type=type_major, speed=speed_fast, elements="Moon,Fire,Animal", exclude_from_deck=True).save()

def delete_vengeance_of_the_dead_exploratory(apps, schema_editor):
    Card = apps.get_model("pbf", "Card")
    Card.objects.get(name="Vengeance of the Dead exploratory").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('pbf', '0058_card_exclude_from_deck'),
    ]

    operations = [
        migrations.RunPython(add_vengeance_of_the_dead_exploratory, delete_vengeance_of_the_dead_exploratory),
    ]
