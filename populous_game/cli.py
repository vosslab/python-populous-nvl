"""Command-line argparse helpers for the populous launcher.

The launcher script (`populous.py`) stays a thin stub. All CLI option
parsing and settings mutation lives here so the test suite can exercise
the helpers in isolation.

CRITICAL CONTRACT: every CLI flag except --seed is presentation-only.
Switching presets, overriding window size, fit-screen, and visible-tile
overrides MUST NOT change simulation outcomes. The simulation digest
parity test (`tests/test_canvas_size_compat.py`) enforces this for
preset switches and applies equally to the argparse-driven path.
"""

# Standard Library
import os
import sys
import argparse

# local repo modules
import populous_game.settings as settings


#============================================
# Argparse setup
#============================================

def parse_args(argv: list | None = None) -> argparse.Namespace:
	"""Parse command-line arguments for the populous launcher.

	Args:
		argv: Optional list of arguments (defaults to sys.argv[1:]).

	Returns:
		argparse.Namespace with all CLI options populated.
	"""
	parser = argparse.ArgumentParser(
		prog='populous',
		description='Populous remaster launcher.',
	)
	# Preset selector. All presets except --seed are presentation-only.
	parser.add_argument(
		'-p', '--preset', dest='preset',
		choices=tuple(settings.CANVAS_PRESETS.keys()),
		default=None,
		help='Named canvas preset (classic, remaster, large). Sets internal '
			'canvas size, HUD scale, and visible tile count from CANVAS_PRESETS.'
	)
	# Direct internal-canvas size override.
	parser.add_argument(
		'-s', '--size', dest='size', default=None,
		help='Override internal canvas size as WIDTHxHEIGHT (e.g. 640x400). '
			'Does NOT change HUD_SCALE or VISIBLE_TILE_COUNT (those track --preset).'
	)
	# OS window scale multiplier.
	parser.add_argument(
		'-w', '--window-scale', dest='window_scale', type=int, default=None,
		help='OS window scale multiplier. Default 3 produces a 960x600 window '
			'at classic preset.'
	)
	# Fit-screen automatic window scaling.
	parser.add_argument(
		'-f', '--fit-screen', dest='fit_screen', action='store_true',
		help='Automatically pick the largest --window-scale that fits the '
			'current monitor (95%% of screen width, 90%% of height).'
	)
	parser.set_defaults(fit_screen=False)
	# Visible-tile override (presentation only; simulation independent).
	parser.add_argument(
		'-t', '--visible-tiles', dest='visible_tiles', type=int, default=None,
		help='Override settings.VISIBLE_TILE_COUNT (presentation only).'
	)
	# Deterministic terrain seed.
	parser.add_argument(
		'-S', '--seed', dest='seed', type=int, default=None,
		help='Deterministic terrain seed for GameMap.randomize. The only '
			'option that affects simulation output.'
	)
	# Headless screenshot capture.
	parser.add_argument(
		'-o', '--screenshot', dest='screenshot', default=None,
		help='Capture the first rendered post-start frame to PATH (PNG) and exit.'
	)
	args = parser.parse_args(argv)
	return args


#============================================
# Size string parsing
#============================================

def parse_size(size_str: str) -> tuple:
	"""Parse a WIDTHxHEIGHT size string into (w, h) ints.

	Raises ValueError for any malformed input.
	"""
	# Empty / wrong shape strings should never reach the settings module.
	if not size_str or 'x' not in size_str:
		raise ValueError(f'--size requires WIDTHxHEIGHT format, got: {size_str!r}')
	parts = size_str.split('x')
	if len(parts) != 2:
		raise ValueError(f'--size requires exactly one x separator, got: {size_str!r}')
	w_str, h_str = parts[0], parts[1]
	# Reject empty halves (e.g. '640x' or 'x400')
	if not w_str or not h_str:
		raise ValueError(f'--size requires non-empty WIDTH and HEIGHT, got: {size_str!r}')
	# Reject non-numeric pieces
	if not w_str.isdigit() or not h_str.isdigit():
		raise ValueError(f'--size requires numeric dimensions, got: {size_str!r}')
	w = int(w_str)
	h = int(h_str)
	return (w, h)


