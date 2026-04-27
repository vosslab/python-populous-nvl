import pygame
import populous_game.settings as settings


# The camera operates entirely in WORLD coordinates (rows / columns).
# (self.r, self.c) is the top-left grid corner of the NxN visible
# diamond, where N = settings.VISIBLE_TILE_COUNT. The camera clamp
# keeps that NxN diamond inside the grid: r in [0, GRID_HEIGHT - N]
# and c in [0, GRID_WIDTH - N]. The camera never reads canvas pixels
# or HUD_SCALE.
#
# Map-well placement (where the NxN diamond lands on the canvas, the
# screen offset, and the canvas resolution) is the layout's job, not
# the camera's. The camera asks "which world tiles are visible?" and
# the ViewportTransform / Layout answers "render those tiles into
# this canvas region." That separation is why this module does not
# need a transform reference -- world bounds and screen bounds are
# decoupled by design.
class Camera:
	def __init__(self) -> None:
		"""Initialize camera position at center of grid."""
		self.move_timer = 0.0
		# Camera position in world (grid) coordinates (r, c).
		# Corresponds to the top-left corner of the NxN visible
		# diamond (N = VISIBLE_TILE_COUNT).
		half = settings.VISIBLE_TILE_COUNT // 2
		self.r = float(settings.GRID_HEIGHT // 2 - half)
		self.c = float(settings.GRID_WIDTH // 2 - half)

	def move_direction(self, direction: str) -> None:
		"""Move camera in the specified direction string."""
		# Translate cardinal/diagonal direction names to (dr, dc) deltas.
		directions = {
			'NE':  (-1.0, 0.0),
			'E': (-1.0, 1.0),
			'SE':  (0.0, 1.0),
			'S': (1.0, 1.0),
			'SW':  (1.0, 0.0),
			'W': (1.0, -1.0),
			'NW':  (0.0, -1.0),
			'N': (-1.0, -1.0),
		}
		if direction in directions:
			dr, dc = directions[direction]
			self.move(dr, dc)

	def move(self, dr: float, dc: float) -> None:
		"""Move camera by the given delta row and delta column.

		Clamps the visible NxN tile diamond inside the grid in world
		(row, col) space. Bounds: 0 <= r <= GRID_HEIGHT - N, and
		0 <= c <= GRID_WIDTH - N, where N = VISIBLE_TILE_COUNT. Screen
		bounds and map-well placement are not the camera's concern --
		the layout / ViewportTransform handles those.
		"""
		self.r += float(dr)
		self.c += float(dc)
		n = settings.VISIBLE_TILE_COUNT
		max_r = float(settings.GRID_HEIGHT - n)
		max_c = float(settings.GRID_WIDTH - n)
		self.r = max(0.0, min(self.r, max_r))
		self.c = max(0.0, min(self.c, max_c))

	def center_on(self, r, c) -> None:
		"""Center the NxN viewport on the given grid coordinate.

		N is settings.VISIBLE_TILE_COUNT. The viewport top-left moves to
		(r - N//2, c - N//2), clamped to legal world bounds (same
		[0, GRID - N] window as move()). Used by the _find_* buttons
		to jump the camera onto a battle, papal magnet, or knight.
		"""
		n = settings.VISIBLE_TILE_COUNT
		half = float(n // 2)
		max_r = float(settings.GRID_HEIGHT - n)
		max_c = float(settings.GRID_WIDTH - n)
		self.r = max(0.0, min(float(r) - half, max_r))
		self.c = max(0.0, min(float(c) - half, max_c))

	def update(self, dt: float) -> None:
		"""Update camera position based on keyboard input."""
		keys = pygame.key.get_pressed()
		self.move_timer -= dt
		if self.move_timer > 0:
			return

		# Map keys -> direction string. Uses arrow keys and WASD as
		# equivalent inputs; diagonals require both axes pressed.
		direction = None
		if keys[pygame.K_LEFT] or keys[pygame.K_a]:
			if keys[pygame.K_UP] or keys[pygame.K_w]:
				direction = 'NW'
			elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
				direction = 'SW'
			else:
				direction = 'W'
		elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
			if keys[pygame.K_UP] or keys[pygame.K_w]:
				direction = 'NE'
			elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
				direction = 'SE'
			else:
				direction = 'E'
		elif keys[pygame.K_UP] or keys[pygame.K_w]:
			direction = 'N'
		elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
			direction = 'S'

		if direction:
			self.move_direction(direction)
			# Cooldown between key-driven camera steps (seconds).
			self.move_timer = 0.15
