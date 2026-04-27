#!/usr/bin/env python3
"""Per-button effect screenshots for python-populous.

For each named UI button, boot the game headlessly, perform whatever
follow-up actions that button needs to actually take effect (e.g. click
on a target tile for AOE powers, scroll repeatedly for dpad arrows,
raise terrain multiple times for the terrain button), then snapshot
the resulting frame to tools/screenshots/buttons/button_<action>.png.

Run all buttons:
    ./tools/button_smoke.py

Run one:
    ./tools/button_smoke.py -b _do_quake
    ./tools/button_smoke.py -b N
"""

# Standard Library
import os
import sys
import argparse

# Force headless before any pygame import
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

# PIP3 modules
import pygame

# local repo modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import populous_game.game as game_module
import populous_game.settings as settings

#============================================

# Frame pacing
WARMUP_TICKS: int = 30
DT: float = 1.0 / 60.0

# Pixel inside the viewport that maps to the visible-grid center; powers
# targeted here land in the middle of the rendered terrain plateau.
TARGET_INTERNAL_XY: tuple = (settings.MAP_OFFSET_X, settings.MAP_OFFSET_Y + 50)

# How many times each dpad button gets clicked to make scrolling visible
DPAD_REPEATS: int = 6
# How many times the raise-terrain button is followed by terrain clicks
TERRAIN_PAINT_CLICKS: int = 8

#============================================

def parse_args():
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(description="Per-UI-button effect smoke screenshots.")
	parser.add_argument(
		'-b', '--button', dest='button_action', default=None,
		help='If set, snapshot only this button action (e.g. "_do_quake", "N").'
	)
	parser.add_argument(
		'-o', '--output-dir', dest='output_dir', default=None,
		help='Output directory (default: tools/screenshots/buttons/).'
	)
	args = parser.parse_args()
	return args

#============================================

def boot_to_playing(player_count: int = 8, enemy_count: int = 8) -> game_module.Game:
	"""Construct a Game in PLAYING state with terrain + peeps for visible action."""
	game = game_module.Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.game_map.set_all_altitude(3)
	if player_count > 0:
		game.spawn_initial_peeps(player_count)
	if enemy_count > 0:
		game.spawn_enemy_peeps(enemy_count)
	return game

#============================================

def step_game(game: game_module.Game) -> None:
	"""One iteration of the real game loop, headless."""
	game.events()
	if game.app_state.is_playing() and not game.app_state.is_simulation_paused():
		scaled_dt = DT * game.app_state.time_scale
		game.update(scaled_dt)
	game.draw()

#============================================

def post_click(game: game_module.Game, internal_x: int, internal_y: int, button: int = 1) -> None:
	"""Post a left/right click at internal-canvas coords."""
	mx = internal_x * game.display_scale
	my = internal_y * game.display_scale
	pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=(mx, my)))
	step_game(game)
	pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=button, pos=(mx, my)))
	step_game(game)

#============================================

def click_button(game: game_module.Game, action: str) -> None:
	"""Click a named UI button by its center coords."""
	bcx, bcy = game.ui_panel.buttons[action]['c']
	post_click(game, int(bcx), int(bcy))

#============================================

def click_target_in_viewport(game: game_module.Game, ticks_after: int = 30) -> None:
	"""Click roughly-center of the visible terrain plateau, then settle."""
	x, y = TARGET_INTERNAL_XY
	post_click(game, x, y)
	for _ in range(ticks_after):
		step_game(game)

#============================================
# Per-button effect runners
#============================================

def effect_aoe_power(game: game_module.Game, action: str) -> None:
	"""Volcano / flood / quake / swamp: button -> target -> auto-confirm -> wait.

	The confirm dialog (when configured) opens on the target click, not on
	the button click. We post the target click, then if a dialog is now
	open we send 'Y' to accept, then settle.
	"""
	click_button(game, action)
	# Click the target tile inside the viewport
	x, y = TARGET_INTERNAL_XY
	post_click(game, x, y)
	# Auto-confirm any dialog that opened as a result of the target click
	if game.app_state.has_confirm_dialog():
		pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_y, mod=0, unicode='y'))
		step_game(game)
	# Let the effect play out
	for _ in range(60):
		step_game(game)

