# Atlas layout

This file is the technical atlas reference for `data/gfx/`. It records
source dimensions, slicing geometry, known frame mappings, tile-bank
roles, and ASM parity notes.

For folder-level policy, asset ownership, and rules for adding files,
see [data/gfx/README.md](README.md).

The renderer should request named frames through the metadata layer
(WP-H1) instead of hardcoded `(row, col)` indexes.

## Reference status

Status terms used below:

- `Verified`: measured from current files or active code.
- `Runtime`: active code depends on this mapping today.
- `Working`: plausible from visual/code comments, but needs audit.
- `Unknown`: keep explicit; do not guess.

The current runtime still slices several atlases directly in
[populous_game/terrain.py](../../populous_game/terrain.py),
[populous_game/peeps.py](../../populous_game/peeps.py), and
[populous_game/assets.py](../../populous_game/assets.py). The target
metadata layer should centralize those rectangles without changing the
source images.

## Coordinate conventions

Atlas coordinates use source pixels before any runtime scaling.

- `origin` is the top-left source pixel of cell `(0, 0)`.
- `cell size` is the copied rectangle size.
- `stride` is the distance between adjacent cell origins.
- `row` increases downward.
- `col` increases to the right.
- Runtime scaling happens after extraction.

Formula:

```text
x = origin_x + col * stride_x
y = origin_y + row * stride_y
rect = (x, y, cell_w, cell_h)
```

The bright green source background `(0, 49, 0)` is transparent for the
Amiga terrain and sprite sheets.

## Runtime scaling

All atlas geometry below is in original logical pixel space (the
original Amiga atlas dimensions). It does NOT change when the runtime
loader resolves a 4x Upscayl sheet.

Runtime extraction is centralized in
[populous_game/sheet_loader.py](../../populous_game/sheet_loader.py)
through `extract_frame(role, logical_rect, runtime_size, ...)`. The
extractor:

- Resolves the role through
  [populous_game/sheet_registry.py](../../populous_game/sheet_registry.py),
  preferring the 4x Upscayl sheet when present and falling back to
  the original PNG when not. Each candidate declares its own
  `source_scale` (4 or 1).
- Multiplies the logical crop rectangle by `source_scale` before
  `subsurface()`, so the same logical rect works for both 1x and 4x
  sheets.
- Resizes the cropped frame to `runtime_size` with smoothscale (when
  downscaling from a 4x sheet) or nearest-neighbor (when scaling up
  from a 1x sheet, preserving the chunky Amiga pixel-art look).
- Caches by `(role, logical_rect, runtime_size, scale_filter)`.

Cached runtime sizes:

- Terrain tiles: `(32 * settings.TERRAIN_SCALE, 24 * settings.TERRAIN_SCALE)`.
- Peep sprites: `(SPRITE_SIZE * settings.TERRAIN_SCALE, ...)`.
- HUD chrome: `(settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT)`.
- Weapon icons: `(16 * settings.HUD_SCALE, 16 * settings.HUD_SCALE)`.
- Button cells: `(34 * settings.HUD_SCALE, 17 * settings.HUD_SCALE)`.

Do not store scaled sizes in atlas metadata. Store only source
rectangles in original logical pixel coordinates and let the runtime
consumer pass the runtime target size to `extract_frame`.

## AmigaSprites1.PNG

Animated peeps, knights, ghosts, flames, weapons, and small UI
icons. This is the source of truth for the world peep sprite set
and for the knight portrait used in the shield panel.

| Property        | Value           |
| ---             | ---             |
| Image size      | 336 x 262 px    |
| Cell size       | 16 x 16 px      |
| Origin (x, y)   | (11, 10)        |
| Stride (x, y)   | (20, 20)        |
| Columns         | 16              |
| Rows            | 9               |
| Transparent key | (0, 49, 0)      |
| Status          | Verified        |

Existing slicing lives in
[populous_game/peeps.py](../../populous_game/peeps.py)
`load_sprite_surfaces()`. `WALK_FRAMES` (alias `PEEP_WALK_FRAMES`)
indexes row 0 today.

### Sprite rectangle examples

| Cell | Rect |
| --- | --- |
| `(0, 0)` | `(11, 10, 16, 16)` |
| `(0, 1)` | `(31, 10, 16, 16)` |
| `(1, 0)` | `(11, 30, 16, 16)` |
| `(5, 8)` | `(171, 110, 16, 16)` |

Approximate row legend (from existing comments in
[populous_game/peeps.py](../../populous_game/peeps.py); confirm by
visual audit before locking the named mapping):

