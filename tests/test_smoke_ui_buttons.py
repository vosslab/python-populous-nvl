"""Smoke test: clicking each UI button does not crash the renderer.

This guards against regressions where the renderer references a Game
attribute that does not exist (e.g., self.game.ui_buttons instead of
self.game.ui_panel.buttons). The default headless smoke test never
triggers a button click, so those AttributeErrors slip through.
"""

import sys
import time

# local repo modules
import git_file_utils

REPO_ROOT = git_file_utils.get_repo_root()
sys.path.insert(0, REPO_ROOT)

#============================================

def test_dpad_button_click_does_not_crash():
	"""After registering a dpad button click, draw the frame without exception."""
	from populous_game.game import Game
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)

	# Simulate a registered click on each dpad button shape
	for action in game.ui_panel.buttons.keys():
		game.last_button_click = (action, time.time())
		game.draw()

	# If we got here without raising, the renderer can resolve every button
	assert True

#============================================

def test_join_forces_from_any_peep_state_does_not_crash():
	"""Same-faction merge must succeed regardless of loser's current state.

	Regression: peep in SEEK_FLAT (or any non-FIGHT state) being absorbed by
	a stronger same-faction peep raised 'Disallowed transition from seek_flat
	to dead'. DEAD is a terminal sink reachable from any state.
	"""
	from populous_game.game import Game
	import populous_game.combat as combat
	import populous_game.peep_state as peep_state

	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(3)
	game.spawn_initial_peeps(4)

	# Force every player peep into a non-FIGHT state and then merge them
	# pairwise; nothing should raise.
	non_fight_states = [
		peep_state.PeepState.IDLE,
		peep_state.PeepState.WANDER,
		peep_state.PeepState.SEEK_FLAT,
		peep_state.PeepState.BUILD,
		peep_state.PeepState.GATHER,
		peep_state.PeepState.JOIN_FORCES,
		peep_state.PeepState.MARCH,
	]
	peeps = list(game.peeps)
	for s, p in zip(non_fight_states, peeps):
		p.state = s

	# Merge first pair: loser is in IDLE
	combat.join_forces(peeps[0], peeps[1])
	# Merge another pair where loser is in SEEK_FLAT (the original crash case)
	combat.join_forces(peeps[2], peeps[3])

	assert True

#============================================

def test_long_gameplay_smoke():
	"""Run the full update + draw loop for ~5 sim seconds with both factions.

	This exercises combat, drowning, AI, and rendering paths together.
	"""
	from populous_game.game import Game

	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(3)
	game.spawn_initial_peeps(8)
	game.spawn_enemy_peeps(8)

	for _ in range(300):
		game.update(1.0 / 60.0)
		game.draw()

	assert True

#============================================

def test_renderer_resolves_all_button_attrs():
	"""Verify renderer code paths do not reference missing Game attributes."""
	from populous_game.game import Game
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)

	# Force dpad held state to exercise the held-direction draw branch
	for action in ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']:
		game.last_button_click = (action, time.time())
		game.mode_manager.dpad_held_direction = action
		game.mode_manager.dpad_last_flash_time = time.time()
		game.draw()

	assert True
