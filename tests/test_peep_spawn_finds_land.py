"""Peep spawning falls back to nearest-land BFS when the random pick is water.

Verifies M1 WP-M1-A: spawn count matches request on every fixed and
random seed; raises RuntimeError when the map has no land at all.
"""

import random
import pytest
import populous_game.game as game_module
import populous_game.faction as faction
import populous_game.peep_state as peep_state
import populous_game.settings as settings


FIXED_SEEDS = (1, 2, 3, 4, 5, 1234, 0xdeadbeef)


def _seeded_game(map_seed):
	"""Boot a Game instance with a deterministic map from map_seed."""
	g = game_module.Game()
	g.game_map.randomize(seed=map_seed)
	g.peeps.clear()
	return g


def test_spawn_initial_peeps_count_matches_on_fixed_seeds():
	"""All ten requested peeps spawn on each committed map seed."""
	for seed in FIXED_SEEDS:
		random.seed(seed + 1000)
		game = _seeded_game(seed)
		game.spawn_initial_peeps(10)
		assert len(game.peeps) == 10, (
			f"map_seed {seed}: expected 10 peeps, got {len(game.peeps)}"
		)
		assert all(p.faction_id == faction.Faction.PLAYER for p in game.peeps)


def test_spawn_initial_peeps_awards_player_score():
	"""Initial player placement awards the ASM-cited score side effect."""
	random.seed(77)
	game = _seeded_game(1234)
	game.score = 0
	game.spawn_initial_peeps(3)
	assert len(game.peeps) == 3
	assert game.score == 30


def test_spawn_initial_peeps_honors_asm_cap(monkeypatch):
	"""Spawn allocation refuses peeps once the ASM cap is reached."""
	monkeypatch.setattr(settings, 'ASM_PEEP_CAP', 2)
	random.seed(88)
	game = _seeded_game(1234)
	game.score = 0
	game.spawn_initial_peeps(5)
	assert len(game.peeps) == 2
	assert game.score == 20


def test_spawn_recomputes_map_who_for_live_peeps():
	"""Spawning writes index+1 values into shadow occupancy."""
	random.seed(89)
	game = _seeded_game(1234)
	game.spawn_initial_peeps(1)
	peep_obj = game.peeps[0]
	r = int(peep_obj.y)
	c = int(peep_obj.x)
	assert game.game_map.map_who[r][c] == 1

	peep_obj.dead = True
	peep_obj.state = peep_state.PeepState.DEAD
	game._recompute_map_who()
	assert game.game_map.map_who[r][c] == 0


def test_spawn_enemy_peeps_count_matches_on_fixed_seeds():
	"""All requested enemy peeps spawn on each committed seed."""
	for seed in FIXED_SEEDS:
		random.seed(seed + 2000)
		game = _seeded_game(seed)
		game.spawn_enemy_peeps(10)
		assert len(game.peeps) == 10, (
			f"map_seed {seed}: expected 10 enemy peeps, got {len(game.peeps)}"
		)
		assert all(p.faction_id == faction.Faction.ENEMY for p in game.peeps)


def test_spawn_random_seed_sweep_count_matches():
	"""On 20 random seeds, all ten initial peeps spawn each time."""
	for seed in range(200, 220):
		random.seed(seed + 3000)
		game = _seeded_game(seed)
		game.spawn_initial_peeps(10)
		assert len(game.peeps) == 10, (
			f"map_seed {seed}: spawn under-produced: {len(game.peeps)} of 10"
		)
		assert all(p.faction_id == faction.Faction.PLAYER for p in game.peeps)


def test_spawn_lands_only_on_non_water():
	"""Every spawned peep is on a corner with altitude > 0."""
	random.seed(99)
	game = _seeded_game(0xc0ffee)
	game.spawn_initial_peeps(10)
	for p in game.peeps:
		# Peep stores grid_r + 0.5 / grid_c + 0.5; truncate back to grid.
		r_int = int(p.y)
		c_int = int(p.x)
		alt = game.game_map.get_corner_altitude(r_int, c_int)
		assert alt > 0, (
			f"peep at grid (r={r_int}, c={c_int}) is on water altitude {alt}"
		)


def test_spawn_raises_when_map_has_no_land():
	"""All-water map raises RuntimeError on first spawn attempt."""
	game = game_module.Game()
	game.game_map.set_all_altitude(0)
	game.peeps.clear()
	with pytest.raises(RuntimeError, match="no land tile"):
		game.spawn_initial_peeps(1)


def test_enemy_spawn_raises_when_map_has_no_land():
	"""All-water map raises RuntimeError for enemy spawn too."""
	game = game_module.Game()
	game.game_map.set_all_altitude(0)
	game.peeps.clear()
	with pytest.raises(RuntimeError, match="no land tile"):
		game.spawn_enemy_peeps(1)