| Row | Contents | Status |
| --- | --- | --- |
| 0 | Blue/player peep walk frames, all 8 facings | Runtime |
| 1 | Blue/player walk continuation or variants | Working |
| 2 | Red/enemy peep walk frames | Working |
| 3 | Red/enemy walk continuation or variants | Working |
| 4 | Fight, battle, or special frames | Working |
| 5 | Drown/death/soul frames; `DROWN` uses `(5, 8..11)` | Runtime |
| 6 | Effects and flames | Working |
| 7 | Items and weapons | Working |
| 8 | UI or power icons | Working |

### Current peep animation map

`PEEP_WALK_FRAMES` currently uses row 0 only:

| Direction | Cells |
| --- | --- |
| `N` | `(0, 0)`, `(0, 1)` |
| `NE` | `(0, 2)`, `(0, 3)` |
| `E` | `(0, 4)`, `(0, 5)` |
| `SE` | `(0, 6)`, `(0, 7)` |
| `S` | `(0, 8)`, `(0, 9)` |
| `SW` | `(0, 10)`, `(0, 11)` |
| `W` | `(0, 12)`, `(0, 13)` |
| `NW` | `(0, 14)`, `(0, 15)` |
| `IDLE` | `(0, 8)`, `(0, 9)` |
| `DROWN` | `(5, 8)`, `(5, 9)`, `(5, 10)`, `(5, 11)` |

Knight frames are believed to live in this atlas as repeated
animation cells with player (blue) and enemy (red) variants. The
WP-G2 audit should fill in:

- Player knight rows/columns and per-facing frame ordering.
- Enemy knight rows/columns and per-facing frame ordering.
- Whether ordering matches `PEEP_WALK_FRAMES`.
- Which single atlas frame is the shield-portrait fallback.

Proposed named keys (to land in WP-H1 / WP-G2):

- `player_peep_walk`
- `enemy_peep_walk`
- `player_knight_walk`
- `enemy_knight_walk`
- `knight_shield_portrait`

Current runtime transforms:

- `load_sprite_surfaces()` extracts 16 x 16 cells.
- It removes residual black pixels by setting their alpha to zero.
- It scales each cell by `settings.TERRAIN_SCALE`.
- Peep rendering should continue to use named animation frames, not
  raw visual searches.

## AmigaTiles1.PNG .. AmigaTiles4.PNG

Terrain, building, object, and slope tiles. All four files share the
same sheet dimensions and grid geometry.

| Property        | Value           |
| ---             | ---             |
| Image size      | 336 x 262 px    |
| Cell size       | 32 x 24 px      |
| Origin (x, y)   | (12, 10)        |
| Stride (x, y)   | (35, 27)        |
| Columns         | 9               |
| Rows            | 8               |
| Last row        | Columns 0..4    |
| Transparent key | (0, 49, 0)      |
| Status          | Verified        |

Existing slicing lives in
[populous_game/terrain.py](../../populous_game/terrain.py)
`load_tile_surfaces()` and in
[tools/tile_diagnostic.py](../../tools/tile_diagnostic.py). The final
row is partial: row 7 has only columns 0 through 4.

### Tile rectangle examples

| Cell | Rect |
| --- | --- |
| `(0, 0)` | `(12, 10, 32, 24)` |
| `(0, 1)` | `(47, 10, 32, 24)` |
| `(1, 0)` | `(12, 37, 32, 24)` |
| `(7, 4)` | `(152, 199, 32, 24)` |

### Current terrain mapping

The active runtime uses `AmigaTiles1.png` resolved through
[populous_game/sheet_registry.py](../../populous_game/sheet_registry.py)
under role `tiles_1` (4x Upscayl preferred, original PNG fallback).
The semantic key -> atlas-coordinate mapping is stored in
[populous_game/settings.py](../../populous_game/settings.py).

| Python key | Atlas coordinate | Status |
| --- | --- | --- |
| `TILE_WATER` | `(0, 0)` | Runtime |
| `TILE_WATER_2` | `(1, 7)` | Runtime |
| `TILE_FLAT` | `(1, 6)` | Runtime |
| `TILE_CONSTRUCTED` | `(3, 4)` | Runtime |

Building tiles:

