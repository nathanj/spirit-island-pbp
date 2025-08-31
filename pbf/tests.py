import os
from collections import Counter
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from .models import Card, Elements, Game, GamePlayer, Spirit

class TestPresence(TestCase):
    def test_irrelevant_presence_energy(self):
        game = Game()
        game.save()
        player = GamePlayer(game=game, base_energy_per_turn=1, spirit=Spirit.objects.first())
        player.save()
        player.presence_set.create(left=0, top=0, opacity=0.0)
        self.assertEqual(player.get_gain_energy(), 1)

    def test_presence_covering_energy(self):
        game = Game()
        game.save()
        player = GamePlayer(game=game, base_energy_per_turn=1, spirit=Spirit.objects.first())
        player.save()
        player.presence_set.create(left=0, top=0, opacity=1.0, energy='2')
        self.assertEqual(player.get_gain_energy(), 1)

    def test_max_energy(self):
        game = Game()
        game.save()
        player = GamePlayer(game=game, base_energy_per_turn=1, spirit=Spirit.objects.first())
        player.save()
        player.presence_set.create(left=0, top=0, opacity=0.0, energy='2')
        player.presence_set.create(left=0, top=0, opacity=0.0, energy='3')
        self.assertEqual(player.get_gain_energy(), 3)

    def test_presence_covering_plus_energy(self):
        game = Game()
        game.save()
        player = GamePlayer(game=game, base_energy_per_turn=1, spirit=Spirit.objects.first())
        player.save()
        player.presence_set.create(left=0, top=0, opacity=1.0, energy='+2')
        self.assertEqual(player.get_gain_energy(), 1)

    def test_plus_energy(self):
        game = Game()
        game.save()
        player = GamePlayer(game=game, base_energy_per_turn=1, spirit=Spirit.objects.first())
        player.save()
        player.presence_set.create(left=0, top=0, opacity=0.0, energy='+2')
        player.presence_set.create(left=0, top=0, opacity=0.0, energy='+4')
        self.assertEqual(player.get_gain_energy(), 7)

    def test_max_and_plus_energy(self):
        game = Game()
        game.save()
        player = GamePlayer(game=game, base_energy_per_turn=1, spirit=Spirit.objects.first())
        player.save()
        player.presence_set.create(left=0, top=0, opacity=0.0, energy='2')
        player.presence_set.create(left=0, top=0, opacity=0.0, energy='3')
        player.presence_set.create(left=0, top=0, opacity=0.0, energy='+4')
        player.presence_set.create(left=0, top=0, opacity=0.0, energy='+8')
        self.assertEqual(player.get_gain_energy(), 15)

    def test_no_rot(self):
        game = Game()
        game.save()
        player = GamePlayer(game=game, base_energy_per_turn=1, spirit=Spirit.objects.first())
        player.save()
        player.presence_set.create(left=0, top=0, opacity=0.0)
        self.assertEqual(player.rot_gain(), 0)

    def test_irrelevant_rot(self):
        game = Game()
        game.save()
        player = GamePlayer(game=game, base_energy_per_turn=1, spirit=Spirit.objects.first())
        player.save()
        player.presence_set.create(left=0, top=0, opacity=0.0, elements='Fire')
        self.assertEqual(player.rot_gain(), 0)

    def test_covered_rot(self):
        game = Game()
        game.save()
        player = GamePlayer(game=game, base_energy_per_turn=1, spirit=Spirit.objects.first())
        player.save()
        player.presence_set.create(left=0, top=0, opacity=1.0, elements='Rot')
        self.assertEqual(player.rot_gain(), 0)

    def test_rot(self):
        game = Game()
        game.save()
        player = GamePlayer(game=game, base_energy_per_turn=1, spirit=Spirit.objects.first())
        player.save()
        player.presence_set.create(left=0, top=0, opacity=0.0, elements='Rot')
        self.assertEqual(player.rot_gain(), 1)

    def test_rot_and_something_else(self):
        game = Game()
        game.save()
        player = GamePlayer(game=game, base_energy_per_turn=1, spirit=Spirit.objects.first())
        player.save()
        player.presence_set.create(left=0, top=0, opacity=0.0, elements='Rot,Fire')
        self.assertEqual(player.rot_gain(), 1)

    def test_many_rot(self):
        game = Game()
        game.save()
        player = GamePlayer(game=game, base_energy_per_turn=1, spirit=Spirit.objects.first())
        player.save()
        player.presence_set.create(left=0, top=0, opacity=0.0, elements='Rot')
        player.presence_set.create(left=0, top=0, opacity=0.0, elements='Rot')
        self.assertEqual(player.rot_gain(), 2)

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

