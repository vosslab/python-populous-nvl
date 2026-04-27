"""Asset loader and registry for Populous sprites and UI elements."""

import os
import pygame
import populous_game.settings as settings


# Module-level cache of loaded assets
_WEAPON_SPRITES = None
_WEAPON_SPRITE_INDICES = None
_BUTTON_SPRITES = None
_BUTTON_SPRITE_INDICES = None
_UI_IMAGE = None


def load_all() -> None:
	"""Load all asset sprites and textures. Call once after pygame.display.set_mode()."""
	global _WEAPON_SPRITES, _WEAPON_SPRITE_INDICES, _BUTTON_SPRITES, _BUTTON_SPRITE_INDICES, _UI_IMAGE

	# Load UI image for screen sizing
	ui_path = os.path.join(settings.GFX_DIR, "AmigaUI.png")
	ui_raw = pygame.image.load(ui_path)
	_UI_IMAGE = ui_raw.convert_alpha()

	# Load weapon sprites
	_WEAPON_SPRITES = []
	_WEAPON_SPRITE_INDICES = {
		'hut': 0,
		'house_small': 1,
		'house_medium': 2,
		'castle_small': 3,
		'castle_medium': 4,
		'castle_large': 5,
		'fortress_small': 6,
		'fortress_medium': 7,
		'fortress_large': 8,
		'castle': 9,
	}

	weapons_path = os.path.join(settings.GFX_DIR, "Weapons.png")
	if os.path.exists(weapons_path):
		sheet = pygame.image.load(weapons_path).convert_alpha()
		for i in range(10):
			rect = pygame.Rect(i * 16, 0, 16, 16)
			_WEAPON_SPRITES.append(sheet.subsurface(rect))

	# Load button sprites
	_BUTTON_SPRITES = []
	_BUTTON_SPRITE_INDICES = {}

	button_ui_path = os.path.join(settings.GFX_DIR, "ButtonUI.png")
	if os.path.exists(button_ui_path):
		sheet = pygame.image.load(button_ui_path).convert_alpha()
		sheet_w, sheet_h = sheet.get_size()
		sprite_w, sprite_h = 34, 17
		for row in range(5):
			for col in range(5):
				x = col * sprite_w
				y = row * sprite_h
				if x + sprite_w <= sheet_w and y + sprite_h <= sheet_h:
					rect = pygame.Rect(x, y, sprite_w, sprite_h)
					_BUTTON_SPRITES.append(sheet.subsurface(rect))

	# Map button names to sprite indices
	button_order = [
		'_do_flood', '_battle_over', '_do_quake', 'NW', 'N', 'NE', '_do_shield', '_find_papal', '_find_knight',
		'_do_volcano', '_do_knight', 'W', '_find_shield', 'E', '_raise_terrain', '_find_battle',
		'_do_swamp', 'SW', 'S', 'SE', '_do_papal', '_go_papal', '_go_build', '_go_assemble', '_go_fight'
	]
	for idx, name in enumerate(button_order):
		_BUTTON_SPRITE_INDICES[name] = idx


def get_ui_image() -> pygame.Surface:
	"""Get the UI background image."""
	if _UI_IMAGE is None:
		raise RuntimeError("Assets not loaded. Call assets.load_all() after pygame.display.set_mode().")
	return _UI_IMAGE


def get_weapon_sprites() -> list:
	"""Get list of weapon sprites."""
	if _WEAPON_SPRITES is None:
		raise RuntimeError("Assets not loaded. Call assets.load_all() after pygame.display.set_mode().")
	return _WEAPON_SPRITES


def get_weapon_sprite_indices() -> dict:
	"""Get mapping of weapon type to sprite index."""
	if _WEAPON_SPRITE_INDICES is None:
		raise RuntimeError("Assets not loaded. Call assets.load_all() after pygame.display.set_mode().")
	return _WEAPON_SPRITE_INDICES


def get_button_sprites() -> list:
	"""Get list of button UI sprites."""
	if _BUTTON_SPRITES is None:
		raise RuntimeError("Assets not loaded. Call assets.load_all() after pygame.display.set_mode().")
	return _BUTTON_SPRITES


def get_button_sprite_indices() -> dict:
	"""Get mapping of button action name to sprite index."""
	if _BUTTON_SPRITE_INDICES is None:
		raise RuntimeError("Assets not loaded. Call assets.load_all() after pygame.display.set_mode().")
	return _BUTTON_SPRITE_INDICES
