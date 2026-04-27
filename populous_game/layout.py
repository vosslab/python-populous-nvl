"""Resolution-aware layout helpers (M4 canvas modernization).

The remaster supports a 320x200 (`classic`), 640x400 (`remaster`), or
1280x800 (`large`) internal canvas. Logical UI coordinate space stays
320x200 in every preset; presentation scales by `HUD_SCALE` at
blit time.

Helpers in this module return rectangles and coordinates in the
INTERNAL canvas pixel space (i.e., already multiplied by HUD_SCALE),
so the renderer can blit directly without doing the math itself. The
goal is to keep `populous_game/game.py`, `renderer.py`, `terrain.py`,
`ui_panel.py`, and `input_controller.py` free of bare 320 / 200
constants.

Functions are pure: they read `populous_game.settings` only. Tests can
mutate `settings.ACTIVE_CANVAS_PRESET` and re-import to exercise every
preset without rebuilding a Game instance.
"""

import populous_game.settings as settings


#============================================
# Active-preset resolution
#============================================


def active_preset() -> str:
    """Name of the active canvas preset ('classic', 'remaster', 'large')."""
    return settings.ACTIVE_CANVAS_PRESET


def hud_scale() -> int:
    """Integer scale factor applied to the 320x200 HUD sprite at blit time."""
    return settings.HUD_SCALE


def internal_size() -> tuple:
    """(width, height) of the internal canvas for the active preset."""
    return (settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT)


def visible_tile_count() -> int:
    """Number of tiles in each iso direction visible to the player."""
    return settings.VISIBLE_TILE_COUNT


#============================================
# Logical-to-canvas coordinate scaling
#============================================


def scale_logical_xy(x: int, y: int) -> tuple:
    """Scale a logical 320x200 (x, y) into the active canvas pixel space."""
    s = hud_scale()
    return (x * s, y * s)


def scale_logical_rect(x: int, y: int, w: int, h: int) -> tuple:
    """Scale a logical 320x200 rectangle to canvas pixel space."""
    s = hud_scale()
    return (x * s, y * s, w * s, h * s)


#============================================
# HUD layout
#============================================


def hud_origin() -> tuple:
    """Top-left of the AmigaUI HUD sprite in canvas pixel space."""
    # The HUD covers the entire 320x200 logical canvas; in scaled
    # presets it covers the full 640x400 / 1280x800 canvas as a 2x or
    # 4x nearest-neighbor blit. Origin is always (0, 0).
    return (0, 0)


def hud_size() -> tuple:
    """(width, height) of the HUD on the active canvas."""
    return internal_size()


#============================================
# Terrain viewport layout
#============================================


def terrain_origin() -> tuple:
    """Top-left of the iso-terrain origin (MAP_OFFSET_X/Y) in canvas px."""
    return scale_logical_xy(settings.MAP_OFFSET_X, settings.MAP_OFFSET_Y)


def terrain_viewport_rect() -> tuple:
    """Rectangle of the visible terrain area in canvas px (x, y, w, h).

    The iso-diamond extends `visible_tile_count() * TILE_HALF_W` left
    and right of `MAP_OFFSET_X`, and the same number of `TILE_HALF_H`
    units down from `MAP_OFFSET_Y`. The bounding rect we return is the
    enclosing axis-aligned box so callers can clip blits without
    needing iso math themselves.
    """
    n = visible_tile_count()
    half_w = settings.TILE_HALF_W
    half_h = settings.TILE_HALF_H
    # Logical bounding box around MAP_OFFSET_X/Y.
    lx = settings.MAP_OFFSET_X - n * half_w
    ly = settings.MAP_OFFSET_Y
    lw = 2 * n * half_w
    lh = 2 * n * half_h
    return scale_logical_rect(lx, ly, lw, lh)


#============================================
# Minimap layout
#============================================


def minimap_origin() -> tuple:
    """Top-left of the minimap in canvas px space."""
    # Minimap renders at logical (0, 0) per Minimap.__init__(0, 0).
    return scale_logical_xy(0, 0)


#============================================
# UI button hit-test
#============================================


def button_hit_box(action: str, ui_panel_buttons: dict) -> tuple:
    """Return the canvas-space (x, y, w, h) bounding rect for a button.

    Args:
        action: Button action name (key in `ui_panel.buttons`).
        ui_panel_buttons: The `self.buttons` dict from a UIPanel.

    Returns:
        (x, y, w, h) in canvas pixel space (already scaled by HUD_SCALE).
        The caller hit-tests by checking diamond proximity inside the
        rect; iso-shape testing belongs to UIPanel.hit_test_button.
    """
    btn = ui_panel_buttons[action]
    cx, cy = btn['c']
    hw, hh = btn['hw'], btn['hh']
    # Logical bounding box around the diamond center.
    lx = cx - hw
    ly = cy - hh
    lw = 2 * hw
    lh = 2 * hh
    return scale_logical_rect(lx, ly, lw, lh)


def button_center_canvas(action: str, ui_panel_buttons: dict) -> tuple:
    """Return the canvas-space (cx, cy) center of a button."""
    cx, cy = ui_panel_buttons[action]['c']
    return scale_logical_xy(cx, cy)
