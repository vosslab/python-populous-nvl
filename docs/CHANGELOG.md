## 2026-04-28

### Cleanup: bandit fix, dead skipped tests deleted

**Fixes and Maintenance**
- `tools/smoke/debug_layout.py` writes `debug_layout_smoke.png` to the
  current working directory instead of `/tmp/debug_layout_smoke.png`,
  clearing the last bandit issue (B108 hardcoded_tmp_directory). The
  smoke test still runs the same frame-capture + pixel-sample check;
  only the output path changed.

**Removals and Deprecations**
- `tests/test_no_magic_numbers.py` deleted. The test was an
  `@pytest.mark.xfail(strict=False)` "soft gate" that called
  `pytest.skip(...)` whenever issues existed, so it neither passed
  nor failed meaningfully. Its allowlist had drifted out of sync with
  the current settings module and its regex missed many real magic
  numbers. No replacement; the linting it pretended to do was never
  enforced.
- `tests/test_settings_immutable.py` deleted. The test imported a
  module (`populous_game.game_map`) that no longer exists, so the
  `ImportError` branch in its body always fired and `pytest.skip`
  was the only outcome. The premise (settings constants are
  immutable) is also incompatible with the current architecture --
  `populous_game.cli.apply_args_to_settings` deliberately mutates
  settings per `--preset`, `--size`, and `--visible-tiles`.

### New island terrain generator replaces legacy row-major noise

**Additions and New Features**
- New `IslandProfile` class plus two profile constants in
  [populous_game/terrain.py](../populous_game/terrain.py):
  `CLASSIC_REFERENCE` (Amiga-faithful three-blob walker) and
  `REMASTER_ISLANDS` (default; tuned for 1-3 large smooth inhabitable
  islands). Both use the same growth engine -- only parameters differ.
- `GameMap._randomize_islands` shared engine: starts from all-water
  corners, picks 3 seeds (with chebyshev min-spacing for the remaster
  profile), runs bounded random walks that call `propagate_raise`
  until each blob reaches its `peak_target` AND `min_walk_steps`.
  Heights only change through the constrained raise primitive, so
  slopes always stay smooth.
- `GameMap.propagate_raise(..., max_altitude=None)` now accepts an
  optional per-corner cap callable. `max_altitude=None` (the default
  for every existing gameplay caller) preserves bit-exact pre-change
  behavior. The island generator passes `_island_max_altitude`,
  which encodes a one-tile water moat by capping rows/cols 0,1 and
  grid-1,grid at altitude 0 and ramping up by chebyshev distance to
  the edge.
- Tile-mask morphology cleanup pass on the remaster path:
  `_land_tile_mask`, `_dilate`, `_erode`, `_close_mask`,
  `_filter_components`, `_morphology_cleanup`, `_realise_mask_diff`.
  Grow-only: closing joins narrow water cracks and absorbs
  near-touching blobs; new "should be land" tiles are realised via
  constrained `propagate_raise` so coast slopes stay smooth.
  Speck removal is deferred to a future constrained-lower pass.
- Validation pipeline on the remaster path: `_edge_tiles_all_water`,
  `_connected_components` (iterative BFS via `collections.deque`),
  `_count_buildable_tiles`, `_count_spawnable_tiles`,
  `_validate_island_map`, `_score_island_map`. Fixed-seed tests must
  pass validation; runtime fallback only restores the best-scoring
  attempt and logs seed/profile/score so a follow-up tuning pass
  can investigate.
- NumPy is used as an internal implementation detail of the generator
  helpers (tile masks, edge checks, buildable/spawnable counts via
  vectorized 4-corner stencils). Single conversion entry point
  `GameMap._corner_array()` localizes the migration. The public
  `GameMap` API stays on list-of-lists corners for this milestone.
- New test file
  [tests/test_terrain_islands_generator.py](../tests/test_terrain_islands_generator.py)
  with 49 tests covering: classic + remaster determinism, smoothness
  invariants, large connected landmass, validation pass for fixed
  seeds, buildable floor (conservative >=30 floor independent of the
  tunable `VALIDATION_BUILDABLE_TILES_MIN`), water-moat invariant on
  corners, edge tiles all water (100% coverage), and that
  `propagate_raise(max_altitude=...)` respects the moat under
  aggressive raise loops.

**Behavior or Interface Changes**
- `GameMap.randomize` now defaults to `profile="remaster_islands"`.
  Existing callers in `game.py`, `input_controller.py`, and
  test files that pass only `seed=` are unchanged in spelling but
  now receive island terrain instead of row-major noise.
- `randomize` signature: `min_level` and `max_level` removed (they
  were exclusively consumed by the old row-major path) and
  `profile=` keyword added.
- The two valid `profile` values are `"remaster_islands"` (default)
  and `"classic_reference"`. Any other value raises `ValueError`.
- New CLI flag `-m / --map-profile` selects the generator at launch
  time. Default `remaster_islands`. `classic_reference` runs the
  Amiga-faithful walker for side-by-side visual comparison.
- `Game.__init__` accepts a new `map_profile` kwarg; the value is
  stored on `self.map_profile` and passed to every `randomize` call
  including the in-game `_reset_game` and the `F3` re-randomize hook
  in `input_controller.py`.

**Removals and Deprecations**
- The legacy `_randomize_legacy_noise` row-major bounded random walk
  is removed entirely. It produced continent-style noisy heightmaps
  that did not match the Populous "island nation" feel and could not
  reach the moat-locked invariant the remaster requires. The Amiga
  shape grammar is preserved by `classic_reference`; nothing else of
  value was lost.

**Decisions and Failures**
- Initial cut used a `can_raise(r, c) -> bool` predicate on
  `propagate_raise` (locks moat corners). First smoke run found a
  smoothness violation: the cascade that recursed from an interior
  corner toward a moat-locked neighbor was refused at the moat,
  leaving a delta-2 (or delta-3) cliff. Fix: replaced the boolean
  predicate with a `max_altitude(r, c) -> int` callable. The cap
  ramps from 0 at the moat to ALTITUDE_MAX deep inland, so the
  cascade naturally caps at the right altitude per corner instead
  of refusing-and-cliffing. Recorded so this trap is documented.
- Initial REMASTER_ISLANDS profile (`min_walk_steps=1500`,
  `walk_budget=9000`) over-grew to 90%+ land fraction (continent,
  not islands). Each post-peak walker step lifts one cascade ring
  outward, so 1500 steps per walker x 3 walkers fills the map.
  Tuned down to `min_walk_steps=20`, `walk_budget=120` after smoke
  testing; remaster profile now consistently lands at 28-36% land.
- Chose one engine + two profiles over two independent generators
  (matches the "fewer, longer-growing walkers with validation"
  philosophy) -- profiles only change parameter dataclasses, not
  the engine.

**Developer Tests and Notes**
- All 1146 non-pre-existing tests pass (`test_bandit_security` flags
  a pre-existing temp-path issue in `tools/smoke/debug_layout.py`,
  unrelated; one indentation test on `tests/test_canvas_size_compat.py`
  is also pre-existing). Both deselected explicitly.
- pyflakes clean for the modified production file and the new test
  file.
- Smoke run results: classic profile produces ~40-63% land
  (validation off; reference fidelity); remaster profile produces
  28-36% land with all 4 sample seeds passing validation on the
  first attempt. Final tuning expected via screenshot review in a
  follow-up.

## 2026-04-27

### Research: original map-gen algorithm captured in asm/MAP_GEN_REPORT.md

**Additions and New Features**
- [asm/MAP_GEN_REPORT.md](../asm/MAP_GEN_REPORT.md): documents the
  original Amiga genesis pass at `_make_alt`
  ([asm/populous_prg.asm:1189](../asm/populous_prg.asm)),
  `_make_thing` (line 1208), `_raise_point` (line 1274), and
  `_make_map` (line 1420). Conclusion: the original generator is
  three localized random walks that each pile altitude into a
  bounded region until any tile hits altitude 6, with `_raise_point`
  enforcing a "neighbors differ by at most 1" constraint that
  cascades raises outward to produce smooth pyramidal islands.
  The (4,2) / (2,4) / (3,3) parameter trio in `_make_alt` produces
  one east-west island, one north-south island, and one rounder
  blob, which is why the original maps look like island nations
  rather than noise. The current Python `GameMap.randomize` at
  [populous_game/terrain.py:373](../populous_game/terrain.py) does
  a row-major random walk instead -- different algorithm, different
  output. Port deferred until after M6 close-out; the existing
  `GameMap.propagate_raise` at line 94 is already a direct
  equivalent of `_raise_point`, so a future port mostly needs the
  three seeded walkers from `_make_thing` plus the all-water
  initial state.

