from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('pbf', '0037_add_covets_gleaming_shards_of_earth'),
    ]

    operations = [
        migrations.AddField(
            model_name='gameplayer',
            name='spirit_specific_per_turn_flags',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
