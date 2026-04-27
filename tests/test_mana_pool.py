"""Tests for the mana pool system."""

import os

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pytest
import populous_game.mana_pool as mana_pool_module
import populous_game.faction as faction
import populous_game.settings as settings


@pytest.fixture
def pool():
	"""Create a mana pool for testing."""
	return mana_pool_module.ManaPool([faction.Faction.PLAYER, faction.Faction.ENEMY])


def test_initial_mana_set_correctly(pool):
	"""Mana pool initializes with INITIAL_MANA per faction."""
	assert pool.get_mana(faction.Faction.PLAYER) == settings.INITIAL_MANA
	assert pool.get_mana(faction.Faction.ENEMY) == settings.INITIAL_MANA


def test_add_mana_increases_total(pool):
	"""Adding mana increases the faction's mana."""
	initial = pool.get_mana(faction.Faction.PLAYER)
	pool.add(faction.Faction.PLAYER, 10.0)
	assert pool.get_mana(faction.Faction.PLAYER) == initial + 10.0


def test_mana_capped_at_maximum(pool):
	"""Mana is capped at a soft maximum."""
	pool.add(faction.Faction.PLAYER, 10000.0)
	final_mana = pool.get_mana(faction.Faction.PLAYER)
	assert final_mana <= settings.PEEP_LIFE_MAX * 4


def test_spend_mana_success(pool):
	"""Spend returns True and decrements when sufficient mana."""
	initial = pool.get_mana(faction.Faction.PLAYER)
	success = pool.spend(faction.Faction.PLAYER, 10.0)
	assert success
	assert pool.get_mana(faction.Faction.PLAYER) == initial - 10.0


def test_spend_mana_insufficient_returns_false(pool):
	"""Spend returns False and does not decrement when insufficient mana."""
	# Drain the pool
	pool.spend(faction.Faction.PLAYER, settings.INITIAL_MANA)
	initial = pool.get_mana(faction.Faction.PLAYER)
	# Try to spend more
	success = pool.spend(faction.Faction.PLAYER, 10.0)
	assert not success
	assert pool.get_mana(faction.Faction.PLAYER) == initial


def test_regen_from_houses(pool):
	"""Mana regenerates from non-destroyed houses."""
	# Create mock houses
	class MockHouse:
		def __init__(self, faction_id, destroyed=False):
			self.faction_id = faction_id
			self.destroyed = destroyed

	houses = [
		MockHouse(faction.Faction.PLAYER, destroyed=False),
		MockHouse(faction.Faction.PLAYER, destroyed=False),
		MockHouse(faction.Faction.ENEMY, destroyed=False),
		MockHouse(faction.Faction.ENEMY, destroyed=True),  # Destroyed house should not regen
	]

	initial_player = pool.get_mana(faction.Faction.PLAYER)
	initial_enemy = pool.get_mana(faction.Faction.ENEMY)

	# Regenerate for 1 second
	pool.regen_from_houses(houses, 1.0)

	# Player should have gained from 2 houses
	expected_player_regen = settings.MANA_REGEN_PER_HOUSE_PER_SEC * 2 * 1.0
	assert pool.get_mana(faction.Faction.PLAYER) == initial_player + expected_player_regen

	# Enemy should have gained from 1 house (other is destroyed)
	expected_enemy_regen = settings.MANA_REGEN_PER_HOUSE_PER_SEC * 1 * 1.0
	assert pool.get_mana(faction.Faction.ENEMY) == initial_enemy + expected_enemy_regen


def test_regen_destroyed_houses_skip(pool):
	"""Destroyed houses do not regenerate mana."""
	class MockHouse:
		def __init__(self, faction_id, destroyed=False):
			self.faction_id = faction_id
			self.destroyed = destroyed

	houses = [
		MockHouse(faction.Faction.PLAYER, destroyed=True),
	]

	initial = pool.get_mana(faction.Faction.PLAYER)
	pool.regen_from_houses(houses, 1.0)
	# Mana should not increase
	assert pool.get_mana(faction.Faction.PLAYER) == initial