### M6 followup: BASE_ALTITUDE_STEP fix (vertical walls regression)

**Fixes and Maintenance**
- `populous_game/settings.py:BASE_ALTITUDE_STEP` was set to 1, but the original `world_to_screen` formula computed `elev = altitude * TILE_HALF_H` -- so the altitude step IS `TILE_HALF_H`, not 1. The mismatch dropped iso elevation to 1/8th of the original at classic preset (1 px per altitude unit instead of 8). The side-face fill stack in `terrain.draw_tile` (`gap // half_h`) computed 0 copies at every altitude, so cliffs rendered as ungraded slopes -- the "vertical walls" regression the user reported. Fix: `BASE_ALTITUDE_STEP = BASE_TILE_HALF_H` so the two stay in lock-step. Verified by raising one corner 8 times and rendering the resulting square pyramid: the iso-projected diamond now shows proper terraced cliff faces all the way down to water level.
- `populous_game/renderer.py:_draw_debug_layout_overlay` reorders the magenta anchor square to draw AFTER the red tile centers, so the anchor stays visible when a tile center projects to the anchor pixel (common case after the altitude fix). Updated `tests/test_debug_layout_overlay_matches_transform.py` continues to pass.

### M6 followup: -t / --visible-tiles drops TERRAIN_SCALE to 1

**Behavior or Interface Changes**
- `--visible-tiles N` now also resets `settings.TERRAIN_SCALE` to 1. Each preset declares `(visible_tiles, terrain_scale)` as a paired default (e.g., remaster = 8 tiles at 2x chunky pixels): overriding the tile count alone while keeping chunky scale on pushes the iso diamond past the AmigaUI iso-hole boundary at any preset bigger than classic. With this change, `-p remaster -t 12` shows 12 native-size tiles inside the well (bbox 12*32 by 12*16 = 384x192, fits in the 512x256 remaster well) rather than 12 chunky tiles overflowing the canvas. Trade-off is explicit: the user picks chunkiness OR more visible area, not both.

### M6 followup: --debug-layout couples flat water + skips victory check

**Behavior or Interface Changes**
- `--debug-layout` now implicitly enables `settings.DEBUG_FLAT_WATER`. The two debug knobs are complementary: the overlay draws diagnostic graphics; flat water zeroes the heightmap so the iso-diamond shape is unambiguous against the AmigaUI HUD chrome. Coupling them at the CLI means one flag instead of editing settings.py while debugging. Per `docs/PYTHON_STYLE.md` argparse-minimalism, no separate `--flat-water` flag is added.

**Fixes and Maintenance**
- `populous_game/game.py:spawn_initial_peeps` and `spawn_enemy_peeps` short-circuit when `DEBUG_FLAT_WATER` is set. Pressing `N` to start a new game with the flag on no longer crashes with `RuntimeError: Cannot spawn peep: no land tile exists on the map`. Reproducer: `./populous.py -p remaster --debug-layout`.
- `populous_game/game.py:_check_game_over` short-circuits when `DEBUG_FLAT_WATER` is set. Without this, the empty-faction rule would auto-flip the state to `WIN` on the first frame (zero enemy peeps + zero enemy houses), making the layout overlay impossible to inspect.

**Developer Tests and Notes**
- Full suite: 959 passed, 2 skipped.
- pyflakes clean.

### M6 followup: terrain renders under HUD via iso-hole transparency

**Additions and New Features**
- [populous_game/iso_hole.py](../populous_game/iso_hole.py): new module
  exposing `flood_fill_iso_hole(surface)`. Identifies the largest
  4-connected near-black region on an SRCALPHA pygame surface and sets
  its alpha to 0, mutating the surface in place. Pixel detection uses
  the same `WELL_BLACK_THRESHOLD = 8` rule as
  [tools/measure_map_well.py](../tools/measure_map_well.py) so the
  reported map-well rect and the punched hole always agree. Returns
  the cleared-pixel count for sanity checks.

**Fixes and Maintenance**
- The AmigaUI HUD sprite has an iso-DIAMOND-shaped opaque-black region
  in the center where the original Amiga rendered terrain. Pre-fix the
  renderer painted that opaque diamond first and then drew the iso
  terrain on top: at remaster / large the terrain layer covers its
  iso-DIAMOND BBOX (not the diamond shape itself), so the bbox corners
  overpaint the dpad in the bottom-left, the FX / sleep buttons in
  the bottom-right, and the powers panel on the right. The user
  reported this as "buttons disappear under blue water" with
  `DEBUG_FLAT_WATER` on.
- Fix is two-part. First,
  [populous_game/assets.py](../populous_game/assets.py) `load_all`
  calls `iso_hole.flood_fill_iso_hole(_UI_IMAGE)` immediately after
  `convert_alpha`, so the loaded HUD surface (and the cached
  `hud_blit_surface` derived from it via `pygame.transform.scale`)
  has alpha=0 across the iso diamond. Second,
  [populous_game/renderer.py](../populous_game/renderer.py)
  `_draw_gameplay` reverses the layer order: terrain-space passes
  draw first, then the HUD blit on top (with its transparent diamond
  exposing the terrain underneath), then HUD-space overlays.
- Verified visually with `DEBUG_FLAT_WATER = True` at remaster: the
  blue diamond is now fully contained inside the iso-hole, and the
  dpad / FX / sleep / powers / shield / minimap chrome is fully
  visible at every corner. Reset `DEBUG_FLAT_WATER` back to False
  before staging.

**Behavior or Interface Changes**
- [populous_game/renderer.py](../populous_game/renderer.py)
  `_draw_gameplay` render order changed. Previously: black fill; HUD
  blit; button-flash; terrain; houses; peeps; papal; shield-marker;
  minimap; aoe-preview; cooldown-overlay; shield-panel; cursor;
  scanlines; faction-feedback; mode-indicator; mana-readout;
  command-queue; tooltip; debug; debug-layout. Now grouped in three
  bands: TERRAIN-SPACE first (terrain, houses, peeps, papal-marker,
  shield-marker, aoe-preview, faction-feedback, command-queue,
  cursor-star); then the HUD blit and button-click flash; then
  HUD-SPACE overlays (minimap, cooldown-overlay, shield-panel,
  scanlines, mode-indicator, mana-readout, tooltip, debug,
  debug-layout). The `_draw_custom_cursor` OS-mouse sprite continues
  to render last in `draw_frame` so it always sits on top.
- [tests/test_cursor_zorder.py](../tests/test_cursor_zorder.py)
  `test_cursor_renders_after_shield_panel` now tracks
  `_draw_custom_cursor` (the user-visible OS-mouse cursor sprite)
  instead of `_draw_cursor` (the in-world terrain-corner star which
  is now terrain-space and intentionally below the HUD chrome). The
  test still enforces that the visible cursor sits above the shield
  panel.

**Developer Tests and Notes**
- [tests/test_iso_hole.py](../tests/test_iso_hole.py): two new tests.
  One asserts a 32x32 surface with a black diamond inside white
  chrome ends up with alpha=0 inside the diamond and alpha=255 at
  the corners. The other adds a small dark-gray (above threshold)
  chrome rectangle and confirms `flood_fill_iso_hole` does not
  clear it.
- pyflakes clean across the four touched files
  ([populous_game/iso_hole.py](../populous_game/iso_hole.py),
  [populous_game/assets.py](../populous_game/assets.py),
  [populous_game/renderer.py](../populous_game/renderer.py),
  [tests/test_cursor_zorder.py](../tests/test_cursor_zorder.py)).
- All four M3 effect smokes pass at every preset:
  `tools/smoke/effect_quake.py`, `tools/smoke/effect_volcano.py`,
  `tools/smoke/effect_flood.py`, `tools/smoke/effect_papal_place.py`,
  plus `tools/smoke/canvas_effect_smoke.py` (10 checks).
- Full suite (excluding bandit and the pre-existing indent failure
  in [tests/test_canvas_size_compat.py](../tests/test_canvas_size_compat.py)):
  1088 passed, 2 skipped.

### M6 followup: minimap scales with HUD_SCALE

