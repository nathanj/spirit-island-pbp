from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('pbf', '0035_remove_gameplayer_impending_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='gameplayer',
            name='spirit_specific_resource',
            field=models.IntegerField(default=0),
        ),
    ]
