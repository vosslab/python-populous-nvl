"""Tests for ui_panel.hover_info_at (M7)."""

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


def test_hover_info_returns_terrain_dict_inside_viewport():
	"""Hovering over the viewport returns a terrain info dict."""
	from populous_game.game import Game
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(3)
	# Pick the middle of the viewport rect
	mx = game.view_rect.x + game.view_rect.width // 2
	my = game.view_rect.y + game.view_rect.height // 2
	info = game.ui_panel.hover_info_at(mx, my, game)
	assert info is not None
	assert info['kind'] == 'terrain'
	assert info['altitude'] == 3


def test_hover_info_returns_none_outside_viewport():
	"""A click outside the viewport with no entity hit returns None."""
	from populous_game.game import Game
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	# Coords far outside any UI element
	info = game.ui_panel.hover_info_at(-100, -100, game)
	assert info is None
