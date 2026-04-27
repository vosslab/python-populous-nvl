"""Tests for pathfinding module.

Covers A* path finding on grids with water, cliffs, and various start/goal configurations.
"""

import time
import random
import pytest
import populous_game.pathfinding as pathfinding
import populous_game.settings as settings


#============================================
# Mock GameMap for testing
#============================================

class MockGameMap:
	"""A simple mock GameMap for testing pathfinding without pygame."""

	def __init__(self, grid_height: int, grid_width: int):
		self.grid_height = grid_height
		self.grid_width = grid_width
		# Grid of corner altitudes: (grid_height+1) x (grid_width+1)
		self.corners = [[1 for _ in range(grid_width + 1)] for _ in range(grid_height + 1)]

	def get_corner_altitude(self, r: int, c: int) -> int:
		"""Get altitude at corner (r, c), or -1 if out of bounds."""
		if 0 <= r <= self.grid_height and 0 <= c <= self.grid_width:
			return self.corners[r][c]
		return -1

	def set_corner_altitude(self, r: int, c: int, value: int):
		"""Set altitude at corner (r, c)."""
		if 0 <= r <= self.grid_height and 0 <= c <= self.grid_width:
			self.corners[r][c] = value

	def set_water_line(self, row: int, value: int = 0):
		"""Set all corners in a row to the given altitude (0 = water)."""
		for c in range(self.grid_width + 1):
			self.set_corner_altitude(row, c, value)

	def set_vertical_line(self, col: int, value: int = 0):
		"""Set all corners in a column to the given altitude."""
		for r in range(self.grid_height + 1):
			self.set_corner_altitude(r, col, value)

#============================================
# Test 1: Trivial path on flat grid
#============================================

def test_pathfinding_trivial_path():
	"""A path on flat 5x5 grid from (0,0) to (4,4) returns 5 cells.

	On a flat grid with no obstacles, the A* pathfinder uses pure diagonal
	moves to reach (4,4) from (0,0), yielding 5 cells (start + 4 diagonal steps).
	"""
	game_map = MockGameMap(5, 5)
	# All corners have altitude 1, so all cells walkable
	path = pathfinding.find_path((0, 0), (4, 4), game_map)
	assert path is not None
	assert len(path) == 5
	assert path[0] == (0, 0)
	assert path[-1] == (4, 4)
	# Path should be purely diagonal
	for i in range(len(path) - 1):
		r1, c1 = path[i]
		r2, c2 = path[i + 1]
		# Each move should be diagonal (r differs and c differs)
		assert abs(r2 - r1) == 1 and abs(c2 - c1) == 1

#============================================
# Test 2: Blocked by water
#============================================

def test_pathfinding_blocked_by_water():
	"""A grid with a water barrier prevents direct traversal.

	When row 2 is all water (altitude 0), a path from (0,0) to (4,4) must
	navigate around the barrier or return None if completely blocked.
	"""
	game_map = MockGameMap(5, 5)
	# Set row 2 (corners at row 2) to water
	game_map.set_water_line(2, value=0)
	# Also set row 1 corners to water to ensure the water barrier blocks cell traversal
	game_map.set_water_line(1, value=0)

	# Now the bottom half (rows 3,4) is unreachable from top (rows 0)
	path = pathfinding.find_path((0, 0), (4, 4), game_map)
	# Should be None because the water blocks the path
	assert path is None

#============================================
# Test 3: Cliff blocking
#============================================

def test_pathfinding_cliff_blocked():
	"""A cell with high altitude (altitude 5) blocks normal traversal.

	When a cell has altitude 5 surrounded by altitude 1, peeps cannot climb
	the cliff (delta > 1), so the path must avoid it or return None.
	"""
	game_map = MockGameMap(5, 5)
	# Set all corners of cell (2, 2) to altitude 5 (a cliff)
	game_map.set_corner_altitude(2, 2, 5)
	game_map.set_corner_altitude(2, 3, 5)
	game_map.set_corner_altitude(3, 2, 5)
	game_map.set_corner_altitude(3, 3, 5)

	# Try to cross from (1, 1) to (3, 3) - but (2, 2) is a cliff
	# The path should avoid the cliff
	path = pathfinding.find_path((1, 1), (3, 3), game_map)

	if path is not None:
		# If a path exists, it must not go through the cliff cell (2, 2)
		assert (2, 2) not in path
	# If no path, that's also acceptable (cliff completely blocks)

#============================================
# Test 4: Start on water returns None
#============================================

def test_pathfinding_start_on_water():
	"""Starting on water (altitude 0) returns None."""
	game_map = MockGameMap(5, 5)
	# Set cell (0, 0) to water
	game_map.set_corner_altitude(0, 0, 0)
	game_map.set_corner_altitude(0, 1, 0)
	game_map.set_corner_altitude(1, 0, 0)
	game_map.set_corner_altitude(1, 1, 0)

	path = pathfinding.find_path((0, 0), (4, 4), game_map)
	assert path is None

#============================================
# Test 5: Goal on water returns None
#============================================

def test_pathfinding_goal_on_water():
	"""Goal on water (altitude 0) returns None."""
	game_map = MockGameMap(5, 5)
	# Set cell (4, 4) to water
	game_map.set_corner_altitude(4, 4, 0)
	game_map.set_corner_altitude(4, 5, 0)
	game_map.set_corner_altitude(5, 4, 0)
	game_map.set_corner_altitude(5, 5, 0)

	path = pathfinding.find_path((0, 0), (4, 4), game_map)
	assert path is None

