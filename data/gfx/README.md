# Graphics assets

This folder contains the runtime graphics used by the Python Populous
port. It is an asset folder, not a scratch directory.

Most files here are sprite sheets or tile atlases extracted from the
Amiga asset set. Keep those sheets intact. Their row and column
layout is data, especially when matching renderer behavior to the
original ASM references under [asm/](../../asm/).

For exact atlas geometry, slicing formulas, and ASM parity notes, see
[data/gfx/ATLAS_LAYOUT.md](ATLAS_LAYOUT.md).

## Folder policy

Use atlas sheets as the source of truth.

Do not split a sheet into many loose PNG files just because one tile
or sprite is needed. Instead, add a named atlas mapping in the code
that records where that tile or sprite lives in the sheet.

Loose PNG files are allowed only when the image has a clear standalone
runtime purpose and is not already part of a sheet.

Do not add generated contact sheets, cropped experiments, screenshots,
or visual notes to this folder. Put temporary visual diagnostics under
`output/` or `/tmp`, and put durable tooling under
[tools/](../../tools/).

## File roles

| File | Role | Runtime status |
| --- | --- | --- |
| `AmigaSprites1.PNG` | Main entity/effect sprite atlas | Active |
| `Sprites.PNG` | Older alternate sprite sheet | Reference / audit |
| `AmigaTiles1.PNG` | Active terrain tile bank | Active |
| `AmigaTiles2.PNG` | Alternate terrain tile bank | Reference / future |
| `AmigaTiles3.PNG` | Alternate terrain tile bank | Reference / future |
| `AmigaTiles4.PNG` | Alternate terrain tile bank | Reference / future |
| `AmigaUI.png` | Main 320 x 200 HUD chrome | Active |
| `AmigaUI_click.png` | Pressed-button HUD reference | Reference / future |
| `AmigaUI_backup.png` | Backup/comparison HUD copy | Reference |
| `ButtonUI.png` | Power and direction button atlas | Active |
| `Weapons.png` | Shield-panel weapon/building icon atlas | Active |
| `knight_peep.png` | Transitional loose knight portrait | Retiring |

If a file is marked reference/future, keep it until the related audit
confirms that no runtime or parity work needs it. Do not remove
reference assets as a cleanup shortcut.

## Current files

### Unit and effect sprites

- `AmigaSprites1.PNG`
  - Main animated sprite sheet.
  - Sliced today by `load_sprite_surfaces()` in
    [populous_game/peeps.py](../../populous_game/peeps.py); row 0
    drives `PEEP_WALK_FRAMES` (alias `WALK_FRAMES`).
  - Contains peeps, faction variants, promoted units, ghosts, flames,
    shields, weapons, effects, and small icon-like frames.
  - Source of truth for animated world entities and (after WP-G3) the
    knight portrait used in the shield panel.

- `Sprites.PNG`
  - Additional sprite sheet from the original asset set.
  - Keep intact until its exact role is fully mapped. The WP-G2 audit
    should confirm whether any runtime path still reads it.
  - Do not use it for new runtime frames unless the frame is missing
    from `AmigaSprites1.PNG`.

### Terrain and object tiles

- `AmigaTiles1.PNG`
- `AmigaTiles2.PNG`
- `AmigaTiles3.PNG`
- `AmigaTiles4.PNG`

These are terrain/object tile sheets. They include land, water,
slopes, rocks, buildings, vegetation, ruins, bridges, and other world
tiles.

Use these sheets for terrain rendering and future ASM tile/block
parity work. `AmigaTiles1.PNG` is the active runtime bank through
`settings.TILES_PATH`; the other banks should stay available for
theme or level-bank work. Do not crop individual terrain tiles into
separate runtime files.

### UI graphics

- `AmigaUI.png`
  - Main UI sheet. The iso-diamond hole at the center is punched
    transparent at load time by
    [populous_game/iso_hole.py](../../populous_game/iso_hole.py) so
    terrain renders under the HUD.

- `AmigaUI_click.png`
  - Clicked or active UI states.

- `AmigaUI_backup.png`
  - Backup or comparison copy. Keep only if it remains useful or
    referenced; safe to remove during the WP-G5 / asset-cleanup pass
    once references are confirmed clear.

- `ButtonUI.png`
  - Button UI atlas. 5 rows x 5 cols, 34 x 17 px cells. Action-name
    mapping lives in `button_order` inside
    [populous_game/assets.py](../../populous_game/assets.py)
    (`load_all()`).

### Weapon icons

