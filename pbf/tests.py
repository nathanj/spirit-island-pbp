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
        self.assert_cards_gained('minor', 4, 3, spirit='Shifting - Mentor')

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
