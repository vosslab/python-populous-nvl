"""Pin behavior of the check_life_result() Python compatibility helper."""

import populous_game.peep_helpers as peep_helpers
import populous_game.terrain as terrain


def _make_map(width=5, height=5):
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


def test_water_neighborhood_scores_zero():
	"""All-water neighborhood: score 0, no flat block, scanned 9."""
	game_map = _make_map()
	result = peep_helpers.check_life_result(game_map, 2, 2)
	assert result.score == 0
	assert result.a_flat_block is False
	assert result.all_of_city is False
	assert result.scanned == 9


def test_flat_block_increments_score_and_flag():
	"""A flat tile at the center adds 2 and sets a_flat_block."""
	game_map = _make_map()
	# Raise the four corners around tile (2, 2) to make it flat.
	for r in (2, 3):
		for c in (2, 3):
			game_map.set_corner_altitude(r, c, 2)
	result = peep_helpers.check_life_result(game_map, 2, 2)
	assert result.a_flat_block is True
	assert result.score >= 2


def test_corner_tile_has_partial_scan():
	"""A corner tile's ring includes off-map offsets that are skipped."""
	game_map = _make_map()
	result = peep_helpers.check_life_result(game_map, 0, 0)
	# Self + 3 in-bounds neighbors out of the 3x3 ring.
	assert result.scanned == 4


def test_referential_transparency():
	"""Repeated calls on the same map state return equal results."""
	game_map = _make_map()
	game_map.set_corner_altitude(2, 2, 1)
	first = peep_helpers.check_life_result(game_map, 1, 1)
	second = peep_helpers.check_life_result(game_map, 1, 1)
	assert first == second
