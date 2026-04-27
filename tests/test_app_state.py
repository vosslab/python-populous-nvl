"""Tests for AppState (game state machine).

Covers state transitions, allowed transitions, disallowed transitions, and
state query methods.
"""

import pytest
import populous_game.app_state as app_state


def test_app_state_initial_state():
	"""AppState starts in MENU state."""
	state = app_state.AppState()
	assert state.current == app_state.AppState.MENU
	assert state.is_menu()
	assert not state.is_playing()
	assert not state.is_paused()
	assert not state.is_gameover()


def test_app_state_menu_to_playing():
	"""MENU -> PLAYING transition is allowed."""
	state = app_state.AppState()
	state.transition_to(app_state.AppState.PLAYING)
	assert state.current == app_state.AppState.PLAYING
	assert state.is_playing()


def test_app_state_playing_to_paused():
	"""PLAYING -> PAUSED transition is allowed."""
	state = app_state.AppState()
	state.transition_to(app_state.AppState.PLAYING)
	state.transition_to(app_state.AppState.PAUSED)
	assert state.current == app_state.AppState.PAUSED
	assert state.is_paused()


def test_app_state_paused_to_playing():
	"""PAUSED -> PLAYING transition is allowed."""
	state = app_state.AppState()
	state.transition_to(app_state.AppState.PLAYING)
	state.transition_to(app_state.AppState.PAUSED)
	state.transition_to(app_state.AppState.PLAYING)
	assert state.is_playing()


def test_app_state_playing_to_gameover():
	"""PLAYING -> GAMEOVER transition is allowed."""
	state = app_state.AppState()
	state.transition_to(app_state.AppState.PLAYING)
	state.transition_to(app_state.AppState.GAMEOVER)
	assert state.is_gameover()


def test_app_state_gameover_to_menu():
	"""GAMEOVER -> MENU transition is allowed."""
	state = app_state.AppState()
	state.transition_to(app_state.AppState.PLAYING)
	state.transition_to(app_state.AppState.GAMEOVER)
	state.transition_to(app_state.AppState.MENU)
	assert state.is_menu()


def test_app_state_paused_to_menu():
	"""PAUSED -> MENU transition is allowed."""
	state = app_state.AppState()
	state.transition_to(app_state.AppState.PLAYING)
	state.transition_to(app_state.AppState.PAUSED)
	state.transition_to(app_state.AppState.MENU)
	assert state.is_menu()


def test_app_state_menu_to_paused_disallowed():
	"""MENU -> PAUSED transition is not allowed."""
	state = app_state.AppState()
	with pytest.raises(ValueError):
		state.transition_to(app_state.AppState.PAUSED)


def test_app_state_menu_to_gameover_disallowed():
	"""MENU -> GAMEOVER transition is not allowed."""
	state = app_state.AppState()
	with pytest.raises(ValueError):
		state.transition_to(app_state.AppState.GAMEOVER)


def test_app_state_playing_to_menu_disallowed():
	"""PLAYING -> MENU transition is not allowed."""
	state = app_state.AppState()
	state.transition_to(app_state.AppState.PLAYING)
	with pytest.raises(ValueError):
		state.transition_to(app_state.AppState.MENU)


def test_app_state_paused_to_gameover_disallowed():
	"""PAUSED -> GAMEOVER transition is not allowed."""
	state = app_state.AppState()
	state.transition_to(app_state.AppState.PLAYING)
	state.transition_to(app_state.AppState.PAUSED)
	with pytest.raises(ValueError):
		state.transition_to(app_state.AppState.GAMEOVER)


def test_app_state_gameover_result_none_initially():
	"""gameover_result is None initially."""
	state = app_state.AppState()
	assert state.gameover_result is None


def test_app_state_gameover_result_can_be_set():
	"""gameover_result can be set to 'win' or 'lose'."""
	state = app_state.AppState()
	state.gameover_result = 'win'
	assert state.gameover_result == 'win'

	state.gameover_result = 'lose'
	assert state.gameover_result == 'lose'
