"""Tests for UI button tooltips (M7)."""

import populous_game.settings as settings
import populous_game.ui_panel as ui_panel_module


class _StubGame:
	"""Minimal stub so UIPanel can construct."""
	pass


def test_button_tooltips_table_covers_powers():
	"""Power button tooltips exist for each power action."""
	for action in ('_do_papal', '_do_volcano', '_do_flood', '_do_quake', '_do_swamp', '_do_knight'):
		assert action in settings.BUTTON_TOOLTIPS
		assert settings.BUTTON_TOOLTIPS[action]


def test_tooltip_for_known_action_returns_string():
	"""tooltip_for() returns the configured text for known actions."""
	panel = ui_panel_module.UIPanel(_StubGame())
	text = panel.tooltip_for('_do_papal')
	assert isinstance(text, str)
	assert len(text) > 0


def test_tooltip_for_none_returns_none():
	"""tooltip_for() handles None action gracefully."""
	panel = ui_panel_module.UIPanel(_StubGame())
	assert panel.tooltip_for(None) is None
	assert panel.tooltip_for('not_a_real_action') is None


def test_hit_test_picks_closest_button_when_overlapping():
	"""When two diamond buttons would both qualify, the closer one wins.

	Regression: the previous hit_test returned the FIRST matching button in
	dict-iteration order, so clicks at the boundary between two buttons
	activated whichever was inserted first. The user reported clicking one
	button and getting another.
	"""
	panel = ui_panel_module.UIPanel(_StubGame())
	# Pick the exact center of a known button; that button must win
	target = '_do_volcano'
	cx, cy = panel.buttons[target]['c']
	assert panel.hit_test_button(cx, cy) == target


def test_hit_test_returns_none_far_outside_panel():
	"""A coordinate far from any button returns None."""
	panel = ui_panel_module.UIPanel(_StubGame())
	assert panel.hit_test_button(-9999, -9999) is None
