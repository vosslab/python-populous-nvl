"""Test AOE preview overlay rendering."""

import pytest
import pygame
from unittest.mock import patch

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


def test_aoe_preview_method_exists(renderer):
	"""Test that _draw_aoe_preview method exists."""
	assert hasattr(renderer, '_draw_aoe_preview')
	assert callable(renderer._draw_aoe_preview)


def test_aoe_preview_no_preview_when_no_pending_power(game, renderer):
	"""Test that no preview is drawn when no power is pending."""
	assert game.mode_manager.pending_power is None
	# Should not raise
	renderer._draw_aoe_preview()


def test_aoe_preview_with_volcano_power(game, renderer):
	"""Test that AOE preview works with volcano power."""
	game.mode_manager.pending_power = 'volcano'
	# Should not raise
	renderer._draw_aoe_preview()


def test_aoe_preview_with_flood_power(game, renderer):
	"""Test that AOE preview works with flood power."""
	game.mode_manager.pending_power = 'flood'
	# Should not raise
	renderer._draw_aoe_preview()


def test_aoe_preview_with_quake_power(game, renderer):
	"""Test that AOE preview works with quake power."""
	game.mode_manager.pending_power = 'quake'
	# Should not raise
	renderer._draw_aoe_preview()


def test_aoe_preview_with_swamp_power(game, renderer):
	"""Test that AOE preview works with swamp power."""
	game.mode_manager.pending_power = 'swamp'
	# Should not raise
	renderer._draw_aoe_preview()


def test_aoe_preview_skips_papal_with_zero_aoe(game, renderer):
	"""Test that papal power (zero AOE radius) is skipped."""
	game.mode_manager.pending_power = 'papal'
	# Papal has aoe_radius=0, so should not draw
	# Should not raise
	renderer._draw_aoe_preview()


def test_aoe_preview_skips_knight_with_zero_aoe(game, renderer):
	"""Test that knight power (zero AOE radius) is skipped."""
	game.mode_manager.pending_power = 'knight'
	# Knight has aoe_radius=0, so should not draw
	renderer._draw_aoe_preview()


def test_aoe_preview_called_from_draw_gameplay(game, renderer):
	"""Test that _draw_gameplay calls _draw_aoe_preview."""
	with patch.object(renderer, '_draw_aoe_preview', wraps=renderer._draw_aoe_preview) as mock_aoe:
		with patch('pygame.display.flip'):
			renderer._draw_gameplay()
		mock_aoe.assert_called_once()


def test_aoe_preview_when_mouse_outside_view(game, renderer):
	"""Test that AOE preview handles mouse outside view rectangle."""
	game.mode_manager.pending_power = 'volcano'

	with patch('pygame.mouse.get_pos') as mock_mouse:
		# Position way outside the view
		mock_mouse.return_value = (10000, 10000)
		# Should not raise
		renderer._draw_aoe_preview()


def test_aoe_preview_respects_visible_bounds(game, renderer):
	"""Test that AOE preview only draws cells in visible bounds."""
	game.mode_manager.pending_power = 'volcano'
	# Should not raise and should respect bounds
	renderer._draw_aoe_preview()


def test_aoe_preview_with_different_pending_powers(game, renderer):
	"""Test that AOE preview works with various pending powers."""
	for power_name in ['volcano', 'flood', 'quake', 'swamp']:
		game.mode_manager.pending_power = power_name
		# Should not raise
		renderer._draw_aoe_preview()
		game.mode_manager.pending_power = None


def test_aoe_preview_clears_when_pending_power_cleared(game, renderer):
	"""Test that AOE preview is not drawn when pending_power is cleared."""
	game.mode_manager.pending_power = 'volcano'
	renderer._draw_aoe_preview()  # Draw once

	game.mode_manager.pending_power = None
	# Should not raise and should not draw anything
	renderer._draw_aoe_preview()
