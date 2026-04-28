"""Tests for selection helpers, including knight discovery."""

import pygame

import populous_game.game as game_module
import populous_game.faction as faction
import populous_game.peep_state as peep_state
import populous_game.settings as settings
import populous_game.selection as selection


def test_find_knight_finds_promoted_peep_immediately():
	"""_find_knight should find the newly promoted knight right away."""
	game = game_module.Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.spawn_initial_peeps(5)
	game.spawn_enemy_peeps(2)

	result = game.power_manager.activate('knight', None)
	assert result.success

	found = selection.find_next_knight(game)
	assert found is not None
	idx, r, c = found
	knight = game.peeps[idx]
	assert getattr(knight, 'weapon_type', None) == 'knight'
	assert (r, c) == (int(knight.y), int(knight.x))


def test_handle_find_knight_centers_camera_on_promoted_peep():
	"""The real UI handler should center the camera on the promoted knight."""
	game = game_module.Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.spawn_initial_peeps(5)
	game.spawn_enemy_peeps(2)

	result = game.power_manager.activate('knight', None)
	assert result.success

	knight = next(p for p in game.peeps if getattr(p, 'weapon_type', None) == 'knight')
	game.input_controller._find_knight_cursor = -1
	game.camera.center_on(0, 0)
	game.input_controller._handle_find_knight()

	expected_r = max(0.0, min(float(int(knight.y)) - float(settings.VISIBLE_TILE_COUNT // 2), float(settings.GRID_HEIGHT - settings.VISIBLE_TILE_COUNT)))
	expected_c = max(0.0, min(float(int(knight.x)) - float(settings.VISIBLE_TILE_COUNT // 2), float(settings.GRID_WIDTH - settings.VISIBLE_TILE_COUNT)))
	assert game.camera.r == expected_r
	assert game.camera.c == expected_c


def test_find_knight_cycles_deterministically_with_multiple_knights():
	"""Repeated _find_knight calls should step through knights in order."""
	game = game_module.Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.spawn_initial_peeps(8)
	game.spawn_enemy_peeps(2)

	first = game.power_manager.activate('knight', None)
	assert first.success

	# Clear the knight cooldown so the second activation exercises the
	# deterministic selection path rather than the timing gate.
	game.power_manager.cooldowns['knight'] = 0.0
	game.mana_pool.add(faction.Faction.PLAYER, 1000)
	eligible = [p for p in game.peeps if p.faction_id == faction.Faction.PLAYER and getattr(p, 'weapon_type', None) != 'knight']
	assert eligible
	second = game.power_manager.activate('knight', None)
	assert second.success

	first_result = selection.find_next_knight(game, after_index=-1)
	assert first_result is not None
	second_result = selection.find_next_knight(game, after_index=first_result[0])
	assert second_result is not None
	assert second_result[0] != first_result[0]


def test_knight_still_updates_and_renders():
	"""A promoted knight should still update and draw like a normal peep."""
	game = game_module.Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.spawn_initial_peeps(3)
	game.spawn_enemy_peeps(1)

	result = game.power_manager.activate('knight', None)
	assert result.success

	knight = next(p for p in game.peeps if getattr(p, 'weapon_type', None) == 'knight')
	surface = pygame.Surface((64, 64))
	before = (knight.x, knight.y, knight.life, knight.state)
	knight.update(0.1, game.viewport_transform)
	knight.draw(surface, game.viewport_transform)
	after = (knight.x, knight.y, knight.life, knight.state)

	assert after[2] <= before[2]  # passive life decay still applies
	assert knight.weapon_type == 'knight'


def test_knight_still_participates_in_merge_and_combat_paths():
	"""A knight should still go through normal merge and combat resolution."""
	game = game_module.Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.spawn_initial_peeps(2)
	game.spawn_enemy_peeps(1)

	result = game.power_manager.activate('knight', None)
	assert result.success
	knight = next(p for p in game.peeps if getattr(p, 'weapon_type', None) == 'knight')

	# Normal same-faction merge path should still work with a knight peep.
	ally = next(p for p in game.peeps if p is not knight and p.faction_id == faction.Faction.PLAYER)
	knight.x = ally.x
	knight.y = ally.y
	knight.life = 60
	ally.life = 10
	game._apply_combat_resolution(0.1)
	assert knight.state in peep_state.PeepState.ALL
	assert knight.life >= 60
	assert ally.state == peep_state.PeepState.DEAD
