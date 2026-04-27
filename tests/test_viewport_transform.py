"""Tests for the M6 ViewportTransform foundation (Patch 2).

Covers:
- Float-precision round-trip exactness for `ViewportTransform`.
- Integer-rounded round-trip tile tolerance.
- `build_viewport_transform` centers the projected diamond bbox in the
  active map well.
- `max_visible_tiles_that_fit` selects the largest fitting N and
  degrades to `min(candidates)` when nothing fits.
- `Layout` and `ViewportTransform` are frozen dataclasses.

Per repo convention, the file mutates `populous_game.settings` to
exercise each canvas preset and restores the original preset in a
`try/finally` block.
"""

# Standard Library
import math
import dataclasses

# PIP3 modules
import pygame
import pytest

# local repo modules
import populous_game.layout as layout
import populous_game.settings as settings


#============================================
# Preset switching helpers
#============================================


def _set_preset(name: str) -> None:
	"""Mutate the five mirror constants in settings to match a preset."""
	preset = settings.CANVAS_PRESETS[name]
	settings.ACTIVE_CANVAS_PRESET = name
	settings.INTERNAL_WIDTH = preset[0]
	settings.INTERNAL_HEIGHT = preset[1]
	settings.HUD_SCALE = preset[2]
	settings.VISIBLE_TILE_COUNT = preset[3]
	settings.TERRAIN_SCALE = preset[4]


class _FakeCamera:
	"""Minimal duck-typed camera with `.r` / `.c` floats."""

	def __init__(self, r: float, c: float) -> None:
		self.r = float(r)
		self.c = float(c)


def _grid_center_camera() -> _FakeCamera:
	"""Camera at the center of the simulation grid."""
	cr = settings.GRID_HEIGHT / 2.0
	cc = settings.GRID_WIDTH / 2.0
	return _FakeCamera(cr, cc)


def _sweep_points(camera_r: float, camera_c: float, half: float) -> list:
	"""Sample of (row, col) points: four diamond corners + interior."""
	points = [
		(camera_r - half, camera_c - half),
		(camera_r - half, camera_c + half),
		(camera_r + half, camera_c - half),
		(camera_r + half, camera_c + half),
		(camera_r, camera_c),
		(camera_r + 0.25, camera_c - 0.5),
		(camera_r - 1.5, camera_c + 2.0),
		(camera_r + 3.0, camera_c + 0.0),
	]
	return points


#============================================
# Float round-trip exactness
#============================================


