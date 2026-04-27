"""Tests for scenario loader (M8)."""

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pytest
import populous_game.scenario as scenario_module


def test_load_scenario_01_plateau():
	"""The bundled scenario 1 loads and has the documented fields."""
	s = scenario_module.load_scenario_by_name('scenario_01_plateau')
	assert s.name == 'Plateau'
	assert s.seed == 12345
	assert s.altitude == 3
	assert s.player_peeps == 10
	assert s.enemy_peeps == 5


def test_unsupported_format_version_raises(tmp_path):
	"""Loading a scenario with an unknown format_version raises ValueError."""
	bad_path = tmp_path / 'bad.yaml'
	bad_path.write_text('format_version: 99\nname: x\nseed: 1\naltitude: 1\n')
	with pytest.raises(ValueError):
		scenario_module.load_scenario_file(str(bad_path))


def test_apply_scenario_to_game():
	"""apply_to_game raises terrain and spawns peeps from the scenario."""
	from populous_game.game import Game
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	s = scenario_module.load_scenario_by_name('scenario_01_plateau')
	scenario_module.apply_to_game(s, game)
	# Terrain set to scenario altitude
	assert game.game_map.corners[0][0] == s.altitude
	# Peeps spawned for both factions
	assert len(game.peeps) == s.player_peeps + s.enemy_peeps
