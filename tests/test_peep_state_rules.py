"""Rules-conformance tests for peep state machine (per asm/PEEPS_REPORT.md)."""

import pytest
import populous_game.peep_state as peep_state
import populous_game.faction as faction
import populous_game.combat as combat
import populous_game.peeps as peeps


class MockGameMap:
	"""Minimal mock game map."""

	def __init__(self):
		self.grid_width = 64
		self.grid_height = 64


class MockPeep:
	"""Mock Peep for state machine testing."""

	_ALLOWED_TRANSITIONS = {
		peep_state.PeepState.IDLE: {peep_state.PeepState.WANDER, peep_state.PeepState.SEEK_FLAT, peep_state.PeepState.JOIN_FORCES, peep_state.PeepState.FIGHT, peep_state.PeepState.DROWN},
		peep_state.PeepState.WANDER: {peep_state.PeepState.IDLE, peep_state.PeepState.SEEK_FLAT, peep_state.PeepState.BUILD, peep_state.PeepState.JOIN_FORCES, peep_state.PeepState.MARCH, peep_state.PeepState.FIGHT, peep_state.PeepState.DROWN},
		peep_state.PeepState.SEEK_FLAT: {peep_state.PeepState.IDLE, peep_state.PeepState.WANDER, peep_state.PeepState.BUILD, peep_state.PeepState.DROWN},
		peep_state.PeepState.BUILD: {peep_state.PeepState.IDLE, peep_state.PeepState.WANDER, peep_state.PeepState.DROWN},
		peep_state.PeepState.GATHER: {peep_state.PeepState.IDLE, peep_state.PeepState.WANDER, peep_state.PeepState.MARCH, peep_state.PeepState.JOIN_FORCES, peep_state.PeepState.DROWN},
		peep_state.PeepState.JOIN_FORCES: {peep_state.PeepState.MARCH, peep_state.PeepState.FIGHT, peep_state.PeepState.IDLE, peep_state.PeepState.DROWN},
		peep_state.PeepState.MARCH: {peep_state.PeepState.FIGHT, peep_state.PeepState.JOIN_FORCES, peep_state.PeepState.IDLE, peep_state.PeepState.DROWN},
		peep_state.PeepState.FIGHT: {peep_state.PeepState.DEAD, peep_state.PeepState.IDLE, peep_state.PeepState.MARCH, peep_state.PeepState.DROWN},
		peep_state.PeepState.DROWN: {peep_state.PeepState.DEAD},
		peep_state.PeepState.DEAD: set(),
	}

	def __init__(self, faction_id: int = faction.Faction.PLAYER):
		self.faction_id = faction_id
		self.state = peep_state.PeepState.IDLE
		self.life = 50.0

	def transition(self, new_state: str) -> None:
		"""Validate and execute a state transition."""
		if new_state not in peep_state.PeepState.ALL:
			raise ValueError(f"Invalid state: {new_state}")
		if new_state not in self._ALLOWED_TRANSITIONS.get(self.state, set()):
			raise ValueError(f"Disallowed transition from {self.state} to {new_state}")
		self.state = new_state


def test_peepstate_constants_exist():
	"""Per asm/PEEPS_REPORT.md: PeepState constants are defined correctly."""
	assert peep_state.PeepState.IDLE == 'idle'
	assert peep_state.PeepState.WANDER == 'wander'
	assert peep_state.PeepState.SEEK_FLAT == 'seek_flat'
	assert peep_state.PeepState.BUILD == 'build'
	assert peep_state.PeepState.GATHER == 'gather'
	assert peep_state.PeepState.JOIN_FORCES == 'join_forces'
	assert peep_state.PeepState.MARCH == 'march'
	assert peep_state.PeepState.FIGHT == 'fight'
	assert peep_state.PeepState.DROWN == 'drown'
	assert peep_state.PeepState.DEAD == 'dead'


def test_peep_starts_in_idle():
	"""Per asm/PEEPS_REPORT.md: newly constructed peep starts in IDLE state."""
	p = MockPeep()
	assert p.state == peep_state.PeepState.IDLE


def test_real_peep_asm_shadow_fields_default():
	"""New peeps expose additive ASM shadow bookkeeping fields."""
	p = peeps.Peep(1, 2, MockGameMap())
	assert p.asm_flags == 0
	assert p.movement_substate == 0
	assert p.town_counter == 0
	assert p.linked_peep is None
	assert p.remembered_target is None
	assert p.terrain_marker is None
	assert p.last_move_offset == 0
	assert p.shield_opponent is None


def test_allowed_transitions_from_idle():
	"""Per asm/PEEPS_REPORT.md: IDLE allows transitions to WANDER, SEEK_FLAT, etc."""
	p = MockPeep()
	p.transition(peep_state.PeepState.WANDER)
	assert p.state == peep_state.PeepState.WANDER

	p.state = peep_state.PeepState.IDLE
	p.transition(peep_state.PeepState.SEEK_FLAT)
	assert p.state == peep_state.PeepState.SEEK_FLAT

	p.state = peep_state.PeepState.IDLE
	p.transition(peep_state.PeepState.FIGHT)
	assert p.state == peep_state.PeepState.FIGHT


def test_disallowed_transitions_raise():
	"""Per asm/PEEPS_REPORT.md: invalid transitions raise ValueError."""
	p = MockPeep()
	p.state = peep_state.PeepState.IDLE

	# IDLE cannot transition to BUILD directly
	with pytest.raises(ValueError):
		p.transition(peep_state.PeepState.BUILD)

	# IDLE cannot transition to GATHER directly
	with pytest.raises(ValueError):
		p.transition(peep_state.PeepState.GATHER)


def test_drown_to_dead_transition():
	"""Per asm/PEEPS_REPORT.md section 4.1: peep drowning transitions to DEAD."""
	p = MockPeep()
	p.state = peep_state.PeepState.DROWN
	p.transition(peep_state.PeepState.DEAD)
	assert p.state == peep_state.PeepState.DEAD


def test_dead_is_terminal():
	"""Per asm/PEEPS_REPORT.md: DEAD state is terminal (no outgoing transitions)."""
	p = MockPeep()
	p.state = peep_state.PeepState.DEAD

	with pytest.raises(ValueError):
		p.transition(peep_state.PeepState.IDLE)

	with pytest.raises(ValueError):
		p.transition(peep_state.PeepState.WANDER)


def test_join_forces_causes_loser_death():
	"""Per asm/PEEPS_REPORT.md section 4.4: join_forces transitions loser to DEAD."""
	peep_a = MockPeep(faction_id=faction.Faction.PLAYER)
	peep_a.life = 40.0
	peep_a.state = peep_state.PeepState.FIGHT  # must be in FIGHT to transition to DEAD

	peep_b = MockPeep(faction_id=faction.Faction.PLAYER)
	peep_b.life = 50.0
	peep_b.state = peep_state.PeepState.FIGHT

	result = combat.join_forces(peep_a, peep_b)

	assert result is True
	assert peep_a.state == peep_state.PeepState.DEAD  # loser transitions to DEAD
	# winner state is unchanged by join_forces (both stay in FIGHT)
	assert peep_b.life == min(90.0, 200.0)  # capped at PEEP_LIFE_MAX
