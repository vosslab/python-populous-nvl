"""Diagnostic-overlay sanity test for M6 Patch 8 --debug-layout.

Boots a game with debug_layout enabled, steps one frame, and samples
the internal surface to confirm the overlay's reference pixels land at
the geometric anchors derived from the live ViewportTransform.

The assertions are intentionally tolerant (small neighborhood scans)
because pygame.draw.rect with width=1 paints a 1 px outline that may
be biased by half-pixel rounding at non-classic presets.
"""

# Standard Library
import os

# PIP3 modules
import pygame

# local repo modules
import tools.headless_runner as runner


#============================================
# Helpers
#============================================


def _color_in_neighborhood(surface, x: int, y: int, target: tuple, radius: int = 1) -> bool:
	"""Return True if `target` RGB appears in a (2*radius+1) box at (x, y).

	Clipped to the surface bounds. Used so a 1 px line drawn at a
	subpixel-rounded position still triggers a positive sample.
	"""
	w, h = surface.get_size()
	for dy in range(-radius, radius + 1):
		for dx in range(-radius, radius + 1):
			px = x + dx
			py = y + dy
			# Skip out-of-bounds samples instead of raising; some
			# button rects sit at the canvas edge.
			if px < 0 or py < 0 or px >= w or py >= h:
				continue
			if surface.get_at((px, py))[:3] == target:
				return True
	return False


#============================================
# Tests
#============================================


def test_anchor_pixel_is_magenta():
	"""3x3 magenta square is painted at the ViewportTransform anchor."""
	# SDL_VIDEODRIVER is set by tests/conftest.py; safety net for direct runs.
	os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
	os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
	game = runner.boot_game_for_tests(state='gameplay', seed=4242, players=2, enemies=2)
	game.debug_layout = True
	runner.step_frames(game, n=1)
	surface = game.internal_surface.copy()
	transform = game.viewport_transform
	# The anchor square is exactly 3x3 painted at (anchor-1, anchor-1).
	# Sampling the central pixel must hit magenta.
	pixel = surface.get_at((transform.anchor_x, transform.anchor_y))[:3]
	assert pixel == (255, 0, 255), (
		f"expected magenta at anchor "
		f"({transform.anchor_x}, {transform.anchor_y}), got {pixel}"
	)


def test_map_well_outline_is_cyan():
	"""The map-well rect outline paints cyan along its boundary."""
	os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
	os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
	game = runner.boot_game_for_tests(state='gameplay', seed=4243, players=2, enemies=2)
	game.debug_layout = True
	runner.step_frames(game, n=1)
	surface = game.internal_surface.copy()
	rect = game.layout.map_well_rect
	# Sample points around the rect perimeter; with a 1 px tolerance
	# neighborhood at least one sample at each must hit cyan. Avoid
	# the corners (overlay corners stack) AND the top/bottom edge
	# midpoints where the iso diamond's top/bottom apex lands -- after
	# the M6 centering fix, the magenta anchor square sits exactly at
	# (rect.centerx, rect.top) and the bottom-apex tile center can
	# paint a red dot at (rect.centerx, rect.bottom - 1).
	cyan = (0, 200, 255)
	# Quarter-points on top/bottom edges + edge midpoints on
	# left/right edges. Each is on the cyan outline but well clear of
	# the iso apex coordinates.
	samples = (
		(rect.left + rect.width // 4, rect.top),
		(rect.right - 1 - rect.width // 4, rect.bottom - 1),
		(rect.left, rect.centery),
		(rect.right - 1, rect.centery),
	)
	for sx, sy in samples:
		assert _color_in_neighborhood(surface, sx, sy, cyan, radius=1), (
			f"expected cyan map-well outline near ({sx}, {sy})"
		)


def test_visible_tile_centers_are_red():
	"""At least one visible tile center renders as a red pixel."""
	os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
	os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
	game = runner.boot_game_for_tests(state='gameplay', seed=4244, players=2, enemies=2)
	game.debug_layout = True
	runner.step_frames(game, n=1)
	surface = game.internal_surface.copy()
	transform = game.viewport_transform
	# Probe four tiles inside the camera viewport. Tile altitudes are
	# random; the overlay accounts for altitude, so sampling at the
	# corner altitude reproduces the same projection. Use radius=1 to
	# tolerate sub-pixel rounding.
	cam_r = int(transform.camera_row)
	cam_c = int(transform.camera_col)
	red = (255, 0, 0)
	# Pick 4 tiles a couple steps in from the edge so the projection
	# stays within the canvas at every preset.
	probes = (
		(cam_r + 1, cam_c + 1),
		(cam_r + 2, cam_c + 1),
		(cam_r + 1, cam_c + 2),
		(cam_r + 2, cam_c + 2),
	)
	hits = 0
	for r, c in probes:
		alt = game.game_map.get_corner_altitude(r, c)
		if alt < 0:
			alt = 0
		sx, sy = transform.world_to_screen(r + 0.5, c + 0.5, alt)
		if _color_in_neighborhood(surface, sx, sy, red, radius=1):
			hits += 1
	assert hits >= 3, (
		f"expected >= 3 red tile-center pixels in 4 probes, got {hits}"
	)


def test_overlay_disabled_by_default():
	"""With debug_layout False, the magenta anchor pixel is NOT painted."""
	os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
	os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
	game = runner.boot_game_for_tests(state='gameplay', seed=4245, players=2, enemies=2)
	# default-off
	assert game.debug_layout is False
	runner.step_frames(game, n=1)
	surface = game.internal_surface.copy()
	transform = game.viewport_transform
	# Without the overlay, the pixel at the anchor should NOT be the
	# overlay's pure-magenta. (It will be whatever terrain rendered.)
	pixel = surface.get_at((transform.anchor_x, transform.anchor_y))[:3]
	assert pixel != (255, 0, 255), (
		f"unexpected magenta at anchor with debug_layout disabled: {pixel}"
	)


# Suppress unused pygame import warning; some readers expect the
# top-level pygame to be live before any surface methods run.
_ = pygame
