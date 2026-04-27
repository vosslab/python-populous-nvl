"""Smoke tests for AI opponent (M5 Wave 3, Patch 2)."""

import populous_game.game as game_module
import populous_game.faction as faction
import populous_game.peep_state as peep_state
import populous_game.settings as settings


class TestAIOpponent:
	"""AI opponent basic functionality and decision-making."""

	def test_ai_opponent_exists(self):
		"""Game creates an AI opponent instance."""
		game = game_module.Game()
		assert hasattr(game, 'ai_opponent')
		assert game.ai_opponent is not None

	def test_ai_update_called(self):
		"""AI opponent update() can be called without error."""
		game = game_module.Game()
		game.game_map.set_all_altitude(3)
		game.spawn_enemy_peeps(5)
		# Should not raise
		game.ai_opponent.update(0.5)

	def test_ai_transitions_on_tick(self):
		"""AI makes a state transition after time accumulation."""
		game = game_module.Game()
		game.game_map.set_all_altitude(3)
		# Spawn enemies with low life (below AI_BUILD_LIFE_THRESHOLD)
		game.spawn_enemy_peeps(3)
		for p in game.peeps:
			p.life = settings.AI_BUILD_LIFE_THRESHOLD - 5.0
			p.state = peep_state.PeepState.IDLE
		# Call update multiple times to trigger AI tick
		for _ in range(int(settings.AI_TICK_INTERVAL * 2) + 1):
			game.ai_opponent.update(0.6)
		# At least one peep should have transitioned to SEEK_FLAT
		seek_flat_count = sum(1 for p in game.peeps if p.state == peep_state.PeepState.SEEK_FLAT)
		assert seek_flat_count >= 1

	def test_ai_march_above_threshold(self):
		"""AI commands MARCH when enemy population exceeds threshold."""
		game = game_module.Game()
		game.game_map.set_all_altitude(3)
		# Spawn enough enemies to trigger march threshold
		game.spawn_enemy_peeps(settings.AI_MARCH_THRESHOLD + 2)
		# Spawn at least one player peep as target
		game.spawn_initial_peeps(2)
		# Set all enemy peeps to WANDER state (MARCH requires WANDER or other eligible states)
		for p in game.peeps:
			if p.faction_id == faction.Faction.ENEMY:
				p.state = peep_state.PeepState.WANDER
				p.life = settings.PEEP_LIFE_MAX
		# Trigger AI update multiple times to accumulate tick time
		for _ in range(int(settings.AI_TICK_INTERVAL * 2) + 1):
			game.ai_opponent.update(0.6)
		# At least one enemy should have transitioned to MARCH
		march_count = sum(1 for p in game.peeps if p.faction_id == faction.Faction.ENEMY and p.state == peep_state.PeepState.MARCH)
		assert march_count >= 1

	def test_ai_no_action_if_no_enemies(self):
		"""AI does nothing if no enemy peeps exist."""
		game = game_module.Game()
		game.game_map.set_all_altitude(3)
		game.spawn_initial_peeps(5)
		# No enemies spawned
		assert len([p for p in game.peeps if p.faction_id == faction.Faction.ENEMY]) == 0
		# Should not raise
		game.ai_opponent.update(2.0)

	def test_ai_no_march_without_players(self):
		"""AI does not command MARCH if no player peeps exist."""
		game = game_module.Game()
		game.game_map.set_all_altitude(3)
		game.spawn_enemy_peeps(settings.AI_MARCH_THRESHOLD + 2)
		# No players spawned
		assert len([p for p in game.peeps if p.faction_id == faction.Faction.PLAYER]) == 0
		for p in game.peeps:
			p.state = peep_state.PeepState.IDLE
		# Trigger AI update
		for _ in range(int(settings.AI_TICK_INTERVAL * 2) + 1):
			game.ai_opponent.update(0.6)
		# No enemy should have transitioned to MARCH
		march_count = sum(1 for p in game.peeps if p.state == peep_state.PeepState.MARCH)
		assert march_count == 0

	def test_ai_respects_state_transitions(self):
		"""AI only transitions through valid state transitions."""
		game = game_module.Game()
		game.game_map.set_all_altitude(3)
		game.spawn_enemy_peeps(1)
		peep_a = game.peeps[0]
		# Force peep to DROWN (dead state)
		peep_a.state = peep_state.PeepState.DROWN
		peep_a.life = 0.1
		# AI should not attempt invalid transitions
		for _ in range(int(settings.AI_TICK_INTERVAL * 2) + 1):
			game.ai_opponent.update(0.6)
		# Peep should not have transitioned from DROWN to SEEK_FLAT
		assert peep_a.state == peep_state.PeepState.DROWN
