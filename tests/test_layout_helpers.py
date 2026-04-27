"""Pure-function tests for populous_game/layout.py (M4 WP-M4-A).

Layout helpers must scale 320x200 logical coordinates to the active
canvas preset by exactly the integer HUD_SCALE factor, with no
silent rounding or fudge.
"""

import populous_game.layout as layout
import populous_game.settings as settings


def test_classic_preset_returns_320_200():
    """Classic preset internal_size() is (320, 200)."""
    settings.ACTIVE_CANVAS_PRESET = 'classic'
    settings.INTERNAL_WIDTH = 320
    settings.INTERNAL_HEIGHT = 200
    settings.HUD_SCALE = 1
    settings.VISIBLE_TILE_COUNT = 8
    assert layout.internal_size() == (320, 200)
    assert layout.hud_scale() == 1


def test_scale_logical_xy_round_trips_at_classic():
    """At classic (1x), logical and canvas pixels match exactly."""
    settings.HUD_SCALE = 1
    assert layout.scale_logical_xy(192, 64) == (192, 64)


def test_scale_logical_xy_doubles_at_remaster():
    """At remaster (2x), every logical coord is exactly doubled."""
    settings.HUD_SCALE = 2
    assert layout.scale_logical_xy(192, 64) == (384, 128)
    settings.HUD_SCALE = 1


def test_scale_logical_rect_scales_all_four_components():
    """scale_logical_rect multiplies x, y, w, h by the active scale."""
    settings.HUD_SCALE = 4
    assert layout.scale_logical_rect(10, 20, 30, 40) == (40, 80, 120, 160)
    settings.HUD_SCALE = 1


def test_terrain_origin_uses_map_offset_constants():
    """terrain_origin returns MAP_OFFSET_X/Y scaled by HUD_SCALE."""
    settings.HUD_SCALE = 2
    expected = (settings.MAP_OFFSET_X * 2, settings.MAP_OFFSET_Y * 2)
    assert layout.terrain_origin() == expected
    settings.HUD_SCALE = 1
