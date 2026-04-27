#!/usr/bin/env python3
"""Headless screenshot tool for python-populous.

Boots the game in a chosen state under SDL_VIDEODRIVER=dummy, advances
the simulation for a configurable number of ticks (driving the real
event loop and input controller), then saves the rendered internal
surface to a PNG file. A YAML script may be supplied to inject key
presses and mouse clicks at specific ticks, with named captures along
the way.

Examples:
    ./tools/screenshot.py                          # default: mid-game, 60 ticks
    ./tools/screenshot.py -s menu                  # main menu
    ./tools/screenshot.py -s gameplay -t 600       # 10 sim seconds in
    ./tools/screenshot.py -s gameplay -o /tmp/foo.png
    ./tools/screenshot.py --script my_play.yaml    # scripted gameplay
"""

# Standard Library
import os
import sys
import argparse

# Force headless before any pygame import
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

# PIP3 modules
import yaml
import pygame

# local repo modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import populous_game.game as game_module

#============================================

STATE_CHOICES = ('menu', 'gameplay', 'gameover')

# Map of friendly key names to pygame key constants
KEY_MAP = {
	'return': pygame.K_RETURN, 'enter': pygame.K_RETURN,
	'escape': pygame.K_ESCAPE, 'esc': pygame.K_ESCAPE,
	'space': pygame.K_SPACE,
	'tab': pygame.K_TAB,
	'backspace': pygame.K_BACKSPACE,
	'up': pygame.K_UP, 'down': pygame.K_DOWN,
	'left': pygame.K_LEFT, 'right': pygame.K_RIGHT,
	'backquote': pygame.K_BACKQUOTE, 'tilde': pygame.K_BACKQUOTE,
}

#============================================

def parse_args():
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(description="Headless screenshot of populous game state.")
	parser.add_argument(
		'-s', '--state', dest='state', choices=STATE_CHOICES, default='gameplay',
		help='Game state to capture (default: gameplay).'
	)
	parser.add_argument(
		'-t', '--ticks', dest='ticks', type=int, default=60,
		help='Number of update ticks to advance before capture (default: 60).'
	)
	parser.add_argument(
		'-o', '--output', dest='output_file', default=None,
		help='Output PNG path (default: tools/screenshots/<state>.png).'
	)
	parser.add_argument(
		'-p', '--players', dest='player_count', type=int, default=8,
		help='Player peeps to spawn for gameplay state (default: 8).'
	)
	parser.add_argument(
		'-e', '--enemies', dest='enemy_count', type=int, default=8,
		help='Enemy peeps to spawn for gameplay state (default: 8).'
	)
	parser.add_argument(
		'--script', dest='script_file', default=None,
		help='YAML script of events and named captures (overrides -s/-t/-o defaults).'
	)
	args = parser.parse_args()
	return args

#============================================

def default_output_path(name: str) -> str:
	"""Build the default output path for a given screenshot name."""
	repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	out_dir = os.path.join(repo_root, 'tools', 'screenshots')
	os.makedirs(out_dir, exist_ok=True)
	out_path = os.path.join(out_dir, f'{name}.png')
	return out_path

#============================================

def boot_game(state: str, player_count: int, enemy_count: int) -> game_module.Game:
	"""Construct a Game and place it in the requested state."""
	game = game_module.Game()
	if state == 'menu':
		return game
	if state == 'gameplay':
		game.app_state.transition_to(game.app_state.PLAYING)
		game.game_map.set_all_altitude(3)
		game.spawn_initial_peeps(player_count)
		if enemy_count > 0:
			game.spawn_enemy_peeps(enemy_count)
		return game
	if state == 'gameover':
		game.app_state.transition_to(game.app_state.PLAYING)
		game.app_state.transition_to(game.app_state.GAMEOVER)
		game.app_state.gameover_result = 'win'
		return game
	raise ValueError(f'Unknown state: {state}')

#============================================

def resolve_key(name: str) -> int:
	"""Translate a friendly key name to a pygame key constant."""
	low = name.lower()
	if low in KEY_MAP:
		return KEY_MAP[low]
	if len(low) == 1:
		# Single-character keys: a-z, 0-9
		return pygame.key.key_code(low)
	raise ValueError(f'Unknown key: {name}')

#============================================

def post_event(event_spec: dict) -> None:
	"""Translate a script event entry into a pygame event and post it."""
	etype = event_spec['type']
	if etype == 'keydown':
		key = resolve_key(event_spec['key'])
		pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=''))
		return
	if etype == 'keyup':
		key = resolve_key(event_spec['key'])
		pygame.event.post(pygame.event.Event(pygame.KEYUP, key=key, mod=0))
		return
	if etype == 'mousedown':
		# 'pos' is the simulated screen pos; default button is 1 (left)
		button = event_spec.get('button', 1)
		pos = tuple(event_spec['pos'])
		pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=pos))
		return
	if etype == 'mouseup':
		button = event_spec.get('button', 1)
		pos = tuple(event_spec['pos'])
		pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=button, pos=pos))
		return
	if etype == 'mousemotion':
		pos = tuple(event_spec['pos'])
		pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))
		return
	raise ValueError(f'Unknown event type: {etype}')

#============================================

def step_game(game: game_module.Game, dt: float) -> None:
	"""One iteration of the real game loop, headless."""
	game.events()
	if game.app_state.is_playing() and not game.app_state.is_simulation_paused():
		scaled_dt = dt * game.app_state.time_scale
		game.update(scaled_dt)
	game.draw()

#============================================

def capture(game: game_module.Game, out_path: str) -> None:
	"""Save the current internal surface to a PNG file."""
	pygame.image.save(game.internal_surface, out_path)
	w, h = game.internal_surface.get_size()
	print(f'wrote {out_path}  {w}x{h}')

#============================================

def run_scripted(script_path: str) -> None:
	"""Drive the game via a YAML script with timed events and captures."""
	with open(script_path, 'r') as fh:
		script = yaml.safe_load(fh)

	state = script.get('state', 'menu')
	ticks = int(script.get('ticks', 60))
	player_count = int(script.get('players', 4))
	enemy_count = int(script.get('enemies', 0))
	events = script.get('events', []) or []
	captures = script.get('captures', []) or []

	# Bucket events and captures by tick for O(1) lookup per tick
	events_by_tick: dict = {}
	for ev in events:
		events_by_tick.setdefault(int(ev['tick']), []).append(ev)
	captures_by_tick: dict = {}
	for cap in captures:
		captures_by_tick.setdefault(int(cap['tick']), []).append(cap)

	game = boot_game(state, player_count, enemy_count)
	dt = 1.0 / 60.0
	for t in range(ticks + 1):
		# Inject any events scheduled for this tick BEFORE the loop iteration
		for ev in events_by_tick.get(t, []):
			post_event(ev)
		step_game(game, dt)
		# Save any captures scheduled for this tick AFTER the iteration
		for cap in captures_by_tick.get(t, []):
			out_path = cap.get('path') or default_output_path(cap['name'])
			capture(game, out_path)

#============================================

def main() -> None:
	"""Run the screenshot tool."""
	args = parse_args()

	if args.script_file:
		run_scripted(args.script_file)
		return

	out_path = args.output_file if args.output_file else default_output_path(args.state)
	game = boot_game(args.state, args.player_count, args.enemy_count)
	dt = 1.0 / 60.0
	for _ in range(args.ticks):
		step_game(game, dt)
	capture(game, out_path)

#============================================

if __name__ == '__main__':
	main()
