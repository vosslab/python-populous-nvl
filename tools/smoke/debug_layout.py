#!/usr/bin/env python3
"""Smoke test for the M6 Patch 8 --debug-layout overlay.

Boots a headless game, flips on `debug_layout`, captures one frame to
`debug_layout_smoke.png` in the current working directory, then samples
a handful of overlay-color pixels to confirm the diagnostic geometry
actually rendered.

Exits 0 on PASS, 1 on FAIL.
"""

# Standard Library
import os
import sys
import subprocess


# Resolve repo root via git so the smoke is runnable from anywhere
_REPO_ROOT = subprocess.check_output(
	['git', 'rev-parse', '--show-toplevel'],
	text=True,
).strip()
if _REPO_ROOT not in sys.path:
	sys.path.insert(0, _REPO_ROOT)

# Headless pygame must be set before any pygame import.
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

# local repo modules
import tools.headless_runner as runner


# Output path is reused across runs and lives in the current working
# directory so bandit's hardcoded-tmp-directory rule (CWE-377) is happy
# and so the file is easy to inspect alongside the test invocation.
OUT_PATH = 'debug_layout_smoke.png'


def main() -> int:
	"""Boot, capture, sample, report. Returns process exit code."""
	# Boot a deterministic game and turn the overlay on.
	game = runner.boot_game_for_tests(
		state='gameplay', seed=8888, players=4, enemies=4,
	)
	game.debug_layout = True
	# Step one frame so terrain + overlay both render before the capture.
	runner.step_frames(game, n=1)
	runner.capture(game, OUT_PATH)

	# Pull the in-memory surface for color sampling. Using a copy so a
	# later draw cannot retroactively affect the smoke result.
	surface = game.internal_surface.copy()
	transform = game.viewport_transform

	failures = []

	# 1. Magenta anchor pixel.
	anchor_px = surface.get_at((transform.anchor_x, transform.anchor_y))[:3]
	if anchor_px != (255, 0, 255):
		failures.append(
			f"anchor pixel at ({transform.anchor_x}, {transform.anchor_y}) "
			f"is {anchor_px}, expected magenta (255, 0, 255)"
		)

	# 2. Cyan map-well midpoint (top edge).
	rect = game.layout.map_well_rect
	cyan = (0, 200, 255)
	# Scan a 3x3 box around the top-edge midpoint in case of subpixel rounding.
	well_hit = False
	for dy in (-1, 0, 1):
		for dx in (-1, 0, 1):
			px = rect.centerx + dx
			py = rect.top + dy
			w, h = surface.get_size()
			if 0 <= px < w and 0 <= py < h:
				if surface.get_at((px, py))[:3] == cyan:
					well_hit = True
					break
		if well_hit:
			break
	if not well_hit:
		failures.append(
			f"no cyan map-well outline pixel near ({rect.centerx}, {rect.top})"
		)

	# 3. Red tile-center pixel near the camera origin.
	cam_r = int(transform.camera_row) + 1
	cam_c = int(transform.camera_col) + 1
	alt = game.game_map.get_corner_altitude(cam_r, cam_c)
	if alt < 0:
		alt = 0
	sx, sy = transform.world_to_screen(cam_r + 0.5, cam_c + 0.5, alt)
	red = (255, 0, 0)
	tile_hit = False
	for dy in (-1, 0, 1):
		for dx in (-1, 0, 1):
			px = sx + dx
			py = sy + dy
			w, h = surface.get_size()
			if 0 <= px < w and 0 <= py < h:
				if surface.get_at((px, py))[:3] == red:
					tile_hit = True
					break
		if tile_hit:
			break
	if not tile_hit:
		failures.append(
			f"no red tile-center pixel near ({sx}, {sy}) for tile ({cam_r}, {cam_c})"
		)

	# Report.
	if failures:
		print(f"FAIL: {len(failures)} overlay sample(s) missed")
		for f in failures:
			print(f"  - {f}")
		print(f"  capture: {OUT_PATH}")
		return 1
	print("PASS: --debug-layout overlay renders anchor, map-well, and tile-center pixels")
	print(f"  capture: {OUT_PATH}")
	return 0


if __name__ == '__main__':
	sys.exit(main())
