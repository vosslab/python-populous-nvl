# Code architecture

## Overview

`python-populous` is a single-process pygame application that reimplements
the classic Bullfrog *Populous* on an isometric 64x64 tile grid. The entry
point [populous.py](../populous.py) instantiates `populous_game.game.Game`,
which owns the main loop and delegates work to focused modules under the
[populous_game/](../populous_game/) package. Shared constants and asset
paths live in [populous_game/settings.py](../populous_game/settings.py).

## Geometry single source of truth (M6 ViewportTransform)

`populous_game/layout.py:ViewportTransform` and the
`build_viewport_transform()` factory are the **single source of geometry
truth** for the renderer and the input controller:

- The transform owns world-to-screen and screen-to-world projection.
  `world_to_screen(r, c, alt)` and `world_to_screen_float(r, c, alt)`
  produce canvas pixel coordinates; `screen_to_world(x, y)` and
  `screen_to_nearest_corner(x, y)` resolve canvas pixels back to a tile
  or corner. Every preset gets the same NxN visible viewport centered
  inside the AmigaUI black diamond well (`MAP_WELL_RECT_LOGICAL`).
- Renderers (`populous_game/renderer.py`) and the input controller
  (`populous_game/input_controller.py`) both route through the
  transform; no module re-derives `MAP_OFFSET_X / MAP_OFFSET_Y *
  HUD_SCALE` arithmetic in flight.
- Sprite anchor offsets (where the foot of a peep, the base of a house,
  or the tip of a flag should land relative to a projected tile) live in
  `populous_game/sprite_geometry.py:SPRITE_ANCHORS`, not in renderer
  code. Renderers call `sprite_geometry._apply_anchor((sx, sy),
  SPRITE_ANCHORS[name], (sw, sh))` so the same metadata drives blit
  positions across modules.
- The camera (`populous_game/camera.py`) operates entirely in world
  (row / column) coordinates; map-well placement is the layout's
  responsibility, not the camera's. `camera.r / camera.c` store the
  top-left of the visible NxN viewport; `build_viewport_transform`
  projects the four viewport corners to find the bbox center and
  aligns it to `map_well_rect.center`.
- The `--debug-layout` CLI flag overlays the map-well rectangle, the
  projection anchor, every visible tile center, and HUD button hit-boxes
  for diagnosis. Combine with `--screenshot` for a static snapshot, or
  run interactively to verify clicks land on the highlighted hit-boxes.

## Major components

- [populous_game/game.py](../populous_game/game.py) - `Game` class. Owns
  the pygame window, the internal canvas surface, the event/update/draw
  pump, and instances of every subsystem below. Caches a presized HUD
  blit surface (`self.hud_blit_surface`) once at boot: when
  `settings.HUD_SCALE > 1`, the original 320x200 AmigaUI sprite is
  upscaled once via `pygame.transform.scale` and reused per-frame.
- [populous_game/settings.py](../populous_game/settings.py) - constants
  for grid size, tile geometry, color palette, asset paths, lookup
  tables (`SLOPE_TILES`, `BUILDING_TILES`, `OBJECT_TILES`), button
  tooltips, audio defaults, and the canvas-preset infrastructure
  described below.
- [populous_game/layout.py](../populous_game/layout.py) - resolution-aware
  layout helpers. Pure functions over `populous_game.settings`. Returns
  canvas pixel-space rectangles already scaled by `HUD_SCALE` for HUD
  origin/size, terrain origin, terrain viewport rect, minimap rect, and
  button hit-box. Logical UI coordinate space stays 320x200; presentation
  scales by the active preset.
- [populous_game/terrain.py](../populous_game/terrain.py) - the 64x64
  altitude grid, tile spritesheet slicing, slope-tile selection,
  flat-area scoring for build placement, and the houses container.
- [populous_game/peeps.py](../populous_game/peeps.py) - `Peep` class plus
  sprite loading. Drives movement, animation, drowning, and combat
  state.
- [populous_game/houses.py](../populous_game/houses.py) - `House` class.
  Tracks building life, growth rate, and pending peep spawns.
- [populous_game/camera.py](../populous_game/camera.py) - `Camera` class.
  Holds the floating-point `(r, c)` position of the visible window and
  reads `settings.VISIBLE_TILE_COUNT` for clamps and centering.
- [populous_game/minimap.py](../populous_game/minimap.py) - isometric
  losange overview, viewport indicator, click-to-recenter, and
  mouse-wheel zoom.
- [populous_game/renderer.py](../populous_game/renderer.py) - draws
  background, terrain, houses, peeps, HUD, tooltips, hover help, and the
  minimap. Reads layout helpers; never mixes coordinate spaces.
- [populous_game/input_controller.py](../populous_game/input_controller.py)
  - mouse/keyboard router. On every click it computes two coordinate
  copies: a canvas-space `(mx, my)` for terrain hit-tests
  (`view_rect`, `screen_to_nearest_corner`) and a logical-space
  `(mx, my) // HUD_SCALE` for UI hit-tests (`ui_panel.hit_test_button`,
  `minimap.handle_click`). At classic (`HUD_SCALE == 1`) both copies
  match.
- [populous_game/ui_panel.py](../populous_game/ui_panel.py) - HUD button
  hit-test map and tooltip lookup. Buttons live in 320x200 logical space.
- [populous_game/audio.py](../populous_game/audio.py) - `AudioManager`.
  Music/SFX toggles, mute flags, sample-rate sanitization for bundled
  WAV files.
