"""Power dispatch with rules-faithful effects (per asm/CONSTRUCTION_REPORT.md)
and modern UX layer (cooldowns, mana, AOE preview).

Each power is a callable that takes (game, target_position) and returns a
PowerResult with mana spent, cooldown applied, and a list of affected cells.
"""

import populous_game.settings as settings


class PowerResult:
	"""Outcome of a power activation."""

	def __init__(self, success: bool, mana_spent: float = 0.0,
		cooldown: float = 0.0, affected_cells: list = None,
		message: str = ''):
		self.success = success
		self.mana_spent = mana_spent
		self.cooldown = cooldown
		self.affected_cells = affected_cells or []
		self.message = message


class PowerSpec:
	"""Static specification for a power: cost, cooldown, AOE radius, sfx."""

	def __init__(self, name: str, mana_cost: float, cooldown: float,
		aoe_radius: int, sfx: str, requires_confirm: bool = False):
		self.name = name
		self.mana_cost = mana_cost
		self.cooldown = cooldown
		self.aoe_radius = aoe_radius
		self.sfx = sfx
		self.requires_confirm = requires_confirm


# Per asm/CONSTRUCTION_REPORT.md (mana costs are interim pending precise asm
# citation; see settings.POWER_*_COST). Cooldowns are modern UX defaults.

POWERS: dict = {
	'papal': PowerSpec('papal', settings.POWER_PAPAL_COST,
		settings.POWER_PAPAL_COOLDOWN, 0, 'papal_place'),
	'volcano': PowerSpec('volcano', settings.POWER_VOLCANO_COST,
		settings.POWER_VOLCANO_COOLDOWN, settings.POWER_VOLCANO_RADIUS,
		'building_destroy', requires_confirm=True),
	'flood': PowerSpec('flood', settings.POWER_FLOOD_COST,
		settings.POWER_FLOOD_COOLDOWN, settings.POWER_FLOOD_RADIUS,
		'peep_drown', requires_confirm=True),
	'quake': PowerSpec('quake', settings.POWER_QUAKE_COST,
		settings.POWER_QUAKE_COOLDOWN, settings.POWER_QUAKE_RADIUS,
		'building_destroy'),
	'swamp': PowerSpec('swamp', settings.POWER_SWAMP_COST,
		settings.POWER_SWAMP_COOLDOWN, settings.POWER_SWAMP_RADIUS,
		'terrain_lower'),
	'knight': PowerSpec('knight', settings.POWER_KNIGHT_COST,
		settings.POWER_KNIGHT_COOLDOWN, 0, 'peep_spawn'),
}


class PowerManager:
	"""Tracks per-power cooldowns and dispatches activation."""

	def __init__(self, game):
		self.game = game
		self.cooldowns: dict = {name: 0.0 for name in POWERS}

	def update(self, dt: float) -> None:
		"""Decrement all active cooldowns."""
		for name in self.cooldowns:
			if self.cooldowns[name] > 0.0:
				self.cooldowns[name] = max(0.0, self.cooldowns[name] - dt)

	def can_activate(self, name: str, mana: float) -> bool:
		"""Check if a power can be activated (not on cooldown and sufficient mana)."""
		if name not in POWERS:
			return False
		spec = POWERS[name]
		if self.cooldowns[name] > 0.0:
			return False
		if mana < spec.mana_cost:
			return False
		return True

	def activate(self, name: str, target: tuple) -> PowerResult:
		"""Activate a power. target is (r, c) grid coords (or None for global)."""
		if name not in POWERS:
			return PowerResult(False, message=f'Unknown power: {name}')
		spec = POWERS[name]
		mana = self.game.mana_pool.get_mana(self.game.player_faction_id())
		if not self.can_activate(name, mana):
			return PowerResult(False, message=f'Cannot activate {name}: cooldown or insufficient mana')
		# Dispatch
		impl = POWER_IMPLS[name]
		result = impl(self.game, target, spec)
		if result.success:
			self.game.mana_pool.spend(self.game.player_faction_id(), spec.mana_cost)
			self.cooldowns[name] = spec.cooldown
			self.game.audio_manager.play_sfx(spec.sfx)
		return result


# --- Per-power implementations ---

def _power_papal(game, target, spec) -> PowerResult:
	"""Place the papal marker. target = (r, c)."""
	import populous_game.faction as faction
	if target is None:
		return PowerResult(False, message='papal requires a target')
	r, c = target
	game.mode_manager.set_faction_magnet(faction.Faction.PLAYER, r, c)
	return PowerResult(True, mana_spent=spec.mana_cost,
		cooldown=spec.cooldown, affected_cells=[(r, c)])


def _power_volcano(game, target, spec) -> PowerResult:
	"""Raise terrain in a circle around target; destroys houses in the radius."""
	if target is None:
		return PowerResult(False, message='volcano requires a target')
	r, c = target
	affected = _cells_in_radius(r, c, spec.aoe_radius)
	for (rr, cc) in affected:
		# Raise corners by 2 each (simulates volcano cone). Bound check inside game_map.
		game.game_map.raise_corner(rr, cc)
		game.game_map.raise_corner(rr, cc)
	# Destroy any house in the AOE.
	for h in list(game.game_map.houses):
		if (h.r, h.c) in affected and not h.destroyed:
			h.destroyed = True
			h.life = 0.0
	return PowerResult(True, mana_spent=spec.mana_cost,
		cooldown=spec.cooldown, affected_cells=affected)


