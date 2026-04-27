# M6 layout projection plan

Author: this session, 2026-04-27.

## Why this plan exists

M4 modernized the canvas with named presets (classic / remaster / large)
and introduced [populous_game/layout.py](../../populous_game/layout.py)
as a partial layout helper. After landing M4 with `remaster` as the
default and reverting to `classic` based on user feedback, two
architectural failings surfaced:

1. **Object-specific hard-coded offsets.** Terrain, peeps, buildings,
   cursors, hover tooltips, AOE previews, and effect overlays each
   compute their own screen positions with private X/Y shifts. The
   shifts add up to a viewport that does not align with the AmigaUI
   map well at any preset other than `classic`.
2. **Map-well geometry is implicit.** The black diamond-shaped map
   well in the AmigaUI sprite is never expressed as a rectangle the
   layout helper knows about. `MAP_OFFSET_X = 192`,
   `MAP_OFFSET_Y = 64` (in 320x200 logical space) hard-codes the
   terrain anchor to a position that happens to look right at classic
   but drifts up / right at remaster, leaving large blank regions in
   the well.

The user observed this directly: at the remaster default the rendered
terrain occupies only a small portion of the visible black map well
and is shifted up and right relative to the well center. Hover
tooltips appear in the wrong place because the mouse-to-tile mapping
uses one coordinate system and the visual draw uses another.

## Design philosophy

- Layout is the single source of truth for screen geometry.
- HUD layout defines where the map view lives.
- Camera defines which world tile is centered.
- Projection defines how world coordinates become screen pixels.
- Objects never guess their own offsets. Terrain, peeps, buildings,
  cursors, tooltips, AOE previews, drag-paint indicators, and any
  future overlay all use the same `tile_to_screen()` projection.
- Mouse clicks are resolved through the matching `screen_to_tile()`
  inverse. The two functions round-trip exactly.
- Canvas size is presentation only. Simulation digest must remain
  preset-independent (locked in by `tests/test_canvas_size_compat.py`).

## Required additions to populous_game/layout.py

Define a frozen Layout dataclass that captures every screen rectangle
the renderer and input controller need:

```python
@dataclass(frozen=True)
class Layout:
    canvas_w: int             # internal canvas width in pixels
    canvas_h: int             # internal canvas height in pixels
    hud_scale: int            # AmigaUI sprite blit-scale factor
    hud_rect: pygame.Rect     # full-canvas HUD blit rect
    map_well_rect: pygame.Rect       # the black diamond-shaped map well
    terrain_clip_rect: pygame.Rect   # axis-aligned bounding rect for clipping
    terrain_anchor_px: tuple         # (x, y) of the (cam_r, cam_c) corner
    minimap_rect: pygame.Rect        # minimap area
```

Provide `active_layout()` returning a `Layout` instance derived from
`settings.CANVAS_PRESETS[settings.ACTIVE_CANVAS_PRESET]`.

The map-well rectangle must be measured from the AmigaUI sprite once
(empirically - the well is iso-shaped in the 320x200 logical space)
and stored as logical coordinates in `CANVAS_PRESETS` or a sibling
constant. At remaster / large presets, the rectangle scales by
`HUD_SCALE`. The terrain anchor centers the iso diamond inside the
well, derived from the well rect rather than hard-coded MAP_OFFSET_X /
MAP_OFFSET_Y.

## Centralized projection

Add to `populous_game/layout.py` (or a sibling `populous_game/projection.py`):

```python
def tile_to_screen(layout, camera, row, col, z=0):
    """Project a world-tile coordinate into canvas pixel space.

    All world objects (terrain, peeps, buildings, cursors, AOE
    previews, hover tooltips, effects) MUST go through this function.
    No private offsets allowed.
    """
    ax, ay = layout.terrain_anchor_px
    half_w = settings.TILE_HALF_W
    half_h = settings.TILE_HALF_H
    step   = settings.ALTITUDE_PIXEL_STEP
    x = ax + (col - camera.c) * half_w - (row - camera.r) * half_w
    y = ay + (col - camera.c) * half_h + (row - camera.r) * half_h - z * step
    return x, y


def screen_to_tile(layout, camera, x, y):
    """Inverse of tile_to_screen. Used for mouse-to-tile hit-testing.

    Round-trips with tile_to_screen for any (row, col) such that the
    altitude argument is the same in both directions.
    """
    ax, ay = layout.terrain_anchor_px
    half_w = settings.TILE_HALF_W
    half_h = settings.TILE_HALF_H
    dx = x - ax
    dy = y - ay
    # Inverse isometric transform: (col-camera.c, row-camera.r) from (dx, dy)
    # dx = (dc - dr) * half_w
    # dy = (dc + dr) * half_h
    # So dc = (dx / half_w + dy / half_h) / 2
    #    dr = (dy / half_h - dx / half_w) / 2
    dc = (dx / half_w + dy / half_h) / 2
    dr = (dy / half_h - dx / half_w) / 2
    return camera.r + dr, camera.c + dc
```

## Required call-site migrations

Every site below currently computes its own screen position. Each
must route through `tile_to_screen` (and `screen_to_tile` for inverse
hit-tests):

