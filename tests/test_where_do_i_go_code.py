"""Pin behavior of where_do_i_go_code(): terrain-only shadow helper."""

import random

import populous_game.pathfinding as pathfinding
import populous_game.settings as settings
import populous_game.terrain as terrain


class _StubPeep:
	def __init__(self, x, y):
		self.x = x
		self.y = y


def _make_map(width=4, height=4, base_alt=2):
	game_map = terrain.GameMap.__new__(terrain.GameMap)
	game_map.grid_width = width
	game_map.grid_height = height
	game_map.corners = [
		[base_alt for _ in range(width + 1)]
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


def test_blocked_neighborhood_returns_failed_code():
	"""All-rock or out-of-bounds neighborhood returns ASM_MOVE_FAILED_CODE."""
	game_map = _make_map(base_alt=settings.ALTITUDE_MAX)
	rng = random.Random(0)
	peep = _StubPeep(x=1.5, y=1.5)
	result = pathfinding.where_do_i_go_code(peep, game_map, rng)
	assert result == settings.ASM_MOVE_FAILED_CODE


def test_flat_neighborhood_yields_offset():
	"""On open flat terrain the helper returns one of the 8 ring offsets."""
	game_map = _make_map(base_alt=2)
	rng = random.Random(0)
	peep = _StubPeep(x=2.5, y=2.5)
	result = pathfinding.where_do_i_go_code(peep, game_map, rng)
	# A real (dr, dc) delta from the ASM ring.
	assert isinstance(result, tuple)
	assert result in (
		(-1, 0), (-1, 1), (0, 1), (1, 1),
		(1, 0), (1, -1), (0, -1), (-1, -1),
	)


def test_seeded_rng_is_deterministic():
	"""Same seed -> same return for repeated runs."""
	game_map = _make_map(base_alt=2)
	peep = _StubPeep(x=2.5, y=2.5)
	first = pathfinding.where_do_i_go_code(peep, game_map, random.Random(42))
	second = pathfinding.where_do_i_go_code(peep, game_map, random.Random(42))
	assert first == second
