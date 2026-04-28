# MAP_GEN_REPORT - Initial terrain generation (Populous Amiga)

## 1) Scope and method

This document captures the initial heightmap generator used at game start.
It complements the existing terraforming analysis in
[asm/ARCHITECTURE_REPORT.md](ARCHITECTURE_REPORT.md), which covers
runtime altitude manipulation (`_make_level`, `_raise_point` from the
power system) but not the genesis pass.

Sources:
- [asm/populous_prg.asm](populous_prg.asm)

Routines analyzed:
- `_make_alt`     -- top-level: spawns three "things"
- `_make_thing`   -- one mountain: random walk + raise loop
- `_raise_point`  -- recursive single-tile raise with neighbor constraint
- `_make_map`     -- post-pass that derives `_map_alt` and `_map_blk`
  from the corner altitude grid

Grid layout: the heightmap is a 65 x 65 array of corners (`_alt`,
2 bytes per cell, stride 0x82 = 130 bytes per row). Tiles are the
64 x 64 cells between those corners. Six-pixel-wide x and y bounds
are tracked in `_xmin / _xmax / _ymin / _ymax` so later code knows
the affected region.

## 2) Top-level: `_make_alt`
Label: [asm/populous_prg.asm:1189](populous_prg.asm).

`_make_alt` calls `_make_thing` exactly three times with hard-coded
spread parameters pushed on the stack:

| Call | x-spread | y-spread | Source line |
| --- | --- | --- | --- |
| 1 | 4 | 2 | asm/populous_prg.asm:1191-1194 |
| 2 | 2 | 4 | asm/populous_prg.asm:1195-1198 |
| 3 | 3 | 3 | asm/populous_prg.asm:1199-1202 |

These two parameters control how far the random walker can step on
each axis. The asymmetry of (4,2) and (2,4) produces "things" that
elongate east-west and north-south respectively; the (3,3) call
produces a roughly circular blob. Result: three islands of mixed
shape, not pure-random noise.

## 3) Per-mountain: `_make_thing`
Label: [asm/populous_prg.asm:1208](populous_prg.asm).

Algorithm (proven from the disassembly):

1. Pick a random `(x, y)` seed in `[0, 63]` using
   `___newrand mod 64` for each axis (lines 1211-1220).
2. Loop:
   1. Call `_raise_point(x, y)` (line 1224).
   2. If the value returned in `D0` equals 6, terminate
      (line 1226-1227). The return value is the altitude of the
      tile after the raise, so this stops the moment the raise
      pushes a tile to altitude 6.
   3. Otherwise, step the seed:
      - `dx = (rand mod (2*W_x + 1)) - W_x` where `W_x` is the
        x-spread argument (lines 1228-1238).
      - `dy = (rand mod (2*W_y + 1)) - W_y` (lines 1239-1249).
   4. Clamp `x, y` to `[0, 64]` (lines 1250-1264).
   5. Branch back to step 2.1 (line 1266).

The bounded random walk keeps successive raise points clustered
around the seed, so each "thing" deposits a localized pile rather
than scattering raises across the whole grid.

Termination behavior: because `_raise_point` caps the per-call
altitude at 8 (see Section 4) and propagates raises to neighbors
when their delta exceeds 1, repeated calls in the same area form
a smooth pyramid. Once any point in that pyramid hits altitude 6,
`_make_thing` returns and the next "thing" begins.

## 4) Recursive raise with constraint: `_raise_point`
Label: [asm/populous_prg.asm:1274](populous_prg.asm).

Behavior at `(x, y)`:
1. If `x` or `y` falls outside `[0, 64]`, return 0 (lines 1279-1288).
2. Compute `(_alt + (y * 0x41 + x) * 2)` to address the corner cell
   (lines 1293-1301). Note: stride 0x41 = 65 entries, with byte
   stride 2 since each entry is a word.
3. If the cell value is already >= 8, skip the raise and return
   the current altitude (lines 1302-1303 jump to LAB_3F0AC at
   line 1414, which loads `(A2)` into `D0` and returns).
