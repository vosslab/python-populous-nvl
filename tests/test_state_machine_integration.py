"""Integration tests for game state machine (menu -> playing -> gameover -> menu).

Tests the full session loop via input controller without requiring visual display.
"""

import pygame
from unittest import mock

from populous_game.game import Game


def test_full_session_loop_menu_to_play_to_win_to_menu():
	"""Boot in MENU, press Enter to play, F11 to win, Enter to restart menu."""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()

		# Should start in MENU state
		assert game.app_state.is_menu()
		assert game.peeps == []

		# Simulate Enter key to start game
		enter_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN})
		with mock.patch('pygame.event.get', return_value=[enter_event]):
			result = game.input_controller.poll()
		assert result is True
		assert game.app_state.is_playing()
		assert len(game.peeps) > 0  # spawn_initial_peeps was called

		# Simulate F11 (win condition)
		f11_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_F11})
		with mock.patch('pygame.event.get', return_value=[f11_event]):
			result = game.input_controller.poll()
		assert result is True
		assert game.app_state.is_gameover()
		assert game.app_state.gameover_result == 'win'

		# Simulate Enter to restart (back to menu)
		enter_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN})
		with mock.patch('pygame.event.get', return_value=[enter_event]):
			result = game.input_controller.poll()
		assert result is True
		assert game.app_state.is_menu()
		assert game.peeps == []  # reset_game cleared them
	finally:
		pygame.quit()


def test_escape_pauses_game():
	"""In PLAYING state, Escape pauses the game."""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.spawn_initial_peeps(1)

		# Simulate Escape to pause
		escape_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
		with mock.patch('pygame.event.get', return_value=[escape_event]):
			result = game.input_controller.poll()
		assert result is True
		assert game.app_state.is_paused()
	finally:
		pygame.quit()


def test_escape_resumes_from_pause():
	"""In PAUSED state, Escape resumes the game."""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.spawn_initial_peeps(1)
		game.app_state.transition_to(game.app_state.PAUSED)

		# Simulate Escape to resume
		escape_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
		with mock.patch('pygame.event.get', return_value=[escape_event]):
			result = game.input_controller.poll()
		assert result is True
		assert game.app_state.is_playing()
	finally:
		pygame.quit()


def test_q_returns_to_menu_from_paused():
	"""In PAUSED state, Q returns to MENU."""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.spawn_initial_peeps(1)
		game.app_state.transition_to(game.app_state.PAUSED)

		# Simulate Q
		q_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_q})
		with mock.patch('pygame.event.get', return_value=[q_event]):
			result = game.input_controller.poll()
		assert result is True
		assert game.app_state.is_menu()
		assert game.peeps == []
	finally:
		pygame.quit()


def test_f10_triggers_lose():
	"""F10 in PLAYING state triggers LOSE condition."""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.spawn_initial_peeps(1)

		# Simulate F10 (lose)
		f10_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_F10})
		with mock.patch('pygame.event.get', return_value=[f10_event]):
			result = game.input_controller.poll()
		assert result is True
		assert game.app_state.is_gameover()
		assert game.app_state.gameover_result == 'lose'
	finally:
		pygame.quit()


def test_menu_left_click_starts_game():
	"""In MENU state, a left-click starts the game (Bug 1 fix)."""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()
		assert game.app_state.is_menu()

		# Simulate left-click on the menu screen.
		click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (400, 300)})
		with mock.patch('pygame.event.get', return_value=[click_event]):
			with mock.patch('pygame.mouse.get_pos', return_value=(400, 300)):
				result = game.input_controller.poll()
		# Click should transition to PLAYING and not request quit.
		assert game.app_state.is_playing()
		assert result is True
	finally:
		pygame.quit()


def test_gameover_state_q_returns_to_menu():
	"""In GAMEOVER state, Q returns to MENU."""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.spawn_initial_peeps(1)
		game.app_state.transition_to(game.app_state.GAMEOVER)
		game.app_state.gameover_result = 'win'

		# Simulate Q
		q_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_q})
		with mock.patch('pygame.event.get', return_value=[q_event]):
			result = game.input_controller.poll()
		assert result is True
		assert game.app_state.is_menu()
	finally:
		pygame.quit()


def test_reset_clears_knight_state_and_score():
	"""Resetting the game should clear promoted knights and score."""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.spawn_initial_peeps(5)
		result = game.power_manager.activate('knight', None)
		assert result.success
		assert game.score == 150
		assert any(getattr(p, 'weapon_type', None) == 'knight' for p in game.peeps)

		game._reset_game()

		assert game.score == 0
		assert not any(getattr(p, 'weapon_type', None) == 'knight' for p in game.peeps)
		assert game.input_controller._find_knight_cursor == -1
		assert game.input_controller._find_battle_cursor == -1
	finally:
		pygame.quit()


def test_new_game_starts_knight_cycle_from_beginning():
	"""A fresh session should not inherit find-knight cursor state."""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.spawn_initial_peeps(6)
		game.spawn_enemy_peeps(2)
		assert game.power_manager.activate('knight', None).success
		game.input_controller._handle_find_knight()
		assert game.input_controller._find_knight_cursor != -1

		game.app_state.transition_to(game.app_state.PAUSED)
		game._reset_game()
		assert game.input_controller._find_knight_cursor == -1
		assert game.input_controller._find_battle_cursor == -1
		game.app_state.transition_to(game.app_state.MENU)
		game.app_state.transition_to(game.app_state.PLAYING)
		game.spawn_initial_peeps(6)
		game.spawn_enemy_peeps(2)
		assert game.power_manager.activate('knight', None).success
		game.input_controller._handle_find_knight()

		assert game.input_controller._find_knight_cursor >= 0
	finally:
		pygame.quit()