- `Weapons.png`
  - Weapon icon atlas. 1 row x 10 cols, 16 x 16 px cells.
  - Mapping is `_WEAPON_SPRITE_INDICES` in
    [populous_game/assets.py](../../populous_game/assets.py):
    `{'hut': 0, 'house_small': 1, ..., 'castle': 9}`.
  - Use atlas slicing rather than loose weapon icon files.

## Runtime ownership

Runtime consumers should load these assets through stable modules:

| Asset family | Primary consumer |
| --- | --- |
| Terrain tiles | [populous_game/terrain.py](../../populous_game/terrain.py) |
| Peep/world sprites | [populous_game/peeps.py](../../populous_game/peeps.py) |
| HUD, buttons, weapons | [populous_game/assets.py](../../populous_game/assets.py) |
| HUD hole mask | [populous_game/iso_hole.py](../../populous_game/iso_hole.py) |
| Map-well measurement | [tools/measure_map_well.py](../../tools/measure_map_well.py) |
| Visual tile audit | [tools/tile_diagnostic.py](../../tools/tile_diagnostic.py) |
| Visual sprite audit | [tools/sprite_diagnostic.py](../../tools/sprite_diagnostic.py) |

New renderer code should not open PNGs directly when an existing
asset module can provide the surface.

## Atlas mapping policy

Runtime code should ask for named frames, not hardcoded crop
rectangles scattered through renderer code.

Good:

```python
frame = assets.get_sprite_frame("player_peep_walk", direction, anim_frame)
```

Bad:

```python
frame = sheet.subsurface(pygame.Rect(11 + 20 * 3, 10 + 20 * 0, 16, 16))
```

The named-frame layer (planned in WP-H1) keeps the code readable, lets
the audit catch ASM-tile-id drift, and makes it cheap to swap atlas
sheets without combing through renderer call sites.

Keep semantic names close to gameplay concepts:

- `player_peep_walk`
- `enemy_peep_walk`
- `player_knight_walk`
- `enemy_knight_walk`
- `shield_knight_portrait`
- `terrain_water_0`
- `terrain_flat_land`
- `terrain_slope_high_nw`
- `button_do_flood`

Exact names may differ once the metadata layer lands, but the naming
should describe the frame's role rather than its crop rectangle.

## ASM parity policy

The ASM references describe behavior in terms of original tables and
state, not modern file names. When documenting parity, keep both
layers visible:

- Python semantic name, such as `terrain_flat_land`.
- Atlas coordinate, such as `(row: 1, col: 6)`.
- Original ASM id, such as `_map_blk`, when verified.

Use `unknown`, `null`, or a clearly marked audit note when an ASM id
has not been confirmed. Do not infer a block id from visual similarity
alone.

## Loose and retired assets

- `knight_peep.png` is scheduled for removal in WP-G5 once the
  atlas-driven knight rendering lands. Do not add new loose knight
  PNGs. The shield-panel portrait branch currently derives from this
  file as a transitional shim and should move to atlas metadata.
- `knight_peep.gif` is not present in the current folder. Do not
  reintroduce it unless the runtime needs an external animation source
  that cannot be represented by `AmigaSprites1.PNG`.

## Adding or changing assets

When adding or changing graphics:

- Keep filenames lowercase with underscores unless preserving an
  original `Amiga*.PNG` source name.
- Prefer PNG for runtime graphics.
- Keep generated outputs out of `data/gfx/`.
- Update [data/gfx/ATLAS_LAYOUT.md](ATLAS_LAYOUT.md) if geometry,
  dimensions, frame names, or bank roles change.
- Update code constants in one place rather than duplicating crop math.
- Add or update focused tests when the runtime behavior changes.
- Add a dated note to [docs/CHANGELOG.md](../../docs/CHANGELOG.md).

Documentation-only changes do not need gameplay tests.

## Related docs

- [data/gfx/ATLAS_LAYOUT.md](ATLAS_LAYOUT.md) -- atlas geometry,
  slicing rules, tile banks, and ASM parity notes.
- [docs/active_plans/](../../docs/active_plans/) -- current visual
  parity / atlas-mapping plan.
- [docs/CODE_ARCHITECTURE.md](../../docs/CODE_ARCHITECTURE.md) --
  overall code layout including renderer/asset boundaries.
- [asm/PEEPS_BEHAVIOR.md](../../asm/PEEPS_BEHAVIOR.md) -- ASM-side
  reference for peep frame ordering.
- [asm/MAP_GEN_REPORT.md](../../asm/MAP_GEN_REPORT.md) -- map-block
  and terrain generation reference.
