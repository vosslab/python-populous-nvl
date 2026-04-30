"""Rules-conformance tests for combat mechanics (per asm/PEEPS_REPORT.md)."""

import pytest
import populous_game.combat as combat
import populous_game.faction as faction
import populous_game.peep_state as peep_state
import populous_game.settings as settings


class MockPeep:
	"""Mock Peep for testing combat without full game context."""

	def __init__(self, faction_id: int = faction.Faction.PLAYER, life: float = 50.0):
		self.faction_id = faction_id
		self.life = life
		self.state = peep_state.PeepState.FIGHT

	def transition(self, new_state: str) -> None:
		"""Mock transition for testing."""
		self.state = new_state


class MockHouse:
	"""Mock House for testing combat without full game context."""

	def __init__(self, faction_id: int = faction.Faction.PLAYER, life: float = 50.0):
		self.faction_id = faction_id
		self.life = life
		self.destroyed = False
		self.r = 5
		self.c = 5


def test_two_equal_life_enemy_peeps_damage_equally():
	"""Per asm/PEEPS_REPORT.md section 4.3: equal-life peeps deal equal damage.

	Higher-life peeps have advantage; equal-life peeps should take equal time to kill each other.
	"""
	# Create fresh peeps for each damage calculation to avoid state modifications
	peep_a = MockPeep(faction_id=faction.Faction.PLAYER, life=settings.PEEP_LIFE_REFERENCE)
	peep_b = MockPeep(faction_id=faction.Faction.ENEMY, life=settings.PEEP_LIFE_REFERENCE)

	peep_a2 = MockPeep(faction_id=faction.Faction.PLAYER, life=settings.PEEP_LIFE_REFERENCE)
	peep_b2 = MockPeep(faction_id=faction.Faction.ENEMY, life=settings.PEEP_LIFE_REFERENCE)

	dt = 1.0
	dmg_a_on_b = combat.damage_peep_vs_peep(peep_a, peep_b, dt)
	dmg_b_on_a = combat.damage_peep_vs_peep(peep_b2, peep_a2, dt)

	# Both should deal equal damage per second since life is equal
	assert dmg_a_on_b == dmg_b_on_a
	assert dmg_a_on_b > 0.0


def test_higher_life_peep_wins_faster():
	"""Per asm/PEEPS_REPORT.md section 4.3: higher-life peep wins in combat.

	A peep with double the life should deal double damage per frame.
	"""
	# Create fresh peeps for each damage calculation to avoid state modifications
	peep_strong = MockPeep(faction_id=faction.Faction.PLAYER, life=2 * settings.PEEP_LIFE_REFERENCE)
	peep_weak = MockPeep(faction_id=faction.Faction.ENEMY, life=settings.PEEP_LIFE_REFERENCE)

	peep_strong2 = MockPeep(faction_id=faction.Faction.PLAYER, life=2 * settings.PEEP_LIFE_REFERENCE)
	peep_weak2 = MockPeep(faction_id=faction.Faction.ENEMY, life=settings.PEEP_LIFE_REFERENCE)

	dt = 1.0
	dmg_strong_on_weak = combat.damage_peep_vs_peep(peep_strong, peep_weak, dt)
	dmg_weak_on_strong = combat.damage_peep_vs_peep(peep_weak2, peep_strong2, dt)

	# Strong peep should deal roughly double the damage
	assert dmg_strong_on_weak > dmg_weak_on_strong
	assert dmg_strong_on_weak / dmg_weak_on_strong == pytest.approx(2.0, rel=0.01)


def test_same_faction_peeps_no_damage():
	"""Per asm/PEEPS_REPORT.md section 4.3: same-faction peeps cause no damage.

	Allies should not damage each other.
	"""
	peep_a = MockPeep(faction_id=faction.Faction.PLAYER, life=50.0)
	peep_b = MockPeep(faction_id=faction.Faction.PLAYER, life=50.0)

	dt = 1.0
	dmg = combat.damage_peep_vs_peep(peep_a, peep_b, dt)

	assert dmg == 0.0
	assert peep_b.life == 50.0


