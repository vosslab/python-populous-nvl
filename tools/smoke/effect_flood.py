#!/usr/bin/env python3
"""Flood button lowers terrain (creates more water tiles) (M3 WP-M3-B)."""

import os
import subprocess
import sys

# Add repo root to sys.path so we can import populous_game
_REPO_ROOT = subprocess.check_output(
	['git', 'rev-parse', '--show-toplevel'],
	text=True,
).strip()
if _REPO_ROOT not in sys.path:
	sys.path.insert(0, _REPO_ROOT)

# Set headless pygame environment
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import populous_game.faction as faction
import populous_game.settings as power_settings
import tools.headless_runner as runner


def _count_water_tiles(game_map, r0, c0, radius):
	"""Count tiles where get_tile_key returns the water sprite key.

	Iterates the AOE bounding square centered on (r0, c0).
	"""
	water_count = 0
	for dr in range(-radius, radius + 1):
		for dc in range(-radius, radius + 1):
			rr, cc = r0 + dr, c0 + dc
			if not (0 <= rr < game_map.grid_height and 0 <= cc < game_map.grid_width):
				continue
			# All-zero corners means water; check directly to avoid coupling
			# to the renderer's tile-key dict.
			a = game_map.get_corner_altitude(rr, cc)
			b = game_map.get_corner_altitude(rr, cc + 1)
			c = game_map.get_corner_altitude(rr + 1, cc + 1)
			d = game_map.get_corner_altitude(rr + 1, cc)
			if a == b == c == d == 0:
				water_count += 1
	return water_count


def _altitude_sum_in_radius(game_map, r0, c0, radius):
	"""Sum of corner altitudes in the AOE; falls when flood lowers terrain."""
	total = 0
	for dr in range(-radius, radius + 1):
		for dc in range(-radius, radius + 1):
			rr, cc = r0 + dr, c0 + dc
			if 0 <= rr <= game_map.grid_height and 0 <= cc <= game_map.grid_width:
				total += game_map.corners[rr][cc]
	return total


def check_flood_lowers_total_altitude():
	"""Flood reduces the sum of corner altitudes in its AOE."""
	game = runner.boot_game_for_tests(state='gameplay', seed=5555, players=4)
	game.camera.r, game.camera.c = 16.0, 16.0
	game.mana_pool.add(faction.Faction.PLAYER, 5000)
	target_r, target_c = 20, 20
	radius = power_settings.POWER_FLOOD_RADIUS
	pre_total = _altitude_sum_in_radius(game.game_map, target_r, target_c, radius)
	pre_water = _count_water_tiles(game.game_map, target_r, target_c, radius)
	game.input_controller._handle_ui_click('_do_flood')
	# Flood has requires_confirm=True; bypass the confirm UI for the
	# effect test (the confirm flow has its own tests).
	game.power_manager.activate('flood', (target_r, target_c))
	runner.step_frames(game, n=3)
	post_total = _altitude_sum_in_radius(game.game_map, target_r, target_c, radius)
	post_water = _count_water_tiles(game.game_map, target_r, target_c, radius)
	assert post_total < pre_total, (
		f"Flood did not lower total altitude in the AOE: "
		f"pre={pre_total} post={post_total} (radius={radius})"
	)
	# Either water-tile count rose or the AOE was already mostly water.
	assert post_water >= pre_water, (
		f"Flood somehow reduced water-tile count: pre={pre_water} post={post_water}"
	)


def main():
	checks = [
		('check_flood_lowers_total_altitude', check_flood_lowers_total_altitude),
	]
	failed = []
	for name, check_fn in checks:
		try:
			check_fn()
			print(f"PASS: {name}")
		except Exception as e:
			print(f"FAIL: {name}: {e}")
			failed.append(name)
	if failed:
		print(f"\n{len(failed)} checks failed")
		sys.exit(1)
	print(f"\nAll {len(checks)} checks passed")
	sys.exit(0)


if __name__ == '__main__':
	main()
