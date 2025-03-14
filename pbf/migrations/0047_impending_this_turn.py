from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('pbf', '0046_earthquake_presence_impending'),
    ]

    operations = [
        migrations.AddField(
            model_name='GamePlayerImpendingWithEnergy',
            name='this_turn',
            field=models.BooleanField(default=True),
        ),
    ]
