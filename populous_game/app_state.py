"""Game application state machine."""


class AppState:
	"""Game application state machine.

	Manages high-level game states: menu, playing, paused, and game-over.
	Enforces allowed state transitions and tracks win/lose results.
	"""

	# State constants
	MENU = 'menu'
	PLAYING = 'playing'
	PAUSED = 'paused'
	GAMEOVER = 'gameover'

	def __init__(self):
		"""Initialize app state to MENU."""
		self.current = self.MENU
		self.gameover_result = None  # 'win' or 'lose' when in GAMEOVER state

		# Transition matrix: from_state -> set of allowed to_states
		self._allowed_transitions = {
			self.MENU: {self.PLAYING},
			self.PLAYING: {self.PAUSED, self.GAMEOVER},
			self.PAUSED: {self.PLAYING, self.MENU},
			self.GAMEOVER: {self.MENU},
		}

		# Confirm dialog state (pauses simulation while open)
		self.confirm_dialog: dict | None = None  # {'message': str, 'on_confirm': callable, 'on_cancel': callable | None}

		# Time scaling for fast-forward (1.0 = normal, 4.0 = 4x speed)
		self.time_scale: float = 1.0

	def transition_to(self, new_state: str) -> None:
		"""Transition to a new state if allowed.

		Args:
			new_state: The target state (one of MENU, PLAYING, PAUSED, GAMEOVER).

		Raises:
			ValueError: If the transition is not allowed from the current state.
		"""
		if new_state not in self._allowed_transitions.get(self.current, set()):
			raise ValueError(
				f"Transition from {self.current} to {new_state} not allowed"
			)
		self.current = new_state

	def is_menu(self) -> bool:
		"""Return True if in MENU state."""
		return self.current == self.MENU

	def is_playing(self) -> bool:
		"""Return True if in PLAYING state."""
		return self.current == self.PLAYING

	def is_paused(self) -> bool:
		"""Return True if in PAUSED state."""
		return self.current == self.PAUSED

	def is_gameover(self) -> bool:
		"""Return True if in GAMEOVER state."""
		return self.current == self.GAMEOVER

	def request_confirm(self, message: str, on_confirm, on_cancel=None) -> None:
		"""Request a confirmation dialog. Pauses simulation while open.

		Args:
			message: The confirmation prompt to display.
			on_confirm: Callable to invoke if user confirms (Y/Enter).
			on_cancel: Callable to invoke if user cancels (N/Escape), or None.
		"""
		self.confirm_dialog = {
			'message': message,
			'on_confirm': on_confirm,
			'on_cancel': on_cancel,
		}

	def confirm(self) -> None:
		"""User confirmed the dialog. Call on_confirm and clear."""
		if self.confirm_dialog:
			on_confirm = self.confirm_dialog['on_confirm']
			self.confirm_dialog = None
			if on_confirm:
				on_confirm()

	def cancel(self) -> None:
		"""User cancelled the dialog. Call on_cancel (if set) and clear."""
		if self.confirm_dialog:
			on_cancel = self.confirm_dialog['on_cancel']
			self.confirm_dialog = None
			if on_cancel:
				on_cancel()

	def has_confirm_dialog(self) -> bool:
		"""Return True if a confirm dialog is currently open."""
		return self.confirm_dialog is not None

	def is_simulation_paused(self) -> bool:
		"""Return True if simulation is paused (either PAUSED state or confirm dialog open)."""
		return self.is_paused() or self.has_confirm_dialog()
#============================================
