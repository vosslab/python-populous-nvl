"""Pin iso-hole alpha behavior after the source-scaled HUD load."""

import pygame
import populous_game.settings as settings
import populous_game.sheet_loader as sheet_loader
import populous_game.assets as assets


def _init_pygame():
	pygame.init()
	pygame.display.set_mode((1, 1))


def test_central_iso_diamond_is_transparent():
	"""Center of the HUD should be alpha 0 after the iso-hole punch."""
	_init_pygame()
	sheet_loader.clear_caches()
	assets._UI_IMAGE = None
	assets._WEAPON_SPRITES = None
	assets._BUTTON_SPRITES = None
	assets.load_all()
	hud = assets.get_ui_image()
	# Sample the center of the internal canvas; it lives inside the
	# iso-diamond well in both classic (320x200) and remaster
	# (640x400) presets.
	cx = settings.INTERNAL_WIDTH // 2
	cy = settings.INTERNAL_HEIGHT // 2
	pixel = hud.get_at((cx, cy))
	assert pixel.a == 0


def test_top_left_corner_remains_opaque():
	"""Non-well HUD chrome must keep its alpha after the punch."""
	_init_pygame()
	sheet_loader.clear_caches()
	assets._UI_IMAGE = None
	assets._WEAPON_SPRITES = None
	assets._BUTTON_SPRITES = None
	assets.load_all()
	hud = assets.get_ui_image()
	pixel = hud.get_at((1, 1))
	assert pixel.a > 0
