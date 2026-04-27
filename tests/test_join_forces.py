"""Tests for join_forces mechanics (per asm/PEEPS_REPORT.md section 4.4)."""

import populous_game.combat as combat
import populous_game.faction as faction
import populous_game.peep_state as peep_state
import populous_game.settings as settings


class MockPeep:
	"""Mock Peep for join_forces testing."""

	def __init__(self, faction_id: int = faction.Faction.PLAYER, life: float = 50.0):
		self.faction_id = faction_id
		self.life = life
		self.state = peep_state.PeepState.IDLE

	def transition(self, new_state: str) -> None:
		"""Mock transition."""
		self.state = new_state


def test_same_faction_merge_absorbs_life():
	"""Per asm/PEEPS_REPORT.md section 4.4: same-faction peeps merge, stronger absorbs.

	When two same-faction peeps merge, the winner absorbs loser's life (capped at MAX).
	"""
	peep_a = MockPeep(faction_id=faction.Faction.PLAYER, life=60.0)
	peep_b = MockPeep(faction_id=faction.Faction.PLAYER, life=40.0)

	result = combat.join_forces(peep_a, peep_b)

	assert result is True
	assert peep_a.life == min(100.0, settings.PEEP_LIFE_MAX)
	assert peep_b.state == peep_state.PeepState.DEAD


def test_different_faction_merge_fails():
	"""Per asm/PEEPS_REPORT.md section 4.4: different-faction peeps cannot merge.

	Enemies and allies should not merge.
	"""
	peep_a = MockPeep(faction_id=faction.Faction.PLAYER, life=60.0)
	peep_b = MockPeep(faction_id=faction.Faction.ENEMY, life=40.0)

	result = combat.join_forces(peep_a, peep_b)

	assert result is False
	assert peep_a.life == 60.0
	assert peep_b.life == 40.0
	assert peep_b.state == peep_state.PeepState.IDLE


def test_neutral_faction_no_merge():
	"""Per asm/PEEPS_REPORT.md: NEUTRAL faction peeps do not merge."""
	peep_a = MockPeep(faction_id=faction.Faction.NEUTRAL, life=60.0)
	peep_b = MockPeep(faction_id=faction.Faction.NEUTRAL, life=40.0)

	result = combat.join_forces(peep_a, peep_b)

	assert result is False


def test_merge_with_self_fails():
	"""Per asm/PEEPS_REPORT.md: peep cannot merge with itself."""
	peep_a = MockPeep(faction_id=faction.Faction.PLAYER, life=60.0)

	result = combat.join_forces(peep_a, peep_a)

	assert result is False
	assert peep_a.life == 60.0


def test_merge_with_dead_peep_fails():
	"""Per asm/PEEPS_REPORT.md: dead peeps do not merge."""
	peep_a = MockPeep(faction_id=faction.Faction.PLAYER, life=60.0)
	peep_b = MockPeep(faction_id=faction.Faction.PLAYER, life=40.0)
	peep_b.state = peep_state.PeepState.DEAD

	result = combat.join_forces(peep_a, peep_b)

	assert result is False


def test_life_capped_at_max_on_merge():
	"""Per asm/PEEPS_REPORT.md section 4.4: merged life capped at PEEP_LIFE_MAX (0x7d00).

	Winner with very high life plus loser's life should be capped.
	"""
	peep_a = MockPeep(faction_id=faction.Faction.PLAYER, life=150.0)
	peep_b = MockPeep(faction_id=faction.Faction.PLAYER, life=100.0)

	result = combat.join_forces(peep_a, peep_b)

	assert result is True
	assert peep_a.life == settings.PEEP_LIFE_MAX
	assert peep_a.life <= 250.0  # Would be 250 without cap


def test_weaker_peep_becomes_winner():
	"""Per asm/PEEPS_REPORT.md section 4.4: stronger peep always survives.

	When peep_b is stronger, it should be the winner, not peep_a.
	"""
	peep_a = MockPeep(faction_id=faction.Faction.PLAYER, life=30.0)
	peep_b = MockPeep(faction_id=faction.Faction.PLAYER, life=70.0)

	result = combat.join_forces(peep_a, peep_b)

	assert result is True
	assert peep_a.state == peep_state.PeepState.DEAD
	assert peep_b.life == min(100.0, settings.PEEP_LIFE_MAX)
