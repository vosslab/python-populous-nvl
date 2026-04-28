"""Cross-cutting smoke coverage for pre-parity cleanup paths."""

import random

import populous_game.combat as combat
import populous_game.game as game_module
import populous_game.pathfinding as pathfinding
import populous_game.settings as settings


class TinyMap:
	def __init__(self):
		self.grid_height = 2
		self.grid_width = 2
		self.corners = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]

	def get_corner_altitude(self, r: int, c: int) -> int:
		if 0 <= r <= self.grid_height and 0 <= c <= self.grid_width:
			return self.corners[r][c]
		return -1

	def find_nearest_land(self, r: int, c: int):
		return (0, 0)


def test_preparity_smoke_path_spawn_and_merge():
	game_map = TinyMap()
	assert pathfinding._is_valid_move(0, 0, 1, 1, game_map) is True
	path = pathfinding.find_path((0, 0), (1, 1), game_map)
	assert path == [(0, 0), (1, 1)]

	game = game_module.Game()
	game.game_map = game_map
	game.peeps = []
	random.seed(0)
	game.spawn_initial_peeps(1)
	game.spawn_enemy_peeps(1)
	assert len(game.peeps) == 2

	peep_a, peep_b = game.peeps
	peep_b.faction_id = peep_a.faction_id
	peep_a.life = 30.0
	peep_b.life = 20.0
	assert combat.join_forces(peep_a, peep_b) is True
	assert peep_a.life == min(settings.PEEP_LIFE_MAX, 50.0)