class TestSetupPowerCards(TestCase):
    NUM_MINORS = Card.objects.filter(type=Card.MINOR).count()

    def setup_game(self, spirit):
        client = Client()
        client.post("/new")
        game = Game.objects.last()
        r = client.post(f"/game/{game.id}/add-player", {"spirit": spirit, "color": "random"})
        v = game.gameplayer_set.all()
        self.assertEqual(len(v), 1, "didn't find one game player; spirit not created successfully?")
        player = v[0]
        return (client, game, player)

    def test_base_of_aspect_remove_card(self):
        _, game, player = self.setup_game('River')
        self.assertEqual(4, player.hand.count())
        self.assertEqual(self.NUM_MINORS, game.minor_deck.count())
        card_names = player.hand.values_list('name', flat=True)
        self.assertIn('Boon of Vigor', card_names)

    def test_aspect_remove_card(self):
        _, game, player = self.setup_game('River - Sunshine')
        self.assertEqual(3, player.hand.count())
        self.assertEqual(self.NUM_MINORS, game.minor_deck.count())
        card_names = player.hand.values_list('name', flat=True)
        self.assertNotIn('Boon of Vigor', card_names)

    def test_base_of_aspect_add_card(self):
        _, game, player = self.setup_game('Shadows')
        self.assertEqual(4, player.hand.count())
        self.assertEqual(self.NUM_MINORS, game.minor_deck.count())
        card_names = player.hand.values_list('name', flat=True)
        self.assertNotIn('Unquenchable Flames', card_names)
        self.assertEqual(1, game.minor_deck.filter(name='Unquenchable Flames').count())

    def test_aspect_add_card(self):
        _, game, player = self.setup_game('Shadows - Dark Fire')
        self.assertEqual(5, player.hand.count())
        self.assertEqual(self.NUM_MINORS - 1, game.minor_deck.count())
        card_names = player.hand.values_list('name', flat=True)
        self.assertIn('Unquenchable Flames', card_names)
        self.assertEqual(0, game.minor_deck.filter(name='Unquenchable Flames').count())

    def test_base_of_aspect_replace_card(self):
        _, game, player = self.setup_game('Earth')
        self.assertEqual(4, player.hand.count())
        self.assertEqual(self.NUM_MINORS, game.minor_deck.count())
        card_names = player.hand.values_list('name', flat=True)
        self.assertIn('A Year of Perfect Stillness', card_names)
        self.assertNotIn('Voracious Growth', card_names)
        self.assertEqual(1, game.minor_deck.filter(name='Voracious Growth').count())

    def test_aspect_replace_card(self):
        _, game, player = self.setup_game('Earth - Nourishing')
        self.assertEqual(4, player.hand.count())
        self.assertEqual(self.NUM_MINORS - 1, game.minor_deck.count())
        card_names = player.hand.values_list('name', flat=True)
        self.assertNotIn('A Year of Perfect Stillness', card_names)
        self.assertIn('Voracious Growth', card_names)
        self.assertEqual(0, game.minor_deck.filter(name='Voracious Growth').count())

    def test_days_that_never_were(self):
        client, game, player = self.setup_game('Fractured')
        minors = game.minor_deck.count()
        majors = game.major_deck.count()
        client.post(f"/game/{player.id}/create_days/4")
        self.assertEqual(game.minor_deck.count(), minors - 4)
        self.assertEqual(game.major_deck.count(), majors - 4)
        self.assertEqual(player.days.count(), 8)
        self.assertEqual(player.days.filter(type=Card.MINOR).count(), 4)
        self.assertEqual(player.days.filter(type=Card.MAJOR).count(), 4)

class TestEnergyGainAndBargainDebt(TestCase):
    def test_no_debt(self):
        player = GamePlayer(energy=1)
        player.gain_energy_or_pay_debt(2)
        self.assertEqual(player.energy, 3)
        self.assertEqual(player.bargain_paid_this_turn, 0)

    def test_debt_fully_paid(self):
        player = GamePlayer(energy=1, bargain_cost_per_turn=2, bargain_paid_this_turn=2)
        player.gain_energy_or_pay_debt(4)
        self.assertEqual(player.energy, 5)
        self.assertEqual(player.bargain_paid_this_turn, 2)

    def test_gain_less_than_remaining_debt(self):
        player = GamePlayer(energy=1, bargain_cost_per_turn=8, bargain_paid_this_turn=2)
        player.gain_energy_or_pay_debt(4)
        self.assertEqual(player.energy, 1)
        self.assertEqual(player.bargain_paid_this_turn, 6)

    def test_gain_exactly_remaining_debt(self):
        player = GamePlayer(energy=1, bargain_cost_per_turn=8, bargain_paid_this_turn=2)
        player.gain_energy_or_pay_debt(6)
        self.assertEqual(player.energy, 1)
        self.assertEqual(player.bargain_paid_this_turn, 8)

    def test_gain_more_than_remaining_debt(self):
        player = GamePlayer(energy=1, bargain_cost_per_turn=8, bargain_paid_this_turn=2)
        player.gain_energy_or_pay_debt(10)
        self.assertEqual(player.energy, 5)
        self.assertEqual(player.bargain_paid_this_turn, 8)

