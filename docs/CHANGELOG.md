## 2026-04-27

### Post-M5 followups (user-reported fixes)

**Additions and New Features**
- New module [populous_game/cli.py](../populous_game/cli.py) hosts the launcher argparse logic. `populous.py` stays a thin stub and now calls `cli.parse_args()` / `cli.apply_args_to_settings()` before constructing `Game`.
- New CLI flags on `populous.py`: `--preset {classic,remaster,large}`, `--size WIDTHxHEIGHT`, `--window-scale N`, `--fit-screen`, `--visible-tiles N`, `--seed N`, `--screenshot PATH`. All flags except `--seed` are presentation-only; the simulation digest must remain identical across preset switches per [tests/test_canvas_size_compat.py](../tests/test_canvas_size_compat.py).
- `Game.__init__` accepts optional `display_scale` and `seed` kwargs (default `None`). When `None`, behavior is byte-identical to the previous code path (`display_scale = 3`, wall-clock seed). The CLI plumbs both kwargs when set.
- New tests [tests/test_cli_overrides.py](../tests/test_cli_overrides.py) cover preset switch mirror-constant rederivation, `--size` parser error handling, visible-tile override, and the fit-screen integer math.
- New smoke [tools/smoke/cli_overrides.py](../tools/smoke/cli_overrides.py) end-to-end-checks the CLI override path against the booted `Game.internal_surface`.

**Behavior or Interface Changes**
- `populous_game/settings.py:ACTIVE_CANVAS_PRESET` reverted from `remaster` back to `classic`. The remaster default exposed terrain centering and viewport-fill issues that need a follow-up plan; until that work lands, the classic 320x200 path is the polished default. Users wanting the bigger canvas can pass `--preset remaster` or `--preset large`.
- `populous_game/input_controller.py` MOUSEBUTTONDOWN handler now treats any left-click on the menu screen as the equivalent of pressing Enter: transitions to `PLAYING`, calls `spawn_initial_peeps(10)` and `spawn_enemy_peeps(10)`. Previously the menu only accepted ENTER / SPACE keys.

**Decisions and Failures**
- Argparse minimalism rule normally favors zero flags, but the user explicitly requested presentation-only overrides for debugging layout issues. The contract is documented in [populous_game/cli.py](../populous_game/cli.py) and enforced by the existing canvas-size-compat parity test.
- `tests/test_state_machine_integration.py:test_menu_state_ignores_gameplay_input` was renamed to `test_menu_left_click_starts_game` to reflect the new menu-click behavior.

**Developer Tests and Notes**
- `python3 populous.py --help` prints all options without crashing. Default boot path (`python3 populous.py` with no flags) still produces a 320x200 internal canvas in a 960x600 OS window.
- `tests/test_cli_overrides.py`: 9 passed. Pyflakes clean across `populous_game/cli.py`, the updated `populous.py`, the new test file, and the new smoke script.

### M5 docs closeout (closes M5)

**Additions and New Features**
- New [docs/USAGE.md](USAGE.md) documents the canvas presets, audio toggles, headless smoke tests, screenshot tool, and headless test helpers.
- [docs/CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) refreshed to reflect the `populous_game/` package layout, the new `populous_game/layout.py` helper module, the `CANVAS_PRESETS` system, the `hud_blit_surface` cache pattern in `Game.__init__`, and the input controller's canvas-space vs logical-space coordinate split.
- [docs/FILE_STRUCTURE.md](FILE_STRUCTURE.md) refreshed to include `populous_game/layout.py`, `tools/headless_runner.py`, the `tools/smoke/` directory and its seven scripts plus README, and `docs/active_plans/m2_button_gaps.md`.

**Decisions and Failures**
- Optional scenario-wireup task (Patch 13 in the plan) deferred to a later plan; the plan acknowledges this. The bundled `data/scenarios/scenario_01_plateau.yaml` remains unreachable from the menu start, but the loader (`populous_game/scenario.py`) and tests (`tests/test_scenario_loader.py`) confirm the format works.

