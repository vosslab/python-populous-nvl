"""Regression tests for movement legality classification."""

import populous_game.pathfinding as pathfinding
import populous_game.settings as settings


class MockGameMap:
	def __init__(self):
		self.grid_height = 4
		self.grid_width = 4
		self.corners = [[1 for _ in range(5)] for _ in range(5)]
		self.rock_cells = set()

	def get_corner_altitude(self, r: int, c: int) -> int:
		if 0 <= r <= self.grid_height and 0 <= c <= self.grid_width:
			return self.corners[r][c]
		return -1


def test_classify_move_reports_out_of_bounds():
	game_map = MockGameMap()
	allowed, reason = pathfinding._classify_move(1, 1, 5, 1, game_map)
	assert allowed is False
	assert reason == "out_of_bounds"


def test_classify_move_reports_water():
	game_map = MockGameMap()
	game_map.corners[2][2] = 0
	game_map.corners[2][3] = 0
	game_map.corners[3][2] = 0
	game_map.corners[3][3] = 0
	allowed, reason = pathfinding._classify_move(1, 1, 2, 2, game_map)
	assert allowed is False
	assert reason == "water"


def test_classify_move_reports_cliff():
	game_map = MockGameMap()
	game_map.corners[2][2] = 5
	game_map.corners[2][3] = 5
	game_map.corners[3][2] = 5
	game_map.corners[3][3] = 5
	allowed, reason = pathfinding._classify_move(1, 1, 2, 2, game_map)
	assert allowed is False
	assert reason == "cliff"


def test_classify_move_reports_ok_for_flat_land():
	game_map = MockGameMap()
	allowed, reason = pathfinding._classify_move(1, 1, 2, 2, game_map)
	assert allowed is True
	assert reason == "ok"


def test_public_is_valid_move_tracks_classification():
	game_map = MockGameMap()
	game_map.corners[2][2] = 5
	game_map.corners[2][3] = 5
	game_map.corners[3][2] = 5
	game_map.corners[3][3] = 5
	assert pathfinding._is_valid_move(1, 1, 2, 2, game_map) is False
	assert pathfinding._is_valid_move(1, 1, 1, 2, game_map) is True


def test_valid_move_code_reports_open_land():
	game_map = MockGameMap()
	code = pathfinding.valid_move_code(1, 1, 2, 2, game_map)
	assert code == settings.ASM_VALID_MOVE_OPEN_CODE


def test_valid_move_code_reports_out_of_bounds():
	game_map = MockGameMap()
	code = pathfinding.valid_move_code(1, 1, 5, 1, game_map)
	assert code == settings.ASM_VALID_MOVE_OUT_OF_BOUNDS_CODE


def test_valid_move_code_reports_empty_water():
	game_map = MockGameMap()
	game_map.corners[2][2] = 0
	game_map.corners[2][3] = 0
	game_map.corners[3][2] = 0
	game_map.corners[3][3] = 0
	code = pathfinding.valid_move_code(1, 1, 2, 2, game_map)
	assert code == settings.ASM_VALID_MOVE_EMPTY_CODE


def test_valid_move_code_reports_rock_marker():
	game_map = MockGameMap()
	game_map.rock_cells.add((2, 2))
	code = pathfinding.valid_move_code(1, 1, 2, 2, game_map)
	assert code == settings.ASM_VALID_MOVE_ROCK_CODE


def test_find_path_respects_blocked_and_cliff_tiles():
	game_map = MockGameMap()
	game_map.corners[1][1] = 0
	game_map.corners[1][2] = 0
	game_map.corners[2][1] = 0
	game_map.corners[2][2] = 0
	path = pathfinding.find_path((0, 0), (3, 3), game_map)
	assert path is not None
	assert all((r, c) != (1, 1) for r, c in path)

	game_map = MockGameMap()
	for r in range(1, 4):
		for c in range(5):
			game_map.corners[r][c] = 5
	path = pathfinding.find_path((0, 0), (3, 3), game_map)
	assert path is None
