"""Test confirm dialog rendering."""

import pytest
from unittest.mock import patch, MagicMock
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


def test_confirm_dialog_is_active_when_requested(game, renderer):
	"""Test that confirm dialog is active after request_confirm."""
	assert not game.app_state.has_confirm_dialog()
	game.app_state.request_confirm("Test message", lambda: None)
	assert game.app_state.has_confirm_dialog()


def test_confirm_dialog_method_exists(renderer):
	"""Test that _draw_confirm_dialog method exists and is callable."""
	assert hasattr(renderer, '_draw_confirm_dialog')
	assert callable(renderer._draw_confirm_dialog)


def test_no_dialog_when_not_active(game, renderer):
	"""Test that _draw_confirm_dialog returns early when no dialog is active."""
	assert not game.app_state.has_confirm_dialog()
	# Should not raise; simply returns
	renderer._draw_confirm_dialog()


def test_dialog_draws_with_mock_font(game, renderer):
	"""Test that confirm dialog attempts to render text when active."""
	message = "Test warning"
	game.app_state.request_confirm(message, lambda: None)

	# Use patch.object on pygame.font module's SysFont
	with patch('pygame.font.SysFont') as mock_sysfont_class:
		mock_font_instance = MagicMock()
		mock_sysfont_class.return_value = mock_font_instance

		# Mock render to return a real Surface to avoid blit errors
		mock_surface = pygame.Surface((100, 20))
		mock_font_instance.render.return_value = mock_surface

		renderer._draw_confirm_dialog()

		# Verify SysFont was called
		mock_sysfont_class.assert_called()


def test_confirm_dialog_called_from_draw_frame(game, renderer):
	"""Test that draw_frame calls _draw_confirm_dialog."""
	game.app_state.request_confirm("Frame test", lambda: None)

	with patch.object(renderer, '_draw_confirm_dialog', wraps=renderer._draw_confirm_dialog) as mock_draw:
		with patch('pygame.display.flip'):
			renderer.draw_frame()
		mock_draw.assert_called_once()


def test_confirm_dialog_renders_without_error(game, renderer):
	"""Test that _draw_confirm_dialog can render without crashing."""
	game.app_state.request_confirm("Test message content here", lambda: None)
	# Should not raise any exception
	renderer._draw_confirm_dialog()