| Python key | Atlas coordinate | Status |
| --- | --- | --- |
| `hut` | `(3, 6)` | Runtime |
| `house_small` | `(3, 7)` | Runtime |
| `house_medium` | `(3, 8)` | Runtime |
| `castle_small` | `(4, 0)` | Runtime |
| `castle_medium` | `(4, 1)` | Runtime |
| `castle_large` | `(4, 2)` | Runtime |
| `fortress_small` | `(4, 3)` | Runtime |
| `fortress_medium` | `(4, 4)` | Runtime |
| `fortress_large` | `(4, 5)` | Runtime |

Large-castle composition tiles:

| Python key | Atlas coordinate | Status |
| --- | --- | --- |
| `corner` | `(4, 5)` | Runtime |
| `center` | `(4, 6)` | Runtime |
| `side_lr` | `(4, 7)` | Runtime |
| `side_tb` | `(4, 8)` | Runtime |

Object tiles:

| Python key | Atlas coordinate | Status |
| --- | --- | --- |
| `volcano` | `(5, 0)` | Runtime |
| `cross` | `(5, 1)` | Runtime |
| `mountain_small` | `(5, 2)` | Runtime |
| `mountain_large` | `(5, 3)` | Runtime |
| `tree_small` | `(5, 4)` | Runtime |
| `tree_medium` | `(5, 5)` | Runtime |
| `tree_large` | `(5, 6)` | Runtime |
| `bush` | `(5, 7)` | Runtime |

Slope tiles are keyed by corner deltas in `SLOPE_TILES` and
`SLOPE_TILES_LOW`. The corner order is:

```text
(NW, NE, SE, SW)
```

`SLOPE_TILES` covers higher-altitude slopes. `SLOPE_TILES_LOW`
covers the first land tier above water. Keep those two banks distinct
until ASM map-block parity is verified.

### ASM parity notes

The ASM reports describe the original map as a corner-height grid plus
derived map-block tables. In particular,
[asm/MAP_GEN_REPORT.md](../../asm/MAP_GEN_REPORT.md) documents
`_make_map`, `_map_alt`, and `_map_blk`. The renderer-facing metadata
should eventually map those original block values to atlas cells.

Do not assume the current row/column names are final ASM names. The
current table is a working Python mapping that produces sensible
terrain; the target table should preserve both:

- the existing semantic names used by Python code;
- the original ASM block ids once each visual mapping is confirmed.

Recommended future structure:

```text
tile_bank:
  source: AmigaTiles1.PNG
  cells:
    water_0: {row: 0, col: 0, asm_blk: null}
    flat_land: {row: 1, col: 6, asm_blk: null}
```

Use `null` for unknown ASM ids rather than guessing.

Suggested metadata fields:

| Field | Purpose |
| --- | --- |
| `name` | Stable Python semantic key |
| `source` | Atlas file name |
| `row` | Source atlas row |
| `col` | Source atlas column |
| `rect` | Derived or cached source rectangle |
| `transparent_key` | Source color key, if any |
| `asm_blk` | Verified original `_map_blk` id, or `null` |
| `notes` | Short audit note when status is not verified |

### Tile-bank roles

The exact theme split across `AmigaTiles1.PNG` through
`AmigaTiles4.PNG` still needs visual audit. Until that audit lands,
document them as same-layout banks:

| File | Current role | Status |
| --- | --- | --- |
| `AmigaTiles1.PNG` | Active terrain sheet used by runtime | Runtime |
| `AmigaTiles2.PNG` | Same-layout alternate terrain bank | Working |
| `AmigaTiles3.PNG` | Same-layout alternate terrain bank | Working |
| `AmigaTiles4.PNG` | Same-layout alternate terrain bank | Working |

Future metadata should select a bank by game theme or level setting
instead of changing the slicing code.

## Weapons.png

Weapon and building icons used by the shield panel weapon quadrant.
Loaded in
[populous_game/assets.py](../../populous_game/assets.py)
`load_all()`.

| Property        | Value             |
| ---             | ---               |
| Image size      | 160 x 16 px       |
| Cell size       | 16 x 16 px        |
| Layout          | 1 row x 10 cols   |
| Origin (x, y)   | (0, 0)            |
| Stride (x, y)   | (16, 16)          |
| Status          | Verified          |

The mapping is
`{'hut': 0, 'house_small': 1, ..., 'castle': 9}`.

| Index | Key |
| --- | --- |
| 0 | `hut` |
| 1 | `house_small` |
| 2 | `house_medium` |
| 3 | `castle_small` |
| 4 | `castle_medium` |
| 5 | `castle_large` |
| 6 | `fortress_small` |
| 7 | `fortress_medium` |
| 8 | `fortress_large` |
| 9 | `castle` |

