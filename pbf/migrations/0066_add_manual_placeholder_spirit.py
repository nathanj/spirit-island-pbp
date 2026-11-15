from django.db import migrations


def load_manual(apps, schema_editor):
    Spirit = apps.get_model("pbf", "Spirit")
    Card = apps.get_model("pbf", "Card")
    spirit = Spirit(name="ManualPlaceholder")
    spirit.save()
    Card(name="ManualPlaceholder Card A", cost=0, type=2, speed=2, spirit=spirit, elements="").save()
    Card(name="ManualPlaceholder Card B", cost=0, type=2, speed=2, spirit=spirit, elements="").save()
    Card(name="ManualPlaceholder Card C", cost=0, type=2, speed=2, spirit=spirit, elements="").save()
    Card(name="ManualPlaceholder Card D", cost=0, type=2, speed=2, spirit=spirit, elements="").save()
    Card(name="ManualPlaceholder Card E", cost=0, type=2, speed=2, spirit=spirit, elements="").save()
    Card(name="ManualPlaceholder Card F", cost=0, type=2, speed=2, spirit=spirit, elements="").save()


def delete_manual(apps, schema_editor):
    Spirit = apps.get_model("pbf", "Spirit")
    Card = apps.get_model("pbf", "Card")
    Card.objects.filter(spirit=Spirit.objects.get(name="ManualPlaceholder")).delete()
    Spirit.objects.get(name="ManualPlaceholder").delete()


class Migration(migrations.Migration):

    dependencies = (
        ('pbf', '0065_card_type_rename_special_to_retired'),
    )

    operations = (
        migrations.RunPython(load_manual, delete_manual),
    )
