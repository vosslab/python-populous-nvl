"""Smoke tests for mode_manager module."""

import populous_game.mode_manager as mode_manager
import populous_game.faction as faction


def test_mode_manager_class_exists():
	"""Verify ModeManager class exists."""
	assert hasattr(mode_manager, 'ModeManager')


def test_mode_manager_initialization():
	"""Verify ModeManager initializes correctly."""
	mgr = mode_manager.ModeManager()
	assert mgr.papal_mode is False
	assert mgr.shield_mode is False
	assert mgr.papal_position is not None
	assert mgr.faction_magnets[faction.Faction.PLAYER] == mgr.papal_position
	assert mgr.faction_magnets[faction.Faction.ENEMY] is None
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


def test_mode_manager_updates_player_magnet_with_papal_position():
	"""Papal placement updates the player faction magnet slot."""
	mgr = mode_manager.ModeManager()
	mgr.set_papal_position(8, 9)
	assert mgr.papal_position == (7, 8)
	assert mgr.faction_magnets[faction.Faction.PLAYER] == (7, 8)
	assert mgr.papal_mode is False


def test_mode_manager_clear_magnets():
	"""Faction magnet table can be cleared on game reset."""
	mgr = mode_manager.ModeManager()
	mgr.set_faction_magnet(faction.Faction.PLAYER, 4, 5)
	mgr.set_faction_magnet(faction.Faction.ENEMY, 6, 7)
	mgr.clear_magnets()
	assert mgr.papal_position is None
	assert mgr.faction_magnets[faction.Faction.PLAYER] is None
	assert mgr.faction_magnets[faction.Faction.ENEMY] is None
