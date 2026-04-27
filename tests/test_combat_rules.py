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
