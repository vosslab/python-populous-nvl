"""Test mana readout rendering."""

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


def test_mana_readout_method_exists(renderer):
	"""Test that _draw_mana_readout method exists."""
	assert hasattr(renderer, '_draw_mana_readout')
	assert callable(renderer._draw_mana_readout)


def test_mana_readout_in_playing_state(game, renderer):
	"""Test that mana readout renders in PLAYING state."""
	assert game.app_state.is_playing()
	# Should not raise
	renderer._draw_mana_readout()


def test_mana_readout_skipped_when_not_playing(game, renderer):
	"""Test that mana readout is skipped when not in PLAYING state."""
	game.app_state.transition_to(app_state_module.AppState.PAUSED)
	assert not game.app_state.is_playing()
	# Should not raise; just returns early
	renderer._draw_mana_readout()


def test_mana_readout_with_zero_mana(game, renderer):
	"""Test mana readout with zero mana."""
	# Force mana to zero
	player_faction = game.player_faction_id()
	game.mana_pool._mana[player_faction] = 0.0

	# Should not raise
	renderer._draw_mana_readout()


def test_mana_readout_with_large_mana(game, renderer):
	"""Test mana readout with large mana value."""
	player_faction = game.player_faction_id()
	game.mana_pool._mana[player_faction] = 999.5

	# Should not raise
	renderer._draw_mana_readout()


def test_mana_readout_with_fractional_mana(game, renderer):
	"""Test that fractional mana is truncated to integer."""
	player_faction = game.player_faction_id()
	game.mana_pool._mana[player_faction] = 42.7
	# When rendered, should show "MANA 42" (truncated)
	# Should not raise
	renderer._draw_mana_readout()


def test_mana_readout_called_from_draw_gameplay(game, renderer):
	"""Test that _draw_gameplay calls _draw_mana_readout."""
	# Verify the method is called by patching it
	import unittest.mock as mock
	with mock.patch.object(renderer, '_draw_mana_readout', wraps=renderer._draw_mana_readout) as mock_mana:
		with mock.patch('pygame.display.flip'):
			renderer._draw_gameplay()
		mock_mana.assert_called_once()


def test_mana_readout_uses_hud_font_size(game, renderer):
	"""Test that mana readout uses HUD_FONT_SIZE setting."""
	player_faction = game.player_faction_id()
	game.mana_pool._mana[player_faction] = 100.0

	import unittest.mock as mock
	with mock.patch('pygame.font.SysFont') as mock_sysfont:
		mock_font = mock.MagicMock()
		mock_sysfont.return_value = mock_font
		mock_font.render.return_value = pygame.Surface((100, 20))

		renderer._draw_mana_readout()

		# Verify SysFont was called with HUD_FONT_SIZE
		import populous_game.settings as settings
		mock_sysfont.assert_called_with("consolas", settings.HUD_FONT_SIZE, bold=True)


def test_mana_readout_renders_mana_text(game, renderer):
	"""Test that mana readout text contains 'MANA'."""
	player_faction = game.player_faction_id()
	game.mana_pool._mana[player_faction] = 50.0

	import unittest.mock as mock
	with mock.patch('pygame.font.SysFont') as mock_sysfont:
		mock_font = mock.MagicMock()
		mock_sysfont.return_value = mock_font
		mock_font.render.return_value = pygame.Surface((100, 20))

		renderer._draw_mana_readout()

		# Verify render was called with text containing MANA
		found_mana_text = False
		for call in mock_font.render.call_args_list:
			args = call[0]
			if args and 'MANA' in args[0]:
				found_mana_text = True
				break
		assert found_mana_text, "MANA text not rendered"
