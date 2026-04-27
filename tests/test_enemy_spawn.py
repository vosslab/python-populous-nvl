"""Tests for enemy peep spawning (M5 Wave 3, Patch 1)."""

import random
import pytest
import populous_game.game as game_module
import populous_game.faction as faction
import populous_game.settings as settings


class TestEnemySpawn:
	"""Enemy spawn system: clustering and count verification."""

	def test_spawn_initial_peeps_default_faction(self):
		"""spawn_initial_peeps() defaults to PLAYER faction."""
		game = game_module.Game()
		game.game_map.set_all_altitude(3)  # Ensure non-water terrain
		game.spawn_initial_peeps(5)
		assert len(game.peeps) == 5
		for p in game.peeps:
			assert p.faction_id == faction.Faction.PLAYER

	def test_spawn_initial_peeps_explicit_faction(self):
		"""spawn_initial_peeps(count, faction_id) spawns with specified faction."""
		game = game_module.Game()
		game.game_map.set_all_altitude(3)  # Ensure non-water terrain
		game.spawn_initial_peeps(3, faction_id=faction.Faction.ENEMY)
		assert len(game.peeps) == 3
		for p in game.peeps:
			assert p.faction_id == faction.Faction.ENEMY

	def test_spawn_enemy_peeps(self):
		"""spawn_enemy_peeps() creates enemy faction peeps."""
		game = game_module.Game()
		game.game_map.set_all_altitude(3)  # Ensure non-water terrain
		game.spawn_enemy_peeps(5)
		assert len(game.peeps) == 5
		for p in game.peeps:
			assert p.faction_id == faction.Faction.ENEMY

	def test_enemy_peeps_near_bottom_right(self):
		"""Enemy peeps are clustered near bottom-right quadrant."""
		game = game_module.Game()
		random.seed(42)
		game.spawn_enemy_peeps(10)
		assert len(game.peeps) >= 1
		# All enemy peeps should be in the bottom-right half
		for p in game.peeps:
			assert p.x >= settings.GRID_WIDTH // 2 - 5
			assert p.y >= settings.GRID_HEIGHT // 2 - 5

	def test_player_peeps_near_top_left(self):
		"""Player peeps are clustered near top-left quadrant."""
		game = game_module.Game()
		random.seed(42)
		game.spawn_initial_peeps(10)
		assert len(game.peeps) >= 1
		# Most player peeps should be in top-left half (no hard bounds; random allows some spread)
		count_in_quadrant = sum(1 for p in game.peeps if p.x < settings.GRID_WIDTH // 1.5 and p.y < settings.GRID_HEIGHT // 1.5)
		assert count_in_quadrant >= len(game.peeps) // 2

	def test_mixed_spawn(self):
		"""Spawn both player and enemy peeps."""
		game = game_module.Game()
		game.game_map.set_all_altitude(3)  # Ensure non-water terrain
		random.seed(42)
		game.spawn_initial_peeps(5)
		game.spawn_enemy_peeps(5)
		assert len(game.peeps) == 10
		player_count = sum(1 for p in game.peeps if p.faction_id == faction.Faction.PLAYER)
		enemy_count = sum(1 for p in game.peeps if p.faction_id == faction.Faction.ENEMY)
		assert player_count == 5
		assert enemy_count == 5

	def test_no_land_raises(self):
		"""Spawn raises a descriptive RuntimeError when no land exists.

		Per M1 WP-M1-A: the spawn API does not silently under-produce.
		Either every requested peep gets a land tile via BFS fallback,
		or the call raises so the bug is loud instead of hidden.
		"""
		game = game_module.Game()
		game.game_map.set_all_altitude(0)
		game.peeps.clear()
		with pytest.raises(RuntimeError, match="no land tile"):
			game.spawn_initial_peeps(10)

	def test_spawn_with_valid_altitude(self):
		"""Peeps spawn only where altitude > 0."""
		game = game_module.Game()
		# Set entire map to valid altitude
		game.game_map.set_all_altitude(3)
		game.spawn_initial_peeps(5)
		assert len(game.peeps) == 5