**Developer Tests and Notes**
- M5 closes the Populous 1 Remaster plan. Final test count: 835 focused tests + 125 pyflakes + lint gates = 962 total passed, 2 skipped. All six `tools/smoke/*.py` scripts exit 0. Default canvas is now `remaster` (640x400).
- `docs/CHANGELOG.md` is approaching ~280 lines after this entry; rotation per [docs/REPO_STYLE.md](REPO_STYLE.md) (target ~1000 lines) is not needed yet, but should be considered before the next major milestone.

### M4 closes -- default is now `remaster`

**Additions and New Features**
- New `populous_game/layout.py` module exposes pure-function helpers (`internal_size`, `hud_scale`, `terrain_origin`, `terrain_viewport_rect`, `minimap_origin`, `button_hit_box`, `scale_logical_xy`, `scale_logical_rect`) that read `populous_game.settings`. Helpers return canvas pixel-space rectangles already scaled by `HUD_SCALE`, so the renderer can blit without doing the math.
- `populous_game/settings.py` adds `CANVAS_PRESETS` dict with three named entries: `classic` (320x200, hud_scale=1, 8 visible tiles), `remaster` (640x400, hud_scale=2, 12 visible tiles), `large` (1280x800, hud_scale=4, 16 visible tiles). `INTERNAL_WIDTH`, `INTERNAL_HEIGHT`, `HUD_SCALE`, and `VISIBLE_TILE_COUNT` mirror the active preset.
- New `tests/test_layout_helpers.py` (5 tests, <=2 asserts each) exercises classic and remaster scaling in isolation by mutating `settings.HUD_SCALE` directly.
- WP-M4-D: new `tests/test_canvas_size_compat.py` boots a Game at each of `classic`, `remaster`, `large` with the same seed, advances 30 ticks, and asserts the simulation digest (corners, peep state, mana for each faction) is byte-identical across presets. Two tests: classic-vs-remaster and classic-vs-large.
- WP-M4-D: new `tests/test_canvas_layout.py` (3 tests, one per preset) verifies that `internal_surface` matches the preset size, every UI button center fits inside the canvas (logical x HUD_SCALE), and the minimap rect fits inside the canvas.
- WP-M4-D: new `tests/test_no_hardcoded_classic_pixels.py` walks `populous_game/` and flags any bare `320` / `200` literal that is not the canonical `CANVAS_PRESETS` definition. Whitelist tolerates comment lines, `populous_game/settings.py`, `populous_game/layout.py`, `alpha=200`, `time.get_ticks() / 200`, color tuples, and `PEEP_LIFE_MAX`.
- WP-M4-D: new `tools/smoke/canvas_effect_smoke.py` re-runs quake / flood / papal / sleep / music / FX / dpad effect smokes at `remaster`, plus a smaller subset (quake / flood / sleep) at `large`. Each check switches the preset BEFORE booting; restores `classic` in `finally`. Exit 0 on all pass.

