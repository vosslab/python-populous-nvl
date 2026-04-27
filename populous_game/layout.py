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

The M6 ViewportTransform foundation also lives at the bottom of this
module: `Layout`, `ViewportTransform`, `build_viewport_transform`, and
`max_visible_tiles_that_fit`. These types own the iso-projection math
that previously lived ad hoc inside `terrain.py` and friends. Patch 2
adds them additively; later patches migrate callers.
"""

import dataclasses

import pygame

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


#============================================
# M6 ViewportTransform foundation: Layout
#============================================


@dataclasses.dataclass(frozen=True)
class Layout:
    """Static rectangles and tile geometry for the active canvas preset.

    A Layout snapshots `populous_game.settings` at build time. All
    rectangles are in canvas pixel space (already scaled by
    `HUD_SCALE`). All tile geometry is in canvas pixel space (already
    scaled by `TERRAIN_SCALE`). Frozen so it can be hashed / used as a
    cache key and so consumers cannot mutate it inadvertently.
    """

    canvas_rect: pygame.Rect
    hud_rect: pygame.Rect
    map_well_rect: pygame.Rect
    minimap_rect: pygame.Rect
    terrain_clip_rect: pygame.Rect
    tile_w: int
    tile_h: int
    altitude_step: int


def active_layout() -> Layout:
    """Build a Layout for the active canvas preset.

    Reads only `populous_game.settings`. Returned rectangles are in
    canvas pixel space (already multiplied by `HUD_SCALE`).

    Returns:
        Layout: Snapshot of the active preset's geometry.
    """
    # HUD scale folds logical 320x200 coordinates into canvas pixels.
    s = settings.HUD_SCALE
    # Full internal canvas. HUD blits at (0, 0) covering the whole canvas.
    canvas_rect = pygame.Rect(0, 0, settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT)
    # HUD covers the full canvas at 1:1 (it is the same surface).
    hud_rect = pygame.Rect(0, 0, settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT)
    # Map well measured in 320x200 logical space; scale to canvas px.
    well_x, well_y, well_w, well_h = settings.MAP_WELL_RECT_LOGICAL
    map_well_rect = pygame.Rect(well_x * s, well_y * s, well_w * s, well_h * s)
    # Minimap is anchored at logical (0, 0) per Minimap.__init__(0, 0).
    # Its width/height in logical coords is implicit elsewhere; here we
    # mirror the existing minimap_origin() helper and leave the rect
    # to be sized by the minimap renderer when it gains an exact size.
    # For now use the existing origin and a zero-size rect; consumers
    # that need the minimap rect can update this when minimap geometry
    # is migrated through Layout in a later patch.
    minimap_rect = pygame.Rect(0, 0, 0, 0)
    # Terrain clip is the same as the map well: the iso diamond must
    # not paint outside the well or it will overlap the HUD chrome.
    terrain_clip_rect = pygame.Rect(map_well_rect)
    # Tile dimensions in canvas px. tile_w / tile_h are full extents
    # (not halves); we expose halves via ViewportTransform properties.
    tile_w = settings.BASE_TILE_HALF_W * 2 * settings.TERRAIN_SCALE
    tile_h = settings.BASE_TILE_HALF_H * 2 * settings.TERRAIN_SCALE
    altitude_step = settings.BASE_ALTITUDE_STEP * settings.TERRAIN_SCALE
    return Layout(
        canvas_rect=canvas_rect,
        hud_rect=hud_rect,
        map_well_rect=map_well_rect,
        minimap_rect=minimap_rect,
        terrain_clip_rect=terrain_clip_rect,
        tile_w=tile_w,
        tile_h=tile_h,
        altitude_step=altitude_step,
    )


#============================================
# M6 ViewportTransform foundation: ViewportTransform
#============================================


@dataclasses.dataclass(frozen=True)
class ViewportTransform:
    """Iso projection bound to a Layout, a camera, and a tile budget.

    Maps grid coordinates `(row, col, altitude)` to canvas pixel
    coordinates `(x, y)` and back. The `anchor_x`/`anchor_y` integers
    place the camera-origin tile inside the map well such that an
    `visible_tiles`-tile diamond is centered in `map_well_rect`.

    `world_to_screen_float` is the math primitive (no rounding).
    `world_to_screen` returns the integer-rounded blit pixel.
    `screen_to_world` is the inverse of the float form.
    """

    canvas_rect: pygame.Rect
    map_well_rect: pygame.Rect
    terrain_clip_rect: pygame.Rect
    visible_tiles: int
    tile_w: int
    tile_h: int
    altitude_step: int
    camera_row: float
    camera_col: float
    anchor_x: int
    anchor_y: int

    @property
    def half_w(self) -> int:
        """Half the iso tile width (pixels). Always tile_w // 2."""
        return self.tile_w // 2

    @property
    def half_h(self) -> int:
        """Half the iso tile height (pixels). Always tile_h // 2."""
        return self.tile_h // 2

    def world_to_screen_float(self, row: float, col: float, altitude: float = 0) -> tuple:
        """Project a grid coordinate to canvas pixels (float, no rounding).

        Use for math tests and analytic round-tripping. Do not blit at
        the float result; blits must use integer pixels via
        `world_to_screen`.

        Args:
            row: Grid row (float ok for sub-tile interpolation).
            col: Grid column (float ok).
            altitude: Tile altitude in altitude steps (float ok).

        Returns:
            tuple: (x, y) canvas-pixel floats.
        """
        # Camera-relative grid offset. Float math is exact for ints.
        dc = col - self.camera_col
        dr = row - self.camera_row
        # Iso projection: x grows as col-row, y grows as col+row.
        x = self.anchor_x + (dc - dr) * self.half_w
        y = self.anchor_y + (dc + dr) * self.half_h - altitude * self.altitude_step
        return x, y

    def world_to_screen(self, row: float, col: float, altitude: float = 0) -> tuple:
        """Project a grid coordinate to integer canvas pixels.

        Use for blits and click-pixel comparisons.

        Args:
            row: Grid row.
            col: Grid column.
            altitude: Tile altitude in altitude steps.

        Returns:
            tuple: (x, y) canvas-pixel ints (Python's `round` half-even).
        """
        x, y = self.world_to_screen_float(row, col, altitude)
        return round(x), round(y)

    def screen_to_world(self, x: int, y: int, altitude: float = 0) -> tuple:
        """Inverse projection: canvas pixels back to grid coordinates.

        Inverts `world_to_screen_float` exactly when given that
        function's float output. With integer pixel input there is up
        to one tile of slack near tile boundaries due to rounding.

        Args:
            x: Canvas pixel x.
            y: Canvas pixel y.
            altitude: Tile altitude in altitude steps (corrects for
                the altitude offset baked into world_to_screen).

        Returns:
            tuple: (row, col) grid coordinates as floats.
        """
        # Translate into camera-anchor-relative pixel space.
        sx = x - self.anchor_x
        sy = y - self.anchor_y + altitude * self.altitude_step
        # Algebraic inverse of the iso forward projection.
        dc = (sx / self.half_w + sy / self.half_h) / 2
        dr = (sy / self.half_h - sx / self.half_w) / 2
        return self.camera_row + dr, self.camera_col + dc


