"""Per-preset canvas layout sanity checks (M4 WP-M4-D).

For each canvas preset, verify three boundary rules:

1. The captured `internal_surface` matches `(INTERNAL_WIDTH, INTERNAL_HEIGHT)`.
2. Every UI button center, in canvas-pixel coordinates (logical * HUD_SCALE),
   lies inside the canvas rectangle.
3. The minimap's bounding rectangle, scaled to canvas pixels, fits inside
   the canvas rectangle.

These guard against off-canvas drift if HUD_SCALE or button geometry
changes break alignment at a non-classic preset.
"""

# local repo modules
import populous_game.settings as settings
import tools.headless_runner as runner


def _set_preset(name):
	"""Mutate the four mirror constants in settings to match a preset."""
	preset = settings.CANVAS_PRESETS[name]
	settings.ACTIVE_CANVAS_PRESET = name
	settings.INTERNAL_WIDTH = preset[0]
	settings.INTERNAL_HEIGHT = preset[1]
	settings.HUD_SCALE = preset[2]
	settings.VISIBLE_TILE_COUNT = preset[3]


def _check_layout_for_preset(name):
	"""Boot a Game at the preset and assert canvas/button/minimap bounds."""
	original = settings.ACTIVE_CANVAS_PRESET
	try:
		_set_preset(name)
		game = runner.boot_game_for_tests(state='gameplay', seed=9999,
			players=2, enemies=2)
		w = settings.INTERNAL_WIDTH
		h = settings.INTERNAL_HEIGHT
		scale = settings.HUD_SCALE
		# Internal surface size must match the active preset.
		surf_w, surf_h = game.internal_surface.get_size()
		assert (surf_w, surf_h) == (w, h), (
			f"internal_surface size {(surf_w, surf_h)} != preset {(w, h)} "
			f"for preset={name}"
		)
		# Every button center, scaled to canvas px, must be inside the canvas.
		for action, btn in game.ui_panel.buttons.items():
			cx, cy = btn['c']
			canvas_x = cx * scale
			canvas_y = cy * scale
			assert 0 <= canvas_x < w and 0 <= canvas_y < h, (
				f"Button {action!r} center {(canvas_x, canvas_y)} outside "
				f"canvas {(w, h)} at preset={name}"
			)
		# Minimap rect, scaled to canvas px, must fit inside the canvas.
		mm = game.minimap
		mm_x_canvas = mm.x * scale
		mm_y_canvas = mm.y * scale
		mm_w_canvas = mm.width * scale
		mm_h_canvas = mm.height * scale
		assert (mm_x_canvas >= 0 and mm_y_canvas >= 0
			and mm_x_canvas + mm_w_canvas <= w
			and mm_y_canvas + mm_h_canvas <= h), (
			f"Minimap rect ({mm_x_canvas},{mm_y_canvas},"
			f"{mm_w_canvas}x{mm_h_canvas}) does not fit canvas {(w, h)} "
			f"at preset={name}"
		)
	finally:
		_set_preset(original)


def test_classic_canvas_layout():
	"""Classic preset: internal_surface, buttons, minimap inside 320x200."""
	_check_layout_for_preset('classic')


def test_remaster_canvas_layout():
	"""Remaster preset: internal_surface, buttons, minimap inside 640x400."""
	_check_layout_for_preset('remaster')


def test_large_canvas_layout():
	"""Large preset: internal_surface, buttons, minimap inside 1280x800."""
	_check_layout_for_preset('large')
