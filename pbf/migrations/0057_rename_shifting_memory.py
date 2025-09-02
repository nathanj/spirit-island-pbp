from django.db import migrations, models

def rename_spirit(apps, old_name, new_name):
    Spirit = apps.get_model('pbf', 'Spirit')
    spirit = Spirit.objects.get(name=old_name)
    spirit.name = new_name
    spirit.save()

def rename_shifting_to_memory(apps, schema_editor):
    rename_spirit(apps, 'Shifting', 'Memory')

def rename_memory_to_shifting(apps, schema_editor):
    rename_spirit(apps, 'Memory', 'Shifting')

class Migration(migrations.Migration):
    dependencies = [
        ('pbf', '0056_covets_gleaming_shards_of_earth_v13'),
    ]

    operations = [
        migrations.RunPython(rename_shifting_to_memory, rename_memory_to_shifting),
    ]
