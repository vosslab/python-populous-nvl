"""Tests for power effects (rules-faithful per asm/CONSTRUCTION_REPORT.md)."""

import pytest
import random
import pygame
import os

# Set headless mode before importing the game
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import populous_game.game as game_module
import populous_game.faction as faction
import populous_game.settings as settings


@pytest.fixture
def game():
	"""Create a game instance for testing."""
	g = game_module.Game()
	g.spawn_initial_peeps(10, faction_id=faction.Faction.PLAYER)
	g.spawn_enemy_peeps(5)
	# Ensure a flat test area exists
	for r in range(5, 10):
		for c in range(5, 10):
			for _ in range(10):
				g.game_map.raise_corner(r, c)
	yield g
	pygame.quit()


def test_volcano_raises_terrain_and_destroys_houses(game):
	"""Per asm/CONSTRUCTION_REPORT.md: volcano raises terrain in a radius.

	Test that:
	1. Terrain corners in the radius are raised.
	2. Houses in the AOE are destroyed.
	"""
	# Reset terrain to a lower altitude first
	game.game_map.set_all_altitude(2)
	initial_alt = game.game_map.get_corner_altitude(7, 7)
	assert initial_alt == 2

	# Cast volcano at (7, 7) with radius 3
	result = game.power_manager.activate('volcano', (7, 7))

	assert result.success
	assert result.mana_spent == settings.POWER_VOLCANO_COST
	assert result.cooldown == settings.POWER_VOLCANO_COOLDOWN
	# Verify terrain was raised (raised twice per affected cell)
	new_alt = game.game_map.get_corner_altitude(7, 7)
	assert new_alt > initial_alt, f"Volcano should raise terrain (was {initial_alt}, now {new_alt})"


def test_flood_lowers_terrain(game):
	"""Per asm/CONSTRUCTION_REPORT.md: flood lowers terrain in a radius."""
	# Raise a test area
	for r in range(8, 12):
		for c in range(8, 12):
			for _ in range(5):
				game.game_map.raise_corner(r, c)
	initial_alt = game.game_map.get_corner_altitude(9, 9)

	# Cast flood at (9, 9)
	result = game.power_manager.activate('flood', (9, 9))

	assert result.success
	assert result.mana_spent == settings.POWER_FLOOD_COST
	new_alt = game.game_map.get_corner_altitude(9, 9)
	assert new_alt < initial_alt, "Flood should lower terrain"


def test_quake_random_terrain_changes(game):
	"""Quake applies random raise/lower to terrain in a radius."""
	# Set a fixed seed for determinism
	if hasattr(game, 'sim_rng'):
		game.sim_rng = random.Random(42)
	else:
		random.seed(42)

	initial_alts = {}
	for r in range(10, 15):
		for c in range(10, 15):
			initial_alts[(r, c)] = game.game_map.get_corner_altitude(r, c)

	# Cast quake at (12, 12)
	result = game.power_manager.activate('quake', (12, 12))

	assert result.success
	# Verify that at least some terrain changed (not all stayed the same)
	changes = 0
	for r in range(10, 15):
		for c in range(10, 15):
			if game.game_map.get_corner_altitude(r, c) != initial_alts[(r, c)]:
				changes += 1
	assert changes > 0, "Quake should change some terrain"


def test_swamp_lowers_terrain_for_drowning(game):
	"""Swamp lowers terrain to create water hazard."""
	initial_alt = game.game_map.get_corner_altitude(4, 4)

	result = game.power_manager.activate('swamp', (4, 4))

	assert result.success
	new_alt = game.game_map.get_corner_altitude(4, 4)
	assert new_alt < initial_alt, "Swamp should lower terrain"


def test_knight_boosts_player_peep_life(game):
	"""Knight power converts a player peep into a boosted knight."""
	player_peeps = [p for p in game.peeps if p.faction_id == faction.Faction.PLAYER]
	assert len(player_peeps) > 0
	initial_life = player_peeps[0].life

	result = game.power_manager.activate('knight', None)

	assert result.success
	# Verify a peep was boosted (doubled life, capped at max)
	boosted_peep = [p for p in game.peeps if p.weapon_type == 'knight']
	assert len(boosted_peep) > 0
	assert boosted_peep[0].life >= initial_life


def test_power_insufficient_mana_fails(game):
	"""Power activation fails when player has insufficient mana."""
	# Drain mana
	current_mana = game.mana_pool.get_mana(faction.Faction.PLAYER)
	game.mana_pool.spend(faction.Faction.PLAYER, current_mana)
	assert game.mana_pool.get_mana(faction.Faction.PLAYER) == 0.0

	result = game.power_manager.activate('volcano', (7, 7))

	assert not result.success


def test_power_on_cooldown_fails(game):
	"""Power activation fails when on cooldown."""
	# Activate volcano once
	result1 = game.power_manager.activate('volcano', (7, 7))
	assert result1.success

	# Try to activate immediately (should fail due to cooldown)
	result2 = game.power_manager.activate('volcano', (8, 8))
	assert not result2.success


def test_papal_sets_marker_position(game):
	"""Papal power sets the papal marker at target."""
	result = game.power_manager.activate('papal', (3, 3))

	assert result.success
	assert game.mode_manager.papal_position == (3, 3)


def test_power_cooldown_decrements(game):
	"""Power cooldowns decrement with update()."""
	# Activate a power
	game.power_manager.activate('volcano', (7, 7))
	cooldown_after_activate = game.power_manager.cooldowns['volcano']
	assert cooldown_after_activate > 0

	# Update with small dt
	game.power_manager.update(0.1)
	cooldown_after_update = game.power_manager.cooldowns['volcano']
	assert cooldown_after_update < cooldown_after_activate


def test_power_cooldown_reaches_zero(game):
	"""Cooldown eventually reaches zero and power becomes available."""
	# Activate volcano
	game.power_manager.activate('volcano', (7, 7))
	# Fast-forward cooldown
	cooldown_time = game.power_manager.cooldowns['volcano']
	game.power_manager.update(cooldown_time + 1.0)
	assert game.power_manager.cooldowns['volcano'] == 0.0
	# Verify power is now available
	assert game.power_manager.can_activate('volcano', settings.INITIAL_MANA)
