"""Pure helpers for ASM peep parity work.

These are shape-compatible helpers for ASM routines documented in
asm/PEEPS_BEHAVIOR.md. They are not source-pinned ports yet; production
peep behavior does not consume them, with the exception of
`cleanup_dead_peep()` which is wired into the death path to clear
shadow bookkeeping. Each helper is referentially transparent on its
inputs so that focused tests can pin behavior and later wiring is
safe.
"""

import collections

import populous_game.pathfinding as pathfinding
import populous_game.settings as settings


# Shadow fields cleared on death. Listed once so the helper and the
# corresponding test stay in lock-step. `faction_magnet` is included
# even though the Peep class does not yet expose it; the helper is
# tolerant of missing attributes so this entry is a forward-compat
# placeholder for the eventual magnet model.
_SHADOW_FIELDS_CLEARED_ON_DEATH: tuple = (
	'linked_peep',
	'remembered_target',
	'terrain_marker',
	'shield_opponent',
	'faction_magnet',
)


def cleanup_dead_peep(peep_obj) -> None:
	"""Clear ASM shadow bookkeeping fields on a dead peep.

	Python compatibility helper, not full ASM `_zero_population`
	parity. The ASM routine also repairs map_who, magnet, and view
	tables; this helper covers only the per-peep shadow fields:
	linked-peep references, remembered targets, terrain markers,
	shield opponents, faction-magnet refs (when present), and the
	last-move offset.

	Tolerant of peep objects that have not initialized every shadow
	field (e.g. test doubles) -- only resets fields that exist.
	"""
	for name in _SHADOW_FIELDS_CLEARED_ON_DEATH:
		if hasattr(peep_obj, name):
			setattr(peep_obj, name, None)
	if hasattr(peep_obj, 'last_move_offset'):
		peep_obj.last_move_offset = 0


# Result tuple returned by check_life_result. Mirrors the four
# observable outputs described in asm/PEEPS_BEHAVIOR.md _check_life:
# score (aggregate suitability), all_of_city (every neighbor tile is a
# town tile), a_flat_block (at least one flat tile is in scope), and
# scanned (the count of in-bounds offsets actually inspected).
CheckLifeResult = collections.namedtuple(
	'CheckLifeResult',
	('score', 'all_of_city', 'a_flat_block', 'scanned'),
)


def check_life_result(game_map, r: int, c: int) -> CheckLifeResult:
	"""Score the neighborhood around tile (r, c) for build suitability.

	Scans the local 3x3 ring (matching the first nine ASM_OFFSET_VECTOR
	entries when those flat-byte deltas are decoded on a 64-wide map).
	For each in-bounds neighbor the helper accumulates a small score
	using the ASM tile-class codes from the shadow_blk layer:

	- ASM_TILE_FLAT contributes +2 and sets a_flat_block.
	- ASM_TILE_TOWN contributes +3 (counted toward all_of_city).
	- ASM_TILE_SLOPE contributes +1.
	- ASM_TILE_ROCK and ASM_TILE_WATER contribute 0.
	- Out-of-bounds offsets are skipped (do not advance scanned).

	The helper is documented as a Python compatibility helper, not
	full ASM `_check_life` parity. It does not mutate game state and
	does not write to any peep record. Round 2 of the parity tranche
	ships this helper without a production consumer; downstream code
	may wire it later once the ASM thresholds are pinned.
	"""
	score = 0
	a_flat_block = False
	scanned = 0
	town_count = 0
	# Examine the immediate 3x3 ring (offsets[0..8]). Each offset is
	# a flat-byte delta on the ASM 64-wide map; for the Python tile
	# grid we approximate the local neighborhood with the standard
	# (-1, 0, +1) row/column ring.
	ring = (
		(0, 0), (-1, 0), (0, 1), (1, 0), (0, -1),
		(-1, -1), (-1, 1), (1, 1), (1, -1),
	)
	for dr, dc in ring:
		nr = r + dr
		nc = c + dc
		code = pathfinding.map_blk_code(game_map, nr, nc)
		if code == settings.ASM_TILE_OUT_OF_BOUNDS:
			continue
		scanned += 1
		if code == settings.ASM_TILE_FLAT:
			score += 2
			a_flat_block = True
		elif code == settings.ASM_TILE_TOWN:
			score += 3
			town_count += 1
		elif code == settings.ASM_TILE_SLOPE:
			score += 1
	all_of_city = scanned > 0 and town_count == scanned
	return CheckLifeResult(
		score=score,
		all_of_city=all_of_city,
		a_flat_block=a_flat_block,
		scanned=scanned,
	)


# Frame thresholds described in asm/PEEPS_BEHAVIOR.md _set_frame.
# These are the counter values at which the ASM routine advances to
# a new animation frame or returns the success flag.
ASM_SET_FRAME_THRESHOLDS: tuple = (0x2A, 0x55, 0x5D, 0x60, 0x65, 0x66)


# Result tuple from advance_set_frame: the new counter value and the
# ASM-style success flag (True when the counter has reached or
# crossed one of the documented thresholds during this advance).
SetFrameResult = collections.namedtuple(
	'SetFrameResult',
	('counter', 'success'),
)


def advance_set_frame(counter: int, step: int = 1) -> SetFrameResult:
	"""Advance an ASM-shape town counter by `step` and return the
	(counter, success_flag) tuple.

	The success flag is True when the increment crosses one of the
	thresholds in ASM_SET_FRAME_THRESHOLDS (0x2A, 0x55, 0x5D, 0x60,
	0x65, 0x66). The counter wraps at the last threshold so repeated
	calls keep returning success at the documented points.

	Pure: does not mutate any peep record. Documented as a Python
	compatibility helper, not full ASM `_set_frame` parity. The
	existing `Peep.town_counter` field is suitable as the input value
	and the helper does not yet drive visible animation.
	"""
	new_counter = counter + step
	# Did this step cross a threshold? Compare the inclusive range
	# (counter, new_counter] against each threshold.
	success = False
	for threshold in ASM_SET_FRAME_THRESHOLDS:
		if counter < threshold <= new_counter:
			success = True
			break
	# Wrap so the helper keeps returning the success flag on
	# subsequent loops past the last threshold.
	final_threshold = ASM_SET_FRAME_THRESHOLDS[-1]
	if new_counter > final_threshold:
		new_counter = new_counter % (final_threshold + 1)
	return SetFrameResult(counter=new_counter, success=success)