class TestMatchSpirit(TestCase):
    from .views import try_match_spirit
    try_match_spirit = staticmethod(try_match_spirit)

    def setup_game(self, players):
        game = Game()
        game.save()
        for player in players:
            if isinstance(player, str):
                spirit = player
                aspect = None
                name = ''
            else:
                spirit = player[0]
                aspect = player[1] if len(player) >= 2 else None
                name = player[2] if len(player) >= 3 else ''
            player = GamePlayer(game=game, name=name, spirit=Spirit.objects.get(name=spirit), aspect=aspect)
            player.save()
        return (game, game.gameplayer_set.values_list('id', flat=True))

    def test_no_match(self):
        (game, ids) = self.setup_game(['River'])
        self.assertEqual(self.try_match_spirit(game, 'hello'), None)

    def test_cardinal_1(self):
        (game, ids) = self.setup_game(['River', 'Lightning'])
        self.assertEqual(self.try_match_spirit(game, '1'), ids[0])

    def test_cardinal_2(self):
        (game, ids) = self.setup_game(['River', 'Lightning'])
        self.assertEqual(self.try_match_spirit(game, '2'), ids[1])

    def test_by_id(self):
        # consume some player IDs
        self.setup_game(['River', 'Lightning'])
        (game, ids) = self.setup_game(['Shadows'])
        self.assertEqual(self.try_match_spirit(game, str(ids[0])), ids[0])

    def test_spirit(self):
        (game, ids) = self.setup_game(['River'])
        self.assertEqual(self.try_match_spirit(game, 'River'), ids[0])

    def test_aspect(self):
        (game, ids) = self.setup_game([('River', 'Haven')])
        self.assertEqual(self.try_match_spirit(game, 'Haven'), ids[0])

    def test_spirit_can_refer_to_aspect(self):
        (game, ids) = self.setup_game([('River', 'Haven')])
        self.assertEqual(self.try_match_spirit(game, 'River'), ids[0])

    def test_base_is_preferred(self):
        (game, ids) = self.setup_game([('River', 'Haven'), 'River'])
        self.assertEqual(GamePlayer.objects.get(id=self.try_match_spirit(game, 'River')).aspect, None)
        (game, ids) = self.setup_game(['River', ('River', 'Haven')])
        self.assertEqual(GamePlayer.objects.get(id=self.try_match_spirit(game, 'River')).aspect, None)

    def test_name(self):
        (game, ids) = self.setup_game([('River', None, 'myname')])
        self.assertEqual(self.try_match_spirit(game, 'myname'), ids[0])

    def test_spirit_beats_name(self):
        (game, ids) = self.setup_game([('River', None), ('Lightning', None, 'River')])
        self.assertEqual(GamePlayer.objects.get(id=self.try_match_spirit(game, 'River')).spirit.name, 'River')

    def test_partial_name(self):
        (game, ids) = self.setup_game([('River', None, 'name1')])
        self.assertEqual(self.try_match_spirit(game, 'name'), ids[0])

    def test_exact_name_beats_partial_name(self):
        (game, ids) = self.setup_game([('River', None, 'name1'), ('Lightning', None, 'name')])
        self.assertEqual(GamePlayer.objects.get(id=self.try_match_spirit(game, 'name')).name, 'name')
        (game, ids) = self.setup_game([('River', None, 'name'), ('Lightning', None, 'name1')])
        self.assertEqual(GamePlayer.objects.get(id=self.try_match_spirit(game, 'name')).name, 'name')

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

        client.post(f"/game/{player.id}/take/major/4")

        self.assertEqual(player.hand.filter(type=Card.MAJOR).count(), majors_before + 4)
        self.assertEqual(game.major_deck.count(), arbitrary_cards_in_deck - 4)
        self.assertEqual(game.discard_pile.count(), discard_before)

    def test_reshuffle_on_take(self):
        client, game, player = self.setup_game(1)

        remaining = list(game.major_deck.all())
        majors_before = player.hand.filter(type=Card.MAJOR).count()
        available_cards = game.major_deck.count() + game.discard_pile.count()

        client.post(f"/game/{player.id}/take/major/2")

        self.assertEqual(player.hand.filter(type=Card.MAJOR).count(), majors_before + 2)
        for rem in remaining:
            self.assertIn(rem, player.hand.all(), "card in deck before reshuffle should have been taken")
        self.assertEqual(game.major_deck.count(), available_cards - 2)
        self.assertEqual(game.discard_pile.count(), 0)

    def test_not_reshuffle_on_host_draw(self):
        arbitrary_cards_in_deck = 7
        client, game, _ = self.setup_game(arbitrary_cards_in_deck)

        discard_before = game.discard_pile.count()

        client.post(f"/game/{game.id}/draw", {"type": "major", "num_cards": 4})

        self.assertEqual(game.major_deck.count(), arbitrary_cards_in_deck - 4)
        self.assertEqual(game.discard_pile.count(), discard_before + 4)

    def test_reshuffle_on_host_draw(self):
        client, game, _ = self.setup_game(2)

        remaining = list(game.major_deck.all())
        available_cards = game.major_deck.count() + game.discard_pile.count()

        client.post(f"/game/{game.id}/draw", {"type": "major", "num_cards": 4})

        self.assertEqual(game.major_deck.count(), available_cards - 4)
        discard = game.discard_pile.all()
        self.assertEqual(len(discard), 4)
        for rem in remaining:
            self.assertIn(rem, discard, "game didn't discard a card in the pre-reshuffle deck")

    def test_reshuffle_host_draw_too_many(self):
        client, game, _ = self.setup_game(10)

        available_cards = game.major_deck.count() + game.discard_pile.count()

        client.post(f"/game/{game.id}/draw", {"type": "major", "num_cards": available_cards + 100})

        self.assertEqual(game.major_deck.count(), 0)
        self.assertEqual(game.discard_pile.count(), available_cards)

    # The other tests were all run on major powers,
    # because historically the tests didn't have minor powers available.
    # Now they are, but won't run the full battery of tests on minor powers,
    # since the logic should all be the same.
    # Just doing a few to make sure the basic functionality is there,
    def test_reshuffle_minors_only(self):
        client, game, player = self.setup_game(Card.objects.filter(type=Card.MAJOR).count())

        cards = list(game.minor_deck.all())
        game.minor_deck.set(cards[:2])
        game.discard_pile.add(*cards[2:])

        remaining = list(game.minor_deck.all())
        available_cards = game.minor_deck.count() + game.discard_pile.filter(type=Card.MINOR).count()

        client.post(f"/game/{player.id}/gain/minor/4")

        sel = player.selection.all()
        self.assertEqual(len(sel), 4)
        for rem in remaining:
            self.assertIn(rem, sel, "card in deck before reshuffle should have been drawn")
        self.assertEqual(game.minor_deck.count(), available_cards - 4)
        self.assertEqual(game.discard_pile.count(), 0)

    def test_reshuffle_minors_doesnt_reshuffle_majors(self):
        client, game, player = self.setup_game(30)

        cards = list(game.minor_deck.all())
        game.minor_deck.set(cards[:2])
        game.discard_pile.add(*cards[2:])

        remaining = list(game.minor_deck.all())
        available_cards = game.minor_deck.count() + game.discard_pile.filter(type=Card.MINOR).count()
        majors_in_discard = game.discard_pile.filter(type=Card.MAJOR).count()

        client.post(f"/game/{player.id}/gain/minor/4")

        self.assertEqual(player.selection.count(), 4)
        self.assertEqual(game.minor_deck.count(), available_cards - 4)
        self.assertEqual(game.discard_pile.count(), majors_in_discard)
        self.assertEqual(set(game.discard_pile.values_list('type', flat=True)), {Card.MAJOR})

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
    def cards_gained(self, spirit, card_type, draw):
        client = Client()
        client.post("/new")
        game = Game.objects.last()
        client.post(f"/game/{game.id}/add-player", {"spirit": spirit, "color": "random"})
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
        self.assertEqual(game.discard_pile.count(), draw - selected)
        return selected

    def assert_cards_gained(self, card_type, draw, should_gain, spirit='Waters'):
        self.assertEqual(self.cards_gained(spirit, card_type, draw), should_gain)

    def test_regular_minor(self):
        self.assert_cards_gained('minor', 4, 1)

    def test_boon_of_reimagining(self):
        self.assert_cards_gained('minor', 6, 2)

    def test_mentor_shifting_memory_boon_of_reimagining(self):
        self.assert_cards_gained('minor', 4, 3, spirit='Memory - Mentor')

    def test_regular_major(self):
        self.assert_cards_gained('major', 4, 1)

    def test_unlock_the_gates_major(self):
        self.assert_cards_gained('major', 2, 1)

    def test_covets_major(self):
        self.assert_cards_gained('major', 6, 1)

