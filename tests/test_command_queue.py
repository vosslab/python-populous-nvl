"""Tests for command queue visualization (M7)."""

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


def test_draw_command_queue_no_marching_peeps_does_not_crash():
	"""With no MARCH peeps, the command-queue draw is a no-op."""
	from populous_game.game import Game
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(3)
	game.spawn_initial_peeps(3)
	game.renderer._draw_command_queue()
	assert True


def test_draw_command_queue_with_marching_peep_does_not_crash():
	"""A peep in MARCH with a target draws a line without error."""
	from populous_game.game import Game
	import populous_game.peep_state as peep_state
	import populous_game.faction as faction
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(3)
	game.spawn_initial_peeps(1)
	p = next(x for x in game.peeps if x.faction_id == faction.Faction.PLAYER)
	p.state = peep_state.PeepState.MARCH
	p.target_x = float(p.x) + 5.0
	p.target_y = float(p.y) + 5.0
	game.renderer._draw_command_queue()
	assert True
