"""Test confirm dialog input handling.

Patch M7.2: Y/N keys trigger on_confirm/on_cancel.
"""

import pytest
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from unittest.mock import Mock
from populous_game.game import Game


@pytest.fixture
def game():
	"""Boot game to PLAYING state."""
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	return game


def test_confirm_dialog_input_yes(game):
	"""Pressing Y with confirm dialog open calls on_confirm."""
	mock_confirm = Mock()
	game.app_state.request_confirm("Test?", on_confirm=mock_confirm)
	assert game.app_state.has_confirm_dialog()

	# Simulate Y key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_y)
	pygame.event.post(event)

	# Poll events
	game.input_controller.poll()

	# Assert on_confirm was called
	mock_confirm.assert_called_once()
	# Dialog should be cleared
	assert not game.app_state.has_confirm_dialog()


def test_confirm_dialog_input_return(game):
	"""Pressing RETURN with confirm dialog open calls on_confirm."""
	mock_confirm = Mock()
	game.app_state.request_confirm("Test?", on_confirm=mock_confirm)
	assert game.app_state.has_confirm_dialog()

	# Simulate RETURN key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
	pygame.event.post(event)

	# Poll events
	game.input_controller.poll()

	# Assert on_confirm was called
	mock_confirm.assert_called_once()
	assert not game.app_state.has_confirm_dialog()


def test_confirm_dialog_input_no(game):
	"""Pressing N with confirm dialog open calls on_cancel."""
	mock_cancel = Mock()
	game.app_state.request_confirm("Test?", on_confirm=Mock(), on_cancel=mock_cancel)
	assert game.app_state.has_confirm_dialog()

	# Simulate N key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n)
	pygame.event.post(event)

	# Poll events
	game.input_controller.poll()

	# Assert on_cancel was called
	mock_cancel.assert_called_once()
	assert not game.app_state.has_confirm_dialog()


def test_confirm_dialog_input_escape(game):
	"""Pressing ESCAPE with confirm dialog open calls on_cancel."""
	mock_cancel = Mock()
	game.app_state.request_confirm("Test?", on_confirm=Mock(), on_cancel=mock_cancel)
	assert game.app_state.has_confirm_dialog()

	# Simulate ESCAPE key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
	pygame.event.post(event)

	# Poll events
	game.input_controller.poll()

	# Assert on_cancel was called
	mock_cancel.assert_called_once()
	assert not game.app_state.has_confirm_dialog()


def test_confirm_dialog_input_other_key_ignored(game):
	"""Other keys are ignored while confirm dialog is open."""
	mock_confirm = Mock()
	mock_cancel = Mock()
	game.app_state.request_confirm("Test?", on_confirm=mock_confirm, on_cancel=mock_cancel)
	assert game.app_state.has_confirm_dialog()

	# Simulate some random key press (e.g., 'A')
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
	pygame.event.post(event)

	# Poll events
	game.input_controller.poll()

	# Neither callback should be called
	mock_confirm.assert_not_called()
	mock_cancel.assert_not_called()
	# Dialog should still be open
	assert game.app_state.has_confirm_dialog()
