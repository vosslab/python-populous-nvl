"""Selection state for the currently viewed entity (peep or house)."""


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
