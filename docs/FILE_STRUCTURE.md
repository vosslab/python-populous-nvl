# File structure

## Top-level layout

```text
python-populous/
+- README.md              project overview and quick start
+- requirements.txt       pip deps (pygame, numpy)
+- populous.py            main entry point: pygame Game loop
+- settings.py            constants, asset paths, tile lookup tables
+- camera.py              viewport position and keyboard scrolling
+- game_map.py            terrain grid, tile loading, building placement
+- house.py               House class: growth, upgrades, spawns
+- minimap.py             losange overview, click-to-recenter
+- peep.py                Peep class and sprite loading
+- build.ps1              Windows commit/tag/push helper
+- push_and_build.py      cross-platform commit/tag/push helper
+- asm/                   original Amiga disassembly and analysis
+- data/                  game assets (graphics, audio)
+- docs/                  project documentation
`- tools/                 standalone diagnostic scripts
```

## Key subtrees

### [asm/](../asm/) - reverse-engineering reference

```text
asm/
+- populous_main.asm           Amiga 68k disassembly (main)
+- populous_main.cnf           IDA/disassembler config
+- populous_prg.asm            Amiga 68k disassembly (program)
+- populous_prg.cnf            IDA/disassembler config
+- ARCHITECTURE_REPORT.md      engine architecture notes
+- CONSTRUCTION_REPORT.md      building/construction notes
+- MINIMAP_REPORT.md           minimap behavior notes
+- PEEPS_REPORT.md             peep behavior notes
`- SHIELD_REPORT.md            shield/info panel notes
```

These files document the original game and guide the Python port. They are
read-only references, not runtime code.

### [data/](../data/) - game assets

```text
data/
+- gfx/                   PNG and GIF spritesheets
|  +- AmigaTiles1.PNG     primary terrain tileset (loaded by game_map.py)
|  +- AmigaTiles2..4.PNG  additional terrain tilesets
|  +- AmigaSprites1.PNG   peep spritesheet (loaded by peep.py)
|  +- Sprites.PNG         alternate sprite sheet
|  +- AmigaUI.png         interface background
|  +- AmigaUI_click.png   pressed-button overlay
|  +- AmigaUI_backup.png  backup of UI background
|  +- ButtonUI.png        UI button assets
|  +- Weapons.png         weapon icons
|  `- Knight.gif/png      knight sprite
`- sfx/                   .wav samples plus Populous.CUST tracker module
```

Spritesheet slicing parameters are defined in [settings.py](../settings.py)
(`TILES_V_LINES`, `TILES_H_LINES`, `SPRITE_SIZE`) and applied in
`game_map.load_tile_surfaces()` and `peep.load_sprite_surfaces()`.

### [tools/](../tools/) - diagnostic scripts

```text
tools/
+- map_viewer.py          viewer for tile data
+- tile_diagnostic.py     inspect terrain tile slicing
+- sprite_diagnostic.py   inspect peep sprite slicing
`- house_diagnostic.py    inspect building tile data
```

These are run-by-hand utilities; they are not imported by the game.

### [docs/](../docs/) - documentation

```text
docs/
+- CODE_ARCHITECTURE.md   high-level component map and data flow
+- FILE_STRUCTURE.md      this file
`- TODO.md                pending features and completed work log
```

## Generated artifacts

- `__pycache__/` - Python bytecode caches. The recent `git status` shows these
  staged for deletion at the repo root; they should remain untracked. Add
  `__pycache__/` to `.gitignore` if not already present.
- PyInstaller builds (`build/`, `dist/`, `*.spec`) produced by the GitHub
  Actions workflow are not stored in the repo.

There is no `.gitignore` evidence inspected here; verify and extend as needed.

## Documentation map

- Root: [README.md](../README.md) - overview, quick start, doc links.
- [docs/CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) - components, data flow,
  extension points.
- [docs/FILE_STRUCTURE.md](FILE_STRUCTURE.md) - directory layout and where to
  add new work.
- [docs/TODO.md](TODO.md) - backlog and completed work log.
- [asm/](../asm/) `*_REPORT.md` files - reverse-engineering analysis of the
  original Amiga build.

## Where to add new work

- New gameplay code: add a new top-level `*.py` module next to the existing
  ones (the repo is flat, no package nesting).
- New constants or asset paths: extend [settings.py](../settings.py).
- New assets: place under `data/gfx/` or `data/sfx/` and reference paths from
  [settings.py](../settings.py).
- New diagnostics or one-off viewers: add to [tools/](../tools/).
- New documentation: add a SCREAMING_SNAKE_CASE `.md` file under
  [docs/](../docs/) and link it from [README.md](../README.md).
- Tests: there is no `tests/` directory yet; create one at the repo root if
  adding pytest-based tests.

## Known gaps

- No `.gitignore` was inspected; confirm coverage of `__pycache__/`,
  `build/`, `dist/`, and PyInstaller `*.spec` files.
- The GitHub Actions workflow referenced by [build.ps1](../build.ps1) and
  [push_and_build.py](../push_and_build.py) was not located in this snapshot;
  confirm the `.github/workflows/` path and document it here once verified.
