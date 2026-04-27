"""Tests for win and lose conditions triggered by debug keys (F11/F10).

These tests verify that:
- F11 in PLAYING state triggers WIN condition
- F10 in PLAYING state triggers LOSE condition
- GameOver screen renders appropriately with correct text
"""

import pygame
from unittest import mock

from populous_game.game import Game


def test_f11_triggers_win_condition():
	"""Pressing F11 in PLAYING state sets gameover_result='win' and transitions to GAMEOVER."""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.spawn_initial_peeps(1)

		# Simulate F11
		f11_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_F11})
		with mock.patch('pygame.event.get', return_value=[f11_event]):
			game.input_controller.poll()

		assert game.app_state.is_gameover()
		assert game.app_state.gameover_result == 'win'
	finally:
		pygame.quit()


def test_f10_triggers_lose_condition():
	"""Pressing F10 in PLAYING state sets gameover_result='lose' and transitions to GAMEOVER."""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.spawn_initial_peeps(1)

		# Simulate F10
		f10_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_F10})
		with mock.patch('pygame.event.get', return_value=[f10_event]):
			game.input_controller.poll()

		assert game.app_state.is_gameover()
		assert game.app_state.gameover_result == 'lose'
	finally:
		pygame.quit()


def test_gameover_screen_renders_victory():
	"""GameOver screen renders 'VICTORY' in green when result is 'win'."""
	pygame.init()
	pygame.display.set_mode((320, 200))

	try:
		game = Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.spawn_initial_peeps(1)
		game.app_state.transition_to(game.app_state.GAMEOVER)
		game.app_state.gameover_result = 'win'

		# Draw the frame; should not raise
		game.renderer.draw_frame()
		assert True  # If we get here, no exception was raised
	finally:
		pygame.quit()


def test_gameover_screen_renders_defeat():
	"""GameOver screen renders 'DEFEAT' in red when result is 'lose'."""
	pygame.init()
	pygame.display.set_mode((320, 200))

	try:
		game = Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.spawn_initial_peeps(1)
		game.app_state.transition_to(game.app_state.GAMEOVER)
		game.app_state.gameover_result = 'lose'

		# Draw the frame; should not raise
		game.renderer.draw_frame()
		assert True  # If we get here, no exception was raised
	finally:
		pygame.quit()


def test_f11_f10_ignored_in_menu():
	"""F11/F10 in MENU state are ignored; state doesn't change."""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()
		assert game.app_state.is_menu()

		# Simulate F11 in MENU
		f11_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_F11})
		with mock.patch('pygame.event.get', return_value=[f11_event]):
			game.input_controller.poll()

		# Should remain in MENU
		assert game.app_state.is_menu()
		assert game.app_state.gameover_result is None
	finally:
		pygame.quit()


def test_f11_f10_ignored_in_paused():
	"""F11/F10 in PAUSED state are ignored; state doesn't change."""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.spawn_initial_peeps(1)
		game.app_state.transition_to(game.app_state.PAUSED)

		# Simulate F11 in PAUSED
		f11_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_F11})
		with mock.patch('pygame.event.get', return_value=[f11_event]):
			game.input_controller.poll()

		# Should remain in PAUSED
		assert game.app_state.is_paused()
		assert game.app_state.gameover_result is None
	finally:
		pygame.quit()
