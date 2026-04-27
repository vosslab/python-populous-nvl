"""Scenario loader for python-populous (M8).

A scenario describes a starting world: random seed, default altitude,
faction starting positions, mana pool, and an optional password. Scenarios
are stored as YAML under data/scenarios/ and loaded by name or path.

Schema (format_version 1):

    format_version: 1
    name: "Plateau"
    seed: 12345
    altitude: 3
    player:
        peeps: 10
    enemy:
        peeps: 10
    mana:
        initial: 100.0
    password: "ABCDEFG"

Unsupported format_version raises ValueError.
"""

# Standard Library
import os

# PIP3 modules
import yaml

# local repo modules
import populous_game.settings as settings


SCHEMA_VERSION: int = 1
SCENARIO_DIR: str = os.path.join(settings.REPO_ROOT, 'data', 'scenarios')

#============================================

class Scenario:
	"""In-memory representation of a loaded scenario."""

	def __init__(self, data: dict):
		"""Wrap a parsed scenario dict and validate required keys."""
		fmt = int(data['format_version'])
		if fmt != SCHEMA_VERSION:
			raise ValueError(f'unsupported scenario format_version={fmt}')
		self.format_version: int = fmt
		self.name: str = str(data['name'])
		self.seed: int = int(data['seed'])
		self.altitude: int = int(data['altitude'])
		# player and enemy may omit peeps for an empty start
		self.player_peeps: int = int(data.get('player', {}).get('peeps', 0))
		self.enemy_peeps: int = int(data.get('enemy', {}).get('peeps', 0))
		self.initial_mana: float = float(data.get('mana', {}).get('initial', settings.INITIAL_MANA))
		self.password: str | None = data.get('password')

#============================================

def load_scenario_file(path: str) -> Scenario:
	"""Load a Scenario from a YAML file path."""
	with open(path) as fh:
		data = yaml.safe_load(fh)
	return Scenario(data)

#============================================

def load_scenario_by_name(name: str) -> Scenario:
	"""Load a scenario by its bare name from data/scenarios/."""
	path = os.path.join(SCENARIO_DIR, f'{name}.yaml')
	return load_scenario_file(path)

#============================================

def apply_to_game(scenario: Scenario, game) -> None:
	"""Apply a scenario's starting state to a Game instance.

	Sets random seed, raises terrain to scenario altitude, and spawns the
	requested number of peeps for each faction. Does NOT transition app
	state -- callers decide when to enter PLAYING.
	"""
	import random
	random.seed(scenario.seed)
	game.game_map.set_all_altitude(scenario.altitude)
	if scenario.player_peeps > 0:
		game.spawn_initial_peeps(scenario.player_peeps)
	if scenario.enemy_peeps > 0:
		game.spawn_enemy_peeps(scenario.enemy_peeps)
	if hasattr(game, 'mana_pool'):
		game.mana_pool.initial_mana = scenario.initial_mana
