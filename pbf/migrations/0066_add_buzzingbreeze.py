from django.db import migrations


def load_custom(apps, schema_editor):
    Spirit = apps.get_model("pbf", "Spirit")
    Card = apps.get_model("pbf", "Card")
    mijn = Spirit(name="BuzzingBreeze")
    mijn.save()
    Card(name="Waltz on Wings of Wind", cost=1, type=2, speed=1, spirit=mijn, elements="Air,Water,Plant").save()
    Card(name="Nightly Deliveries", cost=0, type=2, speed=2, spirit=mijn, elements="Moon,Air,Plant").save()
    Card(name="Life Brought by Gentle Winds", cost=1, type=2, speed=1, spirit=mijn, elements="Sun,Air,Plant,Animal").save()
    Card(name="Bring Tidings of Woe", cost=2, type=2, speed=1, spirit=mijn, elements="Sun,Moon,Fire,Air").save()


def delete_custom(apps, schema_editor):
    Spirit = apps.get_model("pbf", "Spirit")
    Card = apps.get_model("pbf", "Card")
    Card.objects.filter(spirit=Spirit.objects.get(name="BuzzingBreeze")).delete()
    Spirit.objects.get(name="BuzzingBreeze").delete()


class Migration(migrations.Migration):

    dependencies = (
        ('pbf', '0065_card_type_rename_special_to_retired'),
    )

    operations = (
        migrations.RunPython(load_custom, delete_custom),
    )