class TestHealing(TestCase):
    def setup_game(self, cards=()):
        client = Client()
        client.post('/new')
        game = Game.objects.last()
        player = game.gameplayer_set.create(spirit=Spirit.objects.get(name='Waters'), color='blue')
        for card_name in cards:
            card = Card.objects.get(name=card_name)
            client.get(f"/game/{player.id}/gain_healing")
            client.get(f"/game/{player.id}/choose/{card.id}")
        return (client, game, player)

    def test_gain(self):
        client, game, player = self.setup_game()
        client.get(f"/game/{player.id}/gain_healing")
        self.assertEqual([True, True, True, True], [card.is_healing() for card in player.selection.all()])

    def test_choose_1(self):
        client, game, player = self.setup_game(['Roiling Waters'])
        self.assertEqual(list(player.healing.values_list('name', flat=True)), ['Roiling Waters'])

    def test_choose_2(self):
        client, game, player = self.setup_game(['Roiling Waters', 'Waters Taste of Ruin'])
        self.assertEqual(list(player.healing.values_list('name', flat=True)), ['Roiling Waters', 'Waters Taste of Ruin'])

    def test_change_1(self):
        client, game, player = self.setup_game(['Roiling Waters', 'Serene Waters'])
        self.assertEqual(list(player.healing.values_list('name', flat=True)), ['Serene Waters'])

    def test_change_2(self):
        client, game, player = self.setup_game(['Serene Waters', 'Waters Taste of Ruin', 'Waters Renew'])
        self.assertEqual(list(player.healing.values_list('name', flat=True)), ['Serene Waters', 'Waters Renew'])

class TestDoubleGain(TestCase):
    def test_gain_and_gain(self):
        client = Client()
        client.post('/new')
        game = Game.objects.last()
        deck_size = game.minor_deck.count()
        player = game.gameplayer_set.create(spirit=Spirit.objects.get(name='River'), color='blue')

        # first gain normal
        client.get(f"/game/{player.id}/gain/minor/4")
        self.assertEqual(player.selection.count(), 4)
        self.assertEqual(game.minor_deck.count(), deck_size - 4)
        sel = list(player.selection.all())

        # second gain doesn't change it
        client.get(f"/game/{player.id}/gain/minor/4")
        self.assertEqual(game.minor_deck.count(), deck_size - 4)
        self.assertEqual(list(player.selection.all()), sel)

    def test_gain_and_heal(self):
        client = Client()
        client.post('/new')
        game = Game.objects.last()
        deck_size = game.minor_deck.count()
        player = game.gameplayer_set.create(spirit=Spirit.objects.get(name='Waters'), color='blue')

        client.get(f"/game/{player.id}/gain/minor/4")
        self.assertEqual(player.selection.count(), 4)
        self.assertEqual(game.minor_deck.count(), deck_size - 4)
        sel = list(player.selection.all())

        client.get(f"/game/{player.id}/gain_healing")
        self.assertEqual(list(player.selection.all()), sel)

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

class TestReclaim(TestCase):
    def test_reclaim_all(self):
        game = Game()
        game.save()
        player = GamePlayer(game=game, spirit=Spirit.objects.get(name='River'))
        player.save()
        player.hand.set([Card.objects.get(name="Boon of Vigor"), Card.objects.get(name="Flash Floods")])
        player.discard.set([Card.objects.get(name="River's Bounty"), Card.objects.get(name="Wash Away")])

        Client().post(f"/game/{player.id}/reclaim/all")

        self.assertEqual(4, player.hand.count())
        self.assertEqual(0, player.discard.count())

    def test_reclaim_fire(self):
        game = Game.objects.create()
        player = game.gameplayer_set.create(spirit=Spirit.objects.get(name='Behemoth'))
        player.hand.set([Card.objects.get(name="Blazing Intimidation")])
        player.discard.set([Card.objects.get(name="Terrifying Rampage"), Card.objects.get(name='Treacherous Waterways'), Card.objects.get(name="Delusions of Danger"), Card.objects.get(name='Disorienting Landscape')])

        Client().post(f"/game/{player.id}/reclaim/all/fire")

        self.assertEqual(['Blazing Intimidation', 'Terrifying Rampage', 'Treacherous Waterways'], list(player.hand.values_list('name', flat=True)))
        self.assertEqual(['Delusions of Danger', 'Disorienting Landscape'], list(player.discard.values_list('name', flat=True)))