**Behavior or Interface Changes**
- WP-M4-B: render path migrated to layout helpers. `Game.__init__` now sizes the internal surface from `settings.INTERNAL_WIDTH/HEIGHT` rather than the AmigaUI sprite, and caches a presized HUD blit surface (`self.hud_blit_surface`) once at startup. When `settings.HUD_SCALE > 1` the cache stores a `pygame.transform.scale` copy of `self.ui_image`; at classic the cache IS `self.ui_image`. `populous_game/renderer.py:_draw_gameplay` now blits the cached surface every frame so non-classic presets cover the full canvas without paying a per-frame transform cost. `view_rect` covers the full internal canvas.
- `populous_game/terrain.py` `world_to_screen` and `screen_to_grid` now read terrain origin via `layout.terrain_origin()` so iso math runs in canvas-pixel space. At classic preset the helper returns the same `(MAP_OFFSET_X, MAP_OFFSET_Y)` as before, so behavior is byte-identical.
- `populous_game/input_controller.py` now keeps two coordinate copies on each click: a canvas-space `(mx, my)` for terrain hit-testing (`view_rect`, `screen_to_nearest_corner`) and a `(logical_mx, logical_my) = (mx, my) // settings.HUD_SCALE` for UI hit-testing (`ui_panel.hit_test_button`, `ui_panel.select_at`, `minimap.handle_click`). Mouse-wheel handler does the same for minimap zoom. At classic (`HUD_SCALE == 1`) both copies are identical and the per-event behavior matches pre-patch.
- `populous_game/renderer.py` `_draw_tooltip_or_hover_help` divides the cursor coordinates by `HUD_SCALE` before calling `ui_panel.hit_test_button` and `ui_panel.hover_info_at`, mirroring the input-controller split. Identical behavior at classic.
- WP-M4-C: viewport bounds now read `settings.VISIBLE_TILE_COUNT` instead of a hard-coded `8`. `populous_game/terrain.py:get_visible_bounds`, `populous_game/terrain.py:draw`, and `populous_game/terrain.py:draw_houses` use `n = settings.VISIBLE_TILE_COUNT` for `end_r`/`end_c` (the `draw_houses` migration is required so houses do not clip 8 tiles in while terrain extends to 12 or 16 at remaster/large). `populous_game/camera.py:Camera.__init__`, `Camera.move`, and `Camera.center_on` use `VISIBLE_TILE_COUNT // 2` for the half-extent and `GRID_HEIGHT/WIDTH - VISIBLE_TILE_COUNT` for the clamp. At classic (`VISIBLE_TILE_COUNT == 8`) every value resolves identically to the previous literal `8`/`4`. At remaster (12) and large (16) the iso viewport scales accordingly.
- WP-M4-D: `populous_game/terrain.py:screen_to_nearest_corner` now reads `settings.VISIBLE_TILE_COUNT` and uses `n + 4` slack instead of the hard-coded `12`. At classic (`n == 8`) the search window is still `+ 12` (byte-identical). At remaster (`n == 12`) it grows to `+ 16`; at large (`n == 16`) it grows to `+ 20`. The previous literal was `8 + 4` slack and missed corner-picks near the bottom-right edge of the viewport at remaster and large.
- WP-M4-D: `populous_game/settings.py:ACTIVE_CANVAS_PRESET` switched from `classic` to `remaster`. The four mirror constants (`INTERNAL_WIDTH=640`, `INTERNAL_HEIGHT=400`, `HUD_SCALE=2`, `VISIBLE_TILE_COUNT=12`) are derived from `CANVAS_PRESETS['remaster']` automatically. `tools/screenshot.py --state gameplay --ticks 60` now produces a 640x400 PNG with the iso terrain extending to 12 tiles per side.

**Decisions and Failures**
- Logical UI coordinate space stays 320x200 across every preset; the HUD sprite is reused as-is and scaled by an integer factor at blit time (per DQ-M4-HUD in the plan). No new HUD art is required by this milestone.
- WP-M4-D parity tests confirmed the simulation digest is byte-identical at classic, remaster, and large (`tests/test_canvas_size_compat.py`); the default preset is now `remaster`. Setting `ACTIVE_CANVAS_PRESET = 'classic'` still gives the legacy 320x200 rendering path bit-for-bit, so legacy validation remains available.

**Developer Tests and Notes**
- 962 passed, 2 skipped on full suite after WP-M4-D at the new `remaster` default. Pyflakes clean across `populous_game/`, `tools/`, and `tests/`. `tools/smoke/canvas_effect_smoke.py` exits 0 with PASS lines for every check at remaster (quake / flood / papal / sleep / music / FX / dpad) and at large (quake / flood / sleep). Per-preset screenshots: classic produces 320x200, remaster 640x400, large 1280x800.

### M3 capture-harness wave (closes M3)

