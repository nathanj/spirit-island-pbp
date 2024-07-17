from django.test import Client, TestCase
from .models import Card, Game, Spirit

class TestSetupEnergyAndBaseGain(TestCase):
    def assert_spirit(self, spirit, per_turn=0, setup=0):
        client = Client()
        game = Game()
        game.save()
        r = client.post(f"/game/{game.id}/add-player", {"spirit": spirit})
        v = game.gameplayer_set.all()
        self.assertEqual(len(v), 1, "didn't find one game player; spirit not created successfully?")
        player = v[0]
        self.assertEqual(player.get_gain_energy(), per_turn, "per turn energy incorrect")
        self.assertEqual(player.energy, setup, "setup energy incorrect")

    # Note that the tests don't seed the DB, only migrate,
    # so they're missing some spirits that we have to manually create below.

    def test_base_spirit_with_aspect(self):
        Spirit(name="River").save()
        s = self.assert_spirit("River", per_turn=1)

    def test_aspect_modifying_setup_energy(self):
        Spirit(name="River").save()
        s = self.assert_spirit("River - Sunshine", per_turn=1, setup=1)

    def test_aspect_modifying_nothing(self):
        Spirit(name="River").save()
        s = self.assert_spirit("River - Haven", per_turn=1)

    def test_base_spirit_with_aspect2(self):
        Spirit(name="Bringer").save()
        s = self.assert_spirit("Bringer", per_turn=2)

    def test_aspect_modifying_setup_energy2(self):
        Spirit(name="Bringer").save()
        # have to create the cards added/removed by the aspect,
        # otherwise the spirit can't be added to the game
        Card(name="Bats Scout For Raids By Darkness", cost=1, type=0).save()
        Card(name="Dreams of the Dahan", cost=0, type=2).save()
        s = self.assert_spirit("Bringer - Violence", per_turn=2, setup=1)

    def test_aspect_modifying_nothing2(self):
        Spirit(name="Bringer").save()
        s = self.assert_spirit("Bringer - Enticing", per_turn=2)

    def test_base_spirit_with_aspect3(self):
        Spirit(name="Lightning").save()
        s = self.assert_spirit("Lightning", per_turn=1)

    def test_aspect_modifying_nothing3(self):
        Spirit(name="Lightning").save()
        s = self.assert_spirit("Lightning - Wind", per_turn=1)

    def test_aspect_multiplying_gain(self):
        Spirit(name="Lightning").save()
        s = self.assert_spirit("Lightning - Immense", per_turn=2)

    def test_base_spirit_with_aspect4(self):
        Spirit(name="Keeper").save()
        s = self.assert_spirit("Keeper", per_turn=2)

    def test_aspect_modifying_setup_and_base_gain(self):
        Spirit(name="Keeper").save()
        s = self.assert_spirit("Keeper - Spreading Hostility", per_turn=1, setup=1)

    def test_spirit_with_initial(self):
        s = self.assert_spirit("Vigil", per_turn=0, setup=1)

    def test_spirit_with_initial_2(self):
        s = self.assert_spirit("Waters", per_turn=0, setup=4)
