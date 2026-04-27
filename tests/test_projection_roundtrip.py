"""M6 ViewportTransform parity: projection round-trip across (preset, N).

Patch 9 parity gate. For every (preset, visible_tile_count) candidate
the M6 plan supports, build a Layout + ViewportTransform with a
center camera and confirm that projection and inversion round-trip
exactly in float arithmetic, and within one tile in integer
arithmetic, for a representative sweep of world points.

The existing `tests/test_viewport_transform.py` exercises a smaller
sweep (one visible-tile count per preset). This file is the broader
preset x visible_tiles parity gate; together with the tests in
`tests/test_layout_terrain_centered_in_well.py` it locks the iso
math down before Patch 10 flips the default canvas preset.
"""

# Standard Library
import math

# PIP3 modules
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


def _center_camera(visible_tiles: int) -> _FakeCamera:
	"""Camera at the production-init position for the active preset."""
	half = visible_tiles // 2
	cr = float(settings.GRID_HEIGHT // 2 - half)
	cc = float(settings.GRID_WIDTH // 2 - half)
	return _FakeCamera(cr, cc)


def _sample_world_points(camera: _FakeCamera, visible_tiles: int) -> list:
	"""Return 12 representative (row, col) sample points.

	Mix of viewport corners, interior points, and edge midpoints so
	round-trip parity is exercised across the full visible region.
	"""
	cr = camera.r
	cc = camera.c
	n = float(visible_tiles)
	points = [
		# Four diamond corners of the visible NxN region.
		(cr,           cc),
		(cr,           cc + n),
		(cr + n,       cc),
		(cr + n,       cc + n),
		# Four diagonal interior points.
		(cr + n * 0.25, cc + n * 0.25),
		(cr + n * 0.25, cc + n * 0.75),
		(cr + n * 0.75, cc + n * 0.25),
		(cr + n * 0.75, cc + n * 0.75),
		# Four edge midpoints.
		(cr,           cc + n / 2),
		(cr + n,       cc + n / 2),
		(cr + n / 2,   cc),
		(cr + n / 2,   cc + n),
	]
	return points


#============================================
# Float round-trip exactness
#============================================


@pytest.mark.parametrize("preset,visible_tiles", [
	('classic', 8),
	('remaster', 8), ('remaster', 10), ('remaster', 12),
	('remaster', 14), ('remaster', 16),
	('large', 16), ('large', 20), ('large', 24),
	('large', 28), ('large', 32),
])
def test_float_round_trip(preset, visible_tiles):
	"""screen_to_world(world_to_screen_float(r, c)) == (r, c) within 1e-9."""
	original = settings.ACTIVE_CANVAS_PRESET
	original_w = settings.INTERNAL_WIDTH
	original_h = settings.INTERNAL_HEIGHT
	original_s = settings.HUD_SCALE
	original_n = settings.VISIBLE_TILE_COUNT
	original_t = settings.TERRAIN_SCALE
	try:
		_set_preset(preset)
		ly = layout.active_layout()
		camera = _center_camera(visible_tiles)
		vt = layout.build_viewport_transform(ly, camera, visible_tiles)
		for row, col in _sample_world_points(camera, visible_tiles):
			x, y = vt.world_to_screen_float(row, col)
			r2, c2 = vt.screen_to_world(x, y)
			assert math.isclose(r2, row, abs_tol=1e-9), (
				f"{preset} N={visible_tiles} float row mismatch: "
				f"r2={r2} row={row}"
			)
			assert math.isclose(c2, col, abs_tol=1e-9), (
				f"{preset} N={visible_tiles} float col mismatch: "
				f"c2={c2} col={col}"
			)
	finally:
		settings.ACTIVE_CANVAS_PRESET = original
		settings.INTERNAL_WIDTH = original_w
		settings.INTERNAL_HEIGHT = original_h
		settings.HUD_SCALE = original_s
		settings.VISIBLE_TILE_COUNT = original_n
		settings.TERRAIN_SCALE = original_t


#============================================
# Integer round-trip tile-tolerance
#============================================


@pytest.mark.parametrize("preset,visible_tiles", [
	('classic', 8),
	('remaster', 8), ('remaster', 10), ('remaster', 12),
	('remaster', 14), ('remaster', 16),
	('large', 16), ('large', 20), ('large', 24),
	('large', 28), ('large', 32),
])
def test_int_round_trip(preset, visible_tiles):
	"""screen_to_world(world_to_screen(r, c)) recovers (r, c) within one tile."""
	original = settings.ACTIVE_CANVAS_PRESET
	original_w = settings.INTERNAL_WIDTH
	original_h = settings.INTERNAL_HEIGHT
	original_s = settings.HUD_SCALE
	original_n = settings.VISIBLE_TILE_COUNT
	original_t = settings.TERRAIN_SCALE
	try:
		_set_preset(preset)
		ly = layout.active_layout()
		camera = _center_camera(visible_tiles)
		vt = layout.build_viewport_transform(ly, camera, visible_tiles)
		for row, col in _sample_world_points(camera, visible_tiles):
			x, y = vt.world_to_screen(row, col)
			r2, c2 = vt.screen_to_world(x, y)
			# After integer rounding in world_to_screen there is up
			# to one tile of slack near tile boundaries; allow 1.
			assert abs(round(r2) - round(row)) <= 1, (
				f"{preset} N={visible_tiles} int row mismatch: "
				f"r2={r2} row={row}"
			)
			assert abs(round(c2) - round(col)) <= 1, (
				f"{preset} N={visible_tiles} int col mismatch: "
				f"c2={c2} col={col}"
			)
	finally:
		settings.ACTIVE_CANVAS_PRESET = original
		settings.INTERNAL_WIDTH = original_w
		settings.INTERNAL_HEIGHT = original_h
		settings.HUD_SCALE = original_s
		settings.VISIBLE_TILE_COUNT = original_n
		settings.TERRAIN_SCALE = original_t
