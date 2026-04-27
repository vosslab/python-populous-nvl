"""Peep behavior states (rules-faithful to original Amiga, per asm/PEEPS_REPORT.md)."""

#============================================
# Peep state constants (per asm/PEEPS_REPORT.md)
#============================================

class PeepState:
	IDLE: str = 'idle'
	WANDER: str = 'wander'
	SEEK_FLAT: str = 'seek_flat'
	BUILD: str = 'build'
	GATHER: str = 'gather'
	JOIN_FORCES: str = 'join_forces'
	MARCH: str = 'march'
	FIGHT: str = 'fight'
	DROWN: str = 'drown'
	DEAD: str = 'dead'

	ALL: tuple = (
		IDLE, WANDER, SEEK_FLAT, BUILD, GATHER,
		JOIN_FORCES, MARCH, FIGHT, DROWN, DEAD,
	)
