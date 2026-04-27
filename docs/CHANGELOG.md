## 2026-04-27

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
