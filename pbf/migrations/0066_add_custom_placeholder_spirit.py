from django.db import migrations


def load_custom(apps, schema_editor):
    Spirit = apps.get_model("pbf", "Spirit")
    Card = apps.get_model("pbf", "Card")
    mijn = Spirit(name="CustomPlaceholder")
    mijn.save()
    Card(name="CustomPlaceholder Card A", cost=0, type=2, speed=0, spirit=mijn, elements="").save()
    Card(name="CustomPlaceholder Card B", cost=0, type=2, speed=0, spirit=mijn, elements="").save()
    Card(name="CustomPlaceholder Card C", cost=0, type=2, speed=1, spirit=mijn, elements="").save()
    Card(name="CustomPlaceholder Card D", cost=0, type=2, speed=0, spirit=mijn, elements="").save()
    Card(name="CustomPlaceholder Card E", cost=0, type=2, speed=0, spirit=mijn, elements="").save()
    Card(name="CustomPlaceholder Card F", cost=0, type=2, speed=0, spirit=mijn, elements="").save()


def delete_custom(apps, schema_editor):
    Spirit = apps.get_model("pbf", "Spirit")
    Card = apps.get_model("pbf", "Card")
    Card.objects.filter(spirit=Spirit.objects.get(name="CustomPlaceholder")).delete()
    Spirit.objects.get(name="CustomPlaceholder").delete()


class Migration(migrations.Migration):

    dependencies = (
        ('pbf', '0065_card_type_rename_special_to_retired'),
    )

    operations = (
        migrations.RunPython(load_custom, delete_custom),
    )