#============================================
# M6 ViewportTransform foundation: builder + utilities
#============================================


def build_viewport_transform(layout: Layout, camera, visible_tiles: int) -> ViewportTransform:
    """Center the visible N-tile iso diamond inside the layout's map well.

    Camera convention: `populous_game.camera.Camera` stores `(r, c)` as
    the TOP-LEFT corner of the visible NxN viewport, not its center
    (see `Camera.__init__` -- `self.r = GRID_HEIGHT // 2 - N // 2`).
    To center the rendered terrain in the well we must therefore
    project the corners of the visible NxN bbox `(camera.r..camera.r+N,
    camera.c..camera.c+N)`, not corners around `(camera.r, camera.c)`.

    Algorithm (no magic constants):
      1. Build a provisional ViewportTransform with anchor (0, 0).
      2. Project the four corners of the visible NxN viewport.
      3. Take the bbox of those four projected points; let
         (bbox_cx, bbox_cy) be its center.
      4. Final anchor is
         (map_well.centerx - bbox_cx, map_well.centery - bbox_cy),
         rounded to integers.
      5. Return a new ViewportTransform with that anchor.

    Args:
        layout: Active Layout (provides map_well_rect, tile_w/h, etc.).
        camera: Duck-typed camera with `.r` and `.c` floats. The
            existing `populous_game.camera.Camera` class qualifies.
        visible_tiles: Diamond extent in tiles per iso axis.

    Returns:
        ViewportTransform: Centered transform ready for projection.
    """
    # Provisional transform with anchor at (0, 0). We only need its
    # forward projection, so the anchor it carries does not matter
    # beyond canceling out below.
    provisional = ViewportTransform(
        canvas_rect=layout.canvas_rect,
        map_well_rect=layout.map_well_rect,
        terrain_clip_rect=layout.terrain_clip_rect,
        visible_tiles=visible_tiles,
        tile_w=layout.tile_w,
        tile_h=layout.tile_h,
        altitude_step=layout.altitude_step,
        camera_row=float(camera.r),
        camera_col=float(camera.c),
        anchor_x=0,
        anchor_y=0,
    )
    cr = float(camera.r)
    cc = float(camera.c)
    n = float(visible_tiles)
    # Four corners of the visible NxN viewport whose top-left is
    # (camera.r, camera.c). These are the points the player actually
    # sees; their projected bbox is what must center in the well.
    corners = (
        (cr,     cc    ),
        (cr,     cc + n),
        (cr + n, cc    ),
        (cr + n, cc + n),
    )
    # Project each corner under the provisional anchor (0, 0).
    projected = [provisional.world_to_screen_float(r, c) for r, c in corners]
    xs = [p[0] for p in projected]
    ys = [p[1] for p in projected]
    bbox_cx = (min(xs) + max(xs)) / 2.0
    bbox_cy = (min(ys) + max(ys)) / 2.0
    # Anchor that places the diamond bbox center at the well center.
    anchor_x = round(layout.map_well_rect.centerx - bbox_cx)
    anchor_y = round(layout.map_well_rect.centery - bbox_cy)
    return ViewportTransform(
        canvas_rect=layout.canvas_rect,
        map_well_rect=layout.map_well_rect,
        terrain_clip_rect=layout.terrain_clip_rect,
        visible_tiles=visible_tiles,
        tile_w=layout.tile_w,
        tile_h=layout.tile_h,
        altitude_step=layout.altitude_step,
        camera_row=cr,
        camera_col=cc,
        anchor_x=anchor_x,
        anchor_y=anchor_y,
    )


