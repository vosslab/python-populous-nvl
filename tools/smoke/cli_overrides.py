#!/usr/bin/env python3
"""End-to-end smoke for the launcher CLI overrides.

Mutates settings via cli.apply_args_to_settings, boots a Game, and
confirms the internal surface size matches the expected preset. Restores
the original preset in finally so subsequent runs still pick up the
default classic preset.
"""

# Standard Library
import os
import sys
import argparse
import subprocess

# Add repo root to sys.path so we can import populous_game.
_REPO_ROOT = subprocess.check_output(
	['git', 'rev-parse', '--show-toplevel'],
	text=True,
).strip()
if _REPO_ROOT not in sys.path:
	sys.path.insert(0, _REPO_ROOT)

# Headless pygame environment.
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import populous_game.cli as cli
import populous_game.settings as settings
import populous_game.game as game_module


def _snapshot_preset() -> tuple:
	"""Capture the four mirror constants for restoration."""
	return (
		settings.ACTIVE_CANVAS_PRESET,
		settings.INTERNAL_WIDTH,
		settings.INTERNAL_HEIGHT,
		settings.HUD_SCALE,
		settings.VISIBLE_TILE_COUNT,
	)


def _restore_preset(snap: tuple) -> None:
	"""Restore the four mirror constants from snapshot."""
	settings.ACTIVE_CANVAS_PRESET = snap[0]
	settings.INTERNAL_WIDTH = snap[1]
	settings.INTERNAL_HEIGHT = snap[2]
	settings.HUD_SCALE = snap[3]
	settings.VISIBLE_TILE_COUNT = snap[4]


def _make_args(**overrides) -> argparse.Namespace:
	"""Build a default-populated Namespace with optional overrides."""
	defaults = dict(
		preset=None, size=None, window_scale=None, fit_screen=False,
		visible_tiles=None, seed=None, screenshot=None,
	)
	defaults.update(overrides)
	return argparse.Namespace(**defaults)


def check_remaster_internal_surface() -> None:
	"""--preset remaster boots a Game whose internal surface is 640x400."""
	snap = _snapshot_preset()
	try:
		cli.apply_args_to_settings(_make_args(preset='remaster'))
		game = game_module.Game(display_scale=1, seed=12345)
		size = game.internal_surface.get_size()
		if size != (640, 400):
			print(f'FAIL remaster internal surface: expected (640, 400), got {size}')
			sys.exit(1)
		print('PASS remaster internal surface = (640, 400)')
	finally:
		_restore_preset(snap)


def check_classic_default_unchanged() -> None:
	"""No CLI overrides => classic preset, 320x200 internal surface."""
	snap = _snapshot_preset()
	try:
		game = game_module.Game(display_scale=1, seed=12345)
		size = game.internal_surface.get_size()
		if size != (320, 200):
			print(f'FAIL classic default surface: expected (320, 200), got {size}')
			sys.exit(1)
		print('PASS classic default internal surface = (320, 200)')
	finally:
		_restore_preset(snap)


def main() -> None:
	"""Run all CLI override smoke checks."""
	check_classic_default_unchanged()
	check_remaster_internal_surface()
	print('all CLI override checks passed')


if __name__ == '__main__':
	main()
