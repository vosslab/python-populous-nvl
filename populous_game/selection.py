"""Selection state and find-target helpers (camera locators).

The find-target helpers are pure functions: each takes the game object
and returns a (row, col) coordinate or None. They are used by the
_find_battle, _find_papal, _find_knight UI buttons to jump the camera
to the relevant point of interest.
"""

import populous_game.faction as faction
import populous_game.peep_state as peep_state


class Selection:
	"""Manages the currently selected/viewed entity (peep or house)."""

	def __init__(self):
		"""Initialize with no selection."""
		self.who = None
		self.kind = None

	def set(self, entity, kind: str) -> None:
		"""Set the selected entity and kind ('peep' or 'house')."""
		self.who = entity
		self.kind = kind

	def clear(self) -> None:
		"""Clear the selection."""
		self.who = None
		self.kind = None

	def is_active(self) -> bool:
		"""Return True if something is selected."""
		return self.who is not None and self.kind is not None


#============================================
# Find-target helpers used by the _find_* UI buttons.
#============================================


def find_next_battle(game, after_index: int = -1):
	"""Return (r, c) of the next FIGHT-state peep after the given index.

	Cycles through the peeps list starting at after_index + 1; wraps
	around. Returns (peep_index, r, c) so the caller can remember its
	cursor and step to the following battle on the next click. Returns
	None when no peep is in a FIGHT-class state.
	"""
	count = len(game.peeps)
	if count == 0:
		return None
	for offset in range(1, count + 1):
		idx = (after_index + offset) % count
		p = game.peeps[idx]
		if p.dead or p.state == peep_state.PeepState.DEAD:
			continue
		if p.state == peep_state.PeepState.FIGHT:
			return (idx, int(p.y), int(p.x))
	return None


def find_papal_target(game, prefer_leader: bool = True):
	"""Return (r, c) of the papal target.

	When prefer_leader is True (left-click), jumps to the player leader
	if one exists, else falls back to the papal magnet position. When
	prefer_leader is False (right-click), jumps directly to the magnet.
	The current code does not track a distinct "leader" attribute, so
	prefer_leader currently always falls through to the magnet; this
	keeps the call signature stable for when leader-tracking lands.
	"""
	if prefer_leader:
		# Hook for future leader-tracking; falls through to magnet today.
		pass
	return game.mode_manager.papal_position


def find_next_knight(game, after_index: int = -1):
	"""Return (peep_index, r, c) for the next player knight after the cursor.

	Cycles through player peeps with weapon_type == 'knight'. Returns
	None when no knight exists.
	"""
	count = len(game.peeps)
	if count == 0:
		return None
	for offset in range(1, count + 1):
		idx = (after_index + offset) % count
		p = game.peeps[idx]
		if p.dead or p.state == peep_state.PeepState.DEAD:
			continue
		if p.faction_id != faction.Faction.PLAYER:
			continue
		if getattr(p, 'weapon_type', None) == 'knight':
			return (idx, int(p.y), int(p.x))
	return None


def find_nearest_enemy(game, from_r: int, from_c: int):
	"""Return (r, c) of the nearest non-PLAYER, alive peep to (from_r, from_c).

	Used by _go_fight bulk-march. Returns None when no enemies exist.
	"""
	best = None
	best_d2 = None
	for p in game.peeps:
		if p.dead or p.state == peep_state.PeepState.DEAD:
			continue
		if p.faction_id == faction.Faction.PLAYER:
			continue
		dr = p.y - from_r
		dc = p.x - from_c
		d2 = dr * dr + dc * dc
		if best_d2 is None or d2 < best_d2:
			best_d2 = d2
			best = (int(p.y), int(p.x))
	return best
