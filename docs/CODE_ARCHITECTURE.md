# Code architecture

## Overview

`python-populous` is a single-process pygame application that reimplements the
classic Bullfrog *Populous* on an isometric 64x64 tile grid. The entry point
[populous.py](../populous.py) owns the main loop, input handling, rendering, and
glue between the gameplay modules ([game_map.py](../game_map.py),
[peep.py](../peep.py), [house.py](../house.py), [camera.py](../camera.py),
[minimap.py](../minimap.py)). Shared constants and asset paths live in
[settings.py](../settings.py).

The codebase is small (about 1.9k lines of Python across the runtime modules),
flat (no packages), and uses module-level state plus per-class objects.

## Major components

- [populous.py](../populous.py) (~824 lines) - `Game` class. Owns the pygame
  window, clock, sprite/tile loading, UI overlay, papal/shield modes, mouse
  pointer logic, and the main update/draw loop.
- [settings.py](../settings.py) - constants for screen size, grid size, tile
  geometry, color palette, asset paths, and lookup tables (`SLOPE_TILES`,
  `SLOPE_TILES_LOW`, `BUILDING_TILES`, `CASTLE_9_TILES`, `OBJECT_TILES`).
  Also contains the PyInstaller-aware `BASE_DIR` resolution.
- [game_map.py](../game_map.py) (~435 lines) - terrain grid, tile spritesheet
  loading from `data/gfx/AmigaTiles1.PNG`, slope tile selection, flat-area
  scoring for building placement, and the houses container.
- [house.py](../house.py) - `House` class. Tracks building life, growth rate,
  upgrade tier (`hut` -> `castle_large`), and pending peep spawns.
- [peep.py](../peep.py) (~308 lines) - `Peep` class plus
  `load_sprite_surfaces()` which slices `data/gfx/AmigaSprites1.PNG` into a 16x9
  grid of 16x16 sprites. Handles peep movement, animation, drowning, and
  combat-related state.
- [camera.py](../camera.py) - `Camera` class. Holds the floating-point
  `(r, c)` position of the visible 8x8 window and translates keyboard input
  (arrows or WASD, with diagonals) into clamped grid moves.
- [minimap.py](../minimap.py) - `Minimap` class. Draws an isometric losange
  overview of the 64x64 grid, the camera viewport, houses, and peeps; supports
  click-to-recenter.

### Tools (not part of the game runtime)

- [tools/map_viewer.py](../tools/map_viewer.py) - standalone viewer for tile data.
- [tools/tile_diagnostic.py](../tools/tile_diagnostic.py) - inspects the tile
  spritesheet slicing.
- [tools/sprite_diagnostic.py](../tools/sprite_diagnostic.py) - inspects the peep
  spritesheet slicing.
- [tools/house_diagnostic.py](../tools/house_diagnostic.py) - inspects building
  tile data.

## Data flow

1. `python3 populous.py` runs the module body, instantiating `Game()`.
2. `Game.__init__` calls `pygame.init()`, loads the AmigaUI background, then
   loads tile and sprite surfaces via `game_map.load_tile_surfaces()` and
   `peep.load_sprite_surfaces()`. Asset paths come from
   [settings.py](../settings.py) (`GFX_DIR`, `TILES_PATH`, `SPRITES_PATH`).
3. A `GameMap`, `Camera`, and `Minimap` are constructed. Initial houses and
   peeps are placed on the grid.
4. The main loop ticks the pygame clock, polls events (keyboard, mouse, mode
   toggles for papal/shield), then for each frame:
   - `Camera.update(dt)` reads held keys and slides the visible window.
   - `GameMap` advances house growth; `House.update` may spawn new peeps.
   - Each `Peep.update(dt, game_map)` moves and animates.
   - The renderer draws background, terrain tiles (sorted back-to-front),
     buildings, peeps, the UI overlay, then the minimap on top.
5. Mouse clicks in the minimap recenter the camera; clicks on the main view
   trigger the active power (terrain edit, papal magnet, shield/info).

## Reverse-engineering reference

The [asm/](../asm/) directory contains the original Amiga 68k disassembly
(`populous_main.asm`, `populous_prg.asm`) and analysis notes
([asm/ARCHITECTURE_REPORT.md](../asm/ARCHITECTURE_REPORT.md),
[asm/CONSTRUCTION_REPORT.md](../asm/CONSTRUCTION_REPORT.md),
[asm/MINIMAP_REPORT.md](../asm/MINIMAP_REPORT.md),
[asm/PEEPS_REPORT.md](../asm/PEEPS_REPORT.md),
[asm/SHIELD_REPORT.md](../asm/SHIELD_REPORT.md)) used to guide the Python port.

## Build and distribution

- [build.ps1](../build.ps1) (PowerShell) and
  [push_and_build.py](../push_and_build.py) (Python) commit, tag, and push to
  trigger a GitHub Actions workflow that builds platform executables (presumably
  via PyInstaller, given the `sys.frozen` / `_MEIPASS` handling in
  [settings.py](../settings.py)).

## Testing and verification

There is no automated test suite in the repo. Verification is manual: run
`python3 populous.py` and exercise camera scrolling, building growth, peep
spawning, and the papal/shield powers.

## Extension points

- New building types: extend `BUILDING_TILES` in [settings.py](../settings.py)
  and the `House.TYPES` ordering in [house.py](../house.py).
- New terrain or object tiles: add entries to `OBJECT_TILES` /
  `SLOPE_TILES` / `SLOPE_TILES_LOW` and ensure the spritesheet slicing in
  `game_map.load_tile_surfaces()` covers them.
- New peep behaviors: extend `Peep` in [peep.py](../peep.py); see the pending
  `build`, `gather`, `fight` cases in [docs/TODO.md](TODO.md).
- New input or powers: wire events in `Game` in [populous.py](../populous.py)
  alongside the existing papal and shield modes.

## Known gaps

- No `if __name__ == '__main__':` guard is visible in the inspected portion of
  [populous.py](../populous.py); confirm the actual run trigger before
  documenting alternatives.
- The GitHub Actions workflow file was not located in the repo snapshot;
  confirm its path and PyInstaller configuration before documenting build
  internals.
- No dedicated tests directory exists; if smoke tests are added later, document
  them here.