class TestUndoGain(TestCase):
    def setup_game(self, card_names, spirit='River'):
        game = Game()
        game.save()
        player = GamePlayer(game=game, spirit=Spirit.objects.get(name=spirit))
        player.save()
        cards = [Card.objects.get(name=name) for name in card_names]
        player.selection.set(cards)

        return (game, player)

    def test_undo_minor(self):
        game, player = self.setup_game(['Call to Ferocity', 'Call to Isolation'])
        Client().post(f"/game/{player.id}/undo-gain-card")
        self.assertEqual(0, player.selection.count())
        self.assertEqual(2, game.minor_deck.count())
        self.assertEqual(0, game.major_deck.count())

    def test_undo_major(self):
        game, player = self.setup_game(['Accelerated Rot', 'Angry Bears'])
        Client().post(f"/game/{player.id}/undo-gain-card")
        self.assertEqual(0, player.selection.count())
        self.assertEqual(0, game.minor_deck.count())
        self.assertEqual(2, game.major_deck.count())

    def test_undo_healing(self):
        game, player = self.setup_game(['Roiling Waters', 'Serene Waters'], 'Waters')
        Client().post(f"/game/{player.id}/undo-gain-card")
        self.assertEqual(0, player.selection.count())
        self.assertEqual(0, game.minor_deck.count())
        self.assertEqual(0, game.major_deck.count())

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

    def test_elements_irrelevant_presence(self):
        expected_elements = Counter()

        # If we have no cards, we get back a counter with eight 0s, which isn't the same as an empty counter.
        player = self.setup_game(['Elemental Boon'])
        player.presence_set.create(left=0, top=0, opacity=0.0)
        self.assert_elements(player, expected_elements)

    def test_elements_covered_presence(self):
        expected_elements = Counter()

        player = self.setup_game(['Elemental Boon'])
        player.presence_set.create(left=0, top=0, opacity=1.0, elements='Water')
        self.assert_elements(player, expected_elements)

    def test_elements_presence(self):
        expected_elements = Counter()
        expected_elements[Elements.Water] = 1

        player = self.setup_game(['Elemental Boon'])
        player.presence_set.create(left=0, top=0, opacity=0.0, elements='Water')
        self.assert_elements(player, expected_elements)

    def test_elements_presence_two_different(self):
        expected_elements = Counter()
        expected_elements[Elements.Water] = 1
        expected_elements[Elements.Animal] = 1

        player = self.setup_game(['Elemental Boon'])
        player.presence_set.create(left=0, top=0, opacity=0.0, elements='Water,Animal')
        self.assert_elements(player, expected_elements)

    def test_elements_presence_two_same(self):
        expected_elements = Counter()
        expected_elements[Elements.Water] = 2

        player = self.setup_game(['Elemental Boon'])
        player.presence_set.create(left=0, top=0, opacity=0.0, elements='Water,Water')
        self.assert_elements(player, expected_elements)

    def test_elements_presence_ignore_rot(self):
        expected_elements = Counter()
        expected_elements[Elements.Water] = 1

        player = self.setup_game(['Elemental Boon'])
        player.presence_set.create(left=0, top=0, opacity=0.0, elements='Water,Rot')
        self.assert_elements(player, expected_elements)

