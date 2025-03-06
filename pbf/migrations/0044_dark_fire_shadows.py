from django.db import migrations

def darkfire_to_dark_fire(apps, schema_editor):
    GamePlayer = apps.get_model('pbf', 'GamePlayer')
    players = GamePlayer.objects.filter(spirit__name='Shadows', aspect='DarkFire')
    for player in players:
        player.aspect = 'Dark Fire'
        player.save()

def dark_fire_to_darkfire(apps, schema_editor):
    GamePlayer = apps.get_model('pbf', 'GamePlayer')
    players = GamePlayer.objects.filter(spirit__name='Shadows', aspect='Dark Fire')
    for player in players:
        player.aspect = 'DarkFire'
        player.save()

class Migration(migrations.Migration):
    dependencies = [
        ('pbf', '0043_covets_gleaming_shards_of_earth_v121'),
    ]

    operations = [
        migrations.RunPython(darkfire_to_dark_fire, dark_fire_to_darkfire),
    ]
