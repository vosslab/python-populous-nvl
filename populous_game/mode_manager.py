"""Mode manager for papal, shield, and D-Pad continuous scroll states."""

import time
import populous_game.settings as settings
import populous_game.faction as faction


class ModeManager:
	"""Manages game modes: papal placement, shield coat-of-arms, and D-Pad scroll."""

	def __init__(self):
		"""Initialize mode state."""
		# Papal mode state
		self.papal_mode = False
		self.papal_position = (settings.GRID_HEIGHT // 2, settings.GRID_WIDTH // 2)
		self.faction_magnets = {
			faction.Faction.PLAYER: self.papal_position,
			faction.Faction.ENEMY: None,
		}

		# Shield mode state
		self.shield_mode = False
		self.shield_target = None

		# Pending power mode (power waiting for target click)
		self.pending_power = None  # 'volcano', 'flood', 'quake', 'swamp', or None

		# Continuous D-Pad scroll state
		self.dpad_held_direction = None
		self.dpad_held_timer = 0.0
		self.dpad_repeat_delay = settings.DPAD_REPEAT_DELAY  # seconds between scrolls
		self.dpad_last_flash_time = 0.0  # timestamp of last scroll

	def toggle_papal(self) -> None:
		"""Toggle papal mode on/off."""
		self.papal_mode = not self.papal_mode

	def set_papal_position(self, r: int, c: int) -> None:
		"""Set papal position and turn off papal mode."""
		self.set_faction_magnet(
			faction.Faction.PLAYER,
			max(r - 1, 0),
			max(c - 1, 0),
		)
		self.papal_mode = False

	def set_faction_magnet(self, faction_id: int, r: int, c: int) -> None:
		"""Set the ASM-style magnet table slot for a faction."""
		coord = (max(int(r), 0), max(int(c), 0))
		self.faction_magnets[int(faction_id)] = coord
		if int(faction_id) == faction.Faction.PLAYER:
			self.papal_position = coord

	def clear_magnets(self) -> None:
		"""Clear all faction magnet positions."""
		for faction_id in list(self.faction_magnets):
			self.faction_magnets[faction_id] = None
		self.papal_position = None

	def toggle_shield(self) -> None:
		"""Toggle shield mode on/off."""
		self.shield_mode = not self.shield_mode

	def clear_modes(self) -> None:
		"""Clear all special modes."""
		self.papal_mode = False
		self.shield_mode = False

	def update(self, dt: float) -> None:
		"""Update mode state (handles D-Pad continuous scroll timer)."""
		if self.dpad_held_direction:
			self.dpad_held_timer -= dt
			if self.dpad_held_timer <= 0.0:
				# Timer expired; caller should move camera
				self.dpad_held_timer = self.dpad_repeat_delay
				self.dpad_last_flash_time = time.time()
