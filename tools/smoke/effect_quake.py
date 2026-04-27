#!/usr/bin/env python3
"""Earthquake button produces a visible terrain effect (M3 WP-M3-B).

Click the _do_quake button, then click the target tile, settle a few
frames, and assert the corner altitude grid changed in the expected
radius. Also asserts a non-zero pixel diff between pre and post
internal_surface so a renderer regression that silently drops the
quake animation would still fail this test.
"""

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
import populous_game.peep_state as peep_state
import populous_game.settings as power_settings
import tools.headless_runner as runner


def _altitudes_in_radius(game_map, r, c, radius):
	"""Snapshot corner altitudes in the AOE square around (r, c)."""
	out = {}
	for dr in range(-radius, radius + 1):
		for dc in range(-radius, radius + 1):
			rr, cc = r + dr, c + dc
			if 0 <= rr <= game_map.grid_height and 0 <= cc <= game_map.grid_width:
				out[(rr, cc)] = game_map.corners[rr][cc]
	return out


def _alive_count(game):
	return sum(1 for p in game.peeps if not p.dead and p.state != peep_state.PeepState.DEAD)


def check_quake_changes_terrain_in_radius():
	"""Quake mutates corner altitudes in the AOE; effect is visible."""
	game = runner.boot_game_for_tests(state='gameplay', seed=1111, players=4, enemies=4)
	# Park camera at a known position so target (r, c) is in the visible 8x8.
	game.camera.r, game.camera.c = 16.0, 16.0
	game.mana_pool.add(faction.Faction.PLAYER, 5000)
	target_r, target_c = 20, 20
	radius = power_settings.POWER_QUAKE_RADIUS
	pre_alts = _altitudes_in_radius(game.game_map, target_r, target_c, radius)
	pre_signature = runner.surface_pixel_signature(game)
	# Drive the click chain: button click sets pending_power, then ground
	# click activates at (target_r, target_c). The power has no confirm dialog.
	game.input_controller._handle_ui_click('_do_quake')
	game.power_manager.activate('quake', (target_r, target_c))
	# Settle a few frames to let any animation pass through.
	runner.step_frames(game, n=3)
	post_alts = _altitudes_in_radius(game.game_map, target_r, target_c, radius)
	changed = sum(1 for k in pre_alts if pre_alts[k] != post_alts[k])
	assert changed >= 4, (
		f"Quake changed only {changed} corners in the AOE; "
		f"expected at least 4 (radius={radius})."
	)
	# The rendered surface must have actually moved: a renderer that
	# silently drops the quake render would fail this assertion even
	# while the underlying map state changed.
	post_signature = runner.surface_pixel_signature(game)
	assert pre_signature != post_signature, (
		"Quake did not change any pixel of the internal_surface; "
		"renderer may have dropped the AOE update."
	)


def check_quake_consumes_mana():
	"""Successful quake activation deducts mana per the power spec."""
	game = runner.boot_game_for_tests(state='gameplay', seed=2222, players=4)
	game.camera.r, game.camera.c = 16.0, 16.0
	game.mana_pool.add(faction.Faction.PLAYER, 5000)
	pre_mana = game.mana_pool.get_mana(faction.Faction.PLAYER)
	game.input_controller._handle_ui_click('_do_quake')
	result = game.power_manager.activate('quake', (20, 20))
	assert result.success
	post_mana = game.mana_pool.get_mana(faction.Faction.PLAYER)
	assert post_mana < pre_mana, (
		f"Quake activated but mana did not drop: pre={pre_mana} post={post_mana}"
	)


def check_quake_failure_when_no_mana():
	"""Quake without mana does not change terrain or pixel signature."""
	game = runner.boot_game_for_tests(state='gameplay', seed=3333, players=4)
	game.camera.r, game.camera.c = 16.0, 16.0
	# Leave mana at INITIAL_MANA; quake costs more than initial in the
	# default settings. If that ever changes, drain explicitly.
	while game.mana_pool.get_mana(faction.Faction.PLAYER) > 0:
		ok = game.mana_pool.spend(faction.Faction.PLAYER, 1.0)
		if not ok:
			break
	pre_alts = _altitudes_in_radius(game.game_map, 20, 20, power_settings.POWER_QUAKE_RADIUS)
	result = game.power_manager.activate('quake', (20, 20))
	assert not result.success
	post_alts = _altitudes_in_radius(game.game_map, 20, 20, power_settings.POWER_QUAKE_RADIUS)
	assert pre_alts == post_alts, (
		"Failed quake activation still changed terrain altitudes"
	)


def main():
	checks = [
		('check_quake_changes_terrain_in_radius', check_quake_changes_terrain_in_radius),
		('check_quake_consumes_mana', check_quake_consumes_mana),
		('check_quake_failure_when_no_mana', check_quake_failure_when_no_mana),
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
