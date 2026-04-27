#!/usr/bin/env python3
"""Go-button bulk peep orders (M2 WP-M2-G).

Each wired _go_* button issues an order to player-faction peeps using
existing peep states and existing transitions only. Tests verify the
bulk transition fired, with no new states or rules introduced.
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


def _setup():
	g = game_module.Game()
	g.game_map.randomize(seed=88)
	g.app_state.transition_to(g.app_state.PLAYING)
	g.peeps.clear()
	g.spawn_initial_peeps(6)
	g.spawn_enemy_peeps(6)
	# Force every player peep into WANDER so the matrix permits MARCH,
	# JOIN_FORCES, SEEK_FLAT and BUILD transitions.
	for p in g.peeps:
		if p.faction_id == faction.Faction.PLAYER:
			p.state = peep_state.PeepState.WANDER
	return g


def _player_states(game):
	return [p.state for p in game.peeps
			if p.faction_id == faction.Faction.PLAYER and not p.dead]


def check_go_papal_sets_target_and_marches():
	"""_go_papal sets target_x/target_y on player peeps and transitions to MARCH."""
	game = _setup()
	game.input_controller._handle_ui_click('_go_papal')
	marching = sum(1 for s in _player_states(game) if s == peep_state.PeepState.MARCH)
	assert marching >= 1, (
		f"_go_papal did not transition any player peep to MARCH: "
		f"{_player_states(game)}"
	)
	# Targets set on every player peep.
	for p in game.peeps:
		if p.faction_id != faction.Faction.PLAYER or p.dead:
			continue
		assert hasattr(p, 'target_x') and hasattr(p, 'target_y'), (
			"_go_papal did not set target_x/target_y on a player peep"
		)


def check_go_build_transitions_to_seek_flat():
	"""_go_build transitions player peeps into SEEK_FLAT."""
	game = _setup()
	game.input_controller._handle_ui_click('_go_build')
	seeking = sum(1 for s in _player_states(game) if s == peep_state.PeepState.SEEK_FLAT)
	assert seeking >= 1


def check_go_assemble_transitions_to_join_forces():
	"""_go_assemble transitions player peeps into JOIN_FORCES."""
	game = _setup()
	game.input_controller._handle_ui_click('_go_assemble')
	joining = sum(1 for s in _player_states(game) if s == peep_state.PeepState.JOIN_FORCES)
	assert joining >= 1


def check_go_fight_marches_toward_enemies():
	"""_go_fight marches at least one player peep toward an enemy."""
	game = _setup()
	game.input_controller._handle_ui_click('_go_fight')
	marching = sum(1 for s in _player_states(game) if s == peep_state.PeepState.MARCH)
	assert marching >= 1


def check_go_fight_no_enemies_queues_tooltip():
	"""No enemies -> tooltip queued; no MARCH."""
	game = _setup()
	# Drop all enemies.
	game.peeps = [p for p in game.peeps if p.faction_id == faction.Faction.PLAYER]
	msgs_before = len(game.input_controller.tooltip_messages)
	game.input_controller._handle_ui_click('_go_fight')
	assert len(game.input_controller.tooltip_messages) == msgs_before + 1


def check_go_buttons_do_not_touch_enemy_peeps():
	"""Bulk go-orders must not change enemy peep states."""
	game = _setup()
	enemies_before = [(p, p.state) for p in game.peeps
						if p.faction_id == faction.Faction.ENEMY]
	game.input_controller._handle_ui_click('_go_papal')
	game.input_controller._handle_ui_click('_go_assemble')
	game.input_controller._handle_ui_click('_go_build')
	for p, s_before in enemies_before:
		assert p.state == s_before, (
			f"go-order changed enemy peep state from {s_before} to {p.state}"
		)


def main():
	checks = [
		('check_go_papal_sets_target_and_marches', check_go_papal_sets_target_and_marches),
		('check_go_build_transitions_to_seek_flat', check_go_build_transitions_to_seek_flat),
		('check_go_assemble_transitions_to_join_forces', check_go_assemble_transitions_to_join_forces),
		('check_go_fight_marches_toward_enemies', check_go_fight_marches_toward_enemies),
		('check_go_fight_no_enemies_queues_tooltip', check_go_fight_no_enemies_queues_tooltip),
		('check_go_buttons_do_not_touch_enemy_peeps', check_go_buttons_do_not_touch_enemy_peeps),
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
