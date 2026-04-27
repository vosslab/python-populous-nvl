"""Smoke tests for renderer module."""

import populous_game.renderer as renderer


def test_renderer_class_exists():
	"""Verify Renderer class exists."""
	assert hasattr(renderer, 'Renderer')


def test_renderer_has_draw_frame():
	"""Verify Renderer has draw_frame method."""
	assert hasattr(renderer.Renderer, 'draw_frame')


def test_renderer_has_private_methods():
	"""Verify Renderer has key private drawing methods."""
	methods = dir(renderer.Renderer)
	assert '_draw_terrain' in methods
	assert '_draw_houses' in methods
	assert '_draw_peeps' in methods
	assert '_draw_papal_marker' in methods
	assert '_draw_cursor' in methods
	assert '_draw_minimap' in methods
