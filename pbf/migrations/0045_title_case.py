from django.db import migrations

# The FAQ is inconsistent about "Into":
#
# capitalised:
# Melt Earth Into Quicksand
# Settle Into Hunting-Grounds
# Scream Disease Into the Wind
#
# not capitalised:
# Cast Down into the Briny Deep
# Drift Down into Slumber
# Spill Bitterness into the Earth
# Sweep into the Sea
#
# unknown (no FAQ tag):
# Foundations Sink into Mud
# Sear Anger into the Wild Lands
#
# There's a bare majority for not capitalised.
# By the rules, it's a preposition so it shouldn't be capitalised.

# "Down" in "Cast Down into the Briny Deep" and "Drift Down into Slumber" are a little borderline,
# but the argument is that they are acting as adverbs.

# "Across" in "Hazards Spread Across the Island" and "Sunset's Fire Flows Across the Land" are extremely suspect,
# but apparently they are long enough that you are supposed to capitalise them,
# even though they are clearly prepositions.
changes = (
    ('Bats Scout For Raids By Darkness', 'Bats Scout for Raids by Darkness'),
    ('Call To Guard', 'Call to Guard'),
    ('Cast down into the Briny Deep', 'Cast Down into the Briny Deep'),
    ('Drift down into Slumber', 'Drift Down into Slumber'),
    ('Dry Wood Explodes In Smoldering Splinters', 'Dry Wood Explodes in Smoldering Splinters'),
    ('Entrap The Forces Of Corruption', 'Entrap the Forces of Corruption'),
    ('Favor Of The Sun And Star-Lit Dark', 'Favor of the Sun and Star-Lit Dark'),
    ('Haunted By Primal Memories', 'Haunted by Primal Memories'),
    ('Hazards Spread Across The Island', 'Hazards Spread Across the Island'),
    ('Here there be Monsters', 'Here There Be Monsters'),
    ('Instruments of their own Ruin', 'Instruments of Their Own Ruin'),
    ('Scream Disease Into The Wind', 'Scream Disease into the Wind'),
    ('Sear Anger Into The Wild Lands', 'Sear Anger into the Wild Lands'),
    ('Set Them On An Ever-Twisting Trail', 'Set Them on an Ever-Twisting Trail'),
    ('Settle Into Hunting-Grounds', 'Settle into Hunting-Grounds'),
    ('Skies Herald The Season Of Return', 'Skies Herald the Season of Return'),
    ('Strong And Constant Currents', 'Strong and Constant Currents'),
    ("Sunset's Fire Flows Across The Land", "Sunset's Fire Flows Across the Land"),
    ('Terror Turns To Madness', 'Terror Turns to Madness'),
    ('The Shore Seethes With Hatred', 'The Shore Seethes with Hatred'),
    ('The Wounded Wild Turns on its Assailants', 'The Wounded Wild Turns on Its Assailants'),
    ('Too near the Jungle', 'Too Near the Jungle'),
    ('Twilight Fog brings Madness', 'Twilight Fog Brings Madness'),
    ('Weep For What Is Lost', 'Weep for What Is Lost'),
)

def titlecase(apps, schema_editor):
    Card = apps.get_model('pbf', 'Card')
    for (old, new) in changes:
        card = Card.objects.get(name=old)
        card.name = new
        card.save()

def untitlecase(apps, schema_editor):
    Card = apps.get_model('pbf', 'Card')
    for (old, new) in changes:
        card = Card.objects.get(name=new)
        card.name = old
        card.save()

class Migration(migrations.Migration):
    dependencies = [
        ('pbf', '0044_dark_fire_shadows'),
    ]

    operations = [
        migrations.RunPython(titlecase, untitlecase),
    ]