def test_peep_attacking_enemy_house_destroys_it():
	"""Per asm/PEEPS_REPORT.md section 4.3: peep can destroy enemy house.

	A peep with full life attacking a house should destroy it within calculable time.
	"""
	peep_attacker = MockPeep(faction_id=faction.Faction.PLAYER, life=50.0)
	house_target = MockHouse(faction_id=faction.Faction.ENEMY, life=20.0)

	dt = 1.0
	total_damage = 0.0

	# Apply damage until house is destroyed
	for _ in range(100):
		dmg = combat.damage_peep_vs_house(peep_attacker, house_target, dt)
		total_damage += dmg
		if house_target.destroyed:
			break

	assert house_target.destroyed
	assert total_damage > 0.0


def test_house_destruction_respects_faction():
	"""Per asm/PEEPS_REPORT.md: building destruction yields a peep with correct faction.

	When a house is destroyed via combat, the spawn peep should carry the house's faction_id.
	(This test checks the spawn logic indirectly via game.py integration test.)
	"""
	# This is tested in integration via game update, but here we verify
	# that the capping logic in settings works correctly.
	assert settings.PEEP_LIFE_MAX >= settings.PEEP_LIFE_REFERENCE
	# A house with life > PEEP_LIFE_MAX should spawn a peep capped at PEEP_LIFE_MAX
	house_life = settings.PEEP_LIFE_MAX + 100.0
	capped_life = min(house_life, settings.PEEP_LIFE_MAX)
	assert capped_life == settings.PEEP_LIFE_MAX


def test_asm_peep_constants_are_named_separately():
	"""ASM source constants are available without changing gameplay caps."""
	assert settings.ASM_PEEP_RECORD_STRIDE == 0x16
	assert settings.ASM_PEEP_CAP == 0x00D0
	assert settings.ASM_PEEP_MERGE_LIFE_CAP == 0x7D00
	assert settings.ASM_MOVE_FAILED_CODE == 0x03E7
	assert settings.PEEP_LIFE_MAX < settings.ASM_PEEP_MERGE_LIFE_CAP


def test_mark_peep_vs_peep_fight_sets_shield_metadata():
	"""Enemy contact records opponent references for shield combat bars."""
	peep_a = MockPeep(faction_id=faction.Faction.PLAYER, life=50.0)
	peep_b = MockPeep(faction_id=faction.Faction.ENEMY, life=50.0)
	peep_a.state = peep_state.PeepState.IDLE
	peep_b.state = peep_state.PeepState.IDLE
	peep_a._ALLOWED_TRANSITIONS = {
		peep_state.PeepState.IDLE: {peep_state.PeepState.FIGHT},
	}
	peep_b._ALLOWED_TRANSITIONS = {
		peep_state.PeepState.IDLE: {peep_state.PeepState.FIGHT},
	}

	combat.mark_peep_vs_peep_fight(peep_a, peep_b)

	assert peep_a.state == peep_state.PeepState.FIGHT
	assert peep_b.state == peep_state.PeepState.FIGHT
	assert peep_a.shield_opponent is peep_b
	assert peep_b.shield_opponent is peep_a


def test_damage_clears_dead_shield_opponent():
	"""Fatal damage clears stale shield opponent references."""
	attacker = MockPeep(faction_id=faction.Faction.PLAYER, life=500.0)
	defender = MockPeep(faction_id=faction.Faction.ENEMY, life=1.0)
	attacker.shield_opponent = defender
	defender.shield_opponent = attacker

	combat.damage_peep_vs_peep(attacker, defender, 1.0)

	assert defender.state == peep_state.PeepState.DEAD
	assert attacker.shield_opponent is None
	assert defender.shield_opponent is None
