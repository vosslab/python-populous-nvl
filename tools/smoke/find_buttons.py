#!/usr/bin/env python3
"""Find-button camera locator behavior (M2 WP-M2-F).

Each find button either centers the camera on the relevant target or
queues a "no target" tooltip without moving the camera.
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
import populous_game.game as game_module
import populous_game.peep_state as peep_state


def _setup_game():
	"""Boot a Game with random terrain and a known peep set."""
	g = game_module.Game()
	g.game_map.randomize(seed=4242)
	g.app_state.transition_to(g.app_state.PLAYING)
	g.peeps.clear()
	return g


def check_find_battle_no_battle_queues_tooltip():
	"""No FIGHT-state peep -> camera unchanged + tooltip queued."""
	game = _setup_game()
	game.spawn_initial_peeps(5)
	game.spawn_enemy_peeps(5)
	cam_before = (game.camera.r, game.camera.c)
	msgs_before = len(game.input_controller.tooltip_messages)
	game.input_controller._handle_ui_click('_find_battle')
	assert (game.camera.r, game.camera.c) == cam_before
	assert len(game.input_controller.tooltip_messages) == msgs_before + 1


def check_find_battle_centers_on_fight_state_peep():
	"""A peep in FIGHT state must be reachable by _find_battle."""
	game = _setup_game()
	game.spawn_initial_peeps(3)
	target = game.peeps[1]
	# Move the target peep to a known location away from the camera.
	target.x, target.y = 10.5, 20.5
	target.state = peep_state.PeepState.FIGHT
	game.camera.r, game.camera.c = 0.0, 0.0
	game.input_controller._handle_ui_click('_find_battle')
	# Camera centered around (20, 10), top-left at (16, 6) clamped to 0+.
	assert game.camera.r != 0.0 or game.camera.c != 0.0


def check_find_papal_centers_on_magnet():
	"""_find_papal jumps to the papal magnet position."""
	game = _setup_game()
	game.spawn_initial_peeps(3)
	game.mode_manager.set_papal_position(15, 25)
	game.camera.r, game.camera.c = 0.0, 0.0
	game.input_controller._handle_ui_click('_find_papal')
	assert (game.camera.r, game.camera.c) != (0.0, 0.0)


def check_find_knight_no_knight_queues_tooltip():
	"""No knight -> tooltip; camera unchanged."""
	game = _setup_game()
	game.spawn_initial_peeps(3)
	cam_before = (game.camera.r, game.camera.c)
	msgs_before = len(game.input_controller.tooltip_messages)
	game.input_controller._handle_ui_click('_find_knight')
	assert (game.camera.r, game.camera.c) == cam_before
	assert len(game.input_controller.tooltip_messages) == msgs_before + 1


def check_find_knight_centers_on_player_knight():
	"""A peep with weapon_type='knight' is reachable by _find_knight."""
	game = _setup_game()
	game.spawn_initial_peeps(3)
	knight = game.peeps[0]
	knight.faction_id = faction.Faction.PLAYER
	knight.weapon_type = 'knight'
	knight.x, knight.y = 12.5, 18.5
	game.camera.r, game.camera.c = 0.0, 0.0
	game.input_controller._handle_ui_click('_find_knight')
	assert (game.camera.r, game.camera.c) != (0.0, 0.0)


def check_find_battle_cycles_between_battles():
	"""Repeated clicks step to the next FIGHT-state peep."""
	game = _setup_game()
	game.spawn_initial_peeps(4)
	a, b = game.peeps[0], game.peeps[2]
	a.state = peep_state.PeepState.FIGHT
	a.x, a.y = 8.5, 8.5
	b.state = peep_state.PeepState.FIGHT
	b.x, b.y = 22.5, 22.5
	game.input_controller._handle_ui_click('_find_battle')
	first_cam = (game.camera.r, game.camera.c)
	game.input_controller._handle_ui_click('_find_battle')
	second_cam = (game.camera.r, game.camera.c)
	assert first_cam != second_cam, (
		"Repeated _find_battle clicks did not cycle to a different battle"
	)


def main():
	checks = [
		('check_find_battle_no_battle_queues_tooltip', check_find_battle_no_battle_queues_tooltip),
		('check_find_battle_centers_on_fight_state_peep', check_find_battle_centers_on_fight_state_peep),
		('check_find_papal_centers_on_magnet', check_find_papal_centers_on_magnet),
		('check_find_knight_no_knight_queues_tooltip', check_find_knight_no_knight_queues_tooltip),
		('check_find_knight_centers_on_player_knight', check_find_knight_centers_on_player_knight),
		('check_find_battle_cycles_between_battles', check_find_battle_cycles_between_battles),
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