#============================================
# Test 6: Same cell start == goal
#============================================

def test_pathfinding_same_cell():
	"""Start and goal on the same cell returns a single-cell path."""
	game_map = MockGameMap(5, 5)
	path = pathfinding.find_path((2, 2), (2, 2), game_map)
	assert path is not None
	assert len(path) == 1
	assert path[0] == (2, 2)

#============================================
# Test 7: Performance test on 64x64 grid
#============================================

def test_pathfinding_performance_64x64():
	"""Performance test: 100 random paths on 64x64 grid, 95th percentile < 5.0 ms.

	This test ensures A* can handle the full game grid size efficiently.
	On a typical machine with a pure Python A* implementation, this should
	complete well under 5ms per path.
	"""
	game_map = MockGameMap(settings.GRID_HEIGHT, settings.GRID_WIDTH)

	# Randomize the map with varied altitudes
	random.seed(42)
	for r in range(game_map.grid_height + 1):
		for c in range(game_map.grid_width + 1):
			game_map.set_corner_altitude(r, c, random.randint(1, 7))

	# Run 100 random paths
	latencies = []
	for _ in range(100):
		start_r = random.randint(0, game_map.grid_height - 1)
		start_c = random.randint(0, game_map.grid_width - 1)
		goal_r = random.randint(0, game_map.grid_height - 1)
		goal_c = random.randint(0, game_map.grid_width - 1)

		# Ensure start and goal are not water
		game_map.set_corner_altitude(start_r, start_c, max(1, game_map.get_corner_altitude(start_r, start_c)))
		game_map.set_corner_altitude(start_r, start_c + 1, max(1, game_map.get_corner_altitude(start_r, start_c + 1)))
		game_map.set_corner_altitude(start_r + 1, start_c, max(1, game_map.get_corner_altitude(start_r + 1, start_c)))
		game_map.set_corner_altitude(start_r + 1, start_c + 1, max(1, game_map.get_corner_altitude(start_r + 1, start_c + 1)))

		game_map.set_corner_altitude(goal_r, goal_c, max(1, game_map.get_corner_altitude(goal_r, goal_c)))
		game_map.set_corner_altitude(goal_r, goal_c + 1, max(1, game_map.get_corner_altitude(goal_r, goal_c + 1)))
		game_map.set_corner_altitude(goal_r + 1, goal_c, max(1, game_map.get_corner_altitude(goal_r + 1, goal_c)))
		game_map.set_corner_altitude(goal_r + 1, goal_c + 1, max(1, game_map.get_corner_altitude(goal_r + 1, goal_c + 1)))

		start = (start_r, start_c)
		goal = (goal_r, goal_c)

		t0 = time.perf_counter()
		pathfinding.find_path(start, goal, game_map)
		t1 = time.perf_counter()
		latencies.append((t1 - t0) * 1000)  # Convert to ms

	# Sort and compute 95th percentile
	latencies.sort()
	percentile_95 = latencies[int(0.95 * len(latencies))]

	# Should be well under 5.0 ms
	assert percentile_95 < 5.0, f"95th percentile latency {percentile_95:.2f}ms exceeds 5.0ms"

#============================================
# Test 8: Compute walkability
#============================================

def test_pathfinding_compute_walkability():
	"""compute_walkability correctly identifies walkable and non-walkable cells."""
	game_map = MockGameMap(3, 3)

	# Set cell (1, 1) to water (all corners = 0)
	game_map.set_corner_altitude(1, 1, 0)
	game_map.set_corner_altitude(1, 2, 0)
	game_map.set_corner_altitude(2, 1, 0)
	game_map.set_corner_altitude(2, 2, 0)

	walkability = pathfinding.compute_walkability(game_map)

	# Cell (1, 1) should be not walkable (all corners water)
	assert not walkability[1][1]

	# Other cells should be walkable (average > 0)
	assert walkability[0][0]
	assert walkability[0][1]

#============================================
# Test 9: Out of bounds raises IndexError
#============================================

def test_pathfinding_start_out_of_bounds():
	"""Start outside grid bounds raises IndexError."""
	game_map = MockGameMap(5, 5)
	with pytest.raises(IndexError):
		pathfinding.find_path((-1, 0), (4, 4), game_map)

	with pytest.raises(IndexError):
		pathfinding.find_path((5, 0), (4, 4), game_map)

	with pytest.raises(IndexError):
		pathfinding.find_path((0, -1), (4, 4), game_map)

	with pytest.raises(IndexError):
		pathfinding.find_path((0, 5), (4, 4), game_map)

def test_pathfinding_goal_out_of_bounds():
	"""Goal outside grid bounds raises IndexError."""
	game_map = MockGameMap(5, 5)
	with pytest.raises(IndexError):
		pathfinding.find_path((0, 0), (-1, 4), game_map)

	with pytest.raises(IndexError):
		pathfinding.find_path((0, 0), (5, 4), game_map)

	with pytest.raises(IndexError):
		pathfinding.find_path((0, 0), (4, -1), game_map)

	with pytest.raises(IndexError):
		pathfinding.find_path((0, 0), (4, 5), game_map)
