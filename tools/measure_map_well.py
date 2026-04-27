#!/usr/bin/env python3
"""Measure the map-well rectangle from AmigaUI sprite.

Run if AmigaUI art changes; otherwise the committed
MAP_WELL_RECT_LOGICAL in populous_game/settings.py is authoritative.

Scans data/gfx/AmigaUI.png for the contiguous black-pixel region
representing the iso-shaped map well (the diamond-shaped hole in the
HUD where the terrain is rendered) and prints an axis-aligned bounding
rectangle in 320x200 logical space. The rectangle is the single source
of truth for the M6 ViewportTransform.
"""

# Standard Library
import os
import argparse

# PIP3 modules
import PIL.Image  # python-pillow

# Pixel is considered "well" (true black) when every channel is at most
# this value. The HUD chrome uses dithered dark colors that are not
# pure black, so a strict threshold isolates the map well.
WELL_BLACK_THRESHOLD: int = 8


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments."""
	# Default input is data/gfx/AmigaUI.png relative to repo root.
	repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	default_input = os.path.join(repo_root, "data", "gfx", "AmigaUI.png")
	parser = argparse.ArgumentParser(
		description="Measure the map-well rectangle from AmigaUI.png."
	)
	parser.add_argument(
		'-i', '--input', dest='input_file', default=default_input,
		help="Path to AmigaUI.png (default: data/gfx/AmigaUI.png)",
	)
	parser.add_argument(
		'-v', '--verbose', dest='verbose', action='store_true',
		help="Print each row's leftmost/rightmost black pixel for debug",
	)
	args = parser.parse_args()
	return args


#============================================
def is_well_pixel(pixel: tuple) -> bool:
	"""Return True if pixel counts as map-well black.

	Args:
		pixel: RGB or RGBA tuple from PIL.Image.getpixel.

	Returns:
		True when red, green, and blue channels are all at most
		WELL_BLACK_THRESHOLD. Alpha is ignored.
	"""
	# Unpack red green blue; alpha (if present) is irrelevant for
	# black detection.
	red = pixel[0]
	green = pixel[1]
	blue = pixel[2]
	is_black = (
		red <= WELL_BLACK_THRESHOLD
		and green <= WELL_BLACK_THRESHOLD
		and blue <= WELL_BLACK_THRESHOLD
	)
	return is_black


#============================================
def build_black_mask(image: PIL.Image.Image) -> tuple:
	"""Convert image to a 2D boolean black-pixel mask.

	Args:
		image: Loaded AmigaUI sprite.

	Returns:
		Tuple (mask, width, height) where mask[y][x] is True when the
		pixel at (x, y) qualifies as map-well black.
	"""
	# Convert to RGB so pixel access returns a 3-tuple uniformly.
	rgb_image = image.convert("RGB")
	width, height = rgb_image.size
	# Use load() for fast pixel access (much faster than getpixel).
	pixels = rgb_image.load()
	# Build a 2D list of booleans.
	mask = []
	for y in range(height):
		row = [is_well_pixel(pixels[x, y]) for x in range(width)]
		mask.append(row)
	return (mask, width, height)


#============================================
def find_largest_region(mask: list, width: int, height: int) -> tuple:
	"""Find the largest 4-connected black region via flood fill.

	The AmigaUI sprite contains multiple black regions (the small
	minimap pane plus the large map well). The map well is by far the
	largest connected region; selecting the biggest one isolates it
	from the minimap and any stray dark chrome pixels.

	Args:
		mask: Boolean grid from build_black_mask.
		width: Image width in pixels.
		height: Image height in pixels.

	Returns:
		Tuple (min_x, min_y, max_x, max_y, pixel_count) for the
		largest connected region. Bounds are inclusive.
	"""
	# Mark visited pixels so we never enqueue the same pixel twice.
	visited = [[False] * width for _ in range(height)]
	# Track best region so far.
	best_count = 0
	best_bbox = (0, 0, -1, -1)
	# Iterate every pixel; start a flood fill on each unvisited black
	# pixel. Each fill measures one connected region.
	for start_y in range(height):
		for start_x in range(width):
			if visited[start_y][start_x]:
				continue
			if not mask[start_y][start_x]:
				continue
			# Iterative flood fill (4-connected) using an explicit
			# stack to avoid recursion depth limits on large regions.
			stack = [(start_x, start_y)]
			visited[start_y][start_x] = True
			region_min_x = start_x
			region_min_y = start_y
			region_max_x = start_x
			region_max_y = start_y
			region_count = 0
			while stack:
				cx, cy = stack.pop()
				region_count += 1
				if cx < region_min_x:
					region_min_x = cx
				if cx > region_max_x:
					region_max_x = cx
				if cy < region_min_y:
					region_min_y = cy
				if cy > region_max_y:
					region_max_y = cy
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
			if region_count > best_count:
				best_count = region_count
				best_bbox = (
					region_min_x, region_min_y,
					region_max_x, region_max_y,
				)
	min_x, min_y, max_x, max_y = best_bbox
	return (min_x, min_y, max_x, max_y, best_count)


#============================================
def dump_verbose_rows(mask: list, bbox: tuple) -> None:
	"""Print the leftmost/rightmost black pixel of each row in bbox.

	Args:
		mask: Boolean grid from build_black_mask.
		bbox: (min_x, min_y, max_x, max_y, pixel_count) from
			find_largest_region.
	"""
	min_x, min_y, max_x, max_y, _ = bbox
	for y in range(min_y, max_y + 1):
		row = mask[y]
		# Restrict scan to the bbox columns to keep output focused on
		# the map-well region.
		row_left = None
		row_right = None
		for x in range(min_x, max_x + 1):
			if not row[x]:
				continue
			if row_left is None or x < row_left:
				row_left = x
			if row_right is None or x > row_right:
				row_right = x
		if row_left is not None:
			print(f"  row y={y:3d}: black x=[{row_left:3d}..{row_right:3d}]")


#============================================
def report_bbox(bbox: tuple) -> None:
	"""Print the bounding rectangle and sanity checks.

	Args:
		bbox: Tuple (min_x, min_y, max_x, max_y, pixel_count) from
			scan_well_bbox.
	"""
	min_x, min_y, max_x, max_y, pixel_count = bbox
	# Compute axis-aligned width and height (inclusive bounds).
	rect_w = max_x - min_x + 1
	rect_h = max_y - min_y + 1
	# Iso diamonds compress vertically 2:1, so width is roughly twice
	# the height. A ratio far from 2.0 hints at a mis-thresholded scan.
	ratio = rect_w / rect_h if rect_h > 0 else 0.0
	# Emit the canonical settings line so the value can be copy-pasted.
	settings_line = (
		f"MAP_WELL_RECT_LOGICAL = pygame.Rect("
		f"{min_x}, {min_y}, {rect_w}, {rect_h})"
	)
	# Print summary block.
	print("Map well bounding box (logical 320x200 space):")
	print(f"  {settings_line}")
	print(f"  bbox dims: {rect_w} x {rect_h} px")
	print(f"  detected black pixels: {pixel_count}")
	print(f"  width/height ratio: {ratio:.2f} (expect ~2.0 for iso diamond)")
	# Sanity check: width should be roughly twice height (1.6 to 2.4).
	if 1.6 <= ratio <= 2.4:
		print("  sanity: OK (width is ~2x height, consistent with iso)")
	else:
		print("  sanity: WARN (ratio outside 1.6-2.4; check threshold)")


#============================================
def main() -> None:
	"""Entry point: scan the sprite and report the bounding rectangle."""
	args = parse_args()
	# Validate the input file early so the error is obvious.
	if not os.path.isfile(args.input_file):
		raise FileNotFoundError(f"AmigaUI sprite not found: {args.input_file}")
	# Load the sprite and build a black-pixel mask once.
	image = PIL.Image.open(args.input_file)
	width, height = image.size
	print(f"Loaded {args.input_file} ({width}x{height})")
	mask, mask_w, mask_h = build_black_mask(image)
	# Find the largest connected black region; the AmigaUI sprite
	# contains multiple black regions (minimap pane plus map well)
	# and the map well is by far the largest.
	bbox = find_largest_region(mask, mask_w, mask_h)
	# Fail loud when no black pixels are present rather than print a
	# nonsense bbox.
	if bbox[4] == 0:
		raise ValueError(
			"No black pixels found; check WELL_BLACK_THRESHOLD or sprite path"
		)
	if args.verbose:
		dump_verbose_rows(mask, bbox)
	report_bbox(bbox)


if __name__ == '__main__':
	main()
