"""Smoke tests for mode_manager module."""

import populous_game.mode_manager as mode_manager


def test_mode_manager_class_exists():
	"""Verify ModeManager class exists."""
	assert hasattr(mode_manager, 'ModeManager')


def test_mode_manager_initialization():
	"""Verify ModeManager initializes correctly."""
	mgr = mode_manager.ModeManager()
	assert mgr.papal_mode is False
	assert mgr.shield_mode is False
	assert mgr.papal_position is not None
	assert mgr.dpad_held_direction is None
	assert mgr.dpad_held_timer == 0.0


def test_mode_manager_toggle_papal():
	"""Verify papal mode can be toggled."""
	mgr = mode_manager.ModeManager()
	assert mgr.papal_mode is False
	mgr.toggle_papal()
	assert mgr.papal_mode is True
	mgr.toggle_papal()
	assert mgr.papal_mode is False


def test_mode_manager_toggle_shield():
	"""Verify shield mode can be toggled."""
	mgr = mode_manager.ModeManager()
	assert mgr.shield_mode is False
	mgr.toggle_shield()
	assert mgr.shield_mode is True
	mgr.toggle_shield()
	assert mgr.shield_mode is False


def test_mode_manager_clear_modes():
	"""Verify modes can be cleared."""
	mgr = mode_manager.ModeManager()
	mgr.papal_mode = True
	mgr.shield_mode = True
	mgr.clear_modes()
	assert mgr.papal_mode is False
	assert mgr.shield_mode is False