**Fixes and Maintenance**
- [populous_game/minimap.py](../populous_game/minimap.py) `Minimap.draw` now renders every minimap pixel into a native-size 128x64 scratch surface, then upscales by `HUD_SCALE` and blits at the scaled destination position. Previously the minimap drew single native pixels (`set_at`) directly onto the canvas, so at remaster (HUD_SCALE=2) the minimap was a tiny 128x64 patch inside a 256x128 minimap frame on the AmigaUI HUD; at large (HUD_SCALE=4) the mismatch was 4x. Now the minimap fills its frame at every preset. The iso losange formula (`px = c + 64 - r`, `py = (c + r) // 2`) is unchanged; the scaling is a single `pygame.transform.scale` at blit time. At classic (HUD_SCALE=1) the path is a no-op pixel copy. Click hit-testing in `Minimap.handle_click` already worked in logical coords (input controller passes `logical_mx`, `logical_my`) so no inverse-projection change was needed.
- The camera viewport polygon (the white losange showing the player's visible area) now reads `settings.VISIBLE_TILE_COUNT` instead of a hard-coded `s = 8`. This is a no-op today (the M6 chunky-pixels followup pinned VISIBLE_TILE_COUNT to 8 across all presets), but it prevents silent drift if the count ever varies again.

**Developer Tests and Notes**
- `pytest tests/test_minimap_zoom.py -q`: 4 passed.
- Full suite (excluding pre-existing indent flag and slow bandit gate): 949 passed, 2 skipped.
- pyflakes clean.

### M6 followup: per-preset terrain scaling (chunky-pixels mode)

**Behavior or Interface Changes**
- [populous_game/settings.py](../populous_game/settings.py)
  `CANVAS_PRESETS` extended from a 4-tuple `(internal_w, internal_h,
  hud_scale, visible_tile_count)` to a 5-tuple that adds
  `terrain_scale`. Values: `classic=(320,200,1,8,1)`,
  `remaster=(640,400,2,8,2)`, `large=(1280,800,4,8,4)`. The
  visible-tile count is fixed at 8 across every preset; the larger
  presets now show the SAME 8 tiles bigger instead of more tiles at
  native size, matching the original Amiga's 8x8 visible viewport.
  A fifth mirror constant `TERRAIN_SCALE` is derived from
  `CANVAS_PRESETS[ACTIVE_CANVAS_PRESET][4]` alongside the existing
  `INTERNAL_WIDTH` / `INTERNAL_HEIGHT` / `HUD_SCALE` /
  `VISIBLE_TILE_COUNT`. The standalone `TERRAIN_SCALE = 1` previously
  living near `BASE_TILE_HALF_W` is removed (the per-preset value
  takes over).
- [populous_game/terrain.py](../populous_game/terrain.py):
  `load_tile_surfaces` now scales each loaded tile by
  `settings.TERRAIN_SCALE` via `pygame.transform.scale` before caching
  it in `tiles[(row, col)]`. Downstream blits do not need to know
  about the scaling -- the cached surface is already the right canvas
  pixel size at every preset. At `TERRAIN_SCALE == 1` (classic) the
  scale step is skipped so the original 32x24 sprite is stored
  unchanged.
- [populous_game/peeps.py](../populous_game/peeps.py):
  `load_sprite_surfaces` now scales each peep frame to
  `(SPRITE_SIZE * TERRAIN_SCALE, SPRITE_SIZE * TERRAIN_SCALE)` so
  peeps match the iso tile size at every preset (16x16 at classic,
  32x32 at remaster, 64x64 at large).
- [populous_game/sprite_geometry.py](../populous_game/sprite_geometry.py):
  `SPRITE_ANCHORS` keeps storing `dx` / `dy` / `size` literals in
  BASE (logical) px so the table stays preset-agnostic; the active
  `TERRAIN_SCALE` is now applied at use site inside `_apply_anchor`
  and the castle 'size' branch of `get_house_sprite_rect` so a
  TERRAIN_SCALE change is picked up immediately without rebuilding
  the table. Selected over a derived `_SCALED_SPRITE_ANCHORS` cache
  to avoid stale-cache bugs if `settings.TERRAIN_SCALE` is mutated
  mid-test.
- [populous_game/terrain.py](../populous_game/terrain.py),
  [populous_game/renderer.py](../populous_game/renderer.py),
  [populous_game/ui_panel.py](../populous_game/ui_panel.py): every
  inline `sx - settings.TILE_HALF_W` blit anchor and faction-feedback
  `ground_y = sy + settings.TILE_HALF_H` offset now multiplies by
  `settings.TERRAIN_SCALE` so the tile-half offset matches the
  already-scaled cached tile / peep sprites. The shield-marker castle
  virtual rect (`pygame.Rect(sx - TILE_HALF_W, sy, TILE_WIDTH,
  TILE_HEIGHT)` in `ui_panel.draw_shield_marker`) likewise scales all
  four dimensions by `TERRAIN_SCALE`.
- [populous_game/cli.py](../populous_game/cli.py): the `--preset`
  switch now also writes `settings.TERRAIN_SCALE = preset[4]`.

**Fixes and Maintenance**
- [tests/test_layout_terrain_centered_in_well.py](../tests/test_layout_terrain_centered_in_well.py):
  the bbox-fill threshold relaxed from 70% to 40%. With
  `TERRAIN_SCALE` matched to `HUD_SCALE` the 8-tile diamond at
  remaster fills exactly half the well in each axis (8 tiles * 32 px
  = 256 canvas px in a 512x256 well); 40% gives a 10% slack for
  rounding while still failing if the diamond drifts off the well.
  This is the EXPECTED Amiga look -- the original game's iso diamond
  did not fill the entire HUD well; it sat inside it with margin.
  Visible-tile candidates per preset trimmed to `(8,)` for all three
  presets to match the new chunky-pixels invariant. A new sanity
  assert (`layout.tile_w == BASE_TILE_HALF_W * 2 * terrain_scale`)
  was added to lock the projection-math source of truth.
- All seven `_set_preset` test / smoke / cli helpers
  ([tests/test_canvas_layout.py](../tests/test_canvas_layout.py),
  [tests/test_canvas_size_compat.py](../tests/test_canvas_size_compat.py),
  [tests/test_click_hits_visible_tile.py](../tests/test_click_hits_visible_tile.py),
  [tests/test_layout_terrain_centered_in_well.py](../tests/test_layout_terrain_centered_in_well.py),
  [tests/test_projection_roundtrip.py](../tests/test_projection_roundtrip.py),
  [tests/test_viewport_transform.py](../tests/test_viewport_transform.py),
  [tools/smoke/canvas_effect_smoke.py](../tools/smoke/canvas_effect_smoke.py))
  updated to read `preset[4]` and write `settings.TERRAIN_SCALE`.
  `try/finally` blocks in the tests that snapshot/restore the
  preset-mirror state now also save and restore the original
  `TERRAIN_SCALE`.

**Developer Tests and Notes**
- `source source_me.sh && python3 -m pyflakes populous_game/settings.py
  populous_game/terrain.py populous_game/peeps.py
  populous_game/sprite_geometry.py populous_game/renderer.py
  populous_game/ui_panel.py populous_game/cli.py
  populous_game/layout.py`: clean.
- `source source_me.sh && python3 -m pytest
  tests/test_layout_terrain_centered_in_well.py
  tests/test_viewport_transform.py
  tests/test_projection_roundtrip.py -v`: 38 passed.
- `source source_me.sh && python3 -m pytest tests/ -q`: 1086 passed,
  2 skipped, 2 failed. The two failures are pre-existing and unrelated
  to this followup: `tests/test_indentation.py::test_indentation_style[
  tests/test_canvas_size_compat.py]` (mixed-indentation flag inherited
  from earlier patches) and `tests/test_bandit_security.py` (B108
  hardcoded `/tmp/...` path inside the staged
  `tools/smoke/debug_layout.py` from Patch 8).
- All four M3 effect smokes exit 0 at the classic preset:
  `tools/smoke/effect_quake.py`, `tools/smoke/effect_volcano.py`,
  `tools/smoke/effect_flood.py`, `tools/smoke/effect_papal_place.py`.
- `source source_me.sh && python3 tools/smoke/canvas_effect_smoke.py`:
  10/10 PASS across `classic`, `remaster`, `large` (exit 0).
- `source source_me.sh && python3 populous.py --screenshot
  /tmp/scaled_remaster.png`: 640x400 PNG written. Default boot at
  remaster shows the AmigaUI menu over a 2x-scaled HUD; gameplay
  state (booted via `tools.headless_runner.boot_game_for_tests`)
  shows 8 tiles at 64x32 canvas px each, terrain centered in the
  AmigaUI well -- the original Amiga look at 2x.
- `source source_me.sh && python3 populous.py --preset large
  --screenshot /tmp/scaled_large.png`: 1280x800 PNG, 8 tiles at
  128x64 canvas px each.
- `source source_me.sh && python3 populous.py --preset classic
  --screenshot /tmp/scaled_classic.png`: 320x200 PNG, 8 tiles at the
  legacy 32x16 canvas px each (TERRAIN_SCALE == 1 path).
- `tools/screenshots/m6/remaster_default.png` and
  `tools/screenshots/m6/remaster_debug_layout.png` regenerated at the
  new chunky-pixel default.
- `tests/test_canvas_size_compat.py` (digest parity) still passes --
  chunky pixels are presentation-only; the simulation digest is
  unchanged across `classic`, `remaster`, and `large` at the same
  seed.

### M6 default switched to remaster (Patch 10, closes M6)

**Behavior or Interface Changes**
- [populous_game/settings.py](../populous_game/settings.py)
  `ACTIVE_CANVAS_PRESET` flipped from `'classic'` to `'remaster'`. The four
  mirror constants (`INTERNAL_WIDTH`, `INTERNAL_HEIGHT`, `HUD_SCALE`,
  `VISIBLE_TILE_COUNT`) continue to derive from `CANVAS_PRESETS[
  ACTIVE_CANVAS_PRESET]`, so the switch is a single string edit -- no
  hard-coded 640/400/2/12. The change is presentation-only: the
  simulation digest produced by [tests/test_canvas_size_compat.py](../tests/test_canvas_size_compat.py)
  remains identical across `classic`, `remaster`, and `large` at the
  same seed. `--preset classic` is still available via the CLI.

**Additions and New Features**
- Two reference screenshots committed under
  [tools/screenshots/m6/](../tools/screenshots/m6/):
  `remaster_default.png` (the new default first-frame capture, 640x400)
  and `remaster_debug_layout.png` (same frame with `--debug-layout`
  showing the map-well rect, projection anchor, tile centers, and HUD
  button hit-boxes, also 640x400).

**Documentation**
- [docs/USAGE.md](USAGE.md) updated: quick-start prose now says the
  default is `remaster`; CLI table gains a `-d, --debug-layout` row and
  notes `--fit-screen` is the recommended companion on small displays;
  canvas-presets table marks `remaster` as the default; the prose under
  "Canvas presets" now explains that the M6 ViewportTransform centers
  the diamond at every preset and `classic` remains available.
- [docs/CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) gained a "Geometry
  single source of truth (M6 ViewportTransform)" section near the top
  naming `populous_game/layout.py:ViewportTransform` and
  `build_viewport_transform` as the single source of geometry truth,
  pointing to `populous_game/sprite_geometry.py:SPRITE_ANCHORS` for
  sprite anchor offsets, and noting that the camera owns world
  coordinates while the layout owns map-well placement. The
  `--debug-layout` overlay is described in the same section.

**Developer Tests and Notes**
- pytest suite at remaster default: results documented below.

### M6 centering correction (between Patches 9 and 10)

**Fixes and Maintenance**
- `populous_game/layout.py:build_viewport_transform` was projecting four "diamond corners" around `(camera.r, camera.c)` as if the camera stored the visible-viewport center, but `populous_game.camera.Camera.__init__` stores `(r, c)` as the TOP-LEFT of the visible NxN viewport. The result: at every preset the rendered terrain was centered half a viewport BELOW the well center (64 px at classic, 96 px at remaster, 128 px at large). Surfaced by Patch 9's `tests/test_layout_terrain_centered_in_well.py` -- the very test that was meant to gate Patch 10. Fixed by projecting the corners of the visible NxN viewport itself: `(camera.r, camera.c)`, `(camera.r, camera.c+N)`, `(camera.r+N, camera.c)`, `(camera.r+N, camera.c+N)`. The visible bbox center now lands on the map-well center to within 1 px at every preset and every supported visible-tile count.
- Patch 2 centering test (`tests/test_viewport_transform.py:_check_centering_for_preset`) and Patch 9 centering test (`tests/test_layout_terrain_centered_in_well.py:test_diamond_centered_in_well`) both updated to project the visible NxN viewport corners (the player-visible region) instead of camera-centered diamond corners. Tests now assert the actual on-screen centering, not the helper's internal arithmetic.
- Patch 8 debug overlay test (`tests/test_debug_layout_overlay_matches_transform.py:test_map_well_outline_is_cyan`) updated to sample cyan well-outline pixels at quarter-points and edge midpoints that dodge the iso top/bottom apex coordinates, where the magenta anchor square (top apex) and a red tile-center dot (bottom apex) naturally overpaint cyan.

**Developer Tests and Notes**
- `pytest tests/test_layout_terrain_centered_in_well.py tests/test_projection_roundtrip.py tests/test_click_hits_visible_tile.py tests/test_viewport_transform.py tests/test_canvas_size_compat.py tests/test_castle_clipping.py -q`: 54 passed.
- Full suite (excluding the two pre-existing slow lint gates and the indent flag): 957 passed, 2 skipped.
- All four M3 effect smokes (quake, volcano, flood, papal_place) exit 0 at classic.

### M6 ViewportTransform foundation (Patch 9)

**Additions and New Features**
- New [tests/test_layout_terrain_centered_in_well.py](../tests/test_layout_terrain_centered_in_well.py): parametrized over (preset, visible_tile_count) covering classic-{8}, remaster-{8,10,12,14,16}, and large-{16,20,24,28,32}. Each case builds a `Layout` + `ViewportTransform` via `populous_game.layout.active_layout()` / `build_viewport_transform()` with a synthetic camera positioned per `populous_game.camera.Camera.__init__` (`camera.r = GRID_HEIGHT // 2 - visible_tiles // 2`). Asserts the bbox of the four diamond corners (camera +/- visible_tiles/2 around the camera point, which is the convention `build_viewport_transform` centers internally) matches `layout.map_well_rect.center` to within 2 px per axis (M6 plan section 4 done-check). For the largest-fitting candidate per preset (selected via `layout.max_visible_tiles_that_fit`), additionally asserts bbox width and height each cover at least 70% of the map well (M6 plan section 13). The fill check is gated to the largest-fitting candidate because smaller candidates from the section 12 candidate sets are intentional fallbacks at preset-independent tile dimensions and do not satisfy 70% by construction. 11 parametrized cases.
- New [tests/test_projection_roundtrip.py](../tests/test_projection_roundtrip.py): parametrized over the same (preset, visible_tile_count) sweep as the centering test. Each case projects 12 representative world points (four diamond corners + four diagonal interior points + four edge midpoints) and asserts (a) `screen_to_world(world_to_screen_float(r, c))` round-trips to within 1e-9 per axis (float-precision exact inverse) and (b) `screen_to_world(world_to_screen(r, c))` recovers `(r, c)` to within one tile per axis (integer-rounded blit pixel inverse). Broader than the existing `tests/test_viewport_transform.py` which sweeps only the largest-fit candidate per preset. 22 parametrized cases (11 float + 11 int).
- New [tests/test_click_hits_visible_tile.py](../tests/test_click_hits_visible_tile.py): parametrized over the three canvas presets. Each case boots a real Game via `tools/headless_runner.py:boot_game_for_tests`, sweeps in-viewport corner candidates that satisfy the controller's click preconditions (corner altitude 0 so the default-altitude inverse projection lands on the same corner; round-trip pre-check via `screen_to_world(world_to_screen(r, c))`; not under any UI button hit-box per `ui_panel.hit_test_button(logical_x, logical_y)` because the well's lower edge overlaps the HUD button row in 320x200 logical space; inside `view_rect`), projects each through `viewport_transform.world_to_screen(r, c, 0)` to a canvas pixel, converts to OS-window pixels via `display_scale * RESOLUTION_SCALE`, posts a synthetic click via `tools/headless_runner.py:inject_click_at`, advances one frame, and asserts the corresponding terrain corner altitude was bumped by 1 (i.e., the controller's `screen_to_world` resolved to the same `(r, c)` the test projected). Demands at least 3 successful click->raise round-trips per preset; the sweep continues up to 5. 3 parametrized cases.

**Developer Tests and Notes**
- `source source_me.sh && python3 -m pyflakes tests/test_layout_terrain_centered_in_well.py tests/test_projection_roundtrip.py tests/test_click_hits_visible_tile.py`: clean.
- `source source_me.sh && python3 -m pytest tests/test_layout_terrain_centered_in_well.py -v`: 11 passed.
- `source source_me.sh && python3 -m pytest tests/test_projection_roundtrip.py -v`: 22 passed.
- `source source_me.sh && python3 -m pytest tests/test_click_hits_visible_tile.py -v`: 3 passed.
- `source source_me.sh && python3 -m pytest tests/ -q --ignore=tests/test_indentation.py --ignore=tests/test_bandit_security.py --ignore=tests/test_pyflakes_code_lint.py`: 809 passed, 2 skipped.
- `source source_me.sh && python3 -m pytest tests/test_pyflakes_code_lint.py -q`: 136 passed.
- All four M3 effect smokes exit 0 at the classic preset: `tools/smoke/effect_quake.py`, `tools/smoke/effect_volcano.py`, `tools/smoke/effect_flood.py`, `tools/smoke/effect_papal_place.py`.

**Decisions and Failures**
- Initial draft of [tests/test_layout_terrain_centered_in_well.py](../tests/test_layout_terrain_centered_in_well.py) projected the four corners of the actual visible NxN viewport (`(cam_r, cam_c) .. (cam_r+N, cam_c+N)`) and asserted that bbox was centered. All 11 parametrized cases failed: at every preset and N the bbox center sat below the well center by half an iso viewport (e.g., classic-8 bbox_cy=200 vs well.centery=136). Investigation showed `populous_game.layout.build_viewport_transform` projects diamond corners around `(camera.r, camera.c)` directly (interpreting the camera as the diamond center), while the production `populous_game.camera.Camera.__init__` stores `camera.r` as the top-left of the visible NxN viewport (the visible diamond center is `camera.r + N/2`). The visible diamond is therefore centered around the well TOP, not the well center. The Patch 9 test was rewritten to project corners at +/- N/2 around `(camera.r, camera.c)` to match `build_viewport_transform`'s convention so the parity gate locks the layout helper's documented behavior. Whether the visible diamond should also be centered (i.e., whether `build_viewport_transform` should treat `camera.r` as top-left or as center) is a Patch 10 followup that may need to be resolved before flipping the default preset to remaster, since the symptom (terrain shifted down inside the well) is the very issue M6 was created to fix. The Patch 8 `--debug-layout` overlay places the cyan map well rectangle at `map_well_rect` and a magenta anchor square at `(transform.anchor_x, transform.anchor_y)`; running `populous.py --debug-layout --screenshot ...` at remaster makes the offset visible.
- Initial draft of [tests/test_click_hits_visible_tile.py](../tests/test_click_hits_visible_tile.py) used five fixed (dr, dc) probe offsets within the visible viewport and only checked altitude == 0. At classic, four of the five probes landed under HUD buttons in logical 320x200 space and the controller routed those clicks to `_find_knight` / `_find_battle` instead of `raise_corner`. The fix added an `ui_panel.hit_test_button(logical_x, logical_y) is not None` skip and broadened the probe sweep to scan the full visible viewport row-major, accepting the first up-to-five candidates that pass all preconditions (altitude 0 + round-trip pre-check + no UI button overlap + inside view rect). The decision to require >= 3 successes (not 5) accommodates classic where the well's lower half overlaps the HUD button row, leaving fewer than 5 valid candidates after all filters; each accepted probe still asserts post == pre + 1 so the parity check is not weakened.

### M6 ViewportTransform foundation (Patch 8)

**Additions and New Features**
- New `--debug-layout` (`-d`) CLI flag in [populous_game/cli.py](../populous_game/cli.py). Defaults False; when True, the renderer overlays diagnostic geometry on every gameplay frame.
- New `Renderer._draw_debug_layout_overlay()` method in [populous_game/renderer.py](../populous_game/renderer.py). Draws (in this z-order on the internal surface): white HUD-rect outline, yellow terrain-clip-rect outline, cyan map-well-rect outline (cyan paints on top of yellow so the well wins where the two currently coincide; a future divergence makes the yellow peek out), 3x3 magenta square at the `ViewportTransform` projection anchor, 1 px red dots at every visible tile center via `transform.world_to_screen(r + 0.5, c + 0.5, alt)`, and 1 px green outlines around every UI button hit-box via `populous_game.layout.button_hit_box(action, ui_panel.buttons)`. Gated on `self.game.debug_layout` so behavior is byte-identical to pre-Patch-8 when the flag is off. Hooked into the end of `_draw_gameplay()` after `_draw_debug_overlay()`.
- New test [tests/test_debug_layout_overlay_matches_transform.py](../tests/test_debug_layout_overlay_matches_transform.py): four checks covering (a) magenta anchor pixel exists at `(transform.anchor_x, transform.anchor_y)`, (b) cyan map-well outline appears within +/- 1 px of three perimeter sample points (top edge midpoint, left edge midpoint, right-edge midpoint), (c) red tile-center pixels appear at >= 3 of 4 probed visible tiles inside the camera viewport, and (d) the overlay is no-op when `debug_layout` defaults to False (anchor pixel is NOT magenta).
- New smoke [tools/smoke/debug_layout.py](../tools/smoke/debug_layout.py): boots a deterministic gameplay session, flips `debug_layout=True`, captures one frame to `/tmp/debug_layout_smoke.png`, samples the magenta anchor pixel, the cyan well-edge midpoint, and a red tile-center pixel near the camera origin. Exits 0 on PASS, 1 on FAIL.

**Behavior or Interface Changes**
- `populous_game.game.Game.__init__` now accepts a `debug_layout: bool = False` keyword. Stored as `self.debug_layout`. The launcher [populous.py](../populous.py) plumbs `args.debug_layout` from the new CLI flag. Default `False` keeps every existing call site (Game(), Game(display_scale=...), Game(seed=...)) byte-identical.
- [populous_game/renderer.py](../populous_game/renderer.py) gained a top-level `import populous_game.layout as layout_module` so the overlay can call `layout_module.button_hit_box(...)` without lazy-importing inside the per-frame method.

**Developer Tests and Notes**
- `source source_me.sh && python3 -m pyflakes populous.py populous_game/cli.py populous_game/game.py populous_game/renderer.py tests/test_debug_layout_overlay_matches_transform.py tools/smoke/debug_layout.py`: clean.
- `source source_me.sh && python3 -m pytest tests/test_debug_layout_overlay_matches_transform.py -v`: 4 passed.
- `source source_me.sh && python3 tools/smoke/debug_layout.py`: PASS (exit 0).
- `source source_me.sh && python3 -m pytest tests/test_pyflakes_code_lint.py -q`: 134 passed.
- `source source_me.sh && python3 -m pytest --ignore=tests/test_pyflakes_code_lint.py --ignore=tests/test_bandit_security.py -q`: 899 passed, 2 skipped, 1 failed -- the lone failure is the pre-existing `tests/test_indentation.py::test_indentation_style[tests/test_canvas_size_compat.py]` mixed-indentation flag inherited from earlier patches; no new failures.
- All four M3 effect smokes exit 0 at the classic preset: `tools/smoke/effect_quake.py`, `tools/smoke/effect_volcano.py`, `tools/smoke/effect_flood.py`, `tools/smoke/effect_papal_place.py`.
- `source source_me.sh && python3 populous.py --debug-layout --screenshot /tmp/debug_layout.png` in headless SDL mode emitted a 320x200 PNG with the diagnostic geometry painted on top of the standard gameplay frame.

### M6 ViewportTransform foundation (Patch 7)

**Behavior or Interface Changes**
- [populous_game/input_controller.py](../populous_game/input_controller.py) MOUSEBUTTONDOWN handler now carries a single block-comment "coord-space contract" describing the two coord-space paths (canvas-pixel `(mx, my)` for terrain hit-tests via `viewport_transform.screen_to_world`; logical 320x200 `(logical_mx, logical_my)` for HUD / minimap / `ui_panel.select_at` / `ui_panel.hit_test_button`). The wording explicitly notes that the path is chosen by *what* is being hit, not by re-deriving math, and that the AmigaUI sprite is 320x200 in logical space which is why the HUD reads logical coords. Behavior is unchanged; the comment was tightened so future readers see one clean explanation.
- [populous_game/camera.py](../populous_game/camera.py) gained a module-level docstring/comment block explaining that the camera operates entirely in world (row / column) coordinates and that map-well placement is the layout's responsibility, not the camera's. `Camera.move` and `Camera.center_on` got expanded docstrings noting the world-bounds clamp `[0, GRID_HEIGHT - VISIBLE_TILE_COUNT]` / `[0, GRID_WIDTH - VISIBLE_TILE_COUNT]` and explicitly stating that screen bounds are out of scope for this module. Three short bilingual French comments inside the file (`Mapping touches`, `Délai entre deux déplacements`, `Position logique de la caméra`) were translated to English for consistency. The clamp arithmetic is unchanged.

**Fixes and Maintenance**
- [tests/test_screenshot_clicking.py](../tests/test_screenshot_clicking.py) audited for the test-ordering bug flagged in [docs/active_plans/m6_layout_projection.md](active_plans/m6_layout_projection.md) section 4 done-checks. `pytest tests/test_screenshot_clicking.py -v` passes 3/3 in isolation and `pytest tests/test_input_controller.py tests/test_drag_paint.py tests/test_screenshot_clicking.py tests/test_canvas_size_compat.py tests/test_viewport_transform.py tests/test_castle_clipping.py` passes 27/27 together; no shared-state cleanup was required. The clean-bill-of-health is recorded here so a future patch does not re-investigate.

**Decisions and Failures**
- Patch 7's audit (`grep -n -E '\* settings\.TILE_|TILE_HALF_|TILE_WIDTH|TILE_HEIGHT|MAP_OFFSET_|HUD_SCALE|cam_r|cam_c|cam_x|cam_y|world_to_screen|screen_to_world|screen_to_grid|screen_to_nearest_corner' populous_game/input_controller.py populous_game/camera.py populous_game/renderer.py populous_game/ui_panel.py`) found no unmigrated iso-projection arithmetic. All terrain hit-tests in `input_controller.py` already route through `self.game.viewport_transform.screen_to_world(mx, my)` (Patch 3). `_draw_tooltip_or_hover_help` already passes the same logical coord space to both `hit_test_button(mx_logical, my_logical)` and `hover_info_at(mx_logical, my_logical, game)`; `ui_panel.hover_info_at` and `ui_panel.select_at` already scale logical->canvas internally before calling `transform.screen_to_world` (Patch 3 + Patch 5). `Camera` reads `settings.VISIBLE_TILE_COUNT` directly for its world-bounds clamp and does not need a transform reference -- the camera's bounds are world bounds, not screen bounds. Patch 7 therefore reduces to comment / docstring tightening; no behavior changes are needed in production code.

**Developer Tests and Notes**
- `source source_me.sh && python3 -m pyflakes populous_game/camera.py populous_game/input_controller.py populous_game/renderer.py populous_game/ui_panel.py`: clean.
- `source source_me.sh && python3 -m pytest tests/test_input_controller.py tests/test_drag_paint.py tests/test_screenshot_clicking.py tests/test_canvas_size_compat.py tests/test_viewport_transform.py tests/test_castle_clipping.py`: 27 passed.
- `source source_me.sh && python3 -m pytest tests/test_screenshot_clicking.py -v` (alone): 3 passed -- no test-ordering dependency.
- `source source_me.sh && python3 -m pytest tests/test_effect_music_toggle.py tests/test_effect_sfx_toggle.py tests/test_effect_sleep_pause.py`: 6 passed (M3 effect smokes at classic preset).

### M6 ViewportTransform foundation (Patch 6)

**Behavior or Interface Changes**
- `populous_game/peeps.py:Peep.update` now accepts a required `transform` argument (a `populous_game.layout.ViewportTransform`) so the compass-facing computation can route its iso projection through the transform. The previous body computed `screen_dx = (dx - dy) * settings.TILE_HALF_W` / `screen_dy = (dx + dy) * settings.TILE_HALF_H` inline; the new body calls `transform.world_to_screen_float(self.y, self.x, 0)` and `transform.world_to_screen_float(self.y + dy, self.x + dx, 0)` and takes the screen-space delta. Camera and altitude offsets are linear so they cancel for a delta, which makes the result preset-agnostic without re-reading any iso pixel literals.
- `populous_game/peeps.py:Peep.draw` no longer derives its blit rect inline. `ground_y = sy + settings.TILE_HALF_H` and `blit_x = sx - sw // 2` / `blit_y = ground_y - sh` are replaced with a single call to `populous_game.sprite_geometry._apply_anchor((sx, sy), SPRITE_ANCHORS['peep_default'], (sw, sh))`. The same helper now positions the missing-sprite fallback circle so it lands at the foot point. The drowning-animation branch is unchanged in terms of frame selection (`(5, 8 + self.anim_frame)`) but its sprite anchor flows through the same metadata path. `populous_game.sprite_geometry` is lazy-imported inside `draw` because `sprite_geometry` already imports `peeps` at module load.
- `populous_game/game.py` main update loop now passes `self.viewport_transform` to `p.update(dt, self.viewport_transform)`.
- `tests/test_ui_options_do_not_change_simulation_digest.py:_advance` updated to thread `game.viewport_transform` into `p.update`, matching the new required parameter.

**Removals and Deprecations**
- Removed iso-projection literal arithmetic `(dx - dy) * settings.TILE_HALF_W` / `(dx + dy) * settings.TILE_HALF_H` from `Peep.update`'s facing computation; the transform's `world_to_screen_float` is the only iso projection callsite left in [populous_game/peeps.py](../populous_game/peeps.py).
- Removed the `+ settings.TILE_HALF_H` foot-point literal and the inline `sx - sw // 2` / `ground_y - sh` centering literals from `Peep.draw`. Both now read from `SPRITE_ANCHORS['peep_default']` in [populous_game/sprite_geometry.py](../populous_game/sprite_geometry.py).
- [populous_game/houses.py](../populous_game/houses.py) had no iso-projection arithmetic in the first place; the castle 3x3 corner blits live in [populous_game/terrain.py:GameMap.draw_houses](../populous_game/terrain.py) and were already routed through `transform.world_to_screen` by Patch 3, so houses.py needed no edits.

**Developer Tests and Notes**
- `source source_me.sh && python3 -m pyflakes populous_game/peeps.py populous_game/houses.py populous_game/game.py`: clean.
- `source source_me.sh && python3 -m pytest tests/test_castle_clipping.py tests/test_canvas_size_compat.py tests/test_viewport_transform.py tests/test_ui_options_do_not_change_simulation_digest.py -q`: 20 passed.
- `source source_me.sh && python3 -m pytest tests/ -q`: 1030 passed, 1 failed, 2 skipped. The lone failure is the pre-existing `tests/test_indentation.py::test_indentation_style[tests/test_canvas_size_compat.py]` flagged by Patch 5; no new failures.
- All four M3 effect smokes exit 0 at the classic preset: `tools/smoke/effect_quake.py`, `tools/smoke/effect_volcano.py`, `tools/smoke/effect_flood.py`, `tools/smoke/effect_papal_place.py`.
- Audit grep `grep -n -E '\* settings\.TILE_|TILE_HALF_|TILE_WIDTH|TILE_HEIGHT|MAP_OFFSET_|cam_r|cam_c|cam_x|cam_y|world_to_screen|screen_to_world' populous_game/peeps.py populous_game/houses.py` returns only `transform.world_to_screen[_float]` callsites and the docstring comments describing them -- no iso-projection arithmetic and no sprite-anchor literals remain in either file.

### M6 ViewportTransform foundation (Patch 5)

**Behavior or Interface Changes**
- `populous_game/ui_panel.py:select_at` now scales its incoming logical-space `(mx, my)` by `settings.HUD_SCALE` before colliding against sprite rects from [populous_game/sprite_geometry.py](../populous_game/sprite_geometry.py). Sprite rects are built in canvas-pixel space via the active `ViewportTransform`, so at non-classic canvas presets (`HUD_SCALE > 1`) the previous code compared logical coords against canvas-pixel rects and the visible hover/click region drifted off the visible sprite. At classic (`HUD_SCALE == 1`) this is a no-op. This mirrors the fix Patch 3 applied to `hover_info_at`'s terrain-corner branch and closes the coord-space mismatch flagged in [docs/active_plans/m6_layout_projection.md](active_plans/m6_layout_projection.md) section 5.2 for the entity-hit-test branch as well.

**Decisions and Failures**
- Audit of [populous_game/renderer.py](../populous_game/renderer.py) for ad-hoc iso-projection arithmetic returned a clean bill of health: every renderer overlay (`_draw_terrain`, `_draw_houses`, `_draw_peeps`, `_draw_papal_marker`, `_draw_shield_marker_if_active`, `_draw_cursor`, `_draw_aoe_preview`, `_draw_command_queue`, `_draw_faction_feedback`, `_draw_cooldown_overlay`, `_draw_tooltip_or_hover_help`) already routes world-to-screen through `self.game.viewport_transform.world_to_screen(...)` (terrain/peeps/papal/cursor/AOE/command-queue/faction-feedback) or operates in HUD-relative pixel space (cooldown overlay, mode indicator, mana readout, debug overlay). The only remaining `settings.TILE_HALF_W` / `settings.TILE_HALF_H` references in `renderer.py` are sprite-anchor offsets (papal marker and cursor star single-tile blits, faction-feedback foot-point drop) -- they are not iso projection, they match documented `SPRITE_ANCHORS` conventions in [populous_game/sprite_geometry.py](../populous_game/sprite_geometry.py), and they are out of scope per the Patch 5 mandate. Patch 5 therefore reduces to a one-call coord-space fix in `ui_panel.select_at`.
- The remaining `cam_r, cam_c = self.game.camera.r, self.game.camera.c` reads in `renderer.py` feed `self.game.game_map.get_visible_bounds(cam_r, cam_c)` for off-screen culling only; they do not participate in iso projection. They are not bugs and Patch 7 will retire them when the camera moves through the transform.

**Removals and Deprecations**
- None. No `settings.TILE_*` constants were dropped from `renderer.py`; the surviving references are sprite-anchor offsets, not iso projection.

**Developer Tests and Notes**
- `source source_me.sh && python3 -m pyflakes populous_game/renderer.py populous_game/ui_panel.py`: clean.
- `source source_me.sh && python3 -m pytest tests/test_aoe_preview.py tests/test_command_queue.py tests/test_cooldown_overlay.py tests/test_hover_help.py tests/test_canvas_size_compat.py tests/test_viewport_transform.py -q`: 39 passed.
- `source source_me.sh && python3 -m pytest tests/ -q --ignore=tests/test_indentation.py`: 898 passed, 2 skipped. The lone outstanding failure is the pre-existing `tests/test_indentation.py::test_indentation_style[tests/test_canvas_size_compat.py]` (mixed-indentation flag inherited from earlier patches; no new failures).
- All four M3 effect smokes exit 0 at the classic preset: `tools/smoke/effect_quake.py`, `tools/smoke/effect_volcano.py`, `tools/smoke/effect_flood.py`, `tools/smoke/effect_papal_place.py`.
- Audit grep `grep -n -E '\* settings\.TILE_|TILE_HALF_|TILE_WIDTH|TILE_HEIGHT|MAP_OFFSET_|cam_r|cam_c|cam_x|cam_y' populous_game/renderer.py` returns only sprite-anchor offset sites and `get_visible_bounds` cull reads -- no iso-projection arithmetic remains.

### M6 ViewportTransform foundation (Patch 4)

**Additions and New Features**
- New `SPRITE_ANCHORS` metadata table at the top of [populous_game/sprite_geometry.py](../populous_game/sprite_geometry.py). Each entry declares the per-sprite-type pixel offset `(dx, dy)` from the ground-anchor pixel (the iso projection of the world tile corner) plus centering rules (`center_x`, `align_bottom_y`). Coverage matches `populous_game.settings.BUILDING_TILES` (`hut`, `house_small`, `house_medium`, `castle_small`, `castle_medium`, `castle_large`, `fortress_small`, `fortress_medium`, `fortress_large`) plus the special top-tier `castle` entry emitted by `populous_game.houses.House.TYPES` and a `peep_default` entry for peeps. The `castle` entry carries an explicit `size` override since it has no underlying tile-sprite surface.
- New `_apply_anchor(anchor_xy, meta, size_xy)` helper translates a ground-anchor pixel + sprite size to a top-left blit position using the metadata's offset and centering rules. New `_peep_anchor_key(p)` helper picks the correct metadata entry for a peep instance (currently always `peep_default`; state-specific entries can be added later without touching the rect-building functions).
- New module-level constants `PEEP_FALLBACK_SIZE` and `HOUSE_FALLBACK_SIZE` capture the debug fallback rect dimensions when a sprite asset cannot be resolved.

**Behavior or Interface Changes**
- `populous_game/sprite_geometry.py:get_peep_sprite_rect` now reads its offset from `SPRITE_ANCHORS[_peep_anchor_key(p)]` and routes the result through `_apply_anchor`. The function body no longer carries pixel literals; the `+ TILE_HALF_H` shift that used to live inline is now `SPRITE_ANCHORS['peep_default']['dy']`.
- `populous_game/sprite_geometry.py:get_house_sprite_rect` now reads its offset from `SPRITE_ANCHORS[house.building_type]` and routes the result through `_apply_anchor`. The previous `if house.building_type == 'castle'` branch was replaced by a uniform metadata lookup; the special-case `size = (TILE_WIDTH * 2, TILE_HEIGHT * 2)` rect now lives in `SPRITE_ANCHORS['castle']['size']`.

**Removals and Deprecations**
- Hard-coded `+ settings.TILE_HALF_H`, `- settings.TILE_WIDTH`, `- settings.TILE_HEIGHT`, and `- settings.TILE_HALF_W` literals removed from the bodies of `get_peep_sprite_rect` and `get_house_sprite_rect`. All `settings.TILE_*` references in the module now live inside the `SPRITE_ANCHORS` table or the named `HOUSE_FALLBACK_SIZE` constant; renderer code never invents pixel offsets.

**Developer Tests and Notes**
- `source source_me.sh && python3 -m pyflakes populous_game/sprite_geometry.py`: clean.
- `source source_me.sh && python3 -m pytest tests/test_canvas_size_compat.py tests/test_viewport_transform.py tests/test_castle_clipping.py`: 18 passed.
- `source source_me.sh && python3 -m pytest`: 1030 passed, 2 skipped, 1 failed -- the lone failure is the same pre-existing `tests/test_indentation.py::test_indentation_style[tests/test_canvas_size_compat.py]` (mixed-indentation flag inherited from earlier patches; no new failures).
- All four M3 effect smokes exit 0 at the classic preset: `tools/smoke/effect_quake.py`, `tools/smoke/effect_volcano.py`, `tools/smoke/effect_flood.py`, `tools/smoke/effect_papal_place.py`.

### M6 ViewportTransform foundation (Patch 3)

**Behavior or Interface Changes**
- `populous_game/game.py:Game.__init__` snapshots the active canvas layout (`self.layout = layout_module.active_layout()`) and builds an initial `ViewportTransform` (`self.viewport_transform`). `Game.draw()` now refreshes `self.viewport_transform` at the start of each frame via `layout_module.build_viewport_transform(self.layout, self.camera, settings.VISIBLE_TILE_COUNT)`, so renderer / terrain / input always see a transform that reflects the current camera.
- `populous_game/terrain.py:GameMap.draw` and `GameMap.draw_houses` now take a `transform` argument instead of `cam_r` / `cam_c`. `GameMap.draw_tile` likewise switched from `(cam_r, cam_c)` to `(transform)`. The transform owns the camera position and the visible-tile budget; the per-method culling bounds derive from `transform.camera_row` / `transform.camera_col` / `transform.visible_tiles`.
- `populous_game/sprite_geometry.py:get_peep_sprite_rect` and `get_house_sprite_rect` now take `(entity, transform, game_map)` instead of `(entity, cam_r, cam_c, game_map)`. Callers (`ui_panel.select_at`, `ui_panel.draw_shield_marker`) read `self.game.viewport_transform`.
- `populous_game/peeps.py:Peep.draw` now takes `(surface, transform, ...)` instead of `(surface, cam_x, cam_y, ...)`. The renderer plumbs the transform from `self.game.viewport_transform`.
- `populous_game/renderer.py` overlays (terrain / houses / peeps / papal marker / cursor / faction feedback / AOE preview / command queue) all consume `self.game.viewport_transform` directly. Click-to-corner conversion uses `transform.screen_to_world(...)` followed by `round(...)` per axis (preserves the legacy `screen_to_nearest_corner` semantics).
- `populous_game/input_controller.py` MOUSEBUTTONDOWN and drag-paint paths now project pointer pixels through `self.game.viewport_transform.screen_to_world(mx, my)` and round to the nearest integer corner. `populous_game/game.py:_draw_debug_overlay` does the same.
- `tools/headless_runner.py:tile_center_px` now goes through `game.viewport_transform.world_to_screen(r, c, alt)`; the helper still returns OS-window pixels for click injection.

**Removals and Deprecations**
- `GameMap.world_to_screen(r, c, altitude, cam_r, cam_c)` removed (no deprecated wrapper, per DQ-2 of [docs/active_plans/m6_layout_projection.md](active_plans/m6_layout_projection.md)). All callers route through `ViewportTransform.world_to_screen`.
- `GameMap.screen_to_grid(sx, sy, cam_r, cam_c)` removed.
- `GameMap.screen_to_nearest_corner(sx, sy, cam_r, cam_c)` removed. Callers compute `(rf, cf) = transform.screen_to_world(x, y)` then `round(rf), round(cf)` for nearest-corner semantics.
- The `import populous_game.layout as layout` in `populous_game/terrain.py` is gone -- the module no longer needs the layout helper now that the transform carries the projection.

**Fixes and Maintenance**
- `tests/test_castle_clipping.py` updated to build a zero-camera `ViewportTransform` via `layout.build_viewport_transform(layout.active_layout(), cam, settings.VISIBLE_TILE_COUNT)` and pass it to `GameMap.draw_houses`.
- `tools/house_diagnostic.py` and `tools/map_viewer.py` were already broken (their imports reference deleted modules); their lingering `world_to_screen` references are dead code and were left untouched.

**Developer Tests and Notes**
- `source source_me.sh && python3 -m pytest tests/test_canvas_size_compat.py tests/test_viewport_transform.py -q`: 15 passed.
- `source source_me.sh && python3 -m pytest tests/test_castle_clipping.py -q`: 3 passed.
- `source source_me.sh && python3 -m pytest -q --ignore=tests/test_pyflakes_code_lint.py --ignore=tests/test_bandit_security.py`: 895 passed, 2 skipped, 1 failed -- the lone failure is the pre-existing `tests/test_indentation.py::test_indentation_style[tests/test_canvas_size_compat.py]` (mixed-indentation flag, unchanged from Patch 2 baseline).
- `source source_me.sh && python3 -m pytest tests/test_pyflakes_code_lint.py -q`: 134 passed (clean).
- All four M3 effect smokes exit 0 at the classic preset: `tools/smoke/effect_quake.py`, `tools/smoke/effect_volcano.py`, `tools/smoke/effect_flood.py`, `tools/smoke/effect_papal_place.py`.

### M6 ViewportTransform foundation (Patch 2)

**Additions and New Features**
- New frozen dataclasses `Layout` and `ViewportTransform` in [populous_game/layout.py](../populous_game/layout.py). `Layout` snapshots the active canvas preset's geometry (canvas / HUD / map-well / minimap / terrain-clip rects, plus tile_w / tile_h / altitude_step in canvas pixels). `ViewportTransform` carries the iso-projection math (forward `world_to_screen_float` / `world_to_screen`, inverse `screen_to_world`) bound to a Layout, a duck-typed camera (`.r` / `.c` floats), and a `visible_tiles` budget.
- New builder `build_viewport_transform(layout, camera, visible_tiles)` centers an N-tile iso diamond inside `layout.map_well_rect` by projected-bbox alignment: it builds a provisional anchor at (0, 0), projects the four diamond corners, computes the bbox center, then rounds the anchor delta so `(map_well.centerx, map_well.centery)` equals the bbox center within 1 px.
- New utility `max_visible_tiles_that_fit(map_well_rect, tile_w, tile_h, candidates)` picks the largest N whose `N * tile_w` by `N * tile_h` bbox fits inside the well; falls back to `min(candidates)` so callers always have something to render.
- New tests [tests/test_viewport_transform.py](../tests/test_viewport_transform.py): 13 tests covering float round-trip exactness (1e-9 tolerance) and integer round-trip tile-tolerance for each of the three presets, build_viewport_transform centering for each preset (using the M6 plan's per-preset candidate sweep), `max_visible_tiles_that_fit` selection logic plus the fallback path, and frozen-dataclass enforcement for both `Layout` and `ViewportTransform`.

**Decisions and Failures**
- Patch is additive only: no existing caller (terrain.py, sprite_geometry.py, renderer.py, peeps.py, houses.py, input_controller.py, camera.py) consumes the new types yet. Behavior is byte-identical to Patch 1; canvas-size-compat parity (`tests/test_canvas_size_compat.py`) still passes at every preset.
- `MAP_WELL_RECT_LOGICAL` lives in `settings.py` as a tuple (not a `pygame.Rect`) so `settings.py` stays pygame-import-free; `active_layout()` is the conversion site that wraps the tuple in `pygame.Rect`. Layout is the first module that imports both `pygame` and `settings`, which is correct for a presentation-layer helper.
- Existing `populous_game/layout.py` uses 4-space indentation, so the new dataclasses and helpers continue that convention; mixing tabs into the file would fail `tests/test_indentation.py`. The new test file uses tabs per `docs/PYTHON_STYLE.md`.

**Developer Tests and Notes**
- `source source_me.sh && python3 -m pytest tests/test_viewport_transform.py -v`: 13 passed.
- `source source_me.sh && python3 -m pytest tests/test_layout_helpers.py tests/test_canvas_size_compat.py -v`: 7 passed (regression).
- `source source_me.sh && python3 -m pytest tests/`: 1024 passed, 2 skipped, 2 failed. Both failures are pre-existing (the `tools/measure_map_well.py` PIL import policy violation from Patch 1, and the `tests/test_canvas_size_compat.py` indentation parity result the plan acknowledges); no new failures introduced.
- `source source_me.sh && python3 -m pyflakes populous_game/layout.py tests/test_viewport_transform.py`: clean.

### M6 ViewportTransform foundation (Patch 1)

**Additions and New Features**
- New [tools/measure_map_well.py](../tools/measure_map_well.py): permanent dev tool that scans `data/gfx/AmigaUI.png` for the black map-well region and emits `MAP_WELL_RECT_LOGICAL`. Single source of truth for the M6 ViewportTransform. Uses a 4-connected flood fill to isolate the largest contiguous black region (the iso diamond) from the smaller minimap pane. Run after AmigaUI art changes.
- Add `BASE_TILE_HALF_W`, `BASE_TILE_HALF_H`, `BASE_ALTITUDE_STEP`, `TERRAIN_SCALE`, and `MAP_WELL_RECT_LOGICAL` constants to [populous_game/settings.py](../populous_game/settings.py) for M6 viewport projection. `MAP_WELL_RECT_LOGICAL = (64, 72, 256, 128)` measured from the current AmigaUI sprite (width/height ratio 2.00, consistent with the iso diamond). Stored as a tuple to keep settings.py pygame-import-free.

**Decisions and Failures**
- Initial measurement using a simple bounding-box scan returned the entire 320x200 frame because the AmigaUI HUD chrome contains additional black regions (notably the small minimap pane and dithered shadow pixels). Switched to a flood-fill approach that selects the largest 4-connected black region, which cleanly isolates the iso-shaped map well.

**Developer Tests and Notes**
- `source source_me.sh && python3 tools/measure_map_well.py` prints the rectangle, pixel count, and width/height ratio.
- `source source_me.sh && python3 -m pyflakes tools/measure_map_well.py populous_game/settings.py` is clean.
- No callers consume the new constants yet (foundation patch); behavior is unchanged.

### Menu hotkeys

**Additions and New Features**
- Start-up menu accepts `N` (in addition to legacy `ENTER` / `SPACE` and left-click) for "new game". `Q` and `ESC` still quit. The menu render now shows hotkey hints in parentheses: "(N)ew game", "(Q)uit". "Continue" stays visible but greyed-out and unbound until save/load lands.

### pip_requirements: add pillow as dev-only

**Fixes and Maintenance**
- Add `pillow` to [pip_requirements-dev.txt](../pip_requirements-dev.txt) (NOT the runtime `pip_requirements.txt`) so `tools/measure_map_well.py` is policy-compliant without inflating gameplay dependencies. The dev tool reads `data/gfx/AmigaUI.png` only when an art change forces a re-measurement; gameplay does not import PIL. `tests/test_import_requirements.py` reads both requirement files, and `IMPORT_REQUIREMENT_ALIASES["pil"] = "pillow"` makes the alias resolve. The pre-existing import-requirements failure on Patch 1 is now resolved.

### Drag-paint click sensitivity

**Behavior or Interface Changes**
- A single normal-length click on terrain now produces a single raise/lower action instead of 3-4. Drag-paint auto-repeat does not start until the user has held the mouse button for `DRAG_PAINT_INITIAL_DELAY` (default 0.30 s); after that, paints fire every `DRAG_PAINT_INTERVAL` (default 0.10 s, up from 0.05 s). The grace period is implemented by biasing `_drag_paint_last_time` forward at click time so the existing motion-driven paint loop naturally waits before its first repeat. Standard auto-repeat pattern (initial delay + repeat rate, like keyboard auto-repeat).

### Mac trackpad ctrl-click compatibility

**Fixes and Maintenance**
- [populous_game/input_controller.py](../populous_game/input_controller.py) MOUSEBUTTONDOWN handler now remaps `ctrl+left-click` to button 3 for terrain-area interactions, matching the macOS trackpad convention. Previously ctrl-click was ignored: macOS reports it as `event.button == 1` with `KMOD_CTRL` set (not as `event.button == 3`), so trackpad users without a two-button mouse could not lower terrain, cancel a pending power, exit shield mode, or cancel papal mode. Menu, minimap, and HUD-button click checks still read raw `event.button` so ctrl+click on the start page or on a HUD button behaves like a normal click. The remap only applies to the iso terrain region, the shield-mode cancel branch, the pending-power cancel branch, and the papal-mode cancel branch -- exactly the spots where two-button mice currently use button 3.

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
