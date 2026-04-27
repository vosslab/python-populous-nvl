"""Tests for JSON save/load round-trip (M8)."""

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import json
import pytest
import populous_game.save_state as save_state


def _snapshot(game) -> tuple:
	"""Pure-data summary of simulation state used to verify equality."""
	corners = tuple(tuple(row) for row in game.game_map.corners)
	houses = tuple((h.r, h.c, h.faction_id, round(h.life, 1), h.destroyed)
		for h in game.game_map.houses)
	peeps = tuple((round(p.x, 2), round(p.y, 2), p.faction_id, round(p.life, 1), p.state)
		for p in game.peeps)
	return (corners, houses, peeps)


def test_save_then_load_restores_state(tmp_path):
	"""Save a game, mutate it, reload from disk; snapshot must match the save."""
	from populous_game.game import Game
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(3)
	game.spawn_initial_peeps(5)
	game.spawn_enemy_peeps(3)

	pre = _snapshot(game)
	save_path = tmp_path / 'save.json'
	save_state.save_to_file(game, str(save_path))

	# Mutate the live game
	game.game_map.set_all_altitude(0)
	game.peeps.clear()

	# Reload
	save_state.load_from_file(game, str(save_path))
	post = _snapshot(game)
	assert pre == post


def test_save_format_has_schema_version(tmp_path):
	"""Save file includes a schema_version field readable as JSON."""
	from populous_game.game import Game
	game = Game()
	save_path = tmp_path / 'save.json'
	save_state.save_to_file(game, str(save_path))
	with open(save_path) as fh:
		data = json.load(fh)
	assert 'schema_version' in data
	assert int(data['schema_version']) == save_state.SCHEMA_VERSION


def test_load_unsupported_schema_raises():
	"""Loading a save with an unknown schema_version raises ValueError."""
	from populous_game.game import Game
	game = Game()
	with pytest.raises(ValueError):
		save_state.load_from_dict(game, {
			'schema_version': 999,
			'app_state': 'menu',
			'heightmap': [],
			'houses': [],
			'peeps': [],
			'mode_flags': {'papal_mode': False, 'shield_mode': False},
		})
