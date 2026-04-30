"""Pin behavior of the ASM shadow tile-code layer on GameMap.

The shadow_blk / shadow_bk2 arrays are additive bookkeeping that
must stay in sync with corner altitude mutations and house
placement. Production movement does not consume them yet, but the
invariants they guarantee unblock later parity work.
"""

import populous_game.settings as settings
import populous_game.terrain as terrain


def _make_map(width=4, height=4):
	"""GameMap construction for tests; load_tile_surfaces() is fine
	at import time because pygame imports are guarded inside the
	module under repo CI conventions.
	"""
	# Avoid touching pygame at import time inside tests by stubbing
	# tile_surfaces with a dict.
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


def test_shadow_table_size_matches_grid():
	"""Shadow arrays match the tile-cell grid (height x width)."""
	game_map = _make_map(width=5, height=3)
	assert len(game_map.shadow_blk) == 3
	assert all(len(row) == 5 for row in game_map.shadow_blk)
	assert len(game_map.shadow_bk2) == 3
	assert all(len(row) == 5 for row in game_map.shadow_bk2)


def test_initial_shadow_is_water():
	"""All-zero corners classify every tile as water."""
	game_map = _make_map()
	for r in range(game_map.grid_height):
		for c in range(game_map.grid_width):
			assert game_map.shadow_blk[r][c] == settings.ASM_TILE_WATER
			assert game_map.shadow_bk2[r][c] == settings.ASM_TILE_WATER


def test_raise_corner_marks_neighboring_tiles_non_water():
	"""Lifting one corner pulls its neighboring tiles out of water."""
	game_map = _make_map()
	game_map.set_corner_altitude(2, 2, 1)
	# The tile at (1, 1) shares a corner at (2, 2) and now has a
	# non-water classification (slope, since it has mixed heights).
	assert game_map.shadow_blk[1][1] == settings.ASM_TILE_SLOPE
	# A far tile is unchanged.
	assert game_map.shadow_blk[0][0] == settings.ASM_TILE_WATER


def test_uniform_high_block_classifies_flat():
	"""Four equal non-zero corners on a tile yield ASM_TILE_FLAT."""
	game_map = _make_map()
	game_map.set_corner_altitude(1, 1, 2)
	game_map.set_corner_altitude(1, 2, 2)
	game_map.set_corner_altitude(2, 1, 2)
	game_map.set_corner_altitude(2, 2, 2)
	assert game_map.shadow_blk[1][1] == settings.ASM_TILE_FLAT


def test_recompute_matches_after_bulk_mutation():
	"""set_all_altitude bypasses the per-corner setter; recompute syncs."""
	game_map = _make_map()
	game_map.set_all_altitude(settings.ALTITUDE_MAX)
	# Every tile should now classify as rock peak.
	for r in range(game_map.grid_height):
		for c in range(game_map.grid_width):
			assert game_map.shadow_blk[r][c] == settings.ASM_TILE_ROCK


def test_recompute_is_idempotent():
	"""Calling recompute_shadow_codes twice yields identical arrays."""
	game_map = _make_map()
	game_map.set_corner_altitude(1, 1, 1)
	game_map.set_corner_altitude(2, 2, 1)
	first = [row[:] for row in game_map.shadow_blk]
	game_map.recompute_shadow_codes()
	second = [row[:] for row in game_map.shadow_blk]
	assert first == second
