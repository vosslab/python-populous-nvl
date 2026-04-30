"""Pin runtime cached sizes for tiles, peeps, HUD, weapons, buttons.

The acceptance contract from the upscayl-runtime plan is that cached
surfaces are sized exactly by `TERRAIN_SCALE` / `HUD_SCALE` regardless of
which sheet (1x original or 4x Upscayl) the loader resolved.
"""

import pygame
import populous_game.settings as settings
import populous_game.sheet_loader as sheet_loader
import populous_game.terrain as terrain
import populous_game.peeps as peeps
import populous_game.assets as assets


def _init_pygame():
	pygame.init()
	pygame.display.set_mode((1, 1))


def test_tile_cache_size_matches_terrain_scale():
	_init_pygame()
	sheet_loader.clear_caches()
	tiles = terrain.load_tile_surfaces()
	expected = (32 * settings.TERRAIN_SCALE, 24 * settings.TERRAIN_SCALE)
	# Every cached cell matches the target. Pick a stable cell (0, 0).
	assert tiles[(0, 0)].get_size() == expected


def test_peep_cache_size_matches_terrain_scale():
	_init_pygame()
	sheet_loader.clear_caches()
	sprites = peeps.load_sprite_surfaces()
	side = settings.SPRITE_SIZE * settings.TERRAIN_SCALE
	assert sprites[(0, 0)].get_size() == (side, side)


def test_hud_assets_have_internal_canvas_size():
	_init_pygame()
	sheet_loader.clear_caches()
	# Reset the assets module-level cache so load_all() re-runs.
	assets._UI_IMAGE = None
	assets._WEAPON_SPRITES = None
	assets._BUTTON_SPRITES = None
	assets.load_all()
	assert assets.get_ui_image().get_size() == (
		settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT,
	)


def test_weapon_and_button_cache_sizes_match_hud_scale():
	_init_pygame()
	sheet_loader.clear_caches()
	assets._UI_IMAGE = None
	assets._WEAPON_SPRITES = None
	assets._BUTTON_SPRITES = None
	assets.load_all()
	weapon_target = (16 * settings.HUD_SCALE, 16 * settings.HUD_SCALE)
	button_target = (34 * settings.HUD_SCALE, 17 * settings.HUD_SCALE)
	assert assets.get_weapon_sprites()[0].get_size() == weapon_target
	assert assets.get_button_sprites()[0].get_size() == button_target
