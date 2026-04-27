"""Sprite geometry calculations for peeps and houses.

Sprite-anchor metadata (SPRITE_ANCHORS) is the single source of truth
for translating a tile-corner ground anchor into a sprite blit rect. The
ViewportTransform's world_to_screen returns the iso projection of the
(row, col) world corner; sprite_geometry layers the per-sprite-type
offset (dx, dy) and centering convention from this table on top.

No per-object pixel literals (e.g., +TILE_HALF_H, -TILE_WIDTH) belong
in the rect-building functions below -- if you need a new offset, add a
SPRITE_ANCHORS entry instead.
"""

import pygame
import populous_game.settings as settings
import populous_game.peeps as peep


# Sprite anchor metadata. Each entry describes how a sprite of a given
# class is positioned relative to the ground anchor pixel returned by
# transform.world_to_screen(row, col, altitude).
#
# Schema:
#   dx, dy           -- pixel offset added to the ground anchor before
#                       any centering. dx and dy are pre-centering, so
#                       a peep that should "drop half a tile" before its
#                       feet land on the ground stores dy=TILE_HALF_H.
#   center_x         -- if True, subtract sprite_w // 2 from blit_x so
#                       the sprite is horizontally centered on the
#                       anchor. If False, the sprite's top-left X equals
#                       anchor_x + dx.
#   align_bottom_y   -- if True, subtract sprite_h from blit_y so the
#                       sprite sits with its feet on (anchor_y + dy).
#                       If False, the sprite's top-left Y equals
#                       anchor_y + dy.
#
# Building-type keys must cover every entry in
# populous_game.settings.BUILDING_TILES plus the special 'castle' type
# emitted by populous_game.houses.House when it reaches the top tier.
SPRITE_ANCHORS: dict = {
	# Peeps: anchor drops by TILE_HALF_H so the iso projection of the
	# tile corner becomes the foot point under the sprite. The sprite
	# is centered horizontally on the anchor and bottom-aligned so the
	# feet sit on the ground line.
	'peep_default': {
		'dx': 0,
		'dy': settings.TILE_HALF_H,
		'center_x': True,
		'align_bottom_y': True,
	},
	# Standard houses (hut, house_*, castle_small/medium/large,
	# fortress_*) blit with their top-left at (anchor_x - TILE_HALF_W,
	# anchor_y). The sprite tile already encodes its iso footprint; we
	# only shift left by half a tile so the diamond aligns with the
	# tile under it.
	'hut': {
		'dx': -settings.TILE_HALF_W, 'dy': 0,
		'center_x': False, 'align_bottom_y': False,
	},
	'house_small': {
		'dx': -settings.TILE_HALF_W, 'dy': 0,
		'center_x': False, 'align_bottom_y': False,
	},
	'house_medium': {
		'dx': -settings.TILE_HALF_W, 'dy': 0,
		'center_x': False, 'align_bottom_y': False,
	},
	'castle_small': {
		'dx': -settings.TILE_HALF_W, 'dy': 0,
		'center_x': False, 'align_bottom_y': False,
	},
	'castle_medium': {
		'dx': -settings.TILE_HALF_W, 'dy': 0,
		'center_x': False, 'align_bottom_y': False,
	},
	'castle_large': {
		'dx': -settings.TILE_HALF_W, 'dy': 0,
		'center_x': False, 'align_bottom_y': False,
	},
	'fortress_small': {
		'dx': -settings.TILE_HALF_W, 'dy': 0,
		'center_x': False, 'align_bottom_y': False,
	},
	'fortress_medium': {
		'dx': -settings.TILE_HALF_W, 'dy': 0,
		'center_x': False, 'align_bottom_y': False,
	},
	'fortress_large': {
		'dx': -settings.TILE_HALF_W, 'dy': 0,
		'center_x': False, 'align_bottom_y': False,
	},
	# Top-tier 'castle' building (House.TYPES last entry) is rendered
	# as a 2x2 tile rect rather than a single tile sprite. Its blit
	# rect is anchored a full tile up and to the left of the ground
	# corner, with explicit width/height of (TILE_WIDTH*2, TILE_HEIGHT*2)
	# stored in 'size' below since this case has no underlying sprite
	# surface to query for dimensions.
	'castle': {
		'dx': -settings.TILE_WIDTH, 'dy': -settings.TILE_HEIGHT,
		'center_x': False, 'align_bottom_y': False,
		'size': (settings.TILE_WIDTH * 2, settings.TILE_HEIGHT * 2),
	},
}

# Fallback rect dimensions for a peep when the sprite asset is missing.
# Kept here rather than inline so the rect-building function stays free
# of pixel literals. This is a debug fallback, not part of the normal
# render path.
PEEP_FALLBACK_SIZE: tuple = (8, 8)

# Fallback rect dimensions for a house when the building tile surface
# cannot be resolved. Pulled from settings.TILE_WIDTH / TILE_HEIGHT so
# the fallback diamond sits at the same size as a real tile.
HOUSE_FALLBACK_SIZE: tuple = (settings.TILE_WIDTH, settings.TILE_HEIGHT)


def _peep_anchor_key(p) -> str:
	"""Pick the SPRITE_ANCHORS key for the given peep instance.

	Currently all peep states share the same ground-anchor convention,
	so this returns 'peep_default' unconditionally. State-specific
	offsets (e.g., a different dy for a drowning peep) would be added
	as new SPRITE_ANCHORS entries and selected here.
	"""
	return 'peep_default'


