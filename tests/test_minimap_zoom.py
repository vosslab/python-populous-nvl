"""Tests for minimap zoom (M7)."""

import populous_game.minimap as minimap_module
import populous_game.settings as settings


def test_default_zoom_is_one():
	"""A fresh minimap starts at zoom 1.0."""
	mm = minimap_module.Minimap()
	assert mm.zoom == settings.MINIMAP_ZOOM_DEFAULT


def test_set_zoom_clamps_high():
	"""Setting an absurdly high zoom clamps to MINIMAP_ZOOM_MAX."""
	mm = minimap_module.Minimap()
	mm.set_zoom(10.0)
	assert mm.zoom == settings.MINIMAP_ZOOM_MAX


def test_set_zoom_clamps_low():
	"""Setting a very low zoom clamps to MINIMAP_ZOOM_MIN."""
	mm = minimap_module.Minimap()
	mm.set_zoom(0.0)
	assert mm.zoom == settings.MINIMAP_ZOOM_MIN


def test_set_zoom_in_range():
	"""A normal zoom value within range is preserved."""
	mm = minimap_module.Minimap()
	mm.set_zoom(1.5)
	assert mm.zoom == 1.5
