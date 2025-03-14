from django.db import migrations

def earthquake_presence_impending(apps, schema_editor):
    Presence = apps.get_model('pbf', 'Presence')
    presences = Presence.objects.filter(left=753, top=147, energy="", elements="", game_player__spirit__name="Earthquakes")
    presences.update(energy="Impend2")

def earthquake_presence_unimpend(apps, schema_editor):
    # It's not really necessary to undo this change,
    # as long as the code would ignore the "Impend2" in the energy values.
    # But it's easy enough to undo.
    Presence = apps.get_model('pbf', 'Presence')
    presences = Presence.objects.filter(left=753, top=147, energy="Impend2", elements="", game_player__spirit__name="Earthquakes")
    presences.update(energy="")

class Migration(migrations.Migration):
    dependencies = [
        ('pbf', '0045_title_case'),
    ]

    operations = [
        migrations.RunPython(earthquake_presence_impending, earthquake_presence_unimpend),
    ]
