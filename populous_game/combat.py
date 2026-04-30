"""Combat resolution (peep-vs-peep, peep-vs-house) per asm/PEEPS_REPORT.md."""

import populous_game.settings as settings
import populous_game.peep_state as peep_state
import populous_game.faction as faction


WEAPON_STRENGTH_ORDER: tuple = (
	'hut',
	'house_small',
	'house_medium',
	'castle_small',
	'castle_medium',
	'castle_large',
	'fortress_small',
	'fortress_medium',
	'fortress_large',
	'castle',
	'knight',
)


def is_enemy(a, b) -> bool:
	"""Two entities are enemies iff they have different non-NEUTRAL factions."""
	if a.faction_id == faction.Faction.NEUTRAL or b.faction_id == faction.Faction.NEUTRAL:
		return False
	return a.faction_id != b.faction_id


def _transition_to_fight_if_allowed(peep_obj) -> None:
	"""Move a peep into FIGHT state only when its matrix allows it."""
	if peep_obj.state == peep_state.PeepState.FIGHT:
		return
	allowed = getattr(peep_obj, "_ALLOWED_TRANSITIONS", {}).get(peep_obj.state, set())
	if peep_state.PeepState.FIGHT in allowed:
		peep_obj.transition(peep_state.PeepState.FIGHT)


def mark_peep_vs_peep_fight(peep_a, peep_b) -> None:
	"""Populate combat metadata used by the shield panel."""
	if not is_enemy(peep_a, peep_b):
		return
	if peep_a.state == peep_state.PeepState.DEAD:
		return
	if peep_b.state == peep_state.PeepState.DEAD:
		return
	peep_a.shield_opponent = peep_b
	peep_b.shield_opponent = peep_a
	_transition_to_fight_if_allowed(peep_a)
	_transition_to_fight_if_allowed(peep_b)


def clear_stale_fight_metadata(peep_obj, live_peeps) -> None:
	"""Clear shield opponent references that no longer point to live combatants."""
	opponent = getattr(peep_obj, 'shield_opponent', None)
	if opponent is None:
		return
	if opponent not in live_peeps:
		peep_obj.shield_opponent = None
		return
	if getattr(opponent, 'dead', False):
		peep_obj.shield_opponent = None
		return
	if getattr(opponent, 'state', None) == peep_state.PeepState.DEAD:
		peep_obj.shield_opponent = None


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
		defender.shield_opponent = None
		if getattr(attacker, 'shield_opponent', None) is defender:
			attacker.shield_opponent = None
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
	loser.shield_opponent = None
	loser.transition(peep_state.PeepState.DEAD)


def _weapon_rank(peep_obj) -> int:
	"""Return the ordered strength rank for a peep weapon type."""
	weapon_type = getattr(peep_obj, 'weapon_type', 'hut')
	if weapon_type in WEAPON_STRENGTH_ORDER:
		return WEAPON_STRENGTH_ORDER.index(weapon_type)
	return 0


def _copy_stronger_weapon(winner, loser) -> None:
	"""Copy the stronger source weapon onto the merge winner."""
	if _weapon_rank(loser) > _weapon_rank(winner):
		winner.weapon_type = getattr(loser, 'weapon_type', 'hut')


def _clear_merge_transients(winner) -> None:
	"""Clear transient ASM shadow fields after a successful merge."""
	winner.remembered_target = None
	winner.terrain_marker = None
	winner.last_move_offset = 0
	winner.town_counter = 0
	winner.shield_opponent = None


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
	_copy_stronger_weapon(winner, loser)
	_clear_merge_transients(winner)
	_retire_merged_loser(loser)
	return True
