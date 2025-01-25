from collections import Counter
from django.test import Client, TestCase
from .models import Card, Elements, Game, GamePlayer, Spirit

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
        s = self.assert_spirit("River", per_turn=1)

    def test_aspect_modifying_setup_energy(self):
        s = self.assert_spirit("River - Sunshine", per_turn=1, setup=1)

    def test_aspect_modifying_nothing(self):
        s = self.assert_spirit("River - Haven", per_turn=1)

    def test_base_spirit_with_aspect2(self):
        s = self.assert_spirit("Bringer", per_turn=2)

    def test_aspect_modifying_setup_energy2(self):
        s = self.assert_spirit("Bringer - Violence", per_turn=2, setup=1)

    def test_aspect_modifying_nothing2(self):
        s = self.assert_spirit("Bringer - Enticing", per_turn=2)

    def test_base_spirit_with_aspect3(self):
        s = self.assert_spirit("Lightning", per_turn=1)

    def test_aspect_modifying_nothing3(self):
        s = self.assert_spirit("Lightning - Wind", per_turn=1)

    def test_aspect_multiplying_gain(self):
        s = self.assert_spirit("Lightning - Immense", per_turn=2)

    def test_base_spirit_with_aspect4(self):
        s = self.assert_spirit("Keeper", per_turn=2)

    def test_aspect_modifying_setup_and_base_gain(self):
        s = self.assert_spirit("Keeper - Spreading Hostility", per_turn=1, setup=1)

    def test_spirit_with_initial(self):
        s = self.assert_spirit("Vigil", per_turn=0, setup=1)

    def test_spirit_with_initial_2(self):
        s = self.assert_spirit("Waters", per_turn=0, setup=4)

class TestReshuffleOrNot(TestCase):
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
        available_cards = game.major_deck.count() + game.discard_pile.count()

        client.post(f"/game/{player.id}/gain/major/4")

        sel = player.selection.all()
        self.assertEqual(len(sel), 4)
        for rem in remaining:
            self.assertIn(rem, sel, "card in deck before reshuffle should have been drawn")
        self.assertEqual(game.major_deck.count(), available_cards - 4)
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
        available_cards = game.major_deck.count() + game.discard_pile.count()

        client.post(f"/game/{player.id}/take/major")

        self.assertEqual(player.hand.filter(type=Card.MAJOR).count(), majors_before + 1)
        self.assertEqual(game.major_deck.count(), available_cards - 1)
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
        available_cards = game.major_deck.count() + game.discard_pile.count()

        client.post(f"/game/{game.id}/draw/major")

        self.assertEqual(game.major_deck.count(), available_cards - 1)
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

class TestChooseCard(TestCase):
    def cards_gained(self, card_type, draw):
        # Note that the tests don't seed the DB, only migrate,
        # so the only minor they create is Roiling Bog and Snagging Thorn.
        # We'll need to create some minors so that the tests have enough to work with.
        if card_type == 'minor':
            for i in range(6):
                Card(name=f"Minor {i}", cost=0, type=Card.MINOR, speed=Card.FAST).save()
        client = Client()
        client.post("/new")
        game = Game.objects.last()
        client.post(f"/game/{game.id}/add-player", {"spirit": "Waters", "color": "random"})
        v = game.gameplayer_set.all()
        self.assertEqual(len(v), 1, "didn't find one game player; spirit not created successfully?")
        player = v[0]
        client.post(f"/game/{player.id}/gain/{card_type}/{draw}")
        player.refresh_from_db()
        selected = 0
        while player.selection.exists():
            client.post(f"/game/{player.id}/choose/{player.selection.first().id}")
            selected += 1
            player.refresh_from_db()
        return selected

    def assert_cards_gained(self, card_type, draw, should_gain):
        self.assertEqual(self.cards_gained(card_type, draw), should_gain)

    def test_regular_minor(self):
        self.assert_cards_gained('minor', 4, 1)

    def test_boon_of_reimagining(self):
        self.assert_cards_gained('minor', 6, 2)

    def test_regular_major(self):
        self.assert_cards_gained('major', 4, 1)

    def test_unlock_the_gates_major(self):
        self.assert_cards_gained('major', 2, 1)

    def test_covets_major(self):
        self.assert_cards_gained('major', 6, 1)

class TestPlayCost(TestCase):
    def assert_cost(self, card_names, expected_cost, scenario=''):
        game = Game(scenario=scenario)
        game.save()
        player = GamePlayer(game=game, spirit=Spirit.objects.get(name='Vigil'))
        player.save()
        cards = [Card.objects.get(name=name) for name in card_names]
        player.play.set(cards)
        self.assertEqual(player.get_play_cost(), expected_cost)

    def test_fast_not_blitz(self):
        self.assert_cost(['Favors of Story and Season'], 1)

    def test_slow_not_blitz(self):
        self.assert_cost(['Call to Vigilance'], 2)

    def test_fast_blitz(self):
        self.assert_cost(['Favors of Story and Season'], 0, scenario='Blitz')

    def test_slow_blitz(self):
        self.assert_cost(['Call to Vigilance'], 2, scenario='Blitz')

class TestElements(TestCase):
    def setup_game(self, card_names):
        game = Game()
        game.save()
        player = GamePlayer(game=game, spirit=Spirit.objects.get(name='River'))
        player.save()
        cards = [Card.objects.get(name=name) for name in card_names]
        player.play.set(cards)

        return player

    def assert_elements(self, player, expected_elements):
        # we can just compare the entire counter,
        # but the error message for a mismatch is not great.
        #self.assertEqual(player.elements, expected_elements)
        self.assertEqual(len(player.elements), len(expected_elements))
        for e in player.elements.keys():
            self.assertEqual(player.elements[e], expected_elements[e])

    def test_no_elements(self):
        expected_elements = Counter()

        player = self.setup_game(["Elemental Boon"])
        self.assert_elements(player, expected_elements)

    def test_elements_single_card(self):
        expected_elements = Counter()
        expected_elements[Elements.Sun] = 1
        expected_elements[Elements.Water] = 1
        expected_elements[Elements.Plant] = 1

        player = self.setup_game(["Boon of Vigor"])
        self.assert_elements(player, expected_elements)

    def test_elements_multiple_cards(self):
        expected_elements = Counter()
        expected_elements[Elements.Sun] = 2
        expected_elements[Elements.Air] = 2
        expected_elements[Elements.Water] = 2
        expected_elements[Elements.Animal] = 2

        player = self.setup_game(["River's Bounty", "Call to Isolation", "Flow like Water, Reach like Air"])
        self.assert_elements(player, expected_elements)

    def test_elements_with_temporary(self):
        expected_elements = Counter()
        expected_elements[Elements.Air] = 1
        expected_elements[Elements.Water] = 3
        expected_elements[Elements.Earth] = 1
        expected_elements[Elements.Plant] = 2
        expected_elements[Elements.Animal] = 2

        player = self.setup_game(["Wash Away", "Flow Downriver, Blow Downwind", "Ravaged Undergrowth Slithers Back to Life"])
        player.temporary_animal += 1
        self.assert_elements(player, expected_elements)
