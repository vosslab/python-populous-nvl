"""Test power hotkey activation.

Patch M7.4: Power hotkeys using keymap.
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
	game.spawn_initial_peeps(5)
	return game


def test_volcano_hotkey_sets_pending_power(game):
	"""Pressing V (volcano hotkey) sets pending_power = 'volcano'."""
	assert game.mode_manager.pending_power is None
	assert game.keymap['power_volcano'] == 'v'

	# Simulate V key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v)
	pygame.event.post(event)

	game.input_controller.poll()

	assert game.mode_manager.pending_power == 'volcano'


def test_flood_hotkey_sets_pending_power(game):
	"""Pressing F (flood hotkey) sets pending_power = 'flood'."""
	assert game.mode_manager.pending_power is None
	assert game.keymap['power_flood'] == 'f'

	# Simulate F key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f)
	pygame.event.post(event)

	game.input_controller.poll()

	assert game.mode_manager.pending_power == 'flood'


def test_knight_hotkey_activates_immediately(game):
	"""Pressing K (knight hotkey) activates knight immediately."""
	assert game.keymap['power_knight'] == 'k'

	# Mock activate to track calls
	game.power_manager.activate = Mock(return_value=Mock(success=True))

	# Simulate K key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k)
	pygame.event.post(event)

	game.input_controller.poll()

	# activate should be called with 'knight' and None
	game.power_manager.activate.assert_called_once_with('knight', None)


def test_knight_button_routes_through_same_activation_path(game):
	"""Clicking the knight button should call the same activation path as K."""
	game.power_manager.activate = Mock(return_value=Mock(success=True))

	game.input_controller._handle_ui_click('_do_knight', held=False)

	game.power_manager.activate.assert_called_once_with('knight', None)


def test_papal_hotkey_activates_immediately(game):
	"""Pressing P (papal hotkey) activates papal immediately."""
	assert game.keymap['power_papal'] == 'p'

	# Mock activate to track calls
	game.power_manager.activate = Mock(return_value=Mock(success=True))

	# Simulate P key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p)
	pygame.event.post(event)

	game.input_controller.poll()

	# activate should be called with 'papal'
	game.power_manager.activate.assert_called_once()
	call_args = game.power_manager.activate.call_args
	assert call_args[0][0] == 'papal'


def test_hotkeys_ignored_in_menu(game):
	"""Hotkeys should not trigger while in MENU state."""
	# Transition through proper state flow: PLAYING -> PAUSED -> MENU
	game.app_state.transition_to(game.app_state.PAUSED)
	game._reset_game()
	game.app_state.transition_to(game.app_state.MENU)
	assert game.mode_manager.pending_power is None

	# Simulate V key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v, unicode='v')
	pygame.event.post(event)

	game.input_controller.poll()

	# pending_power should NOT be set
	assert game.mode_manager.pending_power is None


def test_hotkeys_ignored_during_confirm_dialog(game):
	"""Hotkeys should not trigger while confirm dialog is open."""
	game.app_state.request_confirm("Test?", lambda: None)
	assert game.mode_manager.pending_power is None

	# Simulate V key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v)
	pygame.event.post(event)

	game.input_controller.poll()

	# pending_power should NOT be set
	assert game.mode_manager.pending_power is None


def test_hotkeys_respect_keymap_changes(game):
	"""Changing keymap changes which key triggers the power."""
	# Change the keymap: volcano -> 'b' instead of 'v'
	game.keymap['power_volcano'] = 'b'

	# Pressing V should NOT set pending power
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v, unicode='v')
	pygame.event.post(event)
	game.input_controller.poll()
	assert game.mode_manager.pending_power is None

	# Pressing B should set pending power
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, unicode='b')
	pygame.event.post(event)
	game.input_controller.poll()
	assert game.mode_manager.pending_power == 'volcano'