def _check_float_round_trip_for_preset(name: str) -> None:
	"""For one preset, every sweep point survives float round-trip."""
	original = settings.ACTIVE_CANVAS_PRESET
	try:
		_set_preset(name)
		ly = layout.active_layout()
		# Pick a tile budget that fits the well at this preset.
		visible = max(1, ly.map_well_rect.width // ly.tile_w)
		camera = _grid_center_camera()
		vt = layout.build_viewport_transform(ly, camera, visible)
		half = visible / 2.0
		for row, col in _sweep_points(camera.r, camera.c, half):
			x, y = vt.world_to_screen_float(row, col)
			r2, c2 = vt.screen_to_world(x, y)
			assert math.isclose(r2, row, abs_tol=1e-9)
			assert math.isclose(c2, col, abs_tol=1e-9)
	finally:
		_set_preset(original)


def test_float_round_trip_classic() -> None:
	"""Classic preset: float projection round-trips exactly."""
	_check_float_round_trip_for_preset('classic')


def test_float_round_trip_remaster() -> None:
	"""Remaster preset: float projection round-trips exactly."""
	_check_float_round_trip_for_preset('remaster')


def test_float_round_trip_large() -> None:
	"""Large preset: float projection round-trips exactly."""
	_check_float_round_trip_for_preset('large')


#============================================
# Integer round-trip tile-tolerance
#============================================


def _check_int_round_trip_for_preset(name: str) -> None:
	"""For one preset, integer round-trip lands within one tile."""
	original = settings.ACTIVE_CANVAS_PRESET
	try:
		_set_preset(name)
		ly = layout.active_layout()
		visible = max(1, ly.map_well_rect.width // ly.tile_w)
		camera = _grid_center_camera()
		vt = layout.build_viewport_transform(ly, camera, visible)
		half = visible / 2.0
		for row, col in _sweep_points(camera.r, camera.c, half):
			# Project to integer pixels (the blit pixel a renderer
			# would actually use), then invert.
			x, y = vt.world_to_screen(row, col)
			r2, c2 = vt.screen_to_world(x, y)
			assert abs(round(r2) - round(row)) <= 1
			assert abs(round(c2) - round(col)) <= 1
	finally:
		_set_preset(original)


def test_int_round_trip_classic() -> None:
	"""Classic preset: integer round-trip stays within one tile."""
	_check_int_round_trip_for_preset('classic')


def test_int_round_trip_remaster() -> None:
	"""Remaster preset: integer round-trip stays within one tile."""
	_check_int_round_trip_for_preset('remaster')


def test_int_round_trip_large() -> None:
	"""Large preset: integer round-trip stays within one tile."""
	_check_int_round_trip_for_preset('large')


#============================================
# build_viewport_transform: bbox-centering
#============================================


# Visible-tile candidates per preset. After the M6 chunky-pixels
# follow-up the visible-tile count is fixed at 8 across all presets;
# the larger presets show the SAME 8 tiles bigger, not more tiles.
_CENTERING_CANDIDATES = {
	'classic':  (8,),
	'remaster': (8,),
	'large':    (8,),
}


def _check_centering_for_preset(name: str) -> None:
	"""Diamond bbox center matches map_well center within 1 px."""
	original = settings.ACTIVE_CANVAS_PRESET
	try:
		_set_preset(name)
		ly = layout.active_layout()
		# Pick the largest diamond that still fits inside the well.
		visible = layout.max_visible_tiles_that_fit(
			ly.map_well_rect, ly.tile_w, ly.tile_h,
			_CENTERING_CANDIDATES[name],
		)
		camera = _grid_center_camera()
		vt = layout.build_viewport_transform(ly, camera, visible)
		# Project the four corners of the visible NxN viewport. Camera
		# stores top-left, so the visible bbox spans
		# (camera.r .. camera.r+N) x (camera.c .. camera.c+N). The
		# updated build_viewport_transform centers this bbox in the well.
		n = float(visible)
		corners = (
			(camera.r,     camera.c    ),
			(camera.r,     camera.c + n),
			(camera.r + n, camera.c    ),
			(camera.r + n, camera.c + n),
		)
		projected = [vt.world_to_screen_float(r, c) for r, c in corners]
		xs = [p[0] for p in projected]
		ys = [p[1] for p in projected]
		bbox_cx = (min(xs) + max(xs)) / 2.0
		bbox_cy = (min(ys) + max(ys)) / 2.0
		assert abs(bbox_cx - ly.map_well_rect.centerx) <= 1
		assert abs(bbox_cy - ly.map_well_rect.centery) <= 1
	finally:
		_set_preset(original)


def test_build_viewport_transform_centers_classic() -> None:
	"""Classic: the projected diamond bbox is centered in the map well."""
	_check_centering_for_preset('classic')


def test_build_viewport_transform_centers_remaster() -> None:
	"""Remaster: the projected diamond bbox is centered in the map well."""
	_check_centering_for_preset('remaster')


def test_build_viewport_transform_centers_large() -> None:
	"""Large: the projected diamond bbox is centered in the map well."""
	_check_centering_for_preset('large')


#============================================
# max_visible_tiles_that_fit unit tests
#============================================


def test_max_visible_tiles_returns_largest_fit() -> None:
	"""A 256x128 well fits N=8 (256x128) but not N=10 (320x160)."""
	well = pygame.Rect(0, 0, 256, 128)
	assert layout.max_visible_tiles_that_fit(well, 32, 16, [8, 10, 12]) == 8


def test_max_visible_tiles_falls_back_to_min_when_none_fit() -> None:
	"""When no candidate fits, return min(candidates)."""
	well = pygame.Rect(0, 0, 32, 16)
	# tile_w=32, tile_h=16: even N=8 yields a 256x128 bbox > 32x16.
	assert layout.max_visible_tiles_that_fit(well, 32, 16, [8, 10, 12]) == 8


#============================================
# Frozenness
#============================================


def test_layout_is_frozen() -> None:
	"""Assigning a Layout field raises FrozenInstanceError."""
	original = settings.ACTIVE_CANVAS_PRESET
	try:
		_set_preset('classic')
		ly = layout.active_layout()
		with pytest.raises(dataclasses.FrozenInstanceError):
			ly.tile_w = 99
	finally:
		_set_preset(original)


def test_viewport_transform_is_frozen() -> None:
	"""Assigning a ViewportTransform field raises FrozenInstanceError."""
	original = settings.ACTIVE_CANVAS_PRESET
	try:
		_set_preset('classic')
		ly = layout.active_layout()
		camera = _grid_center_camera()
		vt = layout.build_viewport_transform(ly, camera, 8)
		with pytest.raises(dataclasses.FrozenInstanceError):
			vt.anchor_x = 99
	finally:
		_set_preset(original)
