#!/usr/bin/env python3
"""Re-run effect smokes at non-classic canvas presets (M4 WP-M4-D).

Switches the active canvas preset BEFORE booting each Game so the
internal surface, HUD blit, and viewport math run at the requested
size. The full suite (quake, flood, papal, sleep, music, FX, dpad)
runs at `remaster`; a smaller subset (quake, flood, sleep) runs at
`large`. Restores the preset to `classic` in a finally block.

Each check imports the same building blocks the per-power smokes use,
so any divergence between presets surfaces the same way it would in
the existing classic smokes.
"""

import os
import subprocess
import sys

# Add repo root to sys.path so we can import populous_game.
_REPO_ROOT = subprocess.check_output(
	['git', 'rev-parse', '--show-toplevel'],
	text=True,
).strip()
if _REPO_ROOT not in sys.path:
	sys.path.insert(0, _REPO_ROOT)

# Force headless before importing populous_game.
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import populous_game.faction as faction
import populous_game.settings as settings
import tools.headless_runner as runner


#============================================
# Preset switching helper
#============================================


def set_preset(name):
	"""Mutate the four mirror constants in settings to match a preset."""
	preset = settings.CANVAS_PRESETS[name]
	settings.ACTIVE_CANVAS_PRESET = name
	settings.INTERNAL_WIDTH = preset[0]
	settings.INTERNAL_HEIGHT = preset[1]
	settings.HUD_SCALE = preset[2]
	settings.VISIBLE_TILE_COUNT = preset[3]


#============================================
# Per-effect checks
#============================================


def _altitudes_in_radius(game_map, r, c, radius):
	out = {}
	for dr in range(-radius, radius + 1):
		for dc in range(-radius, radius + 1):
			rr, cc = r + dr, c + dc
			if 0 <= rr <= game_map.grid_height and 0 <= cc <= game_map.grid_width:
				out[(rr, cc)] = game_map.corners[rr][cc]
	return out


def check_quake():
	"""Quake mutates corner altitudes and the rendered surface."""
	game = runner.boot_game_for_tests(state='gameplay', seed=1111, players=4, enemies=4)
	game.camera.r, game.camera.c = 16.0, 16.0
	game.mana_pool.add(faction.Faction.PLAYER, 5000)
	target = (20, 20)
	radius = settings.POWER_QUAKE_RADIUS
	pre_alts = _altitudes_in_radius(game.game_map, target[0], target[1], radius)
	pre_sig = runner.surface_pixel_signature(game)
	game.input_controller._handle_ui_click('_do_quake')
	game.power_manager.activate('quake', target)
	runner.step_frames(game, n=3)
	post_alts = _altitudes_in_radius(game.game_map, target[0], target[1], radius)
	changed = sum(1 for k in pre_alts if pre_alts[k] != post_alts[k])
	assert changed >= 4, f"Quake changed only {changed} corners (radius={radius})"
	post_sig = runner.surface_pixel_signature(game)
	assert pre_sig != post_sig, "Quake did not change rendered surface"


def check_flood():
	"""Flood lowers the sum of corner altitudes in its AOE."""
	game = runner.boot_game_for_tests(state='gameplay', seed=5555, players=4)
	game.camera.r, game.camera.c = 16.0, 16.0
	game.mana_pool.add(faction.Faction.PLAYER, 5000)
	target = (20, 20)
	radius = settings.POWER_FLOOD_RADIUS
	pre_alts = _altitudes_in_radius(game.game_map, target[0], target[1], radius)
	pre_total = sum(pre_alts.values())
	game.input_controller._handle_ui_click('_do_flood')
	game.power_manager.activate('flood', target)
	runner.step_frames(game, n=3)
	post_alts = _altitudes_in_radius(game.game_map, target[0], target[1], radius)
	post_total = sum(post_alts.values())
	assert post_total < pre_total, (
		f"Flood did not lower total altitude: pre={pre_total} post={post_total}"
	)


