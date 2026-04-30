"""Atlas metadata layer for sprite sheets.

Each sheet under data/gfx/ has its slicing geometry described once,
in this module, instead of having origin/stride/cell-size literals
scattered through renderer code. Callers should ask for named frames
through `frame_rect()` rather than reaching into a layout directly.

Round 2 of the parity tranche (WP-H1) lands the data structures and
sheet descriptors; existing slicing in
[populous_game/peeps.py](peeps.py) and
[populous_game/terrain.py](terrain.py) is migrated in a follow-up
patch so behavior stays byte-identical during the cutover.
"""

import collections


# Layout descriptor for a single sprite sheet. Coordinates are in
# source pixels before any runtime scaling.
#
# - sheet:     filename (relative to data/gfx/) of the source PNG.
# - cell_w:    width of a cell in source pixels.
# - cell_h:    height of a cell in source pixels.
# - origin_x:  x of cell (0, 0) top-left in source pixels.
# - origin_y:  y of cell (0, 0) top-left in source pixels.
# - stride_x:  pixel distance between adjacent column origins.
# - stride_y:  pixel distance between adjacent row origins.
# - rows:      total rows in the sheet (None when not yet audited).
# - cols:      total columns in the sheet (None when not yet audited).
_ATLAS_LAYOUT_FIELDS = (
	'sheet',
	'cell_w', 'cell_h',
	'origin_x', 'origin_y',
	'stride_x', 'stride_y',
	'rows', 'cols',
)
AtlasLayout = collections.namedtuple('AtlasLayout', _ATLAS_LAYOUT_FIELDS)


# Existing slicing in populous_game/peeps.py uses these values.
# Documented in data/gfx/ATLAS_LAYOUT.md.
AMIGA_SPRITES1_LAYOUT = AtlasLayout(
	sheet='AmigaSprites1.PNG',
	cell_w=16, cell_h=16,
	origin_x=11, origin_y=10,
	stride_x=20, stride_y=20,
	rows=9, cols=16,
)

# Existing slicing in populous_game/terrain.py.
AMIGA_TILES_LAYOUT = AtlasLayout(
	sheet='AmigaTiles1.PNG',
	cell_w=32, cell_h=24,
	origin_x=12, origin_y=10,
	stride_x=35, stride_y=27,
	rows=8, cols=9,
)

# Existing slicing in populous_game/assets.py for weapon icons.
WEAPONS_LAYOUT = AtlasLayout(
	sheet='Weapons.png',
	cell_w=16, cell_h=16,
	origin_x=0, origin_y=0,
	stride_x=16, stride_y=16,
	rows=1, cols=10,
)

# Existing slicing in populous_game/assets.py for HUD button icons.
BUTTONUI_LAYOUT = AtlasLayout(
	sheet='ButtonUI.png',
	cell_w=34, cell_h=17,
	origin_x=0, origin_y=0,
	stride_x=34, stride_y=17,
	rows=5, cols=5,
)


def frame_rect(layout: AtlasLayout, row: int, col: int) -> tuple:
	"""Return the (x, y, w, h) source rectangle for cell (row, col).

	Pure: does not require pygame, does not load images, does not
	depend on runtime scaling. Renderer code can call this and pass
	the rectangle to `pygame.Rect(*frame_rect(...))` or directly to
	`Surface.subsurface()`.
	"""
	x = layout.origin_x + col * layout.stride_x
	y = layout.origin_y + row * layout.stride_y
	rect = (x, y, layout.cell_w, layout.cell_h)
	return rect


# Named-frame registry. Each entry is a tuple of
# (layout, [(row, col), ...]). Build out as named mappings land.
# Knight player/enemy frame mappings are deferred to WP-G2 once the
# visual audit pins the rows/cols.
NAMED_FRAMES: dict = {}