4. Increment `_build_count` and the cell value (lines 1304-1305).
5. For each of the 8 neighbors (in this order: E, SE, S, SW, W, NW,
   N, NE; the address register `A3` walks ((+2), (+0x82+2),
   (-0x82+2 reverse pattern)... see disassembly lines 1306-1393),
   if `(this) - (neighbor) > 1`, recursively call `_raise_point` on
   the neighbor. This is the "neighbors differ by at most 1" rule.
6. Update `_xmin / _xmax / _ymin / _ymax` from the current `(x, y)`
   (lines 1395-1413).
7. Return the cell value via LAB_3F0AC (line 1414-1416).

Why it produces smooth slopes: when one tile is raised from `n` to
`n+1`, any neighbor still at `n-1` now has a delta of 2 with the
raised tile, which triggers a recursive raise on the neighbor. The
recursion cascades outward until every adjacent pair differs by at
most 1, guaranteeing no cliffs in the genesis terrain. The cap at
altitude 8 stops the cascade at mountain peak height.

## 5) Post-process: `_make_map`
Label: [asm/populous_prg.asm:1420](populous_prg.asm).

`_make_map` is invoked by callers passing `(x0, y0, x1, y1)`
ranges on the stack and iterates rows (`D4`) and columns (`D5`)
through that rectangle. For each cell it:

1. Loads the 4 corner altitudes around the cell at offsets
   `(0)`, `(2)`, `(0x82)`, `(0x84)` from the corner pointer
   (lines 1442-1449).
2. Computes the average `D7 = (sum of 4 corners) >> 2`
   (lines 1450-1451). This is the "tile midpoint altitude"
   that becomes `_map_alt`.
3. Builds a 4-bit mask `D6` where each bit is set when the
   corresponding corner is strictly greater than `D7`
   (lines 1453-1474). The mask values are 1, 2, 4, 8 for the
   four corners. This mask becomes `_map_blk` and selects which
   tile sprite to draw.
4. Stores `D7` into `_map_alt[ofs]` and `D6` into `_map_blk[ofs]`
   (lines 1508-1514). Special cases at lines 1492-1506 collapse
   `(D7 != 0, D6 == 0xF)` to `(D7-1, D6 = 0xF)` to handle
   "all four corners equal and above midpoint" smoothly, and
   add 0x10 to `D6` when the tile is a partial-rise (the high
   nibble selects a different sprite bank).
5. Clears `_map_steps[ofs]` (the "tile is animated" flag,
   lines 1524-1528) so freshly generated terrain is not
   mid-flood / mid-quake.
6. If the tile was rock (`map_blk == 0x2f` per
   [asm/CONSTRUCTION_REPORT.md](CONSTRUCTION_REPORT.md) sec. 3.1),
   the original rock value is preserved (lines 1483-1486,
   1511-1517).

Net effect: `_make_map` does not change altitudes -- it derives the
sprite-index lookup tables (`_map_alt`, `_map_blk`) from the corner
grid that `_make_alt` produced. Any caller that mutates the corner
grid is expected to invoke `_make_map` (or the per-tile equivalent
`_make_level` at line 9017) afterward to refresh the lookup tables.

## 6) Why this looks like islands and not noise
Three independent observations converge:

1. **Localized seeds.** `_make_thing` does a bounded random walk
   instead of scattering raises across the whole grid, so each
   "thing" is a localized pile.
2. **Constraint propagation.** `_raise_point`'s "neighbors differ
   by at most 1" rule turns a single raised point into a small
   smooth pyramid because the cascade fans outward each time the
   peak is bumped.
3. **Three blobs of different aspect ratios.** `_make_alt`'s
   (4,2)/(2,4)/(3,3) trio guarantees one east-west island, one
   north-south island, and one rounder one, with the rest of the
   65 x 65 grid staying at altitude 0 (water).

Together these produce two-to-three sloped islands rising out of
sea level on every map, which matches the original game's
"island nation" feel.

## 7) Comparison with the current Python port
File: [populous_game/terrain.py](../populous_game/terrain.py),
function `GameMap.randomize` at line 373.

The Python port currently uses a single-pass row-by-row random walk:

```python
self.corners[0][0] = rng.randint(min_level, max_level)
for c in range(1, self.grid_width + 1):
    prev = self.corners[0][c - 1]
    self.corners[0][c] = max(min_level, min(max_level, prev + rng.choice([-1, 0, 1])))
for r in range(1, self.grid_height + 1):
    prev = self.corners[r - 1][0]
    self.corners[r][0] = max(min_level, min(max_level, prev + rng.choice([-1, 0, 1])))
    for c in range(1, self.grid_width + 1):
        left = self.corners[r][c - 1]
        up = self.corners[r - 1][c]
        lo = max(min_level, left - 1, up - 1)
        hi = min(max_level, left + 1, up + 1)
        base = max(lo, min(hi, (left + up) // 2 + rng.choice([-1, 0, 1])))
        self.corners[r][c] = base
self._enforce_height_constraints()
```

This is a different algorithm:
- **No localized seeds.** Every corner gets a random nudge from its
  neighbors, so the heightmap is filled coast-to-coast.
- **No island shapes.** The mean altitude is roughly `(max+min)/2`,
  not 0, so most tiles sit above water.
- **Adjacency constraint only along the row-major fill order.**
  `_enforce_height_constraints` at line 354 corrects violations
  after the fact rather than producing them naturally during the
  growth.

Net effect: the Python port produces a noisy continent rather than
discrete islands. To reproduce the original look, the genesis pass
should:

1. Initialize all corners to 0 (water).
2. Spawn three "things" with the same (W_x, W_y) trio: (4, 2),
   (2, 4), (3, 3).
3. Implement `_raise_point` recursively (or iteratively with an
   explicit stack) with the "neighbors differ by at most 1"
   propagation rule and a per-tile cap at 8.
4. Stop each "thing" when the random walk produces a `_raise_point`
   call that returns altitude 6.

The corner-based representation is already in place, and the existing
`propagate_raise` method on `GameMap`
([populous_game/terrain.py:94](../populous_game/terrain.py)) is a
direct equivalent of the asm `_raise_point` (it is currently used
for the in-game raise power). A faithful port would call
`propagate_raise` from the genesis loop instead of writing a new
flat random walk.

## 8) Open follow-ups
- Decide whether to ship the port as a behavior-changing replacement
  for the row-major random walk, or as an opt-in scenario flag (the
  scenario file at
  [data/scenarios/scenario_01_plateau.yaml](../data/scenarios/scenario_01_plateau.yaml)
  is the natural place for that toggle).
- Re-confirm the "stop when raise returns 6" termination by single-
  stepping the asm under an emulator. The disassembly is clear
  (CMP.W #$0006,D0; BEQ terminate at lines 1226-1227) but a runtime
  trace would also confirm whether the (4,2)/(2,4)/(3,3) parameters
  are picked up unmodified.
- The 0x10 high-nibble add in `_make_map` (line 1506) is documented
  here as "alternate sprite bank for partial-rise tiles" but the
  exact sprite split is best confirmed against
  [asm/MINIMAP_REPORT.md](MINIMAP_REPORT.md) and the tile sprite
  sheets in `data/gfx/`. That detail belongs to the renderer, not
  the genesis pass.