- [populous_game/app_state.py](../populous_game/app_state.py),
  [populous_game/mode_manager.py](../populous_game/mode_manager.py) -
  global state machine (MENU / PLAYING / PAUSED / GAMEOVER) and
  active-power mode toggles.
- [populous_game/ai_opponent.py](../populous_game/ai_opponent.py) -
  enemy faction heuristics: idle low-life peeps seek flat for building;
  groups above `AI_MARCH_THRESHOLD` mass-march toward the player
  centroid. Deterministic, ticked at `AI_TICK_INTERVAL`.
- [populous_game/combat.py](../populous_game/combat.py),
  [populous_game/faction.py](../populous_game/faction.py),
  [populous_game/mana_pool.py](../populous_game/mana_pool.py),
  [populous_game/powers.py](../populous_game/powers.py) - combat
  resolution, faction identity, mana economy, and the player powers
  (quake/flood/volcano/papal/knight).
- [populous_game/scenario.py](../populous_game/scenario.py),
  [populous_game/save_state.py](../populous_game/save_state.py),
  [populous_game/password_codec.py](../populous_game/password_codec.py)
  - YAML scenario loader, JSON save/load, and the seven-letter password
  codec.
- [populous_game/selection.py](../populous_game/selection.py),
  [populous_game/keymap.py](../populous_game/keymap.py),
  [populous_game/peep_state.py](../populous_game/peep_state.py),
  [populous_game/pathfinding.py](../populous_game/pathfinding.py),
  [populous_game/sprite_geometry.py](../populous_game/sprite_geometry.py),
  [populous_game/assets.py](../populous_game/assets.py) - small focused
  helpers for find-button selection, key bindings, peep state matrix,
  pathfinding, sprite math, and asset loading.

## Canvas-preset system

The remaster adds a resolution-aware presentation layer while keeping
simulation behavior untouched.

- `settings.CANVAS_PRESETS` declares three named presets:
  - `classic`: 320x200, `HUD_SCALE=1`, `VISIBLE_TILE_COUNT=8`.
  - `remaster`: 640x400, `HUD_SCALE=2`, `VISIBLE_TILE_COUNT=12`.
  - `large`: 1280x800, `HUD_SCALE=4`, `VISIBLE_TILE_COUNT=16`.
- `settings.ACTIVE_CANVAS_PRESET` selects the active preset; the
  default is `remaster`.
- The four mirror constants (`INTERNAL_WIDTH`, `INTERNAL_HEIGHT`,
  `HUD_SCALE`, `VISIBLE_TILE_COUNT`) are derived from the active
  preset and read by `layout.py`, `terrain.py`, `camera.py`,
  `renderer.py`, and `input_controller.py`.
- The simulation digest is preset-independent: same seed produces
  byte-identical state across presets. This invariant is enforced by
  [tests/test_canvas_size_compat.py](../tests/test_canvas_size_compat.py).

## Data flow

1. `python3 populous.py` calls `populous_game.game.Game().run()`.
2. `Game.__init__` calls `pygame.init()`, sizes the internal surface
   from `settings.INTERNAL_WIDTH/HEIGHT`, loads the AmigaUI background,
   builds the cached `hud_blit_surface`, and loads tile/sprite
   surfaces.
3. A terrain `GameMap`, `Camera`, `Minimap`, `AudioManager`, and
   `AIOpponent` are constructed; initial player and enemy peeps spawn.
4. The main loop ticks the clock, polls events through
   `input_controller`, then per frame:
   - `Camera.update(dt)` slides the visible window.
   - `GameMap` advances house growth; `House.update` may spawn peeps.
   - Each `Peep.update(dt, game_map)` moves and animates.
   - `AIOpponent.update(dt)` issues enemy orders.
   - `renderer.draw()` blits background, terrain (back-to-front),
     houses, peeps, the cached HUD surface, tooltips, hover help, then
     the minimap.
5. Mouse clicks route through `input_controller`: the minimap rect
   recenters the camera; the viewport triggers the active power; HUD
   buttons toggle music/SFX/sleep, find/go-cycle peeps, or arm a power.

## Reverse-engineering reference

The [asm/](../asm/) directory contains the original Amiga 68k
disassembly and analysis notes
([asm/ARCHITECTURE_REPORT.md](../asm/ARCHITECTURE_REPORT.md),
[asm/CONSTRUCTION_REPORT.md](../asm/CONSTRUCTION_REPORT.md),
[asm/MINIMAP_REPORT.md](../asm/MINIMAP_REPORT.md),
[asm/PEEPS_REPORT.md](../asm/PEEPS_REPORT.md),
[asm/SHIELD_REPORT.md](../asm/SHIELD_REPORT.md)) used to guide the
Python port.

## Testing

Tests live under [tests/](../tests/) and run with pytest. See
[docs/USAGE.md](USAGE.md) for the recommended invocations and the
fast-iteration ignore list. Smoke scripts under
[tools/smoke/](../tools/smoke/) drive click-to-effect chains in
process and exit non-zero on regression.

## Build and distribution

[build.ps1](../build.ps1) (PowerShell) and
[push_and_build.py](../push_and_build.py) (Python) commit, tag, and
push to trigger a GitHub Actions workflow that builds platform
executables via PyInstaller (the `sys.frozen` / `_MEIPASS` handling
in [populous_game/settings.py](../populous_game/settings.py) reflects
this).
