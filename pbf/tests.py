from django.test import Client, TestCase
from .models import Card, Game, Spirit

class TestSetupEnergyAndBaseGain(TestCase):
    def assert_spirit(self, spirit, per_turn=0, setup=0):
        client = Client()
        game = Game()
        game.save()
        r = client.post(f"/game/{game.id}/add-player", {"spirit": spirit, "color": "random"})
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
        Card(name="Bats Scout For Raids By Darkness", cost=1, type=0, speed=1).save()
        Card(name="Dreams of the Dahan", cost=0, type=2, speed=1).save()
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

class TestReshuffleOrNot(TestCase):
    # NB: Since tests don't seed the DB,
    # the games created only have the cards added in Nature Incarnate
    # and any future additions (none as of this writing)
    MAJORS = 12
    # shouldn't be necessary to test minors separately from majors;
    # they use the same logic.
    #MINORS = 1

    def setup_game(self, cards_in_deck):
        client = Client()

        client.post("/new")
        game = Game.objects.last()

        client.post(f"/game/{game.id}/add-player", {"spirit": "Vigil", "color": "random"})
        v = game.gameplayer_set.all()
        self.assertEqual(len(v), 1, "didn't find one game player; spirit not created successfully?")
        player = v[0]

        cards = list(game.major_deck.all())
        game.major_deck.set(cards[:cards_in_deck])
        game.discard_pile.add(*cards[cards_in_deck:])

        return (client, game, player)

    def test_not_reshuffle_on_gain(self):
        arbitrary_cards_in_deck = 7
        client, game, player = self.setup_game(arbitrary_cards_in_deck)

        remaining = list(game.major_deck.all())
        discard_before = game.discard_pile.count()

        client.post(f"/game/{player.id}/gain/major/4")

        sel = player.selection.all()
        self.assertEqual(len(sel), 4)
        for s in sel:
            self.assertIn(s, remaining, "game offered a card not from the deck?")
        self.assertEqual(game.major_deck.count(), arbitrary_cards_in_deck - 4)
        self.assertEqual(game.discard_pile.count(), discard_before)

    def test_reshuffle_on_gain(self):
        client, game, player = self.setup_game(2)

        remaining = list(game.major_deck.all())

        client.post(f"/game/{player.id}/gain/major/4")

        sel = player.selection.all()
        self.assertEqual(len(sel), 4)
        for rem in remaining:
            self.assertIn(rem, sel, "card in deck before reshuffle should have been drawn")
        self.assertEqual(game.major_deck.count(), self.MAJORS - 4)
        self.assertEqual(game.discard_pile.count(), 0)

    def test_not_reshuffle_on_take(self):
        arbitrary_cards_in_deck = 7
        client, game, player = self.setup_game(arbitrary_cards_in_deck)

        discard_before = game.discard_pile.count()
        majors_before = player.hand.filter(type=Card.MAJOR).count()

        client.post(f"/game/{player.id}/take/major")

        self.assertEqual(player.hand.filter(type=Card.MAJOR).count(), majors_before + 1)
        self.assertEqual(game.major_deck.count(), arbitrary_cards_in_deck - 1)
        self.assertEqual(game.discard_pile.count(), discard_before)

    def test_reshuffle_on_take(self):
        client, game, player = self.setup_game(0)

        majors_before = player.hand.filter(type=Card.MAJOR).count()

        client.post(f"/game/{player.id}/take/major")

        self.assertEqual(player.hand.filter(type=Card.MAJOR).count(), majors_before + 1)
        self.assertEqual(game.major_deck.count(), self.MAJORS - 1)
        self.assertEqual(game.discard_pile.count(), 0)

    def test_not_reshuffle_on_host_draw(self):
        arbitrary_cards_in_deck = 7
        client, game, player = self.setup_game(arbitrary_cards_in_deck)

        discard_before = game.discard_pile.count()

        client.post(f"/game/{game.id}/draw/major")

        self.assertEqual(game.major_deck.count(), arbitrary_cards_in_deck - 1)
        self.assertEqual(game.discard_pile.count(), discard_before + 1)

    def test_reshuffle_on_host_draw(self):
        client, game, player = self.setup_game(0)

        client.post(f"/game/{game.id}/draw/major")

        self.assertEqual(game.major_deck.count(), self.MAJORS - 1)
        self.assertEqual(game.discard_pile.count(), 1)

class TestRot(TestCase):
    def assert_rot(self, rot, expected_rot_loss, expected_energy_gain, round_down=False):
        client = Client()
        game = Game()
        game.save()
        r = client.post(f"/game/{game.id}/add-player", {"spirit": "Rot" + (" - Round Down" if round_down else ""), "color": "random"})
        v = game.gameplayer_set.all()
        self.assertEqual(len(v), 1, "didn't find one game player; spirit not created successfully?")
        player = v[0]

        # give them some energy to ensure that energy is being incremented by the gain, not set to the gain.
        player.energy = 10
        player.spirit_specific_resource = rot
        player.save()

        client.get(f"/game/{player.id}/rot/convert")
        player.refresh_from_db()

        self.assertEqual(player.spirit_specific_resource, rot - expected_rot_loss)
        self.assertEqual(player.energy, 10 + expected_energy_gain)

    def test_round_up_odd_even(self):
        self.assert_rot(7, 4, 2)

    def test_round_up_even_even(self):
        self.assert_rot(8, 4, 2)

    def test_round_up_odd_odd(self):
        self.assert_rot(9, 5, 3)

    def test_round_up_even_odd(self):
        self.assert_rot(10, 5, 3)

    def test_round_down_odd_odd(self):
        self.assert_rot(7, 3, 1, round_down=True)

    def test_round_down_even_even(self):
        self.assert_rot(8, 4, 2, round_down=True)

    def test_round_down_odd_even(self):
        self.assert_rot(9, 4, 2, round_down=True)

    def test_round_down_even_odd(self):
        self.assert_rot(10, 5, 2, round_down=True)
