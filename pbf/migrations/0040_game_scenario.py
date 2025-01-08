from django.db import models, migrations

class Migration(migrations.Migration):

    dependencies = [
        ('pbf', '0039_add_spreading_rot_renews_the_earth'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='scenario',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
