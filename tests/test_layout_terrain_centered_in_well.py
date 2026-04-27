"""M6 ViewportTransform parity: terrain diamond centered in map well.

Patch 9 parity gate. Builds a Layout + ViewportTransform for every
(preset, visible_tile_count) candidate the M6 plan supports and
asserts:

- The bounding box of the four projected diamond corners is centered
  on the active `map_well_rect` to within 2 pixels per axis (per the
  plan's section 4 done-checks).
- The bounding box width and height each cover at least 40% of the
  map well's width and height. The 40% floor was 70% prior to the
  M6 chunky-pixels follow-up; with TERRAIN_SCALE matched to HUD_SCALE
  per preset, the 8-tile diamond at remaster fills exactly half the
  well in each axis (8 tiles * 32 px = 256 canvas px vs a 512 px well).
  That is the EXPECTED Amiga look -- the original game's iso diamond
  did not fill the entire HUD well; it sat inside it with margin. 40%
  gives a 10% slack for rounding while still failing if the diamond
  drifts out of the well.

The test mutates `populous_game.settings` to switch presets and
restores the original preset state in a `try/finally` block so it
does not leak preset state across tests (see
`tests/test_canvas_size_compat.py` for the pattern).
"""

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
	"""Camera positioned so the diamond is centered on the grid.

	Mirrors `populous_game.camera.Camera.__init__`: the camera
	position tracks the top-left corner of the NxN visible diamond,
	so the visible viewport spans (cam_r, cam_c) .. (cam_r+N, cam_c+N)
	with center at (cam_r + N/2, cam_c + N/2).
	"""
	half = visible_tiles // 2
	cr = float(settings.GRID_HEIGHT // 2 - half)
	cc = float(settings.GRID_WIDTH // 2 - half)
	return _FakeCamera(cr, cc)


#============================================
# Visible-tile candidates per preset (M6 plan section 12)
#============================================


_CANDIDATES_BY_PRESET = {
	'classic':  (8,),
	'remaster': (8,),
	'large':    (8,),
}


#============================================
# Diamond-centered-in-well parity gate
#============================================


@pytest.mark.parametrize("preset,visible_tiles", [
	('classic', 8),
	('remaster', 8),
	('large', 8),
])
def test_diamond_centered_in_well(preset, visible_tiles):
	"""Projected NxN diamond bbox is centered in the well and fills >= 40%."""
	original = settings.ACTIVE_CANVAS_PRESET
	original_w = settings.INTERNAL_WIDTH
	original_h = settings.INTERNAL_HEIGHT
	original_s = settings.HUD_SCALE
	original_n = settings.VISIBLE_TILE_COUNT
	original_t = settings.TERRAIN_SCALE
	try:
		_set_preset(preset)
		ly = layout.active_layout()
		# Sanity: confirm the layout's tile_w tracks the preset's
		# terrain_scale (BASE_TILE_HALF_W * 2 * terrain_scale).
		expected_tile_w = settings.BASE_TILE_HALF_W * 2 * settings.CANVAS_PRESETS[preset][4]
		assert ly.tile_w == expected_tile_w, (
			f"{preset}: layout.tile_w={ly.tile_w} expected {expected_tile_w}"
		)
		camera = _center_camera(visible_tiles)
		vt = layout.build_viewport_transform(ly, camera, visible_tiles)
		# Project the four corners of the actual visible NxN viewport.
		# Camera stores top-left, so the visible bbox spans
		# (camera.r .. camera.r+N) x (camera.c .. camera.c+N). The
		# updated build_viewport_transform centers this bbox in the
		# well, so the test asserts what the player actually sees is
		# centered, not what an internal helper happens to project.
		n = float(visible_tiles)
		corners = (
			(camera.r,     camera.c    ),
			(camera.r,     camera.c + n),
			(camera.r + n, camera.c    ),
			(camera.r + n, camera.c + n),
		)
		projected = [vt.world_to_screen_float(r, c) for r, c in corners]
		xs = [p[0] for p in projected]
		ys = [p[1] for p in projected]
		min_x = min(xs)
		max_x = max(xs)
		min_y = min(ys)
		max_y = max(ys)
		bbox_cx = (min_x + max_x) / 2.0
		bbox_cy = (min_y + max_y) / 2.0
		# Section 4 done-check: bbox center matches well center to
		# within 2 px (build_viewport_transform rounds the anchor to
		# integer pixels, so a half-pixel slack is expected).
		assert abs(bbox_cx - ly.map_well_rect.centerx) <= 2, (
			f"{preset} N={visible_tiles}: bbox_cx={bbox_cx} "
			f"well.centerx={ly.map_well_rect.centerx}"
		)
		assert abs(bbox_cy - ly.map_well_rect.centery) <= 2, (
			f"{preset} N={visible_tiles}: bbox_cy={bbox_cy} "
			f"well.centery={ly.map_well_rect.centery}"
		)
		# Chunky-pixels acceptance: bbox width AND height each cover
		# at least 40% of the well. With TERRAIN_SCALE matched to
		# HUD_SCALE the 8-tile diamond fills exactly half the well
		# (8 * 32 = 256 canvas px, well = 256 * hud_scale, well *
		# hud_scale = 512). 40% gives a 10% slack for rounding while
		# still failing if the diamond drifts off-well.
		bbox_w = max_x - min_x
		bbox_h = max_y - min_y
		well_w = ly.map_well_rect.width
		well_h = ly.map_well_rect.height
		largest_fit = layout.max_visible_tiles_that_fit(
			ly.map_well_rect, ly.tile_w, ly.tile_h,
			_CANDIDATES_BY_PRESET[preset],
		)
		if visible_tiles == largest_fit:
			assert bbox_w >= 0.40 * well_w, (
				f"{preset} N={visible_tiles}: bbox_w={bbox_w} "
				f"well_w={well_w} ratio={bbox_w / well_w:.3f}"
			)
			assert bbox_h >= 0.40 * well_h, (
				f"{preset} N={visible_tiles}: bbox_h={bbox_h} "
				f"well_h={well_h} ratio={bbox_h / well_h:.3f}"
			)
	finally:
		settings.ACTIVE_CANVAS_PRESET = original
		settings.INTERNAL_WIDTH = original_w
		settings.INTERNAL_HEIGHT = original_h
		settings.HUD_SCALE = original_s
		settings.VISIBLE_TILE_COUNT = original_n
		settings.TERRAIN_SCALE = original_t
