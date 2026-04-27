"""Headless game-runner helpers used by the M3 effect smoke tests.

Tests should never duplicate Game() boot plumbing or hard-code pixel
coordinates. This module exposes a small set of helpers that:

- Boot a Game in the requested state with a deterministic seed.
- Step the real game loop a fixed number of frames.
- Compute coordinate-helper-driven click positions for any UI button
  (no hard-coded 320x200 pixel constants in tests).
- Capture the rendered internal surface to a PNG.

The helpers honor SDL_VIDEODRIVER=dummy and SDL_AUDIODRIVER=dummy set
by tests/conftest.py and only operate in-process; tests do not spawn
subprocesses.
"""

# Standard Library
import os

# Force headless before any pygame import; tests/conftest.py also sets
# this, but importing this module from outside the test runner should
# stay safe.
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

# PIP3 modules
import pygame

# local repo modules
import populous_game.game as game_module
import populous_game.settings as settings


DEFAULT_DT: float = 1.0 / 60.0
DEFAULT_SETTLE_FRAMES: int = 5


def boot_game_for_tests(state: str = 'gameplay',
		players: int = 8, enemies: int = 8,
		seed: int = 12345) -> game_module.Game:
	"""Boot a Game in the requested state with deterministic terrain.

	Args:
		state: 'menu', 'gameplay', or 'gameover'.
		players: Number of player peeps (gameplay only).
		enemies: Number of enemy peeps (gameplay only).
		seed: Heightmap seed for `GameMap.randomize`.
	"""
	game = game_module.Game()
	game.game_map.randomize(seed=seed)
	if state == 'menu':
		return game
	if state == 'gameplay':
		game.app_state.transition_to(game.app_state.PLAYING)
		# Clear pre-existing peeps from boot path before spawning the
		# requested counts so the test sees exactly what it asked for.
		game.peeps.clear()
		game.spawn_initial_peeps(players)
		if enemies > 0:
			game.spawn_enemy_peeps(enemies)
		return game
	if state == 'gameover':
		game.app_state.transition_to(game.app_state.PLAYING)
		game.app_state.transition_to(game.app_state.GAMEOVER)
		game.app_state.gameover_result = 'win'
		return game
	raise ValueError(f'Unknown state: {state}')


def step_frames(game: game_module.Game, n: int = 1, dt: float = DEFAULT_DT) -> None:
	"""Advance the real game loop n frames at fixed dt."""
	for _ in range(n):
		game.events()
		if game.app_state.is_playing() and not game.app_state.is_simulation_paused():
			scaled_dt = dt * game.app_state.time_scale
			game.update(scaled_dt)
		game.draw()


def button_center_px(game: game_module.Game, action: str) -> tuple:
	"""Return the OS-window pixel center of a UI button.

	The center comes from `ui_panel.buttons[action]['c']` (logical
	320x200 coords) scaled by `display_scale * RESOLUTION_SCALE`.
	"""
	bcx, bcy = game.ui_panel.buttons[action]['c']
	scale = game.display_scale * settings.RESOLUTION_SCALE
	return (int(bcx * scale), int(bcy * scale))


def tile_center_px(game: game_module.Game, r: int, c: int) -> tuple:
	"""Return the OS-window pixel center for grid tile (r, c).

	Goes through `game_map.world_to_screen` so the helper stays valid
	when the camera, MAP_OFFSET_X/Y, or canvas preset change.
	"""
	cam_r, cam_c = game.camera.r, game.camera.c
	a = game.game_map.get_corner_altitude(r, c)
	sx, sy = game.game_map.world_to_screen(r, c, a, cam_r, cam_c)
	# world_to_screen returns the corner top point; shift to tile center.
	tx = sx
	ty = sy + settings.TILE_HALF_H
	scale = game.display_scale * settings.RESOLUTION_SCALE
	return (int(tx * scale), int(ty * scale))


def inject_click(game: game_module.Game, action: str, button: int = 1) -> None:
	"""Post a synthetic mouse click on the given UI button action.

	Sends MOUSEBUTTONDOWN followed by MOUSEBUTTONUP. The click is
	consumed by the next `step_frames` call (which polls events).
	"""
	pos = button_center_px(game, action)
	pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=pos))
	pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=button, pos=pos))


def inject_click_at(game: game_module.Game, x: int, y: int, button: int = 1) -> None:
	"""Post a synthetic mouse click at an explicit OS-window pixel."""
	pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=(x, y)))
	pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=button, pos=(x, y)))


def capture(game: game_module.Game, out_path: str) -> None:
	"""Save the rendered internal surface (320x200 logical) to a PNG."""
	# Make sure the parent dir exists; tests use /tmp paths.
	parent = os.path.dirname(out_path)
	if parent:
		os.makedirs(parent, exist_ok=True)
	pygame.image.save(game.internal_surface, out_path)


def surface_pixel_signature(game: game_module.Game) -> int:
	"""Return a stable hash of the rendered internal surface.

	Used by effect tests to assert pre vs post pixel difference without
	loading a file from disk.
	"""
	# Convert the surface to a deterministic byte string.
	raw = pygame.image.tostring(game.internal_surface, 'RGB')
	return hash(raw)
