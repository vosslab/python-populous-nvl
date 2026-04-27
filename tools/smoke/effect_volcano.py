#!/usr/bin/env python3
"""Volcano button raises terrain in a radius (M3 WP-M3-B)."""

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


def _altitudes_in_radius(game_map, r, c, radius):
	out = {}
	for dr in range(-radius, radius + 1):
		for dc in range(-radius, radius + 1):
			rr, cc = r + dr, c + dc
			if 0 <= rr <= game_map.grid_height and 0 <= cc <= game_map.grid_width:
				out[(rr, cc)] = game_map.corners[rr][cc]
	return out


def check_volcano_raises_terrain():
	"""Volcano increases at least one corner altitude in the radius."""
	game = runner.boot_game_for_tests(state='gameplay', seed=4444, players=4)
	game.camera.r, game.camera.c = 16.0, 16.0
	game.mana_pool.add(faction.Faction.PLAYER, 5000)
	target_r, target_c = 20, 20
	radius = power_settings.POWER_VOLCANO_RADIUS
	pre_alts = _altitudes_in_radius(game.game_map, target_r, target_c, radius)
	game.input_controller._handle_ui_click('_do_volcano')
	# Volcano has requires_confirm=True; bypass the confirm UI and call
	# the power directly to test the effect (the confirm flow is
	# exercised by tests/test_confirm_dialog_*.py).
	game.power_manager.activate('volcano', (target_r, target_c))
	runner.step_frames(game, n=3)
	post_alts = _altitudes_in_radius(game.game_map, target_r, target_c, radius)
	raised = sum(1 for k in pre_alts if post_alts[k] > pre_alts[k])
	assert raised >= 1, (
		f"Volcano did not raise any corner altitude in the AOE; "
		f"pre vs post matched on every corner (radius={radius})."
	)


def main():
	checks = [
		('check_volcano_raises_terrain', check_volcano_raises_terrain),
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