def _power_flood(game, target, spec) -> PowerResult:
	"""Lower terrain in a circle around target; turns cells to water."""
	if target is None:
		return PowerResult(False, message='flood requires a target')
	r, c = target
	affected = _cells_in_radius(r, c, spec.aoe_radius)
	for (rr, cc) in affected:
		game.game_map.lower_corner(rr, cc)
		game.game_map.lower_corner(rr, cc)
	return PowerResult(True, mana_spent=spec.mana_cost,
		cooldown=spec.cooldown, affected_cells=affected)


def _power_quake(game, target, spec) -> PowerResult:
	"""Shake terrain in a circle: random alternating raise/lower of corners."""
	import random as _random
	if target is None:
		return PowerResult(False, message='quake requires a target')
	r, c = target
	affected = _cells_in_radius(r, c, spec.aoe_radius)
	# Use the game's deterministic RNG if available; else module random.
	rng = getattr(game, 'sim_rng', _random)
	for (rr, cc) in affected:
		if rng.random() < 0.5:
			game.game_map.raise_corner(rr, cc)
		else:
			game.game_map.lower_corner(rr, cc)
	return PowerResult(True, mana_spent=spec.mana_cost,
		cooldown=spec.cooldown, affected_cells=affected)


def _power_swamp(game, target, spec) -> PowerResult:
	"""Place a swamp tile (lowered terrain) at target.

	Per the original Amiga: swamps drown peeps that walk on them. v1
	implementation: just lower the corners; the existing drowning logic
	handles peeps that step into water.
	"""
	if target is None:
		return PowerResult(False, message='swamp requires a target')
	r, c = target
	affected = _cells_in_radius(r, c, spec.aoe_radius)
	for (rr, cc) in affected:
		game.game_map.lower_corner(rr, cc)
	return PowerResult(True, mana_spent=spec.mana_cost,
		cooldown=spec.cooldown, affected_cells=affected)


def _power_knight(game, target, spec) -> PowerResult:
	"""Convert one of the player's peeps into a Knight (boosted life + state)."""
	import populous_game.faction as faction
	import populous_game.peep_state as peep_state
	if not game.app_state.is_playing() or game.app_state.is_simulation_paused():
		return PowerResult(False, message='Knight requires active play')
	# ASM indexes the current peep target directly. Prefer the selected peep
	# when the UI has one; otherwise fall back to the current live player peep
	# because the existing hotkey/button path does not supply an explicit peep id.
	knight = None
	selected = getattr(game.selection, 'who', None)
	if selected is not None and getattr(game.selection, 'kind', None) == 'peep':
		if selected in game.peeps and selected.faction_id == faction.Faction.PLAYER:
			if selected.state != peep_state.PeepState.DEAD and getattr(selected, 'weapon_type', None) != 'knight':
				knight = selected
	if knight is None:
		candidates = [p for p in game.peeps
			if p.faction_id == faction.Faction.PLAYER
			and p.state != peep_state.PeepState.DEAD
			and getattr(p, 'weapon_type', None) != 'knight']
		if not candidates:
			return PowerResult(False, message='No player peep to knight')
		knight = max(candidates, key=lambda p: p.life)
	knight.life = min(settings.PEEP_LIFE_MAX, knight.life * 2.0)
	knight.weapon_type = 'knight'
	# Preserve a visible target marker for the promoted unit when the
	# current session already tracks one, which is the closest available
	# representation of the ASM magnet/leader bookkeeping in this model.
	game.mode_manager.shield_target = knight
	# Let them go on march toward the centroid of enemies.
	enemies = [p for p in game.peeps if p.faction_id == faction.Faction.ENEMY]
	if enemies and peep_state.PeepState.MARCH in knight._ALLOWED_TRANSITIONS.get(knight.state, ()):
		ex = sum(p.x for p in enemies) / len(enemies)
		ey = sum(p.y for p in enemies) / len(enemies)
		knight.target_x, knight.target_y = float(ex), float(ey)
		knight.transition(peep_state.PeepState.MARCH)
	game.selection.set(knight, 'peep')
	game.score += 150
	return PowerResult(True, mana_spent=spec.mana_cost,
		cooldown=spec.cooldown, affected_cells=[(int(knight.y), int(knight.x))])


def _cells_in_radius(cr: int, cc: int, radius: int) -> list:
	"""Return all grid cells within a circular radius of the center cell."""
	cells = []
	for dr in range(-radius, radius + 1):
		for dc in range(-radius, radius + 1):
			if dr * dr + dc * dc <= radius * radius:
				cells.append((cr + dr, cc + dc))
	return cells


POWER_IMPLS: dict = {
	'papal': _power_papal,
	'volcano': _power_volcano,
	'flood': _power_flood,
	'quake': _power_quake,
	'swamp': _power_swamp,
	'knight': _power_knight,
}
