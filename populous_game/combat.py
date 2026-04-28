"""Combat resolution (peep-vs-peep, peep-vs-house) per asm/PEEPS_REPORT.md."""

import populous_game.settings as settings
import populous_game.peep_state as peep_state
import populous_game.faction as faction


def is_enemy(a, b) -> bool:
	"""Two entities are enemies iff they have different non-NEUTRAL factions."""
	if a.faction_id == faction.Faction.NEUTRAL or b.faction_id == faction.Faction.NEUTRAL:
		return False
	return a.faction_id != b.faction_id


def damage_peep_vs_peep(attacker, defender, dt: float) -> float:
	"""Apply per-frame combat damage between two peeps. Returns damage dealt.

	Per asm/PEEPS_REPORT.md section 4.3: peeps deal damage proportional to their
	own life. Higher-life peeps win against lower-life peeps over time.
	Default rate: settings.COMBAT_PEEP_DPS (life points per second).
	"""
	if not is_enemy(attacker, defender):
		return 0.0
	if defender.state == peep_state.PeepState.DEAD:
		return 0.0
	dmg = settings.COMBAT_PEEP_DPS * (attacker.life / settings.PEEP_LIFE_REFERENCE) * dt
	defender.life = max(0.0, defender.life - dmg)
	if defender.life <= 0.0:
		defender.transition(peep_state.PeepState.DEAD)
	return dmg


def damage_peep_vs_house(peep, house, dt: float) -> float:
	"""Per-frame damage from a peep attacking an enemy house."""
	if not is_enemy(peep, house):
		return 0.0
	if house.destroyed:
		return 0.0
	dmg = settings.COMBAT_HOUSE_DPS * (peep.life / settings.PEEP_LIFE_REFERENCE) * dt
	house.life = max(0.0, house.life - dmg)
	if house.life <= 0.0:
		house.destroyed = True
	return dmg


def _select_merge_winner_and_loser(peep_a, peep_b):
	"""Return the stronger peep and the peep to retire."""
	if peep_a.life >= peep_b.life:
		return peep_a, peep_b
	return peep_b, peep_a


def _retire_merged_loser(loser) -> None:
	"""Apply the dead transition used after a successful merge."""
	loser.life = 0.0
	loser.transition(peep_state.PeepState.DEAD)


def join_forces(peep_a, peep_b) -> bool:
	"""Merge two same-faction peeps. Returns True if merged.

	Per asm/PEEPS_REPORT.md section 4.4: same-faction peeps that meet can
	combine life into the stronger one (which carries the merged life, capped
	at settings.PEEP_LIFE_MAX).
	"""
	if peep_a.faction_id != peep_b.faction_id:
		return False
	if peep_a.faction_id == faction.Faction.NEUTRAL:
		return False
	if peep_a is peep_b:
		return False
	if peep_a.state == peep_state.PeepState.DEAD or peep_b.state == peep_state.PeepState.DEAD:
		return False
	winner, loser = _select_merge_winner_and_loser(peep_a, peep_b)
	winner.life = min(settings.PEEP_LIFE_MAX, winner.life + loser.life)
	_retire_merged_loser(loser)
	return True
