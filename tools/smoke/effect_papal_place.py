#!/usr/bin/env python3
"""Papal placement button changes mode_manager.papal_position (M3 WP-M3-C)."""

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
import tools.headless_runner as runner


def check_papal_button_changes_papal_position():
	"""Click _do_papal then activate sets papal_position to the target."""
	game = runner.boot_game_for_tests(state='gameplay', seed=6666, players=4)
	game.camera.r, game.camera.c = 16.0, 16.0
	game.mana_pool.add(faction.Faction.PLAYER, 5000)
	pre_pos = game.mode_manager.papal_position
	target = (22, 19)
	game.input_controller._handle_ui_click('_do_papal')
	assert game.mode_manager.papal_mode is True, (
		"_do_papal click did not enter papal mode"
	)
	result = game.power_manager.activate('papal', target)
	assert result.success
	runner.step_frames(game, n=2)
	post_pos = game.mode_manager.papal_position
	assert post_pos == target
	assert post_pos != pre_pos, (
		f"papal_position did not change: pre={pre_pos} post={post_pos}"
	)


def main():
	checks = [
		('check_papal_button_changes_papal_position', check_papal_button_changes_papal_position),
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
