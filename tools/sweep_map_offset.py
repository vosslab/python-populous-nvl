#!/usr/bin/env python3
"""Sweep MAP_OFFSET_X / MAP_OFFSET_Y combos and snapshot each.

Saves one PNG per (x, y) combination to tools/screenshots/offset_sweep/
so you can flip through them and pick the best terrain placement.

Each shot is taken from a fresh Game so module-level settings overrides
take effect cleanly.

Usage:
    ./tools/sweep_map_offset.py
    ./tools/sweep_map_offset.py --x 140 160 180 200 --y 50 65 80 95
"""

# Standard Library
import os
import sys
import argparse
import importlib

# Force headless before any pygame import
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

# PIP3 modules
import pygame

# local repo modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#============================================

WARMUP_TICKS: int = 30
DT: float = 1.0 / 60.0

#============================================

def parse_args():
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(description="Sweep MAP_OFFSET_X / MAP_OFFSET_Y values and snapshot each.")
	parser.add_argument(
		'--x', dest='x_values', type=int, nargs='+',
		default=[140, 160, 180, 200, 220],
		help='MAP_OFFSET_X values to test.'
	)
	parser.add_argument(
		'--y', dest='y_values', type=int, nargs='+',
		default=[50, 65, 80, 95, 110],
		help='MAP_OFFSET_Y values to test.'
	)
	parser.add_argument(
		'-o', '--output-dir', dest='output_dir', default=None,
		help='Output directory (default: tools/screenshots/offset_sweep/).'
	)
	args = parser.parse_args()
	return args

#============================================

def default_output_dir() -> str:
	"""Default output directory for the sweep."""
	repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	out_dir = os.path.join(repo_root, 'tools', 'screenshots', 'offset_sweep')
	os.makedirs(out_dir, exist_ok=True)
	return out_dir

#============================================

def step_game(game) -> None:
	"""One iteration of the real game loop, headless."""
	game.events()
	if game.app_state.is_playing() and not game.app_state.is_simulation_paused():
		scaled_dt = DT * game.app_state.time_scale
		game.update(scaled_dt)
	game.draw()

#============================================

def snapshot_with_offset(map_x: int, map_y: int, out_path: str) -> None:
	"""Override MAP_OFFSET_X/Y in settings, boot a Game, snapshot it.

	Re-imports populous_game.game on each call so the patched settings
	values are observed by every module that read them at import time.
	"""
	# Patch settings module first
	import populous_game.settings as settings
	settings.MAP_OFFSET_X = map_x
	settings.MAP_OFFSET_Y = map_y

	# Re-import game module (and its dependencies) so they see the new
	# offsets if they captured them at import time
	for mod_name in list(sys.modules.keys()):
		if mod_name.startswith('populous_game.'):
			# Skip settings (already patched) so we don't re-evaluate it
			if mod_name == 'populous_game.settings':
				continue
			# Drop the cached module so the next import re-evaluates it
			del sys.modules[mod_name]

	# Reset pygame state between runs
	pygame.quit()
	pygame.init()
	pygame.display.set_mode((960, 600))

	# Fresh import of game with new settings
	game_module = importlib.import_module('populous_game.game')
	game = game_module.Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(3)
	game.spawn_initial_peeps(8)
	game.spawn_enemy_peeps(8)
	for _ in range(WARMUP_TICKS):
		step_game(game)

	# Annotate the offsets directly onto the surface so the saved PNG
	# is self-identifying when flipping through them later.
	font = pygame.font.SysFont(None, 14)
	label = font.render(f'X={map_x}  Y={map_y}', True, (255, 255, 0))
	bg = pygame.Surface((label.get_width() + 4, label.get_height() + 2), pygame.SRCALPHA)
	bg.fill((0, 0, 0, 180))
	game.internal_surface.blit(bg, (2, 2))
	game.internal_surface.blit(label, (4, 3))

	pygame.image.save(game.internal_surface, out_path)
	w, h = game.internal_surface.get_size()
	print(f'wrote {out_path}  {w}x{h}  offset=({map_x},{map_y})')

#============================================

def main() -> None:
	"""Run the sweep."""
	args = parse_args()
	out_dir = args.output_dir if args.output_dir else default_output_dir()
	os.makedirs(out_dir, exist_ok=True)

	for x in args.x_values:
		for y in args.y_values:
			out_path = os.path.join(out_dir, f'offset_x{x:03d}_y{y:03d}.png')
			snapshot_with_offset(x, y, out_path)

#============================================

if __name__ == '__main__':
	main()