def check_papal():
	"""Papal click + activate sets papal_position to the target."""
	game = runner.boot_game_for_tests(state='gameplay', seed=6666, players=4)
	game.camera.r, game.camera.c = 16.0, 16.0
	game.mana_pool.add(faction.Faction.PLAYER, 5000)
	target = (22, 19)
	game.input_controller._handle_ui_click('_do_papal')
	assert game.mode_manager.papal_mode is True, "papal_mode did not toggle"
	result = game.power_manager.activate('papal', target)
	assert result.success, "papal activation failed"
	runner.step_frames(game, n=2)
	assert game.mode_manager.papal_position == target, (
		f"papal_position={game.mode_manager.papal_position} != {target}"
	)


def check_sleep():
	"""_sleep button toggles between PLAYING and PAUSED."""
	game = runner.boot_game_for_tests(state='gameplay', seed=7777, players=2)
	assert game.app_state.is_playing()
	game.input_controller._handle_ui_click('_sleep')
	assert game.app_state.is_simulation_paused(), "sleep did not pause"
	game.input_controller._handle_ui_click('_sleep')
	assert not game.app_state.is_simulation_paused(), "sleep did not resume"


def check_music():
	"""_music button toggles audio.is_music_playing."""
	game = runner.boot_game_for_tests(state='gameplay', seed=8888, players=2)
	pre = game.audio_manager.is_music_playing
	game.input_controller._handle_ui_click('_music')
	post = game.audio_manager.is_music_playing
	assert pre != post, f"music toggle had no effect (pre={pre} post={post})"


def check_fx():
	"""_fx button toggles audio.is_sfx_muted."""
	game = runner.boot_game_for_tests(state='gameplay', seed=9999, players=2)
	pre = game.audio_manager.is_sfx_muted
	game.input_controller._handle_ui_click('_fx')
	post = game.audio_manager.is_sfx_muted
	assert pre != post, f"fx mute toggle had no effect (pre={pre} post={post})"


def check_dpad():
	"""Clicking a dpad button moves the camera."""
	game = runner.boot_game_for_tests(state='gameplay', seed=1212, players=2)
	game.camera.r = 16.0
	game.camera.c = 16.0
	pre_r, pre_c = game.camera.r, game.camera.c
	# 'E' direction increments column.
	game.input_controller._handle_ui_click('E')
	post_r, post_c = game.camera.r, game.camera.c
	moved = (pre_r, pre_c) != (post_r, post_c)
	assert moved, f"dpad E did not move camera: pre=({pre_r},{pre_c}) post=({post_r},{post_c})"


#============================================
# Runner
#============================================


def _run_checks(label, checks):
	"""Run a list of (name, fn) checks; return number of failures."""
	failed = []
	for name, fn in checks:
		full = f"[{label}] {name}"
		try:
			fn()
			print(f"PASS: {full}")
		except Exception as e:
			print(f"FAIL: {full}: {e}")
			failed.append(full)
	return failed


def main():
	# Full suite at remaster.
	remaster_checks = [
		('check_quake', check_quake),
		('check_flood', check_flood),
		('check_papal', check_papal),
		('check_sleep', check_sleep),
		('check_music', check_music),
		('check_fx', check_fx),
		('check_dpad', check_dpad),
	]
	# Smaller subset at large.
	large_checks = [
		('check_quake', check_quake),
		('check_flood', check_flood),
		('check_sleep', check_sleep),
	]
	all_failed = []
	try:
		set_preset('remaster')
		all_failed.extend(_run_checks('remaster', remaster_checks))
		set_preset('large')
		all_failed.extend(_run_checks('large', large_checks))
	finally:
		set_preset('classic')
	total = len(remaster_checks) + len(large_checks)
	if all_failed:
		print(f"\n{len(all_failed)} of {total} checks failed")
		sys.exit(1)
	print(f"\nAll {total} checks passed")
	sys.exit(0)


if __name__ == '__main__':
	main()
