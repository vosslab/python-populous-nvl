"""Tests for drag-to-paint terrain (M7)."""

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import time
import pygame


def test_drag_paint_state_initializes_clean():
	"""Fresh InputController has no drag-paint button held."""
	from populous_game.game import Game
	game = Game()
	assert game.input_controller._drag_paint_button is None
	assert game.input_controller._drag_paint_last_time == 0.0


def test_drag_paint_cleared_on_button_up():
	"""Releasing the button clears the drag-paint state."""
	from populous_game.game import Game
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(3)

	game.input_controller._drag_paint_button = 1
	pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(0, 0)))
	game.input_controller.poll()

	assert game.input_controller._drag_paint_button is None


def test_drag_paint_respects_pacing():
	"""Two motion events back-to-back should only paint at most once due to pacing."""
	from populous_game.game import Game
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(3)

	# Prime drag state
	game.input_controller._drag_paint_button = 1
	game.input_controller._drag_paint_last_time = time.time()  # block immediate paint

	# Count raise_corner calls via a wrapper
	calls = []
	original = game.game_map.raise_corner
	def counting_raise(r, c):
		calls.append((r, c))
		return original(r, c)
	game.game_map.raise_corner = counting_raise

	# Fire two motion events at the viewport center back-to-back
	mx = (game.view_rect.x + game.view_rect.width // 2) * game.display_scale
	my = (game.view_rect.y + game.view_rect.height // 2) * game.display_scale
	for _ in range(2):
		ev = pygame.event.Event(pygame.MOUSEMOTION, pos=(mx, my), rel=(0, 0), buttons=(1, 0, 0))
		game.input_controller._handle_drag_paint(ev)

	assert len(calls) == 0  # both blocked by pacing window
