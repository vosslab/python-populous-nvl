"""Tests for win/lose conditions (M5 Wave 3, Patch 5)."""

import populous_game.game as game_module
import populous_game.faction as faction
import populous_game.peep_state as peep_state


class TestWinLoseConditions:
	"""Game-over conditions: victory when enemies eliminated."""

	def test_win_when_all_enemies_eliminated(self):
		"""Game transitions to WIN when all enemy peeps and houses are gone."""
		game = game_module.Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.game_map.set_all_altitude(3)
		game.spawn_initial_peeps(5)
		game.spawn_enemy_peeps(1)
		# Force enemy peeps to DEAD state
		for p in game.peeps:
			if p.faction_id == faction.Faction.ENEMY:
				p.state = peep_state.PeepState.DEAD
				p.life = 0
		# Check for game over
		game._check_game_over()
		assert game.app_state.is_gameover()
		assert game.app_state.gameover_result == 'win'

	def test_lose_when_all_player_eliminated(self):
		"""Game transitions to LOSE when all player peeps and houses are gone."""
		game = game_module.Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.game_map.set_all_altitude(3)
		game.spawn_initial_peeps(1)
		game.spawn_enemy_peeps(5)
		# Force player peeps to DEAD state
		for p in game.peeps:
			if p.faction_id == faction.Faction.PLAYER:
				p.state = peep_state.PeepState.DEAD
				p.life = 0
		# Check for game over
		game._check_game_over()
		assert game.app_state.is_gameover()
		assert game.app_state.gameover_result == 'lose'

	def test_no_gameover_with_living_enemies(self):
		"""Game does not end if living enemy peeps exist."""
		game = game_module.Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.game_map.set_all_altitude(3)
		game.spawn_initial_peeps(5)
		game.spawn_enemy_peeps(3)
		# Leave enemies alive
		game._check_game_over()
		assert game.app_state.is_playing()

	def test_no_gameover_with_living_player(self):
		"""Game does not end if living player peeps exist."""
		game = game_module.Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.game_map.set_all_altitude(3)
		game.spawn_initial_peeps(3)
		game.spawn_enemy_peeps(5)
		# Leave player alive
		game._check_game_over()
		assert game.app_state.is_playing()

	def test_win_with_enemy_houses_destroyed(self):
		"""Game transitions to WIN when all enemy peeps and houses destroyed."""
		game = game_module.Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.game_map.set_all_altitude(3)
		game.spawn_initial_peeps(5)
		game.spawn_enemy_peeps(1)
		# Add an enemy house
		from populous_game.houses import House
		enemy_house = House(20, 20, faction_id=faction.Faction.ENEMY)
		game.game_map.add_house(enemy_house)
		# Kill all enemy peeps
		for p in game.peeps:
			if p.faction_id == faction.Faction.ENEMY:
				p.state = peep_state.PeepState.DEAD
				p.life = 0
		# Destroy all enemy houses
		enemy_house.destroyed = True
		# Check for game over
		game._check_game_over()
		assert game.app_state.is_gameover()
		assert game.app_state.gameover_result == 'win'

	def test_no_check_when_not_playing(self):
		"""_check_game_over() is no-op when not in PLAYING state."""
		game = game_module.Game()
		assert game.app_state.is_menu()
		# Should not raise
		game._check_game_over()
		assert game.app_state.is_menu()

	def test_check_during_game_updates(self):
		"""_check_game_over() is called during game.update()."""
		game = game_module.Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.game_map.set_all_altitude(3)
		game.spawn_initial_peeps(1)
		# No enemies to create instant win condition
		for _ in range(2):
			game.update(0.1)
		# Game should transition to WIN after update checks condition
		# (Only if no enemies are spawned)
		if len([p for p in game.peeps if p.faction_id == faction.Faction.ENEMY]) == 0:
			assert game.app_state.is_gameover()
			assert game.app_state.gameover_result == 'win'
