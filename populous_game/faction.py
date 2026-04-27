"""Faction identifiers for entities (peeps, houses)."""


class Faction:
	"""Faction enum-style class with standard identifiers and names."""

	PLAYER: int = 0
	ENEMY: int = 1
	NEUTRAL: int = 2

	NAMES: dict = {
		PLAYER: 'Player',
		ENEMY: 'Enemy',
		NEUTRAL: 'Neutral',
	}

	@classmethod
	def name(cls, fid: int) -> str:
		"""Return the human-readable name for a faction ID."""
		return cls.NAMES[fid]