#============================================
# Apply CLI overrides to the settings module
#============================================

def apply_args_to_settings(args: argparse.Namespace) -> None:
	"""Mutate populous_game.settings according to args.

	Only --preset, --size, and --visible-tiles touch the settings module.
	--window-scale, --fit-screen, --seed, and --screenshot are consumed
	at Game construction time, not here.
	"""
	# Preset switch: re-derive the four mirror constants from CANVAS_PRESETS.
	if args.preset is not None:
		preset = settings.CANVAS_PRESETS[args.preset]
		settings.ACTIVE_CANVAS_PRESET = args.preset
		settings.INTERNAL_WIDTH = preset[0]
		settings.INTERNAL_HEIGHT = preset[1]
		settings.HUD_SCALE = preset[2]
		settings.VISIBLE_TILE_COUNT = preset[3]
	# Direct size override; only mutates INTERNAL_WIDTH/HEIGHT, not HUD_SCALE.
	if args.size is not None:
		w, h = parse_size(args.size)
		settings.INTERNAL_WIDTH = w
		settings.INTERNAL_HEIGHT = h
	# Visible-tile override.
	if args.visible_tiles is not None:
		settings.VISIBLE_TILE_COUNT = int(args.visible_tiles)


#============================================
# Fit-screen window-scale math
#============================================

def fit_screen_scale(internal_w: int, internal_h: int,
		screen_w: int, screen_h: int,
		w_margin: float = 0.95, h_margin: float = 0.90) -> int:
	"""Return the largest integer N such that the OS window fits the monitor.

	The window is `internal_w * N` wide and `internal_h * N` tall. Returns
	at least 1 even if the internal canvas itself is bigger than the
	monitor (so the window opens, just clipped).

	Args:
		internal_w: Internal canvas width.
		internal_h: Internal canvas height.
		screen_w: Monitor width in pixels.
		screen_h: Monitor height in pixels.
		w_margin: Fraction of screen_w to fit under (default 0.95).
		h_margin: Fraction of screen_h to fit under (default 0.90).
	"""
	max_w = int(screen_w * w_margin)
	max_h = int(screen_h * h_margin)
	# Step N up while the resulting window still fits both axes.
	scale = 1
	while (internal_w * (scale + 1) <= max_w
			and internal_h * (scale + 1) <= max_h):
		scale += 1
	return scale


def resolve_fit_screen(internal_w: int, internal_h: int) -> int:
	"""Query pygame for the current monitor and return the chosen scale.

	pygame must be initialized before calling this. Prints a one-line
	status message to stdout.
	"""
	# Local import to avoid pulling pygame into argparse-only test paths.
	import pygame
	info = pygame.display.Info()
	screen_w = info.current_w
	screen_h = info.current_h
	scale = fit_screen_scale(internal_w, internal_h, screen_w, screen_h)
	window_w = internal_w * scale
	window_h = internal_h * scale
	msg = (
		f'[fit-screen] internal={internal_w}x{internal_h} '
		f'monitor={screen_w}x{screen_h} '
		f'display_scale={scale} '
		f'window={window_w}x{window_h}'
	)
	print(msg)
	return scale


#============================================
# Screenshot mode
#============================================

def capture_screenshot_and_exit(game, out_path: str) -> None:
	"""Render one frame and save the internal surface to out_path, then exit."""
	# Local import; tools/ already exposes the same primitives.
	import tools.headless_runner as headless_runner
	# Step a single frame so terrain / HUD render before capture.
	headless_runner.step_frames(game, n=1)
	# Ensure parent directory exists for the requested path.
	parent = os.path.dirname(out_path)
	if parent:
		os.makedirs(parent, exist_ok=True)
	headless_runner.capture(game, out_path)
	w, h = game.internal_surface.get_size()
	print(f'wrote {out_path}  {w}x{h}')
	sys.exit(0)
