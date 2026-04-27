"""Sprite geometry calculations for peeps and houses."""

import pygame
import populous_game.settings as settings
import populous_game.peeps as peep


def get_peep_sprite_rect(p, cam_r, cam_c, game_map):
	"""Return sprite bounding rect for a peep in screen coords."""
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

	sx, sy = game_map.world_to_screen(p.y, p.x, alt, cam_r, cam_c)
	ground_y = sy + settings.TILE_HALF_H
	sprites = peep.Peep.get_sprites()
	from populous_game.peeps import PEEP_WALK_FRAMES
	anim = PEEP_WALK_FRAMES.get(p.facing, PEEP_WALK_FRAMES['IDLE'])
	key = anim[p.anim_frame % len(anim)]
	sprite = sprites.get(key)
	if sprite is None:
		return pygame.Rect(sx - 4, ground_y - 8, 8, 8)
	sw, sh = sprite.get_size()
	return pygame.Rect(sx - sw // 2, ground_y - sh, sw, sh)


def get_house_sprite_rect(house, cam_r, cam_c, game_map):
	"""Return sprite bounding rect for a house in screen coords."""
	if house.building_type == 'castle':
		alt = game_map.get_corner_altitude(house.r, house.c)
		sx, sy = game_map.world_to_screen(house.r, house.c, alt, cam_r, cam_c)
		return pygame.Rect(sx - settings.TILE_WIDTH, sy - settings.TILE_HEIGHT, settings.TILE_WIDTH * 2, settings.TILE_HEIGHT * 2)

	alt = game_map.get_corner_altitude(house.r, house.c)
	sx, sy = game_map.world_to_screen(house.r, house.c, alt, cam_r, cam_c)
	tile_key = settings.BUILDING_TILES.get(house.building_type, settings.BUILDING_TILES['hut'])
	tile_surf = game_map.tile_surfaces.get(tile_key)
	if tile_surf is None:
		return pygame.Rect(sx - settings.TILE_HALF_W, sy, settings.TILE_WIDTH, settings.TILE_HEIGHT)
	tw, th = tile_surf.get_size()
	return pygame.Rect(sx - settings.TILE_HALF_W, sy, tw, th)
