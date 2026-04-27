"""Test fast-forward toggle functionality.

Patch M7.5: Fast-forward toggle with time_scale.
"""

import pytest
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from populous_game.game import Game


@pytest.fixture
def game():
	"""Boot game to PLAYING state."""
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.spawn_initial_peeps(5)
	return game


def test_fast_forward_toggle_on(game):
	"""Pressing fast-forward key (backtick) toggles time_scale to 4.0."""
	assert game.app_state.time_scale == 1.0
	assert game.keymap['fast_forward'] == '`'

	# Simulate backtick key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKQUOTE, unicode='`')
	pygame.event.post(event)

	game.input_controller.poll()

	assert game.app_state.time_scale == 4.0


def test_fast_forward_toggle_off(game):
	"""Pressing fast-forward key again toggles time_scale back to 1.0."""
	game.app_state.time_scale = 4.0

	# Simulate backtick key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKQUOTE, unicode='`')
	pygame.event.post(event)

	game.input_controller.poll()

	assert game.app_state.time_scale == 1.0


def test_fast_forward_affects_simulation_speed(game):
	"""Simulation advances faster when time_scale is 4.0."""
	# Record initial peep positions
	initial_peeps = [{'x': p.x, 'y': p.y} for p in game.peeps]

	# Run a single update tick at normal speed
	game.update(0.016)  # ~16ms = 1 frame at 60 FPS
	positions_after_normal = [{'x': p.x, 'y': p.y} for p in game.peeps]

	# Reset peeps to initial positions
	for i, p in enumerate(game.peeps):
		p.x = initial_peeps[i]['x']
		p.y = initial_peeps[i]['y']

	# Enable fast-forward
	game.app_state.time_scale = 4.0

	# Run a single update tick at 4x speed (dt * 4)
	game.update(0.064)  # 16ms * 4 = 64ms worth of simulation
	positions_after_fast = [{'x': p.x, 'y': p.y} for p in game.peeps]

	# Verify they match (same computation elapsed time)
	# Allow small floating point differences
	for i, fast_pos in enumerate(positions_after_fast):
		normal_pos = positions_after_normal[i]
		assert abs(fast_pos['x'] - normal_pos['x']) < 0.1, \
			f"Peep {i} x position differs more than expected"
		assert abs(fast_pos['y'] - normal_pos['y']) < 0.1, \
			f"Peep {i} y position differs more than expected"


def test_fast_forward_not_active_in_menu(game):
	"""Fast-forward key should not toggle in MENU state."""
	# Transition to paused, then to menu (valid transition)
	game.app_state.transition_to(game.app_state.PAUSED)
	game._reset_game()
	game.app_state.transition_to(game.app_state.MENU)

	assert game.app_state.time_scale == 1.0

	# Simulate backtick key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKQUOTE, unicode='`')
	pygame.event.post(event)

	game.input_controller.poll()

	# time_scale should NOT change
	assert game.app_state.time_scale == 1.0


def test_fast_forward_not_active_during_confirm_dialog(game):
	"""Fast-forward key should not toggle while confirm dialog is open."""
	game.app_state.request_confirm("Test?", lambda: None)
	assert game.app_state.time_scale == 1.0

	# Simulate backtick key press
	event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKQUOTE, unicode='`')
	pygame.event.post(event)

	game.input_controller.poll()

	# time_scale should NOT change
	assert game.app_state.time_scale == 1.0
