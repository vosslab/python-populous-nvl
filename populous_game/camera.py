import pygame
import populous_game.settings as settings

class Camera:
	def __init__(self) -> None:
		"""Initialize camera position at center of grid."""
		self.move_timer = 0.0
		# Position logique de la caméra en coordonnées de grille (r, c)
		# Correspond au coin supérieur de la zone NxN affichée (N = VISIBLE_TILE_COUNT)
		half = settings.VISIBLE_TILE_COUNT // 2
		self.r = float(settings.GRID_HEIGHT // 2 - half)
		self.c = float(settings.GRID_WIDTH // 2 - half)

	def move_direction(self, direction: str) -> None:
		"""Move camera in the specified direction string."""
		# Déplace la caméra selon la direction
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
		"""Move camera by the given delta row and delta column."""
		self.r += float(dr)
		self.c += float(dc)
		# Limites strictes basées sur la grille; la viewport NxN ne sort jamais du grid
		n = settings.VISIBLE_TILE_COUNT
		max_r = float(settings.GRID_HEIGHT - n)
		max_c = float(settings.GRID_WIDTH - n)
		self.r = max(0.0, min(self.r, max_r))
		self.c = max(0.0, min(self.c, max_c))

	def center_on(self, r, c) -> None:
		"""Center the NxN viewport on the given grid coordinate.

		N is settings.VISIBLE_TILE_COUNT. The viewport top-left moves to
		(r - N//2, c - N//2), clamped to legal bounds. Used by the
		_find_* buttons to jump the camera onto a battle, papal magnet,
		or knight.
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

		# Mapping touches -> direction
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
			self.move_timer = 0.15  # Délai entre deux déplacements (en secondes)
