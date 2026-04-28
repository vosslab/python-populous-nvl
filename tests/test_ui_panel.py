"""Tests for ui_panel module."""

import pygame

import populous_game.ui_panel as ui_panel


class MockGame:
	"""Mock Game object for testing UIPanel."""
	pass


class TestUIPanel:
	"""Test UIPanel class."""

	def test_ui_panel_init(self):
		"""Test UIPanel initialization."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)
		assert panel.game is game
		assert panel.buttons is not None
		assert '_raise_terrain' in panel.buttons
		assert '_do_shield' in panel.buttons

	def test_hit_test_button_center(self):
		"""Test hit_test_button at the center of a real button.

		_find_shield was removed in M2 (no shield-bearer concept in
		code; see docs/active_plans/m2_button_gaps.md). The base center
		coordinate is now unoccupied. Use a known-present button center.
		"""
		game = MockGame()
		panel = ui_panel.UIPanel(game)
		cx, cy = panel.buttons['_raise_terrain']['c']
		action = panel.hit_test_button(cx, cy)
		assert action == '_raise_terrain'

	def test_hit_test_button_inside_diamond(self):
		"""Test hit_test_button inside diamond bounding box."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)
		cx, cy = panel.buttons['_raise_terrain']['c']
		# Center is reachable.
		assert panel.hit_test_button(cx, cy) == '_raise_terrain'
		# A point a few pixels along the x axis stays inside the diamond.
		assert panel.hit_test_button(cx + 4, cy) == '_raise_terrain'

	def test_hit_test_button_outside_all(self):
		"""Test hit_test_button outside all buttons returns None."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)
		# Pick a point far from all buttons
		action = panel.hit_test_button(0, 0)
		assert action is None

	def test_hit_test_button_edge_outside(self):
		"""Test hit_test_button far from any button center returns None."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)
		# Pick a viewport interior point well clear of every button.
		action = panel.hit_test_button(160, 100)
		assert action is None

	def test_button_names_exist(self):
		"""Test that expected button action names exist."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)
		expected_buttons = [
			'_raise_terrain', '_do_shield', '_do_papal',
			'N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW'
		]
		for btn in expected_buttons:
			assert btn in panel.buttons, f"Button {btn} not found in ui_panel.buttons"

	def test_get_weapon_name_house(self):
		"""Test _get_weapon_name for house."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)

		class MockHouse:
			building_type = 'hut'

		house = MockHouse()
		name = panel._get_weapon_name(house, 'house')
		assert name == 'A'

		house.building_type = 'castle'
		name = panel._get_weapon_name(house, 'house')
		assert name == 'J'

	def test_get_weapon_name_peep_life_based(self):
		"""Test _get_weapon_name for peep based on life."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)

		class MockPeep:
			life = 10

		peep = MockPeep()
		name = panel._get_weapon_name(peep, 'peep')
		assert name == 'Mains nues'

		peep.life = 30
		name = panel._get_weapon_name(peep, 'peep')
		assert name == 'Baton'

		peep.life = 50
		name = panel._get_weapon_name(peep, 'peep')
		assert name == 'Epee courte'

		peep.life = 150
		name = panel._get_weapon_name(peep, 'peep')
		assert name == 'Arc'

	def test_get_weapon_name_knight_override(self):
		"""Test that knight promotion overrides life-based weapon text."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)

		class MockPeep:
			life = 10
			weapon_type = 'knight'

		peep = MockPeep()
		name = panel._get_weapon_name(peep, 'peep')
		assert name == 'Knight'

	def test_draw_peep_bars_draws_two_asm_style_bars(self, monkeypatch):
		"""Test that the shield-panel peep bars still draw."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)

		class MockPeep:
			life = 0x1234

		class MockSelection:
			kind = 'peep'
			who = MockPeep()

		draw_calls = []

		def fake_rect(surface, color, rect, width=0):
			draw_calls.append((color, rect, width))

		monkeypatch.setattr(pygame.draw, 'rect', fake_rect)
		panel._draw_peep_bars(pygame.Surface((32, 32)), MockSelection(), (20, 20))

		assert any(color == (102, 102, 102) and rect[0] == 23 for color, rect, _ in draw_calls)
		assert any(color == (102, 102, 102) and rect[0] == 31 for color, rect, _ in draw_calls)
		assert any(color == (255, 220, 0) and rect[0] == 23 for color, rect, _ in draw_calls)
		assert any(color == (255, 140, 0) and rect[0] == 31 for color, rect, _ in draw_calls)

	def test_compute_peep_bar_model_general_branch(self):
		"""General branch should follow the ASM life scaling split."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)

		class MockPeep:
			life = 0x1234
			state = 'wander'

		class MockSelection:
			kind = 'peep'
			who = MockPeep()

		model = panel._compute_peep_bar_model(MockSelection())
		assert model['branch'] == 'general'
		assert [bar['value'] for bar in model['bars']] == [4, 16]

	def test_compute_peep_bar_model_combat_branch(self):
		"""Combat branch should split 16 bars across peep and opponent."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)

		class Opponent:
			life = 10

		class MockPeep:
			life = 30
			state = 'fight'
			shield_opponent = Opponent()

		class MockSelection:
			kind = 'peep'
			who = MockPeep()

		model = panel._compute_peep_bar_model(MockSelection())
		assert model['branch'] == 'combat'
		assert [bar['value'] for bar in model['bars']] == [12, 4]

	def test_compute_peep_bar_model_type1_branch(self):
		"""Type-1 branch should use check_life and the peep life value."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)

		class MockPeep:
			life = 100
			state = 'wander'
			check_life_value = 0x0bea

		class MockSelection:
			kind = 'peep'
			who = MockPeep()

		model = panel._compute_peep_bar_model(MockSelection())
		assert model['branch'] == 'type1'
		assert model['bars'][0]['value'] == 16
		assert model['bars'][1]['value'] == 0

	def test_draw_shield_panel_labels_knight(self):
		"""A knight peep should be labeled explicitly in the shield panel."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)

		class MockPeep:
			life = 10
			weapon_type = 'knight'

		name = panel._get_weapon_name(MockPeep(), 'peep')
		assert name == 'Knight'

	def test_hit_test_button_all_buttons_reachable(self):
		"""Test that all defined buttons are reachable at their center."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)
		for action, shape in panel.buttons.items():
			cx, cy = shape['c']
			result = panel.hit_test_button(cx, cy)
			assert result == action, f"Button {action} at ({cx}, {cy}) not hit"
