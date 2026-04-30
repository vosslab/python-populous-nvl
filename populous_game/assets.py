"""Asset loader and registry for Populous sprites and UI elements."""

import os
import pygame
import populous_game.settings as settings
import populous_game.iso_hole as iso_hole


# Module-level cache of loaded assets
_WEAPON_SPRITES = None
_WEAPON_SPRITE_INDICES = None
_BUTTON_SPRITES = None
_BUTTON_SPRITE_INDICES = None
_UI_IMAGE = None
_KNIGHT_PEEP = None

# Shield panel portrait slot footprint, matching PEEP_WALK_FRAMES sprite size.
KNIGHT_PEEP_SIZE: tuple = (16, 16)


def load_all() -> None:
	"""Load all asset sprites and textures. Call once after pygame.display.set_mode()."""
	global _WEAPON_SPRITES, _WEAPON_SPRITE_INDICES, _BUTTON_SPRITES, _BUTTON_SPRITE_INDICES, _UI_IMAGE, _KNIGHT_PEEP

	# Load UI image for screen sizing. Convert to SRCALPHA so the iso-
	# diamond hole in the center of the sprite (the black region where
	# the original Amiga rendered terrain) can be punched transparent
	# below. The remaster draws terrain UNDER the HUD, so the hole must
	# expose the canvas; without this step the HUD blits opaque black
	# over the entire diamond.
	ui_path = os.path.join(settings.GFX_DIR, "AmigaUI.png")
	ui_raw = pygame.image.load(ui_path)
	_UI_IMAGE = ui_raw.convert_alpha()
	# Punch the iso-diamond hole transparent. Mutates _UI_IMAGE in place.
	# Restricted to the largest 4-connected black region so the small
	# minimap pane (also black) keeps its opacity.
	iso_hole.flood_fill_iso_hole(_UI_IMAGE)

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

	# Load knight portrait for the shield-panel bottom-left quadrant.
	# Used when the selected peep has weapon_type == 'knight' and is not
	# in_house. Scaled once at load time to the portrait slot footprint.
	# If the asset is missing, leave _KNIGHT_PEEP as None so the
	# shield panel falls back to the normal peep walk frame.
	knight_path = os.path.join(settings.GFX_DIR, "knight_peep.png")
	if os.path.exists(knight_path):
		raw = pygame.image.load(knight_path).convert_alpha()
		_KNIGHT_PEEP = pygame.transform.smoothscale(raw, KNIGHT_PEEP_SIZE)


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


def get_knight_peep():
	"""Get the knight shield-panel portrait surface, or None if unavailable.

	Returns the pre-scaled knight.png surface used by the shield panel
	when the selected peep has weapon_type == 'knight'. Returns None
	when the asset failed to load; callers must fall back to the normal
	peep portrait path in that case.
	"""
	return _KNIGHT_PEEP
