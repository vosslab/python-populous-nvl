"""Scripted AI opponent that plays the ENEMY faction.

Rules-faithful to the original Amiga where documented in asm/PEEPS_REPORT.md.
v1 behavior: enemy peeps wander, build houses on flat terrain, and march
toward player territory once population threshold is reached. The decision
heuristics are documented in this module.
"""

import populous_game.faction as faction
import populous_game.peep_state as peep_state
import populous_game.settings as settings


class AIOpponent:
	"""Scripted controller for the ENEMY faction.

	Per asm/PEEPS_REPORT.md the original AI is reactive and population-driven.
	v1 of this controller uses three heuristics:
	  1. Idle peeps with low life seek a flat tile and BUILD.
	  2. When enemy peep count exceeds AI_MARCH_THRESHOLD, switch idle peeps
	     to MARCH state targeting the centroid of player peeps.
	  3. When two same-faction peeps are on adjacent tiles, JOIN_FORCES is
	     attempted by the combat layer (no AI action required).
	"""

	def __init__(self, game):
		self.game = game
		self.tick_seconds: float = 0.0

	def update(self, dt: float) -> None:
		"""Update AI opponent logic on a periodic interval."""
		self.tick_seconds += dt
		if self.tick_seconds < settings.AI_TICK_INTERVAL:
			return
		self.tick_seconds = 0.0
		self._decide()

	def _enemy_peeps(self) -> list:
		"""Return list of non-dead enemy peeps."""
		return [p for p in self.game.peeps
			if p.faction_id == faction.Faction.ENEMY
			and p.state != peep_state.PeepState.DEAD]

	def _player_peeps(self) -> list:
		"""Return list of non-dead player peeps."""
		return [p for p in self.game.peeps
			if p.faction_id == faction.Faction.PLAYER
			and p.state != peep_state.PeepState.DEAD]

	def _decide(self) -> None:
		"""Execute one cycle of AI decision-making."""
		enemies = self._enemy_peeps()
		if not enemies:
			return
		players = self._player_peeps()
		# Heuristic 1: idle low-life peeps seek flat (later: BUILD).
		for p in enemies:
			if p.state in (peep_state.PeepState.IDLE, peep_state.PeepState.WANDER):
				if p.life < settings.AI_BUILD_LIFE_THRESHOLD:
					if peep_state.PeepState.SEEK_FLAT in p._ALLOWED_TRANSITIONS.get(p.state, ()):
						p.transition(peep_state.PeepState.SEEK_FLAT)
		# Heuristic 2: mass marches above threshold.
		if len(enemies) >= settings.AI_MARCH_THRESHOLD and players:
			marchers = [p for p in enemies
				if p.state in (peep_state.PeepState.IDLE, peep_state.PeepState.WANDER)]
			for p in marchers[:settings.AI_MARCH_BATCH]:
				if peep_state.PeepState.MARCH in p._ALLOWED_TRANSITIONS.get(p.state, ()):
					p.transition(peep_state.PeepState.MARCH)

	def _centroid(self, peeps: list) -> tuple:
		"""Compute centroid of a list of peeps."""
		if not peeps:
			return (0.0, 0.0)
		sx = sum(p.x for p in peeps) / len(peeps)
		sy = sum(p.y for p in peeps) / len(peeps)
		return (sx, sy)
