"""Simulation-boundary test (M5 Wave 3, Patch 4).

This is the cross-milestone gate that asserts UI changes do not change
simulation outcomes. All later patches (M6-M8) must keep this test green.
"""

import random
import populous_game.game as game_module
import populous_game.settings as settings


def snapshot_game(game):
	"""Capture a deterministic snapshot of simulation state.

	Does not include UI-only state like selection, mode flags, or scroll position.
	Returns a hashable tuple summarizing the simulation.
	"""
	peep_data = []
	for p in sorted(game.peeps, key=lambda x: (x.x, x.y)):
		peep_data.append((
			round(p.x, 2), round(p.y, 2),
			p.faction_id, round(p.life, 1),
			p.state
		))
	house_data = []
	for h in sorted(game.game_map.houses, key=lambda x: (x.r, x.c)):
		house_data.append((
			h.r, h.c,
			h.faction_id, round(h.life, 1),
			h.destroyed
		))
	return (tuple(peep_data), tuple(house_data))


class TestUIBoundary:
	"""UI changes must not perturb the simulation."""

	def test_colorblind_palette_does_not_affect_simulation(self):
		"""Toggling colorblind palette does not change simulation outcomes."""
		# Run A: with colorblind palette
		random.seed(42)
		settings.USE_COLORBLIND_PALETTE = True
		game_a = game_module.Game()
		game_a.app_state.transition_to(game_a.app_state.PLAYING)
		game_a.game_map.set_all_altitude(3)
		game_a.spawn_initial_peeps(5)
		game_a.spawn_enemy_peeps(5)
		for _ in range(100):
			game_a.update(0.1)
		snapshot_a = snapshot_game(game_a)

		# Run B: without colorblind palette
		random.seed(42)
		settings.USE_COLORBLIND_PALETTE = False
		game_b = game_module.Game()
		game_b.app_state.transition_to(game_b.app_state.PLAYING)
		game_b.game_map.set_all_altitude(3)
		game_b.spawn_initial_peeps(5)
		game_b.spawn_enemy_peeps(5)
		for _ in range(100):
			game_b.update(0.1)
		snapshot_b = snapshot_game(game_b)

		# Reset to default
		settings.USE_COLORBLIND_PALETTE = True

		# Snapshots must match
		assert snapshot_a == snapshot_b

	def test_selection_does_not_affect_simulation(self):
		"""Selecting/deselecting entities does not change simulation."""
		# Run A: with no selection
		random.seed(99)
		game_a = game_module.Game()
		game_a.app_state.transition_to(game_a.app_state.PLAYING)
		game_a.game_map.set_all_altitude(3)
		game_a.spawn_initial_peeps(5)
		game_a.spawn_enemy_peeps(5)
		for _ in range(100):
			game_a.update(0.1)
		snapshot_a = snapshot_game(game_a)

		# Run B: with selection set at tick 50, cleared at tick 100
		random.seed(99)
		game_b = game_module.Game()
		game_b.app_state.transition_to(game_b.app_state.PLAYING)
		game_b.game_map.set_all_altitude(3)
		game_b.spawn_initial_peeps(5)
		game_b.spawn_enemy_peeps(5)
		for i in range(100):
			if i == 50 and game_b.peeps:
				game_b.selection.who = game_b.peeps[0]
				game_b.selection.kind = 'peep'
			if i == 100 and game_b.selection.who:
				game_b.selection.who = None
				game_b.selection.kind = None
			game_b.update(0.1)
		snapshot_b = snapshot_game(game_b)

		# Snapshots must match
		assert snapshot_a == snapshot_b

	def test_mode_toggle_does_not_affect_simulation(self):
		"""Toggling papal/shield mode does not change simulation."""
		# Run A: modes stay IDLE
		random.seed(77)
		game_a = game_module.Game()
		game_a.app_state.transition_to(game_a.app_state.PLAYING)
		game_a.game_map.set_all_altitude(3)
		game_a.spawn_initial_peeps(5)
		game_a.spawn_enemy_peeps(5)
		game_a.mode_manager.papal_mode = False
		game_a.mode_manager.shield_mode = False
		for _ in range(100):
			game_a.update(0.1)
		snapshot_a = snapshot_game(game_a)

		# Run B: papal mode toggled on at tick 30 (without action)
		random.seed(77)
		game_b = game_module.Game()
		game_b.app_state.transition_to(game_b.app_state.PLAYING)
		game_b.game_map.set_all_altitude(3)
		game_b.spawn_initial_peeps(5)
		game_b.spawn_enemy_peeps(5)
		for i in range(100):
			if i == 30:
				game_b.mode_manager.papal_mode = True
			if i == 60:
				game_b.mode_manager.papal_mode = False
			game_b.update(0.1)
		snapshot_b = snapshot_game(game_b)

		# Snapshots must match
		assert snapshot_a == snapshot_b

	def test_determinism_across_multiple_runs(self):
		"""Multiple runs with same seed produce identical simulations."""
		random.seed(123)
		game_1 = game_module.Game()
		game_1.app_state.transition_to(game_1.app_state.PLAYING)
		game_1.game_map.set_all_altitude(3)
		game_1.spawn_initial_peeps(3)
		game_1.spawn_enemy_peeps(3)
		for _ in range(50):
			game_1.update(0.1)
		snapshot_1 = snapshot_game(game_1)

		random.seed(123)
		game_2 = game_module.Game()
		game_2.app_state.transition_to(game_2.app_state.PLAYING)
		game_2.game_map.set_all_altitude(3)
		game_2.spawn_initial_peeps(3)
		game_2.spawn_enemy_peeps(3)
		for _ in range(50):
			game_2.update(0.1)
		snapshot_2 = snapshot_game(game_2)

		# Both runs should be identical
		assert snapshot_1 == snapshot_2
