"""Pin behavior of the ASM map_blk_code / map_bk2_code helpers."""

import populous_game.pathfinding as pathfinding
import populous_game.settings as settings
import populous_game.terrain as terrain


def _make_map(width=4, height=4):
	"""Build a GameMap test double without invoking pygame loaders."""
	game_map = terrain.GameMap.__new__(terrain.GameMap)
	game_map.grid_width = width
	game_map.grid_height = height
	game_map.corners = [
		[0 for _ in range(width + 1)]
		for _ in range(height + 1)
	]
	game_map.houses = []
	game_map.tile_surfaces = {}
	game_map.map_who = game_map._new_map_who_table()
	game_map.shadow_blk = game_map._new_shadow_table()
	game_map.shadow_bk2 = game_map._new_shadow_table()
	game_map.recompute_shadow_codes()
	game_map.water_timer = 0.0
	game_map.water_frame = 0
	game_map.flag_frame = 0
	return game_map


def test_water_tile_yields_water_code():
	game_map = _make_map()
	assert pathfinding.map_blk_code(game_map, 0, 0) == settings.ASM_TILE_WATER
	assert pathfinding.map_bk2_code(game_map, 0, 0) == settings.ASM_TILE_WATER


def test_out_of_bounds_returns_oob_code():
	game_map = _make_map(width=3, height=3)
	assert pathfinding.map_blk_code(game_map, -1, 0) == settings.ASM_TILE_OUT_OF_BOUNDS
	assert pathfinding.map_blk_code(game_map, 0, 99) == settings.ASM_TILE_OUT_OF_BOUNDS
	assert pathfinding.map_bk2_code(game_map, 99, 99) == settings.ASM_TILE_OUT_OF_BOUNDS


def test_rock_tile_yields_rock_code():
	"""A peak corner classifies its tiles as rock via the shadow."""
	game_map = _make_map()
	game_map.set_all_altitude(settings.ALTITUDE_MAX)
	assert pathfinding.map_blk_code(game_map, 1, 1) == settings.ASM_TILE_ROCK


def test_helper_is_referentially_transparent():
	"""Same shadow state -> same return for repeated calls."""
	game_map = _make_map()
	game_map.set_corner_altitude(2, 2, 1)
	first = pathfinding.map_blk_code(game_map, 1, 1)
	second = pathfinding.map_blk_code(game_map, 1, 1)
	assert first == second