def max_visible_tiles_that_fit(map_well_rect, tile_w: int, tile_h: int, candidates) -> int:
    """Return the largest N from `candidates` whose diamond fits the well.

    An N-tile iso diamond's axis-aligned bbox at native tile size is
    `width = N * tile_w`, `height = N * tile_h` (with
    `tile_w = 2 * half_w` and `tile_h = 2 * half_h`). The diamond fits
    when both bbox dimensions are <= the corresponding `map_well_rect`
    dimension. If no candidate fits, returns `min(candidates)` so
    callers always have something to render.

    Args:
        map_well_rect: pygame.Rect (or any object with `.width` /
            `.height`) defining the iso-diamond budget.
        tile_w: Iso tile width in canvas px.
        tile_h: Iso tile height in canvas px.
        candidates: Iterable of integer N candidates.

    Returns:
        int: Largest fitting N, or min(candidates) if none fit.
    """
    well_w = map_well_rect.width
    well_h = map_well_rect.height
    candidate_list = list(candidates)
    # Sort descending so the first fitting candidate is the largest.
    fitting = []
    for n in candidate_list:
        bbox_w = n * tile_w
        bbox_h = n * tile_h
        if bbox_w <= well_w and bbox_h <= well_h:
            fitting.append(n)
    if not fitting:
        return min(candidate_list)
    return max(fitting)
