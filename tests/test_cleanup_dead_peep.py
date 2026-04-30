"""Pin behavior of cleanup_dead_peep() and the death-path wiring."""

import populous_game.peep_helpers as peep_helpers


class _StubPeep:
	"""Minimal peep stand-in carrying just the shadow fields."""

	def __init__(self):
		self.linked_peep = object()
		self.remembered_target = (3, 4)
		self.terrain_marker = 'flag'
		self.last_move_offset = 7
		self.shield_opponent = object()


def test_cleanup_clears_all_listed_fields():
	peep = _StubPeep()
	peep_helpers.cleanup_dead_peep(peep)
	assert peep.linked_peep is None
	assert peep.remembered_target is None
	assert peep.terrain_marker is None
	assert peep.last_move_offset == 0
	assert peep.shield_opponent is None


def test_cleanup_is_idempotent():
	peep = _StubPeep()
	peep_helpers.cleanup_dead_peep(peep)
	peep_helpers.cleanup_dead_peep(peep)
	assert peep.linked_peep is None
	assert peep.last_move_offset == 0


def test_cleanup_tolerates_missing_fields():
	"""Test doubles that lack a given shadow field are not crashed."""

	class Sparse:
		linked_peep = object()

	sparse = Sparse()
	# Should not raise when remembered_target / terrain_marker /
	# shield_opponent are absent.
	peep_helpers.cleanup_dead_peep(sparse)
	assert sparse.linked_peep is None


def test_transition_to_dead_clears_shadow_fields():
	"""Peep.transition(DEAD) routes through cleanup_dead_peep()."""
	import populous_game.peeps as peeps_mod
	import populous_game.peep_state as peep_state
	import populous_game.faction as faction_mod
	import populous_game.terrain as terrain

	game_map = terrain.GameMap.__new__(terrain.GameMap)
	game_map.grid_width = 4
	game_map.grid_height = 4
	game_map.corners = [
		[1 for _ in range(5)] for _ in range(5)
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

	# Bypass __init__ to avoid pygame surfaces.
	peep = peeps_mod.Peep.__new__(peeps_mod.Peep)
	peep.x = 1.5
	peep.y = 1.5
	peep.game_map = game_map
	peep.faction = faction_mod.Faction.PLAYER
	peep.faction_id = faction_mod.Faction.PLAYER
	peep.life = 50
	peep.dead = False
	peep.state = peep_state.PeepState.IDLE
	peep.linked_peep = object()
	peep.remembered_target = (2, 2)
	peep.terrain_marker = 'flag'
	peep.last_move_offset = 5
	peep.shield_opponent = object()

	peep.transition(peep_state.PeepState.DEAD)

	assert peep.state == peep_state.PeepState.DEAD
	assert peep.linked_peep is None
	assert peep.remembered_target is None
	assert peep.terrain_marker is None
	assert peep.last_move_offset == 0
	assert peep.shield_opponent is None
