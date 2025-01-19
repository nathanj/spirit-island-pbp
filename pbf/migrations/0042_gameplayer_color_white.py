from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("pbf", "0041_card_speed"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gameplayer",
            name="color",
            field=models.CharField(
                blank=True,
                choices=[
                    ("blue", "blue"),
                    ("green", "green"),
                    ("orange", "orange"),
                    ("purple", "purple"),
                    ("red", "red"),
                    ("yellow", "yellow"),
                    ("cyan", "cyan"),
                    ("brown", "brown"),
                    ("pink", "pink"),
                    ("white", "white"),
                ],
                max_length=255,
            ),
        ),
    ]
