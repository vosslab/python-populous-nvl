"""Asset loader and registry for Populous sprites and UI elements."""

import os
import pygame
import populous_game.settings as settings
import populous_game.iso_hole as iso_hole
import populous_game.sheet_loader as sheet_loader


# Module-level cache of loaded assets
_WEAPON_SPRITES = None
_WEAPON_SPRITE_INDICES = None
_BUTTON_SPRITES = None
_BUTTON_SPRITE_INDICES = None
_UI_IMAGE = None
_KNIGHT_PEEP = None

# Shield panel portrait slot footprint, matching PEEP_WALK_FRAMES sprite size.
KNIGHT_PEEP_SIZE: tuple = (16, 16)

# Logical AmigaUI sheet dimensions (320x200 internal canvas pixels).
_UI_LOGICAL_W: int = 320
_UI_LOGICAL_H: int = 200


def _hud_iso_hole_mask(surface) -> None:
	"""Punch the iso-diamond hole transparent in source-scaled space.

	The HUD sheet has an iso-diamond opaque-black region in the center
	where the original Amiga rendered terrain. The remaster draws
	terrain UNDER the HUD chrome, so that region must be made
	transparent before the HUD is blitted.

	When the resolved sheet is the 4x Upscayl HUD, this mask runs on
	the cropped 4x surface (1280x800) BEFORE the final smoothscale to
	(INTERNAL_WIDTH, INTERNAL_HEIGHT). Running the flood fill at
	source resolution keeps the alpha hole geometry well-defined and
	avoids soft-edge leakage from a downscale step ahead of the punch.

	The flood fill itself remains the largest 4-connected near-black
	region per `iso_hole.WELL_BLACK_THRESHOLD`, so the small minimap
	pane (also dark) keeps its opacity.
	"""
	# Mutates `surface` in place; flood_fill_iso_hole walks the largest
	# 4-connected region of near-black pixels and sets alpha = 0.
	iso_hole.flood_fill_iso_hole(surface)


def load_all() -> None:
	"""Load all asset sprites and textures. Call once after pygame.display.set_mode()."""
	global _WEAPON_SPRITES, _WEAPON_SPRITE_INDICES, _BUTTON_SPRITES, _BUTTON_SPRITE_INDICES, _UI_IMAGE, _KNIGHT_PEEP

	# HUD chrome. Routes through the sheet loader so the Upscayl 4x
	# AmigaUI sheet is preferred when present and the original PNG is
	# the fallback. The iso-diamond hole is punched on the cropped
	# source-scaled surface (4x for Upscayl, 1x for original), then
	# the result is smoothscaled to (INTERNAL_WIDTH, INTERNAL_HEIGHT)
	# for the cached HUD surface.
	_, ui_source_scale = sheet_loader.load_sheet("ui")
	hud_scale_filter = 'smooth' if ui_source_scale > 1 else 'nearest'
	_UI_IMAGE = sheet_loader.extract_frame(
		"ui",
		(0, 0, _UI_LOGICAL_W, _UI_LOGICAL_H),
		(settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT),
		scale_filter=hud_scale_filter,
		post_mask=_hud_iso_hole_mask,
	)

	# Weapon icons. 16x16 logical cells in a single row at origin
	# (0, 0); cached at (16 * HUD_SCALE, 16 * HUD_SCALE) so the HUD
	# blit pass does not need to re-scale.
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
	_, weapons_source_scale = sheet_loader.load_sheet("weapons")
	weapons_filter = 'smooth' if weapons_source_scale > 1 else 'nearest'
	weapons_target = (
		16 * settings.HUD_SCALE,
		16 * settings.HUD_SCALE,
	)
	for i in range(10):
		_WEAPON_SPRITES.append(
			sheet_loader.extract_frame(
				"weapons",
				(i * 16, 0, 16, 16),
				weapons_target,
				scale_filter=weapons_filter,
			)
		)

	# HUD button cells. 5x5 grid of 34x17 logical cells; cached at
	# (34 * HUD_SCALE, 17 * HUD_SCALE).
	_BUTTON_SPRITES = []
	_BUTTON_SPRITE_INDICES = {}

	_, buttons_source_scale = sheet_loader.load_sheet("buttons")
	buttons_filter = 'smooth' if buttons_source_scale > 1 else 'nearest'
	sprite_w, sprite_h = 34, 17
	buttons_target = (
		sprite_w * settings.HUD_SCALE,
		sprite_h * settings.HUD_SCALE,
	)
	# Logical sheet is 170x85 = 5x5 cells of 34x17.
	for row in range(5):
		for col in range(5):
			x = col * sprite_w
			y = row * sprite_h
			_BUTTON_SPRITES.append(
				sheet_loader.extract_frame(
					"buttons",
					(x, y, sprite_w, sprite_h),
					buttons_target,
					scale_filter=buttons_filter,
				)
			)

	# Map button names to sprite indices
	button_order = [
		'_do_flood', '_battle_over', '_do_quake', 'NW', 'N', 'NE', '_do_shield', '_find_papal', '_find_knight',
		'_do_volcano', '_do_knight', 'W', '_find_shield', 'E', '_raise_terrain', '_find_battle',
		'_do_swamp', 'SW', 'S', 'SE', '_do_papal', '_go_papal', '_go_build', '_go_assemble', '_go_fight'
	]
	for idx, name in enumerate(button_order):
		_BUTTON_SPRITE_INDICES[name] = idx

	# Knight portrait for the shield-panel bottom-left quadrant. This
	# asset lives outside the atlas registry because the file is a
	# single-purpose portrait (not part of a multi-cell atlas) and the
	# 4x Upscayl pipeline has not produced one. If the asset is
	# missing, leave _KNIGHT_PEEP as None so the shield panel falls
	# back to the normal peep walk frame.
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