def _apply_anchor(anchor_xy: tuple, meta: dict, size_xy: tuple) -> tuple:
	"""Translate a ground anchor + sprite size to a top-left blit pos.

	SPRITE_ANCHORS stores `dx`/`dy` in BASE (logical) px so the table
	stays preset-agnostic. The active TERRAIN_SCALE is applied here at
	use site, after the anchor lookup, so a future preset switch (or a
	mid-test mutation of `settings.TERRAIN_SCALE`) is picked up
	immediately without rebuilding the table.

	Args:
		anchor_xy: (ax, ay) ground-anchor pixel from world_to_screen.
		meta: SPRITE_ANCHORS entry describing dx, dy, and centering.
		size_xy: (sprite_w, sprite_h) of the rendered sprite (already
			scaled by TERRAIN_SCALE).

	Returns:
		(blit_x, blit_y) top-left pixel for pygame.Rect construction.
	"""
	ax, ay = anchor_xy
	sw, sh = size_xy
	# Pre-centering offset; metadata stores the geometric base offset
	# from the ground anchor in BASE px. Scale to canvas px so the
	# offset matches the (already-scaled) sprite.
	scale = settings.TERRAIN_SCALE
	bx = ax + meta['dx'] * scale
	by = ay + meta['dy'] * scale
	# Centering rules. Peeps center on their feet; houses use raw
	# top-left positioning. Sprite size is already canvas px so no
	# extra scale is applied here.
	if meta['center_x']:
		bx -= sw // 2
	if meta['align_bottom_y']:
		by -= sh
	return bx, by


def get_peep_sprite_rect(p, transform, game_map):
	"""Return sprite bounding rect for a peep in screen coords.

	transform is a populous_game.layout.ViewportTransform; it owns the
	camera position and iso projection. game_map is consulted for
	corner altitudes underneath the peep. The per-sprite offset comes
	from SPRITE_ANCHORS; this function holds no inline pixel literals
	beyond debug fallbacks.
	"""
	# Bilinearly interpolate altitude under the peep using the four
	# tile corners it currently spans.
	gr, gc = int(p.y), int(p.x)
	fx = p.x - gc
	fy = p.y - gr
	if 0 <= gr < game_map.grid_height and 0 <= gc < game_map.grid_width:
		a_nw = game_map.get_corner_altitude(gr, gc)
		a_ne = game_map.get_corner_altitude(gr, gc + 1)
		a_sw = game_map.get_corner_altitude(gr + 1, gc)
		a_se = game_map.get_corner_altitude(gr + 1, gc + 1)
		alt = (1 - fx) * (1 - fy) * a_nw + fx * (1 - fy) * a_ne + (1 - fx) * fy * a_sw + fx * fy * a_se
	else:
		alt = 0

	# Ground anchor (iso projection of the world corner under the peep).
	anchor = transform.world_to_screen(p.y, p.x, alt)

	# Pick the sprite frame for the current animation state.
	sprites = peep.Peep.get_sprites()
	from populous_game.peeps import PEEP_WALK_FRAMES
	anim = PEEP_WALK_FRAMES.get(p.facing, PEEP_WALK_FRAMES['IDLE'])
	key = anim[p.anim_frame % len(anim)]
	sprite = sprites.get(key)

	# Resolve the metadata for this peep.
	meta = SPRITE_ANCHORS[_peep_anchor_key(p)]

	# Debug fallback when the sprite asset is missing.
	if sprite is None:
		bx, by = _apply_anchor(anchor, meta, PEEP_FALLBACK_SIZE)
		return pygame.Rect(bx, by, PEEP_FALLBACK_SIZE[0], PEEP_FALLBACK_SIZE[1])

	sw, sh = sprite.get_size()
	bx, by = _apply_anchor(anchor, meta, (sw, sh))
	return pygame.Rect(bx, by, sw, sh)


def get_house_sprite_rect(house, transform, game_map):
	"""Return sprite bounding rect for a house in screen coords.

	transform is a populous_game.layout.ViewportTransform; game_map is
	consulted only for the corner altitude under the house. Per-type
	offsets come from SPRITE_ANCHORS keyed by house.building_type --
	no inline pixel literals here.
	"""
	# Ground anchor at the house's tile corner.
	alt = game_map.get_corner_altitude(house.r, house.c)
	anchor = transform.world_to_screen(house.r, house.c, alt)

	# Resolve the metadata for this building type. The 'castle' top
	# tier carries an explicit 'size' override because it has no
	# underlying tile-sprite surface.
	meta = SPRITE_ANCHORS[house.building_type]

	if 'size' in meta:
		# Castle: fixed-size rect, top-left positioned by metadata.
		# meta['size'] is stored in BASE px (TILE_WIDTH * 2,
		# TILE_HEIGHT * 2); scale to canvas px so the rect matches the
		# scaled tile sprites stacked underneath.
		base_w, base_h = meta['size']
		scale = settings.TERRAIN_SCALE
		sw = base_w * scale
		sh = base_h * scale
		bx, by = _apply_anchor(anchor, meta, (sw, sh))
		return pygame.Rect(bx, by, sw, sh)

	# Standard house tile: size comes from the sprite surface in the
	# tile cache, with a fallback to the base tile geometry when the
	# tile is missing.
	tile_key = settings.BUILDING_TILES.get(house.building_type, settings.BUILDING_TILES['hut'])
	tile_surf = game_map.tile_surfaces.get(tile_key)
	if tile_surf is None:
		sw, sh = HOUSE_FALLBACK_SIZE
	else:
		sw, sh = tile_surf.get_size()
	bx, by = _apply_anchor(anchor, meta, (sw, sh))
	return pygame.Rect(bx, by, sw, sh)
