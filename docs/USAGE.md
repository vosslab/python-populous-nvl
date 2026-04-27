# Usage

## Quick start

Run the game from a shell at the repo root:

```bash
source source_me.sh && python3 populous.py
```

The default presentation is the 320x200 `classic` preset. The
`remaster` (640x400) and `large` (1280x800) presets are still selectable
via the `--preset` CLI flag described below.

## Command-line options

The launcher accepts a small set of flags for tweaking presentation at
runtime. Every flag except `--seed` is presentation-only; CLI overrides
must not change simulation outcomes (parity is enforced by
[tests/test_canvas_size_compat.py](../tests/test_canvas_size_compat.py)).

| Flag | Description |
| --- | --- |
| `-p, --preset {classic,remaster,large}` | Select a named canvas preset. |
| `-s, --size WIDTHxHEIGHT` | Override internal canvas size (e.g. `--size 640x400`). Does not change `HUD_SCALE` or `VISIBLE_TILE_COUNT`; those track `--preset`. |
| `-w, --window-scale N` | OS window scale multiplier (default 3 -> 960x600 at classic). |
| `-f, --fit-screen` | Pick the largest `--window-scale` that fits the current monitor. |
| `-t, --visible-tiles N` | Override `settings.VISIBLE_TILE_COUNT`. |
| `-S, --seed N` | Deterministic terrain seed for `GameMap.randomize`. The only flag that affects simulation. |
| `-o, --screenshot PATH` | Capture the first rendered frame to PATH (PNG) and exit. |

Examples:

```bash
source source_me.sh && python3 populous.py --preset remaster
source source_me.sh && python3 populous.py --size 640x400 --window-scale 2
source source_me.sh && python3 populous.py --fit-screen
source source_me.sh && python3 populous.py --seed 12345
source source_me.sh && python3 populous.py --preset remaster --screenshot /tmp/preview.png
```

## Canvas presets

Three canvas presets ship with the remaster, declared in
`populous_game/settings.py:CANVAS_PRESETS`:

| Preset    | Internal size | HUD scale | Visible tiles |
| ---       | ---           | ---       | ---           |
| classic   | 320 x 200     | 1         | 8             |
| remaster  | 640 x 400     | 2         | 12            |
| large     | 1280 x 800    | 4         | 16            |

To switch presets, pass `--preset` on the command line (preferred) or
edit `populous_game/settings.py` and change `ACTIVE_CANVAS_PRESET` to
one of the three names; the four mirror constants (`INTERNAL_WIDTH`,
`INTERNAL_HEIGHT`, `HUD_SCALE`, `VISIBLE_TILE_COUNT`) follow
automatically.

Simulation behavior is preset-independent: the same seed produces the
same world and the same per-tick state digest at every preset. Only
presentation changes. `classic` is the current default; `remaster` and
`large` exist for users who want a larger window but still need the
remaster terrain origin / viewport-fill follow-up before they look as
polished as the classic preset.

## Audio

The game boots silent by default. Click the music button (`_music`) to
start the background tracker; click again to stop. Click the FX button
(`_fx`) to toggle SFX mute. To start music automatically on boot, set
`settings.MUSIC_AUTOSTART = True` in `populous_game/settings.py`.

The sleep button (`_sleep`) toggles simulation pause via the
`PLAYING <-> PAUSED` app-state transition. Audio toggles do not pause
the simulation.

## Headless smoke tests

Runnable smoke scripts under [tools/smoke/](../tools/smoke/) boot a
deterministic-seed `Game`, drive a click-to-effect chain, and assert the
visible behavior. Each script exits 0 on PASS and non-zero on FAIL.
Useful for spot-checking renderer or input changes:

```bash
source source_me.sh && python3 tools/smoke/effect_quake.py
source source_me.sh && python3 tools/smoke/effect_volcano.py
source source_me.sh && python3 tools/smoke/effect_flood.py
source source_me.sh && python3 tools/smoke/effect_papal_place.py
source source_me.sh && python3 tools/smoke/find_buttons.py
source source_me.sh && python3 tools/smoke/go_buttons.py
source source_me.sh && python3 tools/smoke/canvas_effect_smoke.py
```

`canvas_effect_smoke.py` re-runs the click-to-effect checks at
`remaster` and a smaller subset at `large`, so renderer regressions in
the upscaled HUD path show up immediately.

## Headless screenshot tool

[tools/screenshot.py](../tools/screenshot.py) captures the internal
surface to PNG. Basic usage:

```bash
source source_me.sh && python3 tools/screenshot.py \
    --state gameplay --ticks 60 -o /tmp/check.png
```

For scheduled events (clicks at tick N, named captures, settle frames),
pass a YAML script via `--script my_play.yaml`; see
[tools/screenshots/example_play.yaml](../tools/screenshots/example_play.yaml).
The `--prefix` flag prepends a string to every named capture so multiple
runs can coexist:

```bash
source source_me.sh && python3 tools/screenshot.py \
    --script tools/screenshots/example_play.yaml --prefix demo
```

## Headless test helper

[tools/headless_runner.py](../tools/headless_runner.py) exposes the
in-process helpers used by the pytest smoke suite:

- `boot_game_for_tests` - construct a `Game` under
  `SDL_VIDEODRIVER=dummy` with a deterministic seed.
- `step_frames` - advance the real event loop and update tick.
- `inject_click`, `inject_click_at` - synthesize mouse events.
- `button_center_px(game, action)` - return the canvas-space pixel
  center of a HUD button. Tests should use this rather than hard-coding
  320x200 pixel constants; the helper scales by `HUD_SCALE` so the same
  test passes at every preset.
- `tile_center_px` - canvas-space center of an iso tile.
- `capture` - returns a copy of the internal surface.
- `surface_pixel_signature` - cheap hash for renderer-regression checks.

## Running tests

The full suite runs with pytest:

```bash
source source_me.sh && python3 -m pytest tests/
```

To skip slow lint gates while iterating, ignore them on the command
line:

```bash
source source_me.sh && python3 -m pytest tests/ \
    --ignore=tests/test_pyflakes_code_lint.py \
    --ignore=tests/test_ascii_compliance.py \
    --ignore=tests/test_no_magic_numbers.py \
    --ignore=tests/test_bandit_security.py
```

Current totals: ~835 focused tests plus the lint gates, ~962 in all.
