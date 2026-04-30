"""Pin behavior of the atlas_metadata layer (WP-H1 scaffolding)."""

import populous_game.atlas_metadata as atlas_metadata


def test_amiga_sprites1_geometry_matches_existing_slicing():
	"""Layout values must match the literals already in peeps.py."""
	layout = atlas_metadata.AMIGA_SPRITES1_LAYOUT
	assert layout.sheet == 'AmigaSprites1.PNG'
	assert layout.cell_w == 16 and layout.cell_h == 16
	assert layout.origin_x == 11 and layout.origin_y == 10
	assert layout.stride_x == 20 and layout.stride_y == 20


def test_frame_rect_is_pure():
	"""frame_rect() returns the source pixel rectangle deterministically."""
	layout = atlas_metadata.AMIGA_SPRITES1_LAYOUT
	x, y, w, h = atlas_metadata.frame_rect(layout, 0, 0)
	assert (x, y, w, h) == (11, 10, 16, 16)
	x2, y2, w2, h2 = atlas_metadata.frame_rect(layout, 1, 2)
	assert (x2, y2, w2, h2) == (11 + 2 * 20, 10 + 1 * 20, 16, 16)


def test_weapons_and_button_layouts_present():
	"""Round 2 ships layout descriptors for all four atlases."""
	for layout in (
		atlas_metadata.AMIGA_SPRITES1_LAYOUT,
		atlas_metadata.AMIGA_TILES_LAYOUT,
		atlas_metadata.WEAPONS_LAYOUT,
		atlas_metadata.BUTTONUI_LAYOUT,
	):
		assert layout.cell_w > 0 and layout.cell_h > 0
		assert layout.stride_x >= layout.cell_w
		assert layout.stride_y >= layout.cell_h