**Additions and New Features**
- New module `tools/headless_runner.py` exposes `boot_game_for_tests`, `step_frames`, `inject_click`, `inject_click_at`, `button_center_px`, `tile_center_px`, `capture`, and `surface_pixel_signature`. Tests no longer hard-code 320x200 pixel constants; click positions come from `ui_panel.buttons[action]['c']` scaled by `display_scale * RESOLUTION_SCALE`.
- `tools/screenshot.py` gains `--prefix` flag and an optional `settle_frames` YAML key. `--prefix demo` writes captures as `demo_<name>.png`. `settle_frames: N` advances N frames after each event before any subsequent capture, so animations and AOEs land in the snapshot.
- New `tools/smoke/` directory with six runnable smoke scripts: `effect_quake.py`, `effect_volcano.py`, `effect_flood.py`, `effect_papal_place.py`, `find_buttons.py`, `go_buttons.py`. Each boots a deterministic-seed Game, drives a click->effect chain, and asserts the visible behavior. `tools/smoke/README.md` documents the convention.
- New focused pytest tests under `tests/`: `test_effect_sleep_pause.py`, `test_effect_music_toggle.py`, `test_effect_sfx_toggle.py`. These stay tight (one or two assertions per function) per `docs/PYTHON_STYLE.md`.

**Behavior or Interface Changes**
- The earthquake, volcano, flood, papal, music, FX, sleep effects are all verified by capture-harness scripts. The harness asserts state delta plus, for the quake test, a non-zero pixel difference between pre and post `internal_surface` to catch renderer regressions.

**Fixes and Maintenance**
- Heavy integration tests that mutated peep coordinates and asserted on AOE altitude snapshots have moved from `tests/` to `tools/smoke/`. Per `docs/PYTHON_STYLE.md` strict rules (one or two assertions per function, avoid complex logic in tests), they belong as runnable smoke scripts rather than pytest cases.