class TestImpending(TestCase):
    def setup_players(self, n=1):
        client = Client()
        client.post("/new")
        game = Game.objects.last()
        for i in range(n):
            client.post(f"/game/{game.id}/add-player", {"spirit": "Earthquakes", "color": "random"})
            self.assertEqual(game.gameplayer_set.count(), i + 1, "didn't find correct number of players; spirit not created successfully?")
        return (client, *game.gameplayer_set.all())

    def assert_impending_energy(self, player, expected):
        self.assertEqual(list(player.gameplayerimpendingwithenergy_set.values_list('energy', flat=True)), expected)

    def assert_impending_in_play(self, player, expected):
        self.assertEqual(list(player.gameplayerimpendingwithenergy_set.values_list('in_play', flat=True)), expected)

    def test_this_turn_doesnt_gain_energy(self):
        client, player = self.setup_players()

        cards = player.hand.exclude(cost=0).values_list('id', flat=True)

        client.post(f"/game/{player.id}/impend/{cards[0]}")
        self.assert_impending_energy(player, [0])
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_energy(player, [0])

    def test_this_turn_doesnt_autoplay(self):
        client, player = self.setup_players()

        cards = player.hand.filter(cost=0).values_list('id', flat=True)

        client.post(f"/game/{player.id}/impend/{cards[0]}")
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_in_play(player, [False])

    def test_previous_turn_does_gain_energy(self):
        client, player = self.setup_players()

        cards = player.hand.exclude(cost=0).values_list('id', flat=True)

        client.post(f"/game/{player.id}/impend/{cards[0]}")
        self.assert_impending_energy(player, [0])
        client.post(f"/game/{player.id}/discard/all")
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_energy(player, [1])

    def test_previous_turn_1_does_autoplay(self):
        client, player = self.setup_players()

        cards = player.hand.filter(cost=1).values_list('id', flat=True)

        client.post(f"/game/{player.id}/impend/{cards[0]}")
        client.post(f"/game/{player.id}/discard/all")
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_energy(player, [1])
        self.assert_impending_in_play(player, [True])

    def test_discard_impending_from_play(self):
        client, player = self.setup_players()

        cards = player.hand.filter(cost=1).values_list('id', flat=True)

        client.post(f"/game/{player.id}/impend/{cards[0]}")
        client.post(f"/game/{player.id}/discard/all")
        self.assertEqual(player.discard.count(), 0)
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        client.post(f"/game/{player.id}/discard/all")
        self.assertEqual(player.impending_with_energy.count(), 0)
        self.assertEqual(player.discard.count(), 1)

    def test_previous_turn_2_doesnt_autoplay(self):
        client, player = self.setup_players()

        cards = player.hand.filter(cost=2).values_list('id', flat=True)

        client.post(f"/game/{player.id}/impend/{cards[0]}")
        client.post(f"/game/{player.id}/discard/all")
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_energy(player, [1])
        self.assert_impending_in_play(player, [False])

    def test_two_of_each(self):
        client, player = self.setup_players()

        cards = list(player.hand.exclude(cost=0).values_list('id', flat=True))

        client.post(f"/game/{player.id}/impend/{cards[0]}")
        client.post(f"/game/{player.id}/impend/{cards[1]}")
        self.assert_impending_energy(player, [0, 0])
        client.post(f"/game/{player.id}/discard/all")
        client.post(f"/game/{player.id}/impend/{cards[2]}")
        client.post(f"/game/{player.id}/impend/{cards[3]}")
        self.assert_impending_energy(player, [0, 0, 0, 0])
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_energy(player, [1, 1, 0, 0])

    def test_energy_gain_different_players(self):
        client, player1, player2 = self.setup_players(2)

        cards = player1.hand.exclude(cost=0).values_list('id', flat=True)

        client.post(f"/game/{player1.id}/impend/{cards[0]}")
        self.assert_impending_energy(player1, [0])
        client.post(f"/game/{player2.id}/impend/{cards[0]}")
        self.assert_impending_energy(player2, [0])
        client.post(f"/game/{player1.id}/discard/all")
        client.post(f"/game/{player2.id}/discard/all")
        client.post(f"/game/{player1.id}/gain_energy_on_impending")
        self.assert_impending_energy(player1, [1])
        self.assert_impending_energy(player2, [0])
        client.post(f"/game/{player2.id}/gain_energy_on_impending")
        self.assert_impending_energy(player2, [1])
        self.assert_impending_energy(player1, [1])

    def test_gain_multiple_turns(self):
        client, player = self.setup_players()

        cards = player.hand.filter(cost__gte=2).values_list('id', flat=True)

        client.post(f"/game/{player.id}/impend/{cards[0]}")
        self.assert_impending_energy(player, [0])
        client.post(f"/game/{player.id}/discard/all")
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_energy(player, [1])
        client.post(f"/game/{player.id}/discard/all")
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_energy(player, [2])

    def test_plus_two_energy(self):
        client, player = self.setup_players()

        cards = player.hand.filter(cost__gte=2).values_list('id', flat=True)

        player.presence_set.filter(energy="Impend2").update(opacity=0.0)

        client.post(f"/game/{player.id}/impend/{cards[0]}")
        self.assert_impending_energy(player, [0])
        client.post(f"/game/{player.id}/discard/all")
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_energy(player, [2])

    def test_plus_two_capped_at_cost(self):
        client, player = self.setup_players()

        cards = player.hand.filter(cost=3).values_list('id', flat=True)

        player.presence_set.filter(energy="Impend2").update(opacity=0.0)

        client.post(f"/game/{player.id}/impend/{cards[0]}")
        self.assert_impending_energy(player, [0])
        client.post(f"/game/{player.id}/discard/all")
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        client.post(f"/game/{player.id}/discard/all")
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_energy(player, [3])

    def test_plus_two_capped_at_cost_blitz_fast(self):
        client, player = self.setup_players()
        player.game.scenario = 'Blitz'
        player.game.save()

        cards = player.hand.filter(cost=3, speed=Card.FAST).values_list('id', flat=True)

        client.post(f"/game/{player.id}/impend/{cards[0]}")
        self.assert_impending_energy(player, [0])
        client.post(f"/game/{player.id}/discard/all")
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_energy(player, [1])
        player.presence_set.filter(energy="Impend2").update(opacity=0.0)
        client.post(f"/game/{player.id}/discard/all")
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_energy(player, [2])

    def test_plus_two_capped_at_cost_blitz_slow(self):
        client, player = self.setup_players()
        player.game.scenario = 'Blitz'
        player.game.save()

        cards = player.hand.filter(cost=2, speed=Card.SLOW).values_list('id', flat=True)

        client.post(f"/game/{player.id}/impend/{cards[0]}")
        self.assert_impending_energy(player, [0])
        client.post(f"/game/{player.id}/discard/all")
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_energy(player, [1])
        player.presence_set.filter(energy="Impend2").update(opacity=0.0)
        client.post(f"/game/{player.id}/discard/all")
        client.post(f"/game/{player.id}/gain_energy_on_impending")
        self.assert_impending_energy(player, [2])

