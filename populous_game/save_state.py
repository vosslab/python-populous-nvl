"""JSON save/load for python-populous (M8).

A save file is a single JSON document containing a schema_version, the
heightmap, the list of houses, the list of peeps, mode flags, and the
scenario id. Older schema versions are accepted for one milestone after
a bump (currently only schema 1 exists, so this is forward-only).
"""

# Standard Library
import json


SCHEMA_VERSION: int = 1

#============================================

def save_to_dict(game) -> dict:
	"""Capture a game's simulation-relevant state as a JSON-serializable dict."""
	heightmap = [list(row) for row in game.game_map.corners]
	houses = []
	for h in game.game_map.houses:
		house_data = {
			'r': int(h.r),
			'c': int(h.c),
			'faction_id': int(h.faction_id),
			'life': float(h.life),
			'destroyed': bool(h.destroyed),
		}
		houses.append(house_data)
	peeps = []
	for p in game.peeps:
		peep_data = {
			'x': float(p.x),
			'y': float(p.y),
			'faction_id': int(p.faction_id),
			'state': str(p.state),
			'life': float(p.life),
		}
		peeps.append(peep_data)
	mode_flags = {
		'papal_mode': bool(game.mode_manager.papal_mode),
		'shield_mode': bool(game.mode_manager.shield_mode),
	}
	state = {
		'schema_version': SCHEMA_VERSION,
		'app_state': game.app_state.current,
		'heightmap': heightmap,
		'houses': houses,
		'peeps': peeps,
		'mode_flags': mode_flags,
	}
	return state

#============================================

def save_to_file(game, path: str) -> None:
	"""Write a save file as JSON to path."""
	state = save_to_dict(game)
	with open(path, 'w') as fh:
		json.dump(state, fh, indent=2, sort_keys=True)

#============================================

def load_from_dict(game, state: dict) -> None:
	"""Restore a game's simulation state from a save dict."""
	schema = int(state['schema_version'])
	if schema != SCHEMA_VERSION:
		raise ValueError(f'unsupported save schema_version={schema}')
	# Heightmap restore
	for r, row in enumerate(state['heightmap']):
		for c, value in enumerate(row):
			game.game_map.corners[r][c] = int(value)
	# Houses
	import populous_game.houses as houses_module
	game.game_map.houses.clear()
	for hd in state['houses']:
		h = houses_module.House(hd['r'], hd['c'], faction_id=int(hd['faction_id']))
		h.life = float(hd['life'])
		h.destroyed = bool(hd['destroyed'])
		game.game_map.houses.append(h)
	# Peeps
	import populous_game.peeps as peeps_module
	game.peeps.clear()
	for pd in state['peeps']:
		# Peep stores grid_r as y and grid_c as x in its update step;
		# here we restore x, y after construction so spawn placement does
		# not perturb the loaded values.
		new_peep = peeps_module.Peep(0, 0, game.game_map,
			faction_id=int(pd['faction_id']))
		new_peep.x = float(pd['x'])
		new_peep.y = float(pd['y'])
		new_peep.life = float(pd['life'])
		# Bypass transition validation so DEAD or any state can be restored
		new_peep.state = str(pd['state'])
		game.peeps.append(new_peep)
	# Mode flags
	game.mode_manager.papal_mode = bool(state['mode_flags']['papal_mode'])
	game.mode_manager.shield_mode = bool(state['mode_flags']['shield_mode'])

#============================================

def load_from_file(game, path: str) -> None:
	"""Read a save file and restore game state."""
	with open(path) as fh:
		state = json.load(fh)
	load_from_dict(game, state)
