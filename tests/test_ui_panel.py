"""Tests for ui_panel module."""

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

	def test_hit_test_button_all_buttons_reachable(self):
		"""Test that all defined buttons are reachable at their center."""
		game = MockGame()
		panel = ui_panel.UIPanel(game)
		for action, shape in panel.buttons.items():
			cx, cy = shape['c']
			result = panel.hit_test_button(cx, cy)
			assert result == action, f"Button {action} at ({cx}, {cy}) not hit"