class TestUpload(TestCase):
    def png_chunk(type, data):
        import binascii
        import struct

        chunk = type.encode() + bytes(data)
        return struct.pack('>I', len(data)) + chunk + struct.pack('>I', binascii.crc32(chunk))

    # https://evanhahn.com/worlds-smallest-png/
    PNG = b"".join([
        bytes([0x89]), 'PNG'.encode(), bytes([0x0d, 0x0a, 0x1a, 0x0a]), # signature
        png_chunk('IHDR', [
            0, 0, 0, 1, # width 1
            0, 0, 0, 1, # height 1
            1, 0, 0, 0, 0 # bit depth, colour type, compression method, filter method, interlace method
        ]),
        png_chunk('IDAT', [
            0, 0,
            0x78, 0x01, # zlib header
            0x63, 0x60, 0x00, 0x00, # DEFLATE block
            0x00, 0x02, 0x00, 0x01, # zlib checksum
        ]),
        png_chunk('IEND', []),
    ])

    def remove_if_exists(self, path):
        if os.path.exists(path):
            os.remove(path)

    def upload(self, client, game, data):
        client.post(f"/game/{game.id}/screenshot", {k: SimpleUploadedFile(fn, self.PNG) for k, fn in data.items()})
        game.refresh_from_db()
        ss1 = game.screenshot
        ss2 = game.screenshot2
        self.addCleanup(self.remove_if_exists, ss1.path)
        self.addCleanup(self.remove_if_exists, ss2.path)
        return (ss1, ss2)

    def test_replace_first(self):
        client = Client()
        client.post("/new")
        game = Game.objects.last()
        self.addCleanup(os.rmdir, os.path.join('screenshot', str(game.id)))

        ss1_before, ss2_before = self.upload(client, game, {'screenshot': 'test1.png', 'screenshot2': 'test2.png'})
        self.assertIn('test1.png', ss1_before.path)
        self.assertIn('test2.png', ss2_before.path)

        ss1_after, ss2_after = self.upload(client, game, {'screenshot': 'test-replace.png'})
        self.assertIn('test-replace.png', ss1_after.path)
        self.assertIn('test2.png', ss2_after.path)

    def test_replace_second(self):
        client = Client()
        client.post("/new")
        game = Game.objects.last()
        self.addCleanup(os.rmdir, os.path.join('screenshot', str(game.id)))

        ss1_before, ss2_before = self.upload(client, game, {'screenshot': 'test1.png', 'screenshot2': 'test2.png'})
        self.assertIn('test1.png', ss1_before.path)
        self.assertIn('test2.png', ss2_before.path)

        ss1_after, ss2_after = self.upload(client, game, {'screenshot2': 'test-replace.png'})
        self.assertIn('test1.png', ss1_after.path)
        self.assertIn('test-replace.png', ss2_after.path)

    def test_replace_both(self):
        client = Client()
        client.post("/new")
        game = Game.objects.last()
        self.addCleanup(os.rmdir, os.path.join('screenshot', str(game.id)))

        ss1_before, ss2_before = self.upload(client, game, {'screenshot': 'test1.png', 'screenshot2': 'test2.png'})
        self.assertIn('test1.png', ss1_before.path)
        self.assertIn('test2.png', ss2_before.path)

        ss1_after, ss2_after = self.upload(client, game, {'screenshot': 'test-replace1.png', 'screenshot2': 'test-replace2.png'})
        self.assertIn('test-replace1.png', ss1_after.path)
        self.assertIn('test-replace2.png', ss2_after.path)

    def test_reuse_filename(self):
        client = Client()
        client.post("/new")
        game = Game.objects.last()
        self.addCleanup(os.rmdir, os.path.join('screenshot', str(game.id)))

        ss1, _ = self.upload(client, game, {'screenshot': 'test-same-fn.png', 'screenshot2': 'dummy.png'})
        self.assertIn('test-same-fn.png', ss1.path)

        ss2, _ = self.upload(client, game, {'screenshot': 'test-same-fn.png'})
        # image cleanup doesn't seem to happen in tests, so we'll have to do it.
        # we immediately remove this one to simulate the behaviour.
        os.remove(ss1.path)
        self.assertNotEqual(ss1.path, ss2.path)

        ss3, _ = self.upload(client, game, {'screenshot': 'test-same-fn.png'})
        # if the paths are the same, browser caches mean players may see an outdated image.
        self.assertNotEqual(ss1.path, ss3.path)

class TestImport(TestCase):
    NUM_MINORS = Card.objects.filter(type=Card.MINOR).count()

    def import_game(self, str):
        import io
        num_games = Game.objects.count()
        client = Client()
        resp = client.post("/import", {"json": io.StringIO(str)})
        self.assertEqual(num_games + 1, Game.objects.count())
        self.assertEqual(resp.status_code, 302)
        return Game.objects.get(id=resp.url.split('/')[-1])

    def test_import_nothing(self):
        num_games = Game.objects.count()
        self.import_game('{}')
        # no additional asserts; import_game has already asserted that a game was created

    def test_import_name(self):
        game = self.import_game('{"name": "game imported in TEST"}')
        self.assertEqual(game.name, 'game imported in TEST')

    def test_import_scenario(self):
        game = self.import_game('{"scenario": "Blitz"}')
        self.assertEqual(game.scenario, 'Blitz')

    def test_import_spirit_dict(self):
        game = self.import_game('{"players": [{"spirit": {"name": "River"}}]}')
        player = game.gameplayer_set.first()
        self.assertEqual(player.spirit.name, 'River')

    def test_import_spirit_str(self):
        game = self.import_game('{"players": [{"spirit": "River"}]}')
        player = game.gameplayer_set.first()
        self.assertEqual(player.spirit.name, 'River')

    def test_import_aspect(self):
        game = self.import_game('{"players": [{"spirit": "River", "aspect": "Travel"}]}')
        player = game.gameplayer_set.first()
        self.assertEqual(player.aspect, "Travel")

    def test_locus_presence_removed_on_import(self):
        game = self.import_game('{"players": [{"spirit": "Serpent"}]}')
        player = game.gameplayer_set.first()
        self.assertEqual(sum(player.presence_set.values_list('opacity', flat=True)), 12)

        game = self.import_game('{"players": [{"spirit": "Serpent", "aspect": "Locus"}]}')
        player = game.gameplayer_set.first()
        self.assertEqual(sum(player.presence_set.values_list('opacity', flat=True)), 11)

    def test_import_card_dict(self):
        game = self.import_game('{"minor_deck": [{"name": "Call to Isolation"}]}')
        minor = Card.objects.get(name="Call to Isolation")
        self.assertEqual(game.minor_deck.count(), 1)
        self.assertIn(minor, game.minor_deck.all())

    def test_import_card_str(self):
        game = self.import_game('{"minor_deck": ["Call to Isolation"]}')
        minor = Card.objects.get(name="Call to Isolation")
        self.assertEqual(game.minor_deck.count(), 1)
        self.assertIn(minor, game.minor_deck.all())

    def test_shared_discard_removed_from_default_minors(self):
        game = self.import_game('{"discard_pile": ["Call to Isolation"]}')
        minor = Card.objects.get(name="Call to Isolation")
        self.assertEqual(game.discard_pile.count(), 1)
        self.assertIn(minor, game.discard_pile.all())
        self.assertEqual(game.minor_deck.count(), self.NUM_MINORS - 1)
        self.assertEqual(list(game.minor_deck.filter(id=minor.id)), [])

    def test_case_insensitive_card_name(self):
        game = self.import_game('{"minor_deck": ["Call to Isolation", "call to bloodshed"]}')
        minor1 = Card.objects.get(name="Call to Isolation")
        minor2 = Card.objects.get(name="Call to Bloodshed")
        self.assertEqual(game.minor_deck.count(), 2)
        self.assertIn(minor1, game.minor_deck.all())
        self.assertIn(minor2, game.minor_deck.all())

    def test_players_discard_removed_from_default_minors(self):
        game = self.import_game('{"players": [{"spirit": "River", "discard": ["Call to Isolation"]}]}')
        minor = Card.objects.get(name="Call to Isolation")
        self.assertEqual(game.minor_deck.count(), self.NUM_MINORS - 1)
        self.assertEqual(list(game.minor_deck.filter(id=minor.id)), [])
        player = game.gameplayer_set.first()
        self.assertEqual(player.discard.count(), 1)
        self.assertIn(minor, player.discard.all())

    def test_aspect_minor(self):
        game = self.import_game('{"players": [{"spirit": "Serpent", "aspect": "Locus"}]}')
        minor = Card.objects.get(name="Pull Beneath the Hungry Earth")
        player = game.gameplayer_set.first()
        self.assertIn(minor, player.hand.all())
        self.assertEqual(game.minor_deck.count(), self.NUM_MINORS - 1)
        self.assertEqual(list(game.minor_deck.filter(id=minor.id)), [])

    def test_import_impending_name_dict(self):
        game = self.import_game('{"players": [{"spirit": "Earthquakes", "impending": [{"card": {"name": "Call to Isolation"}}]}]}')
        minor = Card.objects.get(name="Call to Isolation")
        player = game.gameplayer_set.first()
        self.assertEqual(player.impending_with_energy.count(), 1)
        self.assertIn(minor, player.impending_with_energy.all())

    def test_import_impending_name_str(self):
        game = self.import_game('{"players": [{"spirit": "Earthquakes", "impending": [{"card": "Call to Isolation"}]}]}')
        minor = Card.objects.get(name="Call to Isolation")
        player = game.gameplayer_set.first()
        self.assertEqual(player.impending_with_energy.count(), 1)
        self.assertIn(minor, player.impending_with_energy.all())

    def test_import_impending_energy(self):
        game = self.import_game('{"players": [{"spirit": "Earthquakes", "impending": [{"card": "Call to Bloodshed", "energy": 1}]}]}')
        minor = Card.objects.get(name="Call to Bloodshed")
        player = game.gameplayer_set.first()
        self.assertEqual(list(player.gameplayerimpendingwithenergy_set.values_list('energy', flat=True)), [1])

    def test_impending_removed_from_default_minors(self):
        game = self.import_game('{"players": [{"spirit": "Earthquakes", "impending": [{"card": "Call to Isolation"}]}]}')
        minor = Card.objects.get(name="Call to Isolation")
        # Other tests have already tested that the card is in the player's impending
        self.assertEqual(game.minor_deck.count(), self.NUM_MINORS - 1)
        self.assertEqual(list(game.minor_deck.filter(id=minor.id)), [])

