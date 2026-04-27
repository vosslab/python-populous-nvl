"""Iso-hole transparency helper for the AmigaUI HUD sprite.

The AmigaUI sprite has an iso-diamond-shaped opaque-black region in the
center where the original game rendered the iso terrain. The remaster
renders terrain UNDER the HUD chrome, so that black region must be made
transparent before the HUD is blitted on top of the canvas.

This module exposes `flood_fill_iso_hole`, which mutates a 32-bit
`pygame.Surface` (SRCALPHA) in place: the largest 4-connected region of
near-black pixels is set to alpha=0. Pixel detection mirrors the logic
in `tools/measure_map_well.py:is_well_pixel` so the rectangle reported
by that diagnostic and the hole punched here always agree.
"""

# Standard Library

# PIP3 modules
import pygame


# Pixel is "well black" when red, green, and blue are all at most this
# value. Mirrors WELL_BLACK_THRESHOLD in tools/measure_map_well.py.
WELL_BLACK_THRESHOLD: int = 8


#============================================
def is_well_pixel(red: int, green: int, blue: int) -> bool:
	"""Return True when (r, g, b) qualifies as map-well black.

	Args:
		red:   Red channel 0-255.
		green: Green channel 0-255.
		blue:  Blue channel 0-255.

	Returns:
		True when every channel is at most WELL_BLACK_THRESHOLD.
	"""
	# All three channels must be near zero to qualify as map-well black.
	is_black = (
		red <= WELL_BLACK_THRESHOLD
		and green <= WELL_BLACK_THRESHOLD
		and blue <= WELL_BLACK_THRESHOLD
	)
	return is_black


#============================================
def _build_black_mask(surface: pygame.Surface) -> tuple:
	"""Build a 2D boolean mask of 'well black' pixels.

	Args:
		surface: 32-bit RGBA pygame surface.

	Returns:
		Tuple (mask, width, height); mask[y][x] True for black pixels.
	"""
	# Lock once for fast pixel reads via get_at on PixelArray would need
	# its own lock; build the mask via a single pixel-array iteration.
	width, height = surface.get_size()
	mask = []
	# pygame.surfarray would pull numpy; keep this dependency-free by
	# using get_at() row-by-row. AmigaUI is 320x200 so 64000 reads is
	# well under a frame budget at load time.
	for y in range(height):
		row = []
		for x in range(width):
			# get_at returns a Color (r, g, b, a).
			color = surface.get_at((x, y))
			row.append(is_well_pixel(color[0], color[1], color[2]))
		mask.append(row)
	return (mask, width, height)


#============================================
def _find_largest_region(mask: list, width: int, height: int) -> list:
	"""Find the largest 4-connected region in the mask.

	The AmigaUI sprite contains several disjoint black regions (small
	minimap pane plus the large map well). The map well is by far the
	largest, so picking the biggest region isolates the iso hole.

	Args:
		mask:   Boolean grid from _build_black_mask.
		width:  Image width in pixels.
		height: Image height in pixels.

	Returns:
		List of (x, y) pixel coordinates in the largest region.
	"""
	# visited[y][x] guards against re-enqueuing pixels.
	visited = [[False] * width for _ in range(height)]
	# Track the best region as a list of pixels.
	best_pixels = []
	# Iterate every pixel; flood-fill each unvisited black pixel.
	for start_y in range(height):
		for start_x in range(width):
			if visited[start_y][start_x]:
				continue
			if not mask[start_y][start_x]:
				continue
			# Iterative flood-fill (4-connected) using an explicit stack
			# to avoid recursion-depth limits on large regions.
			stack = [(start_x, start_y)]
			visited[start_y][start_x] = True
			region_pixels = []
			while stack:
				cx, cy = stack.pop()
				region_pixels.append((cx, cy))
				# Push the four orthogonal neighbours when in bounds,
				# unvisited, and black.
				for nx, ny in (
					(cx + 1, cy), (cx - 1, cy),
					(cx, cy + 1), (cx, cy - 1),
				):
					if nx < 0 or nx >= width:
						continue
					if ny < 0 or ny >= height:
						continue
					if visited[ny][nx]:
						continue
					if not mask[ny][nx]:
						continue
					visited[ny][nx] = True
					stack.append((nx, ny))
			# Keep the largest region seen so far.
			if len(region_pixels) > len(best_pixels):
				best_pixels = region_pixels
	return best_pixels


#============================================
def flood_fill_iso_hole(surface: pygame.Surface) -> int:
	"""Set alpha=0 on every pixel in the largest black region.

	Mutates the supplied 32-bit SRCALPHA surface in place: the iso-
	diamond hole at the center of the AmigaUI sprite becomes fully
	transparent, while the HUD chrome (dithered dark colors but not
	pure black) keeps its original alpha.

	Args:
		surface: 32-bit RGBA pygame surface (must be SRCALPHA).

	Returns:
		Number of pixels cleared. Useful for sanity-checking the call
		actually punched the expected diamond.
	"""
	# Build the mask and find the largest connected black region.
	mask, width, height = _build_black_mask(surface)
	region = _find_largest_region(mask, width, height)
	# Zero the alpha channel for every pixel in the region. set_at on
	# an SRCALPHA surface writes the full RGBA; preserve the original
	# RGB so future debug diffs see "black with alpha 0" rather than
	# a different color.
	transparent_black = pygame.Color(0, 0, 0, 0)
	for (x, y) in region:
		surface.set_at((x, y), transparent_black)
	return len(region)