def effect_papal(game: game_module.Game, _action: str) -> None:
	"""Papal: select power, then place magnet on a tile."""
	click_button(game, '_do_papal')
	click_target_in_viewport(game, ticks_after=30)

def effect_knight(game: game_module.Game, _action: str) -> None:
	"""Knight: instant cast (no target). Snapshot a few ticks later."""
	click_button(game, '_do_knight')
	for _ in range(30):
		step_game(game)

def effect_shield(game: game_module.Game, _action: str) -> None:
	"""Shield: toggle the info mode and snapshot."""
	click_button(game, '_do_shield')
	for _ in range(15):
		step_game(game)

def effect_terrain(game: game_module.Game, _action: str) -> None:
	"""Raise terrain: select tool, then click the same tile several times."""
	click_button(game, '_raise_terrain')
	for _ in range(TERRAIN_PAINT_CLICKS):
		x, y = TARGET_INTERNAL_XY
		post_click(game, x, y)
	for _ in range(15):
		step_game(game)

def effect_dpad(game: game_module.Game, action: str) -> None:
	"""Dpad arrow: click repeatedly so the camera actually moves."""
	for _ in range(DPAD_REPEATS):
		click_button(game, action)
	for _ in range(15):
		step_game(game)

def effect_find_or_go(game: game_module.Game, action: str) -> None:
	"""Find/go buttons: click and snapshot a couple of frames later."""
	click_button(game, action)
	for _ in range(30):
		step_game(game)

EFFECT_RUNNERS: dict = {
	'_do_volcano':    effect_aoe_power,
	'_do_flood':      effect_aoe_power,
	'_do_quake':      effect_aoe_power,
	'_do_swamp':      effect_aoe_power,
	'_do_papal':      effect_papal,
	'_do_knight':     effect_knight,
	'_do_shield':     effect_shield,
	'_raise_terrain': effect_terrain,
	'_find_battle':   effect_find_or_go,
	'_find_papal':    effect_find_or_go,
	'_find_shield':   effect_find_or_go,
	'_find_knight':   effect_find_or_go,
	'_go_papal':      effect_find_or_go,
	'_go_build':      effect_find_or_go,
	'_go_assemble':   effect_find_or_go,
	'_go_fight':      effect_find_or_go,
	'_battle_over':   effect_find_or_go,
}
# Dpad arrows
for _arrow in ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'):
	EFFECT_RUNNERS[_arrow] = effect_dpad

#============================================

def default_output_dir() -> str:
	"""Default output directory for button smoke shots."""
	repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	out_dir = os.path.join(repo_root, 'tools', 'screenshots', 'buttons')
	os.makedirs(out_dir, exist_ok=True)
	return out_dir

#============================================

def snapshot_button_effect(action: str, out_path: str) -> None:
	"""Run the effect runner for one button and save the resulting frame."""
	game = boot_to_playing()
	for _ in range(WARMUP_TICKS):
		step_game(game)
	runner = EFFECT_RUNNERS.get(action, effect_find_or_go)
	runner(game, action)
	pygame.image.save(game.internal_surface, out_path)
	w, h = game.internal_surface.get_size()
	print(f'wrote {out_path}  {w}x{h}  button={action}')

#============================================

def main() -> None:
	"""Run the per-button effect smoke tool."""
	args = parse_args()
	out_dir = args.output_dir if args.output_dir else default_output_dir()
	os.makedirs(out_dir, exist_ok=True)

	# Probe game to enumerate the button list
	probe = boot_to_playing()
	all_actions = list(probe.ui_panel.buttons.keys())
	if args.button_action:
		if args.button_action not in all_actions:
			print(f'error: button {args.button_action!r} not in {all_actions}')
			raise SystemExit(2)
		actions = [args.button_action]
	else:
		actions = all_actions

	for action in actions:
		safe = action.lstrip('_').replace('/', '_')
		out_path = os.path.join(out_dir, f'button_{safe}.png')
		snapshot_button_effect(action, out_path)

#============================================

if __name__ == '__main__':
	main()