class TestLog(TestCase):
    from .views import add_log_msg
    add_log_msg = staticmethod(add_log_msg)

    def test_just_message(self):
        game = Game.objects.create()
        self.add_log_msg(game, text='hello world')
        self.assertEqual(game.gamelog_set.last().text, 'hello world')

    def test_player(self):
        game = Game.objects.create()
        player = game.gameplayer_set.create(spirit=Spirit.objects.get(name='Keeper'), color='green')
        self.add_log_msg(game, player=player, text='drives the invaders from its forbidden grounds')
        self.assertEqual('💚 Keeper drives the invaders from its forbidden grounds', game.gamelog_set.last().text)

    def test_image(self):
        game = Game.objects.create()
        self.add_log_msg(game, text='hello world', images='asdf.jpg')
        self.assertEqual(game.gamelog_set.last().text, 'hello world')
        self.assertEqual(game.gamelog_set.last().images, 'asdf.jpg')

    def test_cards(self):
        game = Game.objects.create()
        self.add_log_msg(game, text='look, cards', cards=[Card.objects.get(name="Gift of Living Energy"), Card.objects.get(name="Gift of Power")])
        self.assertEqual(game.gamelog_set.last().text, 'look, cards: Gift of Living Energy, Gift of Power')
        self.assertEqual(game.gamelog_set.last().spoiler_text, '')
        self.assertEqual(game.gamelog_set.last().images, './pbf/static/pbf/gift_of_living_energy.jpg,./pbf/static/pbf/gift_of_power.jpg')

    def test_cards_spoiler(self):
        game = Game.objects.create()
        self.add_log_msg(game, text='look, cards', cards=[Card.objects.get(name="Gift of Living Energy"), Card.objects.get(name="Gift of Power")], spoiler=True)
        self.assertEqual(game.gamelog_set.last().text, 'look, cards:')
        self.assertEqual(game.gamelog_set.last().spoiler_text, 'Gift of Living Energy, Gift of Power')
        self.assertEqual(game.gamelog_set.last().images, './pbf/static/pbf/gift_of_living_energy.jpg,./pbf/static/pbf/gift_of_power.jpg')

    def test_gain_power(self):
        client = Client()
        client.post('/new')
        game = Game.objects.last()
        player = game.gameplayer_set.create(spirit=Spirit.objects.get(name='River'), color='red')
        client.get(f"/game/{player.id}/gain/minor/4")
        self.assertIn('River gains a minor power. Choices: ', game.gamelog_set.last().text)
        self.assertIn(player.selection.first().name, game.gamelog_set.last().text)
        self.assertIn(player.selection.first().url(), game.gamelog_set.last().images)
        self.assertEqual('', game.gamelog_set.last().spoiler_text)

    def test_gain_power_spoiler(self):
        client = Client()
        client.post('/new')
        game = Game.objects.last()
        player = game.gameplayer_set.create(spirit=Spirit.objects.get(name='River'), color='red')
        client.get(f"/game/{player.id}/gain/minor/4?spoiler_power_gain=true")
        self.assertIn('River gains a minor power. Choices:', game.gamelog_set.last().text)
        self.assertNotIn(player.selection.first().name, game.gamelog_set.last().text)
        self.assertIn(player.selection.first().url(), game.gamelog_set.last().images)
        self.assertIn(player.selection.first().name, game.gamelog_set.last().spoiler_text)
