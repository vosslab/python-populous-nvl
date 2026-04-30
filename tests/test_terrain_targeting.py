"""Terrain mouse targeting rules."""

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

import populous_game.faction as faction
import populous_game.terrain_targeting as terrain_targeting


def _visible_target(game) -> tuple:
	"""Return a stable visible corner and its OS-pixel click position."""
	r = int(game.camera.r) + 2
	c = int(game.camera.c) + 2
	sx, sy = game.viewport_transform.world_to_screen(r, c, 0)
	os_x = sx * game.display_scale
	os_y = sy * game.display_scale
	return r, c, os_x, os_y


def test_terrain_edit_requires_player_peep_on_screen():
	"""A live player peep must be visible before terrain can be edited."""
	from populous_game.game import Game
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(0)
	r, c, os_x, os_y = _visible_target(game)
	game.peeps.clear()

	pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
		button=1, pos=(os_x, os_y)))
	game.input_controller.poll()

	assert game.game_map.get_corner_altitude(r, c) == 0
	assert not terrain_targeting.can_edit_terrain_at(game, r, c)


def test_terrain_click_raises_one_level_with_visible_player_peep():
	"""A valid terrain click raises exactly one level and does not arm repeat."""
	from populous_game.game import Game
	from populous_game.peeps import Peep
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(0)
	r, c, os_x, os_y = _visible_target(game)
	player_peep = Peep(r, c, game.game_map, faction_id=faction.Faction.PLAYER)
	game.peeps = [player_peep]

	pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
		button=1, pos=(os_x, os_y)))
	game.input_controller.poll()
	pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION,
		pos=(os_x, os_y), rel=(0, 0), buttons=(1, 0, 0)))
	game.input_controller.poll()

	assert game.game_map.get_corner_altitude(r, c) == 1
	assert game.input_controller._drag_paint_button is None


def test_enemy_peep_on_screen_does_not_unlock_terrain_editing():
	"""Only player peeps unlock terrain edits."""
	from populous_game.game import Game
	from populous_game.peeps import Peep
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(0)
	r, c, _, _ = _visible_target(game)
	enemy_peep = Peep(r, c, game.game_map, faction_id=faction.Faction.ENEMY)
	game.peeps = [enemy_peep]

	assert not terrain_targeting.live_player_peep_on_screen(game)
	assert not terrain_targeting.can_edit_terrain_at(game, r, c)