**Decisions and Failures**
- Audio assertions read `audio.is_music_playing` and `audio.is_sfx_muted` (the game's own state flags) rather than `pygame.mixer.music.get_busy()`, which is unreliable under `SDL_AUDIODRIVER=dummy`. Suppression is checked by patching the underlying mixer Sound and counting calls.

**Developer Tests and Notes**
- 816 passed, 1 skipped on full suite. Pyflakes clean across `populous_game/`, `tools/`, and `tests/`.
- All six `tools/smoke/*.py` scripts exit 0 with PASS lines for every check when run individually.

### M2 button-revival wave (closes M2)

**Additions and New Features**
- AmigaUI Sleep, Music, and FX buttons are now real, with hit-test entries in `populous_game/ui_panel.py` and tooltip text in `settings.BUTTON_TOOLTIPS`. Geometry estimated from the AmigaUI sprite; refine later via `tools/draw_button_overlay.py` (M2 review artifact).
- `populous_game/audio.py` gains `toggle_music()`, `toggle_sfx_mute()`, `is_music_playing`, `is_sfx_muted`. `play_sfx()` now returns early when SFX are muted. `play_music()` and `stop_music()` keep `is_music_playing` in sync; toggle behavior works in silent mode (no real mixer required).
- `settings.MUSIC_AUTOSTART` (default False) controls whether background music starts on game boot. `Game.__init__` reads this flag once.
- `populous_game/camera.py` gains `Camera.center_on(r, c)` for the find-button camera locators.
- `populous_game/selection.py` gains pure-function helpers `find_next_battle`, `find_papal_target`, `find_next_knight`, `find_nearest_enemy` used by the new UI handlers.
- `populous_game/input_controller.py` gains a `tooltip_messages` queue. Find/go buttons enqueue user-facing messages such as "No active battle" or "No knight" when the runtime state offers no target.

**Behavior or Interface Changes**
- `_find_battle` cycles through peeps in `FIGHT` state, centering the camera on each in turn. `_find_papal` jumps to the player's papal magnet (or leader if leader-tracking lands later). `_find_knight` cycles through peeps with `weapon_type='knight'`. Each tracks a per-cursor index so repeat clicks step to the next target.
- `_go_papal`, `_go_build`, `_go_assemble`, `_go_fight` issue bulk peep orders using existing peep states only (`MARCH`, `SEEK_FLAT`, `JOIN_FORCES`). No new states or rules. Each peep that cannot transition under the existing matrix is left alone; a tooltip surfaces when zero peeps could move.
- `_sleep` toggles between `PLAYING` and `PAUSED` via the existing app-state transitions.
- `_music` toggles `audio.is_music_playing`. `_fx` toggles `audio.is_sfx_muted`.
- `_do_knight` now surfaces a tooltip on activation failure (insufficient mana, no candidate) rather than failing silently.

**Fixes and Maintenance**
- Removed the `pass` stub branch in `populous_game/input_controller.py:_handle_ui_click` that caused `_find_*` and `_go_*` clicks to silently no-op.
- Removed `_find_shield` and `_battle_over` from `populous_game/ui_panel.py` `self.buttons` per the no-silent-stubs rule. Both originals require mechanics that do not exist in the current Python codebase (shield-bearer concept; canonical "battle over" semantics). Tracked in `docs/active_plans/m2_button_gaps.md`. `tests/test_button_gaps_match_hit_test.py` enforces the doc-vs-UI contract.

**Removals and Deprecations**
- `_find_shield` and `_battle_over` removed from the clickable hit-test map until the underlying mechanics are implemented in a later plan.

**Decisions and Failures**
- DQ-7: `_battle_over` original meaning is unconfirmed; following the no-invented-behavior rule, the button is removed from the UI rather than wired to a guessed action.
- The "no silent stubs" invariant is enforced by a new `tests/test_no_silent_button_stubs.py` that clicks every button under controlled preconditions and asserts at least one observable channel (game state, audio, camera, mode, peep states, knight count, or power cooldowns) moved.

**Developer Tests and Notes**
- 747 passed, 1 skipped on full suite. New tests: `test_audio_toggle.py`, `test_button_handler_coverage.py`, `test_no_silent_button_stubs.py`, `test_button_gaps_match_hit_test.py`, `test_find_buttons.py`, `test_go_buttons.py`, `test_ui_options_do_not_change_simulation_digest.py`, `test_effect_sleep_pause.py`. `tests/test_ui_panel.py` updated since `_find_shield` is no longer at the base center.
- Pyflakes clean across `populous_game/`, `tools/`, and `tests/`.

### M1 terrain-revival wave (closes M1)

**Additions and New Features**
- `GameMap.randomize` now accepts an explicit `seed` parameter for deterministic heightmap generation, mirroring the original Amiga Populous "world code -> deterministic terrain" model. Same seed produces the same map. Default `seed=None` continues to use the module-global random state. `tests/test_terrain_seed_determinism.py` locks this in.
- `GameMap.find_nearest_land(r, c)` performs a breadth-first search over the corner grid and returns the closest corner with altitude > 0 (or None if no land exists). Used by peep spawning to handle water tiles without flattening the map.

**Behavior or Interface Changes**
- Menu-Enter ("New Game") no longer calls `game_map.set_all_altitude(3)`. The randomized mixed-terrain heightmap is preserved end-to-end, restoring authentic Populous-style water and land at boot. `tests/test_menu_enter_preserves_randomized_heightmap.py` enforces this.
- `Game.spawn_initial_peeps` and `Game.spawn_enemy_peeps` fall back to `GameMap.find_nearest_land` when the random pick is water (altitude 0). The requested peep count is now produced exactly, instead of silently under-spawning.
- `tools/screenshot.py` boot path also drops the `set_all_altitude(3)` call so headless captures show the same mixed terrain the player sees.

**Fixes and Maintenance**
- **All-land map on fresh game.** Root cause: `input_controller.py:83` called `set_all_altitude(3)` after `randomize()` had already produced mixed terrain, overwriting every corner with 3 and removing all water. The flatten was a workaround for spawn fragility, not a generator. Removed; spawn now searches for land instead.

**Removals and Deprecations**
- None. `GameMap.set_all_altitude` itself stays as a public utility for tests and future scenario loading.

**Decisions and Failures**
- Spawn now raises `RuntimeError("...no land tile...")` when the entire map is water, instead of silently producing zero peeps. Per `docs/PYTHON_STYLE.md` "do not hide bugs with defaults," loud failure is preferred to silent under-production. `tests/test_enemy_spawn.py::test_no_land_raises` updated accordingly.
- Followed the original Populous deterministic-from-seed model rather than the asm-exact LCG (multiply by 0x24a1, add 0x24df, mask 16 bits) since matching the exact generator is out of scope; what matters is that same-seed reproduces the same world.

**Developer Tests and Notes**
- New tests: `tests/test_terrain_seed_determinism.py`, `tests/test_terrain_mixed.py`, `tests/test_peep_spawn_finds_land.py`, `tests/test_menu_enter_preserves_randomized_heightmap.py`. 722 passed, 1 skipped on full suite. Pyflakes clean across changed files.
- Verified visually with `python3 tools/screenshot.py --state gameplay --ticks 60 -o /tmp/m1_check.png`; rendered viewport shows altitude variation rather than a uniform plateau.

### Additions and New Features

- Added `tools/screenshot.py` headless capture tool. Boots the game under `SDL_VIDEODRIVER=dummy`, advances the real event loop and input controller, and saves the internal surface to a PNG. Supports a YAML script format (`tools/screenshots/example_play.yaml`) that injects keyboard and mouse events at scheduled ticks and dumps named captures along the way.
- New `tests/test_smoke_ui_buttons.py` exercises every dpad button click path and a 5-second mixed-faction gameplay loop. Catches `AttributeError` regressions in the renderer and crash paths in combat resolution that the bare-boot smoke test cannot reach.

### Behavior or Interface Changes

- Pressing Enter from the main menu now calls `game_map.set_all_altitude(3)` before spawning peeps. Without this, the default all-zeros heightmap left the entire viewport under water on a fresh game.
- Peep state transitions: DEAD is now reachable from any non-DEAD state (death by absorption, combat, drown, life cap, merge). The transition matrix only constrains non-terminal moves. DROWN -> DEAD still works via the universal rule; no other transitions widened.

### Fixes and Maintenance

- **Renderer crash on dpad click.** `renderer.py:82` referenced `self.game.ui_buttons`, which has not existed since the M2 ui_panel decomposition. Fixed to `self.game.ui_panel.buttons`. Crash reproduced by clicking any arrow button after starting a new game.
- **Same-faction merge crash.** `combat.join_forces()` killed the loser via `transition(DEAD)`, but the strict transition matrix forbade SEEK_FLAT -> DEAD (and several other non-FIGHT states). Loosened the matrix as above.
- **Terrain rendered off-screen since M2.** `MAP_OFFSET_X` is computed from `SCREEN_WIDTH // 2`, but `SCREEN_WIDTH` was set to 1280 (intended OS-window width) while the internal canvas is 320 wide. The pre-M2 code mutated `settings.SCREEN_WIDTH` at runtime to the loaded UI-image width; the M2 cleanup removed that mutation without correcting the constants. Reset `SCREEN_WIDTH=320`, `SCREEN_HEIGHT=200` and added a comment block explaining what these describe (internal canvas, not OS window). Confirmed via headless screenshot: viewport now shows the green plateau and peep sprites.

### Removals and Deprecations

- None.

### Decisions and Failures

- The "no visible terrain on a fresh game" bug went undetected because no test actually inspected the rendered surface; the smoke test only asserted no exceptions and that frames were produced. Adding a headless-capture tool plus a button-click smoke test closes the most expensive class of regression we have hit during the remaster.

### Developer Tests and Notes

- 724 passed, 2 skipped, 1 xpassed after the fixes; pyflakes clean across `populous_game/`, `tools/`, and `tests/`.
- Added `pyyaml` to imports of `tools/screenshot.py` (already present in `pip_requirements.txt`).

### M7 polish wave (closes M7)

**Additions and New Features**
- Tooltips on every UI button: `BUTTON_TOOLTIPS` table in settings, `ui_panel.tooltip_for(action)` lookup, `renderer._draw_tooltip_or_hover_help()` overlays.
- Hover help on terrain, peeps, and houses: `ui_panel.hover_info_at(mx, my, game)` returns a typed dict; renderer draws a small panel near the cursor.
- Drag-to-paint terrain: hold left/right mouse and drag in the viewport to repeatedly raise/lower at `DRAG_PAINT_INTERVAL` pacing (50 ms). Suppressed while paused or in a power/papal/shield mode.
- Mouse-wheel minimap zoom: `Minimap.zoom`, `Minimap.set_zoom(z)` clamped to `[MINIMAP_ZOOM_MIN, MINIMAP_ZOOM_MAX]`. `MOUSEWHEEL` events over the minimap rect adjust by `MINIMAP_ZOOM_STEP * event.y`.
- Command queue visualization: per-frame thin lines from each player MARCH peep to its `target_x/target_y`, in the player faction color.

**Behavior or Interface Changes**
- UI button hit-test (`ui_panel.hit_test_button`) now returns the diamond whose center is closest to the click, not the first match in dict-iteration order. Fixes the user-reported "I clicked one button and got another." Prior code returned the first dict entry whose diamond contained the cursor; with adjacent diamonds sharing edges (dx == hw, dy == hh), boundary clicks were order-dependent.

## 2026-04-27 (M8 wave)

### Additions and New Features

- Scenario loader (`populous_game/scenario.py`): YAML descriptors with `format_version`, seed, altitude, faction starting peep counts, mana, and password. `load_scenario_by_name()` reads from `data/scenarios/`; `apply_to_game()` seeds RNG and spawns from the scenario.
- Bundled scenario `data/scenarios/scenario_01_plateau.yaml` (Easy: flat plateau, 10 player peeps vs 5 enemies, password `AAAJSCB`).
- Password codec (`populous_game/password_codec.py`): seven-letter `A`-`Z` round-trip codec mapping a 32-bit-ish seed space to passwords. Decoder accepts lowercase and short (zero-padded) inputs; raises on non-alpha chars or oversized inputs.
- JSON save/load (`populous_game/save_state.py`): `schema_version` field, full heightmap, houses, peeps, and mode flags. `save_to_dict`, `save_to_file`, `load_from_dict`, `load_from_file`. Round-trips state bit-for-bit at the precision documented by the snapshot helper.
- Tutorial scaffold (`data/tutorial/tutorial_01.yaml`): five-step intro keyed to scenario 1.
- 13 new M8 tests cover password round-trip, scenario load + apply, save/load round-trip, and tutorial YAML schema.

### Fixes and Maintenance

- **Audio crackle / static fix.** Bundled SFX in `data/sfx/` had inconsistent and sometimes implausible sample-rate metadata (one batch claimed 443361 Hz; pygame played them as a tenth-second burst). `audio.AudioManager.load_sfx` now opens each WAV via the stdlib `wave` module, sanitizes any rate outside `[1000, 48000]` Hz down to a fallback 11025 Hz, converts unsigned 8-bit samples to signed 16-bit, nearest-sample-resamples to the mixer rate, and constructs a `pygame.mixer.Sound` from the corrected raw bytes. Mixer is initialized at 22050 Hz mono signed-16, matching Amiga playback.

### Developer Tests and Notes

- 724 passed, 2 skipped, 1 xpassed; pyflakes clean.

## 2026-04-26 (Evening)

### Additions and New Features

**M5 Wave 3 (final M5 wave): Enemy spawn, AI opponent, UX feedback, sim-boundary test**

- Enemy spawn (W5.E): `spawn_initial_peeps(count, faction_id)` now accepts faction param; `spawn_enemy_peeps(count)` spawns enemies near bottom-right map corner (opposite player spawn). Integrated into game start transition.
- AI opponent (W5.F): Created `AIOpponent` class with v1 heuristics per asm/PEEPS_REPORT.md: (1) idle low-life peeps seek flat for building, (2) mass march above `AI_MARCH_THRESHOLD` (6 peeps) toward player centroid. Deterministic (no time.time() calls). `AI_TICK_INTERVAL = 1.0s` per settings.
- UX faction feedback (W5.G): Faction color indicators (3x3 squares) drawn below peeps and houses; mode indicator text (PAPAL/SHIELD/IDLE) in top-left corner. Uses colorblind-safe or Amiga palette per `USE_COLORBLIND_PALETTE`.
- Simulation-boundary test (W5.I): Cross-milestone gate ensuring UI changes (colorblind palette toggle, selection, mode flags) do not affect simulation outcomes. Created `snapshot_game()` for deterministic state capture.
- Added AI opponent constants to settings: `AI_TICK_INTERVAL`, `AI_BUILD_LIFE_THRESHOLD`, `AI_MARCH_THRESHOLD`, `AI_MARCH_BATCH`.
- Win/lose condition implementation: `_check_game_over()` transitions to GAMEOVER when all enemies or all players eliminated (peeps + houses).
- Added `House.faction_id` alias for compatibility with `Peep.faction_id`.

### Behavior or Interface Changes

- Game state machine: PLAYING -> GAMEOVER transition now fired by `_check_game_over()` during update cycle.
- Enemy peeps are spawned and integrated into AI decision-making loop.
- Mode indicator overlaid on gameplay (IDLE/PAPAL/SHIELD).
- Peep state machine fix: allow direct `state = DEAD` assignment when building house (bypasses invalid transition check).

### Fixes and Maintenance

- Fixed `try_build_house()` to set `self.state = DEAD` directly instead of calling `transition()` (avoid invalid state transition).
- Added `faction_id` property to `House` class for consistency.
- All 486 tests pass (35 new test cases added in M5.W5 patches).

### Removals and Deprecations

- None

### Decisions and Failures

- AI march behavior is currently a simple state transition without pathfinding toward target; peeps still use random walk behavior. Full pathfinding integration deferred to future phases.
- Selection ring not implemented in W5.G (focused on faction color + mode indicator).

### Developer Tests and Notes

**New test suites (M5 Wave 3):**
- `test_enemy_spawn.py` (8 tests): Enemy peep spawn location validation, faction assignment, water avoidance
- `test_ai_smoke.py` (7 tests): AI existence, tick accumulation, march threshold, transition validation
- `test_ux_faction_feedback.py` (9 tests): Mode indicator rendering, faction color indicators, palette switching
- `test_ui_does_not_change_simulation.py` (4 tests): Colorblind palette toggle, selection, mode toggle, determinism across runs
- `test_win_lose_conditions_m5.py` (7 tests): WIN on enemy elimination, LOSE on player elimination, multi-faction scenarios

- Total test count: 486 passed, 2 skipped, 1 xpassed (from 451 baseline)
- Simulation-boundary test PASSES: UI changes confirmed not to perturb simulation
- Win condition CONFIRMED: fires when all enemies removed in smoke test
- No blockers discovered; all patches landed successfully

---

## 2026-04-26

### Additions and New Features

- Introduced `Faction` enum in `populous_game/faction.py` with PLAYER (0), ENEMY (1), NEUTRAL (2) identifiers
- Added `faction_id` parameter to `Peep` and `House` constructors (defaults to PLAYER for backward compatibility)
- Added faction color palettes to settings: colorblind-safe (blue/orange/gray) and Amiga classic (blue/red/gray)
- Added `Renderer.faction_color(faction_id)` static method to look up faction colors based on active palette
- Houses built by peeps now inherit the peep's faction

### Behavior or Interface Changes

- Settings now includes `USE_COLORBLIND_PALETTE` toggle (default True) to switch between faction color schemes
- Faction system establishes the foundation for M5.W5.B-F (pathfinding, combat, peep state machine, enemy spawn, AI)

### Fixes and Maintenance

- Ensured all file indentation is consistent (tabs throughout populous_game/)
- All faction-related instantiations maintain backward compatibility

### Removals and Deprecations

- None

### Decisions and Failures

- Faction values are plain ints (0, 1, 2), not enum.Enum, per repo PYTHON_STYLE.md preference for native types
- Faction marker rendering (2x2 colored marker on peeps/houses) deferred to M5.W5.G (UX feedback workstream)
- Selection ring and mode indicator also deferred to M5.W5.G

### Developer Tests and Notes

- Added 9 new tests in `tests/test_faction.py`:
  - Faction constant and name mapping verification
  - Peep default and custom faction assignment
  - House default and custom faction assignment
  - Faction color palette switching (colorblind vs Amiga)
  - Peep spawned from house inherits faction
- Total test count: 292 passed (273 baseline + 19 new tests)
- Smoke test verified: game boots headless without crashing
- All existing code remains functional with default PLAYER faction
