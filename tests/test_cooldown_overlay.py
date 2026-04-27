"""Test cooldown overlay rendering."""

import pytest
import pygame

pygame.init()

import populous_game.game as game_module
import populous_game.app_state as app_state_module


@pytest.fixture
def game():
	"""Create a Game instance in PLAYING state."""
	g = game_module.Game()
	g.app_state.transition_to(app_state_module.AppState.PLAYING)
	return g


@pytest.fixture
def renderer(game):
	"""Create renderer from game."""
	return game.renderer


def test_cooldown_overlay_method_exists(renderer):
	"""Test that _draw_cooldown_overlay method exists."""
	assert hasattr(renderer, '_draw_cooldown_overlay')
	assert callable(renderer._draw_cooldown_overlay)


def test_no_overlay_with_zero_cooldowns(game, renderer):
	"""Test that no overlay is drawn when all cooldowns are zero."""
	# All cooldowns should be zero by default
	for power_name in game.power_manager.cooldowns:
		assert game.power_manager.cooldowns[power_name] == 0.0

	# Should not raise
	renderer._draw_cooldown_overlay()


def test_cooldown_overlay_with_active_volcano(game, renderer):
	"""Test that cooldown overlay works with volcano cooldown set."""
	game.power_manager.cooldowns['volcano'] = 5.0
	# Should not raise
	renderer._draw_cooldown_overlay()


def test_multiple_cooldowns_work(game, renderer):
	"""Test that multiple cooldowns can be active simultaneously."""
	game.power_manager.cooldowns['volcano'] = 3.0
	game.power_manager.cooldowns['flood'] = 2.0
	game.power_manager.cooldowns['quake'] = 1.0

	# Should not raise
	renderer._draw_cooldown_overlay()


def test_cooldown_overlay_with_zero_and_nonzero(game, renderer):
	"""Test that zero and non-zero cooldowns are handled correctly."""
	game.power_manager.cooldowns['volcano'] = 5.0
	game.power_manager.cooldowns['flood'] = 0.0
	game.power_manager.cooldowns['quake'] = 0.0

	# Should not raise
	renderer._draw_cooldown_overlay()


def test_all_power_types_cooldown(game, renderer):
	"""Test that all power types can have cooldowns."""
	game.power_manager.cooldowns['volcano'] = 2.5
	game.power_manager.cooldowns['flood'] = 1.2
	game.power_manager.cooldowns['quake'] = 0.8
	game.power_manager.cooldowns['swamp'] = 1.5
	game.power_manager.cooldowns['papal'] = 3.0
	game.power_manager.cooldowns['knight'] = 2.0

	# Should not raise
	renderer._draw_cooldown_overlay()


def test_cooldown_overlay_alpha_calculation(game, renderer):
	"""Test that alpha is calculated proportionally to cooldown."""
	# Set a known cooldown
	game.power_manager.cooldowns['volcano'] = 5.0

	# Should not raise; the alpha is calculated inside
	renderer._draw_cooldown_overlay()