## ButtonUI.png

Power and direction buttons for the shield-panel HUD. Loaded in
[populous_game/assets.py](../../populous_game/assets.py).

| Property        | Value             |
| ---             | ---               |
| Image size      | 170 x 85 px       |
| Cell size       | 34 x 17 px        |
| Layout          | 5 rows x 5 cols   |
| Origin (x, y)   | (0, 0)            |
| Stride (x, y)   | (34, 17)          |
| Status          | Verified          |

The mapping is the `button_order` list in
[populous_game/assets.py](../../populous_game/assets.py).

Button atlas order is row-major:

| Index | Action |
| --- | --- |
| 0 | `_do_flood` |
| 1 | `_battle_over` |
| 2 | `_do_quake` |
| 3 | `NW` |
| 4 | `N` |
| 5 | `NE` |
| 6 | `_do_shield` |
| 7 | `_find_papal` |
| 8 | `_find_knight` |
| 9 | `_do_volcano` |
| 10 | `_do_knight` |
| 11 | `W` |
| 12 | `_find_shield` |
| 13 | `E` |
| 14 | `_raise_terrain` |
| 15 | `_find_battle` |
| 16 | `_do_swamp` |
| 17 | `SW` |
| 18 | `S` |
| 19 | `SE` |
| 20 | `_do_papal` |
| 21 | `_go_papal` |
| 22 | `_go_build` |
| 23 | `_go_assemble` |
| 24 | `_go_fight` |

## AmigaUI.png / AmigaUI_backup.png / AmigaUI_click.png

The base HUD chrome plus its backup and click-state variants. The
iso-diamond hole in the active sheet is punched transparent at load
time by [populous_game/iso_hole.py](../../populous_game/iso_hole.py).
`AmigaUI_backup.png` is a reference copy and may be removed in a
future asset cleanup once references are confirmed clear.

| File | Size | Runtime role |
| --- | --- | --- |
| `AmigaUI.png` | 320 x 200 px | Active HUD chrome |
| `AmigaUI_click.png` | 320 x 200 px | Pressed-button reference |
| `AmigaUI_backup.png` | 320 x 200 px | Reference copy |

The map well is measured in logical 320 x 200 coordinates. The current
runtime constant is `MAP_WELL_RECT_LOGICAL = (64, 72, 256, 128)` in
[populous_game/settings.py](../../populous_game/settings.py). Re-run
[tools/measure_map_well.py](../../tools/measure_map_well.py) if the
HUD source image changes.

## Sprites.PNG

Older sprite sheet kept alongside `AmigaSprites1.PNG`. Verify in the
audit whether any runtime path still reads it; if not, treat it as a
documentation-only reference rather than a runtime asset.

| Property   | Value        |
| ---        | ---          |
| Image size | 325 x 172 px |
| Status     | Working      |

`Sprites.PNG` uses a different layout from `AmigaSprites1.PNG`.
Diagnostic support exists in
[tools/sprite_diagnostic.py](../../tools/sprite_diagnostic.py), but
new runtime work should prefer `AmigaSprites1.PNG` unless a visual
audit proves a missing frame exists only in this older sheet.

## Retired loose assets

`knight_peep.png` is scheduled for removal in WP-G5 once the
atlas-driven knight rendering lands. Do not add new loose knight PNGs.

`knight_peep.gif` is not present in the current `data/gfx/` directory.
Do not reintroduce it unless the runtime needs an external animation
source that cannot be represented by `AmigaSprites1.PNG`.

## Verification checklist

- Run `file data/gfx/*` after asset changes and update image sizes.
- Run `source source_me.sh && python tools/tile_diagnostic.py` for
  visual terrain audit.
- Run `source source_me.sh && python tools/sprite_diagnostic.py` for
  visual sprite audit.
- Keep atlas metadata ASCII-only and link code references with
  relative Markdown links.
- When a mapping changes runtime behavior, add focused tests for the
  consumer code rather than testing raw PNG pixels.

## Open audit items

- Confirm the visual role of `AmigaTiles2.PNG` through
  `AmigaTiles4.PNG`.
- Confirm player and enemy knight frame rows in `AmigaSprites1.PNG`.
- Confirm whether `Sprites.PNG` has any frame not present in
  `AmigaSprites1.PNG`.
- Map verified `_map_blk` values from the ASM reports to terrain
  atlas cells.
- Replace transitional loose knight portrait loading with an atlas
  frame once the knight audit is complete.
