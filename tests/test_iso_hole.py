"""Unit tests for populous_game.iso_hole.flood_fill_iso_hole."""

# Standard Library
import os

# PIP3 modules
import pygame

# local repo modules
import populous_game.iso_hole as iso_hole


# Headless SDL is set in conftest.py; pygame.Surface still requires
# pygame.init() before allocating surfaces with format flags.
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')


#============================================
def _make_diamond_surface() -> pygame.Surface:
	"""Build a 32x32 SRCALPHA surface with a black diamond in white.

	The diamond inscribed in a 32x32 square has its tips at the four
	cardinal midpoints. Outside the diamond the surface is opaque white;
	inside the diamond pixels are pure black (rgb 0, 0, 0). Matches the
	AmigaUI sprite layout in miniature: the largest connected black
	region IS the diamond, surrounded by non-black chrome.
	"""
	pygame.init()
	size = 32
	surface = pygame.Surface((size, size), pygame.SRCALPHA)
	# Fill outside region with opaque white.
	surface.fill((255, 255, 255, 255))
	half = size // 2
	# Paint a filled diamond: |dx| + |dy| <= half - 1.
	for y in range(size):
		for x in range(size):
			if abs(x - half) + abs(y - half) <= half - 1:
				surface.set_at((x, y), pygame.Color(0, 0, 0, 255))
	return surface


#============================================
def test_flood_fill_punches_diamond_alpha():
	"""Pixels in the black diamond become transparent; corners stay opaque."""
	surface = _make_diamond_surface()
	cleared = iso_hole.flood_fill_iso_hole(surface)
	# Center pixel (inside the diamond) must now have alpha == 0.
	center_alpha = surface.get_at((16, 16))[3]
	assert center_alpha == 0
	# Top-left corner is outside the diamond and must stay opaque.
	corner_alpha = surface.get_at((0, 0))[3]
	assert corner_alpha == 255
	# Sanity: at least one pixel was cleared.
	assert cleared > 0


#============================================
def test_flood_fill_leaves_non_black_chrome_alone():
	"""Non-black HUD chrome pixels keep their original alpha."""
	surface = _make_diamond_surface()
	# Add a small dark-gray chrome rectangle outside the diamond. Gray
	# is above the WELL_BLACK_THRESHOLD so the flood fill must skip it.
	chrome_color = pygame.Color(40, 40, 40, 255)
	for y in range(0, 4):
		for x in range(0, 4):
			surface.set_at((x, y), chrome_color)
	iso_hole.flood_fill_iso_hole(surface)
	# Chrome pixel keeps full alpha.
	chrome_alpha = surface.get_at((1, 1))[3]
	assert chrome_alpha == 255
