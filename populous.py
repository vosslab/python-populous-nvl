#!/usr/bin/env python3
"""Populous launcher stub. Real code lives in populous_game.

CLI argparse handling is delegated to populous_game.cli so the launcher
stub stays minimal; see populous_game/cli.py for the flag definitions
and docs/USAGE.md for usage examples.
"""

# Standard Library
import pygame

# local repo modules
import populous_game.cli as cli
import populous_game.game as game_module
import populous_game.settings as settings


#============================================
def main() -> None:
	"""Run the game with optional CLI overrides."""
	args = cli.parse_args()
	# Mutate settings BEFORE Game() is constructed so the Game reads
	# the chosen INTERNAL_WIDTH/HEIGHT, HUD_SCALE, VISIBLE_TILE_COUNT.
	cli.apply_args_to_settings(args)

	# Resolve window scale: --window-scale wins; --fit-screen otherwise
	# computes the best fit; default None falls back to legacy 3.
	pygame.init()
	display_scale = args.window_scale
	if display_scale is None and args.fit_screen:
		display_scale = cli.resolve_fit_screen(
			settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT,
		)

	game = game_module.Game(
		display_scale=display_scale,
		seed=args.seed,
		debug_layout=args.debug_layout,
		map_profile=args.map_profile,
	)
	# Headless capture path: render one frame to disk and exit.
	if args.screenshot is not None:
		cli.capture_screenshot_and_exit(game, args.screenshot)
	game.run()
#============================================


if __name__ == '__main__':
	main()