- `populous_game/terrain.py`
  - `GameMap.world_to_screen` -> drop; replace internal call with
    `tile_to_screen`. Public callers update accordingly.
  - `GameMap.screen_to_grid` and `GameMap.screen_to_nearest_corner` ->
    drop the inline math; use `screen_to_tile`.
  - `GameMap.draw_tile`, `GameMap.draw_houses`: tile blit positions
    come from `tile_to_screen`.
- `populous_game/sprite_geometry.py`
  - `get_peep_sprite_rect`, `get_house_sprite_rect`: replace the
    private offset math with `tile_to_screen` plus a small
    sprite-anchor offset that is part of the sprite, not the layout.
- `populous_game/renderer.py`
  - `_draw_cursor`, `_draw_aoe_preview`, `_draw_command_queue_lines`,
    drag-paint preview, hover-tooltip placement: all through
    `tile_to_screen`.
- `populous_game/peeps.py`
  - Drowning animation overlay, weapon-marker positions: through
    `tile_to_screen`.
- `populous_game/houses.py`
  - Castle 3x3 corner blit positions: through `tile_to_screen`.
- `populous_game/input_controller.py`
  - Mouse-to-tile resolution after `mx //= display_scale`: route
    through `screen_to_tile`. The current canvas-vs-logical split
    collapses into a single canvas-space pipeline because the
    projection itself is canvas-space-aware via the layout.

## Debug overlay

Add a `--debug-layout` CLI flag (alongside the M5 followup CLI flags
in `populous_game/cli.py`). When set, draws on top of every frame:

- The HUD rect outline (white, 1 px).
- The map well rectangle (cyan, 1 px).
- The terrain clip rect (yellow, 1 px).
- The terrain anchor as a 3x3 magenta square.
- A small dot at every visible tile center (red, 1 px each).
- Every button hit-box in `ui_panel.buttons` (green, 1 px outline).

This artifact is the user's diagnostic for layout bugs: a screenshot
with `--debug-layout` makes terrain-vs-well alignment immediately
visible.

## Tests

- `tests/test_projection_roundtrip.py`: for a range of (row, col)
  pairs covering all four corners of the visible viewport plus a few
  interior points, assert `screen_to_tile(tile_to_screen(...))` round-
  trips to within 0.001 of the input. One test per preset.
- `tests/test_layout_terrain_centered_in_well.py`: at every preset,
  the terrain bounding box (computed from the four corners of an
  N-tile diamond, where N = VISIBLE_TILE_COUNT) is centered inside
  the map-well rect to within 1 pixel and occupies at least 70 % of
  the well area.
- `tests/test_no_private_offsets.py`: lint that scans
  `populous_game/` for forbidden patterns like `+ TILE_HALF_W`,
  `- TILE_HALF_H`, hard-coded sprite anchor literals (not yet
  finalized; tighten as we know what to forbid).

## Acceptance criteria

- Every world object is rendered through `tile_to_screen`. No private
  X/Y shifts remain in `terrain.py`, `sprite_geometry.py`,
  `renderer.py`, `peeps.py`, `houses.py`.
- Every mouse click is resolved through `screen_to_tile`.
- The map-well rect is defined in `Layout` and read by every
  renderer that needs to know "where the playable terrain area is."
- `tests/test_projection_roundtrip.py` passes at every preset.
- `tests/test_layout_terrain_centered_in_well.py` passes at every
  preset (terrain centered in well, fills >=70 % of well).
- `tests/test_canvas_size_compat.py` continues to pass (digest parity).
- `--debug-layout` flag exists and writes a useful overlay.
- Default preset can switch to `remaster` without visible drift,
  large blank regions, or hover-tooltip mismatch.

## Sequencing

1. Define `Layout` dataclass and the map-well rect constant.
2. Add `tile_to_screen` and `screen_to_tile`.
3. Migrate terrain.py first (smallest blast radius).
4. Migrate sprite_geometry.py.
5. Migrate renderer.py overlays.
6. Migrate peeps.py and houses.py.
7. Migrate input_controller.py.
8. Add `--debug-layout` overlay.
9. Add the three new tests.
10. Re-run M3 effect smokes at every preset; fix any bugs.
11. Switch default to `remaster`.

Each step is its own patch. Do NOT batch.

## Out of scope

- New tile sprites at higher resolution.
- Changes to `TILE_HALF_W` / `TILE_HALF_H` (these stay constant; the
  view widens or narrows by changing `VISIBLE_TILE_COUNT`).
- Changes to gameplay rules. The simulation digest must remain
  identical at every preset, before and after this work.

## Open questions for the next session

- Where is the map-well rect measured from? Reading the AmigaUI
  sprite pixel-by-pixel is one option; documenting the empirical
  values in `settings.MAP_WELL_RECT` is another. The latter is
  cheaper but requires a re-measurement when the AmigaUI art
  changes.
- Should the camera bounds clamp to keep the rendered diamond inside
  the well, or should clipping handle off-well pixels? Today the
  camera clamps so the visible 8x8 (or N x N) tile area never goes
  off-grid; M6 needs to clamp so the diamond never goes off-well.
