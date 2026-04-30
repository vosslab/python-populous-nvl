# File structure

## Top-level layout

```text
python-populous/
+- README.md              project overview and quick start
+- AGENTS.md              agent instructions
+- VERSION                project version (synced with pyproject)
+- pip_requirements.txt   pip deps (pygame, numpy, pyyaml)
+- pip_requirements-dev.txt  developer deps (pytest, pyflakes)
+- populous.py            main entry point: instantiates Game().run()
+- build.ps1              Windows commit/tag/push helper
+- push_and_build.py      cross-platform commit/tag/push helper
+- source_me.sh           shell bootstrap for AI agents
+- populous_game/         runtime package (game logic, renderer, audio)
+- asm/                   original Amiga disassembly and analysis
+- data/                  game assets (graphics, audio, scenarios)
+- docs/                  project documentation
+- tools/                 standalone diagnostic and capture scripts
`- tests/                 pytest suite plus lint gates
```

## populous_game/ - runtime package

```text
populous_game/
+- __init__.py            package marker (kept minimal)
+- game.py                Game class: main loop, hud_blit_surface cache
+- settings.py            constants, asset paths, CANVAS_PRESETS
+- layout.py              resolution-aware layout helpers (M4)
+- terrain.py             64x64 altitude grid, tile slicing, building scoring
+- peeps.py               Peep class, sprite loading, animation
+- houses.py              House class: growth, upgrades, spawns
+- camera.py              viewport position, VISIBLE_TILE_COUNT clamps
+- minimap.py             losange overview, click-to-recenter, wheel zoom
+- renderer.py            terrain/sprite/HUD draw path
+- input_controller.py    mouse/keyboard router, dual coordinate spaces
+- ui_panel.py            HUD button hit-test map and tooltips
+- audio.py               AudioManager: music/SFX toggles, mute flags
+- app_state.py           MENU / PLAYING / PAUSED / GAMEOVER state machine
+- mode_manager.py        active-power mode toggles (papal/shield/idle)
+- ai_opponent.py         enemy faction heuristics
+- combat.py              combat resolution, join-forces merging
+- faction.py             Faction identifiers and color palettes
+- mana_pool.py           per-faction mana economy
+- powers.py              quake/flood/volcano/papal/knight powers
+- scenario.py            YAML scenario loader and apply_to_game
+- save_state.py          JSON save/load (schema_version'd)
+- password_codec.py      seven-letter password round-trip codec
+- selection.py           find-button helpers (next battle, papal, knight)
+- keymap.py              key binding lookups
+- peep_state.py          peep state matrix
+- pathfinding.py         pathfinding helpers
+- sprite_geometry.py     iso math helpers
`- assets.py              asset path resolution
```

## asm/ - reverse-engineering reference

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

## data/ - game assets

```text
data/
+- gfx/                   PNG and GIF spritesheets
|  +- AmigaTiles1.png (+ _upscayl_4x_*) primary terrain tileset (4x preferred at runtime)
|  +- AmigaTiles2..4.png (+ _upscayl_4x_*) additional terrain tilesets
|  +- AmigaSprites1.png (+ _upscayl_4x_*) peep spritesheet (4x preferred at runtime)
|  +- Sprites.png (+ _upscayl_4x_*)       alternate sprite sheet
|  +- AmigaUI.png (+ _upscayl_4x_*)       HUD chrome (4x preferred at runtime)
|  +- AmigaUI_click.png (+ _upscayl_4x_*) pressed-button overlay
|  +- ButtonUI.png (+ _upscayl_4x_*)      UI button assets
|  `- Weapons.png (+ _upscayl_4x_*)       weapon icons
+- sfx/                   .wav samples plus Populous.CUST tracker module
+- scenarios/
|  `- scenario_01_plateau.yaml   bundled M8 scenario (flat plateau)
`- tutorial/
   `- tutorial_01.yaml    five-step intro scaffold
```

## tools/ - diagnostic and capture scripts

```text
tools/
+- screenshot.py          headless capture: --state, --ticks, --script, --prefix
+- headless_runner.py     in-process pytest helpers (M3)
+- map_viewer.py          standalone tile data viewer
+- tile_diagnostic.py     terrain tile slicing inspector
+- sprite_diagnostic.py   peep sprite slicing inspector
+- house_diagnostic.py    building tile data inspector
+- button_smoke.py        click coverage for HUD buttons
+- sweep_map_offset.py    map-offset sweep utility
+- screenshots/
|  `- example_play.yaml   YAML script demo for screenshot.py
`- smoke/                 runnable click-to-effect smoke scripts (M3)
   +- README.md           convention and PASS/FAIL rules
   +- effect_quake.py     boot, click, assert quake AOE landed
   +- effect_volcano.py   boot, click, assert volcano AOE landed
   +- effect_flood.py     boot, click, assert flood landed
   +- effect_papal_place.py  boot, place papal magnet, assert
   +- find_buttons.py     verify _find_battle/_find_papal/_find_knight
   +- go_buttons.py       verify _go_papal/_go_build/_go_assemble/_go_fight
   `- canvas_effect_smoke.py  re-runs effect smokes at remaster + large
```

These are run-by-hand utilities; only `headless_runner.py` is imported
(by tests).

## tests/ - pytest suite

Most files match `test_*.py` and follow the focused-assertion rules in
[docs/PYTHON_STYLE.md](PYTHON_STYLE.md). Lint gates include
`test_pyflakes_code_lint.py`, `test_ascii_compliance.py`,
`test_no_magic_numbers.py`, and `test_bandit_security.py`. The shared
helper `tests/git_file_utils.py` resolves the repo root.

## docs/ - documentation

```text
docs/
+- CODE_ARCHITECTURE.md   high-level component map and data flow
+- FILE_STRUCTURE.md      this file
+- USAGE.md               how to run, presets, audio, smoke tests
+- CHANGELOG.md           dated changelog with M1..M8 history
+- PYTHON_STYLE.md        Python conventions (centrally maintained)
+- MARKDOWN_STYLE.md      Markdown conventions (centrally maintained)
+- REPO_STYLE.md          repo conventions (centrally maintained)
+- AUTHORS.md             maintainer list
+- TODO.md                backlog scratchpad
+- PLAYWRIGHT_USAGE.md    Playwright notes
+- TYPESCRIPT_STYLE.md    TypeScript conventions (centrally maintained)
+- CLAUDE_HOOK_USAGE_GUIDE.md  agent-tool guide
`- active_plans/
   `- m2_button_gaps.md   tracks _find_shield and _battle_over removals
```

## Generated artifacts

- `__pycache__/` - Python bytecode caches; should remain untracked.
- PyInstaller builds (`build/`, `dist/`, `*.spec`) produced by the
  GitHub Actions workflow are not stored in the repo.

## Where to add new work

- New gameplay code: add a focused module under
  [populous_game/](../populous_game/).
- New constants, asset paths, or canvas presets: extend
  [populous_game/settings.py](../populous_game/settings.py).
- New layout math: add to
  [populous_game/layout.py](../populous_game/layout.py); never inline a
  bare 320 / 200 literal.
- New assets: place under `data/gfx/`, `data/sfx/`, `data/scenarios/`,
  or `data/tutorial/` and reference paths from `settings.py`.
- New diagnostics or one-off viewers: add to [tools/](../tools/).
- New runnable smoke checks: add to
  [tools/smoke/](../tools/smoke/) following the convention in
  `tools/smoke/README.md`.
- New tests: add to [tests/](../tests/) keeping one or two assertions
  per function per [docs/PYTHON_STYLE.md](PYTHON_STYLE.md).
- New documentation: add a SCREAMING_SNAKE_CASE `.md` file under
  [docs/](../docs/) and link it from [README.md](../README.md).
