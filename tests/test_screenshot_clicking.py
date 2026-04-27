"""End-to-end clicking test using the headless screenshot pipeline (M8 follow-up).

Verifies that posted MOUSEBUTTONDOWN events with explicit positions actually
drive the input controller's click handler, so headless scripts in
tools/screenshot.py can exercise the UI button paths.

Regression: prior to switching MOUSEBUTTONDOWN handling to use event.pos,
posted clicks were ignored because pygame.mouse.get_pos() always returns
(0, 0) under SDL_VIDEODRIVER=dummy.
"""

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame


def test_posted_click_on_papal_button_sets_papal_mode():
	"""Posting a MOUSEBUTTONDOWN at the papal button activates papal mode."""
	from populous_game.game import Game
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(3)

	# The papal button center is in internal-canvas coordinates; the click
	# event's pos is in physical screen coords (display_scale * internal).
	bcx, bcy = game.ui_panel.buttons['_do_papal']['c']
	mx = bcx * game.display_scale
	my = bcy * game.display_scale

	pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(mx, my)))
	game.input_controller.poll()

	assert game.mode_manager.papal_mode is True


def test_posted_click_on_dpad_north_moves_camera():
	"""Clicking the N (north) dpad button registers as a button click."""
	from populous_game.game import Game
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(3)

	bcx, bcy = game.ui_panel.buttons['N']['c']
	mx = bcx * game.display_scale
	my = bcy * game.display_scale

	pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(mx, my)))
	game.input_controller.poll()

	# last_button_click is the visible side-effect of any UI button click
	assert game.last_button_click is not None
	assert game.last_button_click[0] == 'N'


def test_posted_click_on_volcano_sets_pending_power():
	"""Clicking the volcano button puts the game into volcano-target mode."""
	from populous_game.game import Game
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(3)

	bcx, bcy = game.ui_panel.buttons['_do_volcano']['c']
	mx = bcx * game.display_scale
	my = bcy * game.display_scale

	pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(mx, my)))
	game.input_controller.poll()

	assert game.mode_manager.pending_power == 'volcano'
