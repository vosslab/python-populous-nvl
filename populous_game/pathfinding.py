"""A* pathfinding for the Populous game grid.

Finds paths for peeps to walk across the terrain, respecting walkability rules
and altitude delta constraints (cliffs).
"""

import heapq


#============================================
# Constants
#============================================

DIAGONAL_COST: float = 1.41421356
ORTHOGONAL_COST: float = 1.0

#============================================
# Walkability computation
#============================================

def compute_walkability(game_map) -> list:
	"""Return a 2D list (grid_height x grid_width) of bools: True iff cell is walkable.

	A cell is walkable if its average corner altitude > 0 (water = altitude 0 = not walkable).
	"""
	walkability = []
	for r in range(game_map.grid_height):
		row = []
		for c in range(game_map.grid_width):
			# Average the four corners of the cell
			a0 = game_map.get_corner_altitude(r, c)
			a1 = game_map.get_corner_altitude(r, c + 1)
			a2 = game_map.get_corner_altitude(r + 1, c + 1)
			a3 = game_map.get_corner_altitude(r + 1, c)
			avg_alt = (a0 + a1 + a2 + a3) / 4.0
			row.append(avg_alt > 0)
		walkability.append(row)
	return walkability

#============================================
# Cell altitude helpers
#============================================

def _get_cell_altitude(game_map, r: int, c: int) -> float:
	"""Return the average altitude of the four corners of a cell."""
	a0 = game_map.get_corner_altitude(r, c)
	a1 = game_map.get_corner_altitude(r, c + 1)
	a2 = game_map.get_corner_altitude(r + 1, c + 1)
	a3 = game_map.get_corner_altitude(r + 1, c)
	return (a0 + a1 + a2 + a3) / 4.0

#============================================
# Movement cost and validity
#============================================

def _is_valid_move(from_r: int, from_c: int, to_r: int, to_c: int, game_map) -> bool:
	"""Check if a move from one cell to another is allowed.

	A move is allowed if:
	1. The destination is within bounds.
	2. The destination is walkable (not water).
	3. The altitude delta between the two cells is <= 1 (can't climb cliffs).
	"""
	if not (0 <= to_r < game_map.grid_height and 0 <= to_c < game_map.grid_width):
		return False

	# Get walkability (recompute inline to avoid keeping state)
	to_alt = _get_cell_altitude(game_map, to_r, to_c)
	if to_alt <= 0:
		return False

	# Check altitude delta constraint (max 1.0)
	from_alt = _get_cell_altitude(game_map, from_r, from_c)
	if abs(to_alt - from_alt) > 1:
		return False

	return True

def _move_cost(from_r: int, from_c: int, to_r: int, to_c: int) -> float:
	"""Return the cost to move from one cell to another (8-connected grid)."""
	dr = abs(to_r - from_r)
	dc = abs(to_c - from_c)
	if dr == 1 and dc == 1:
		return DIAGONAL_COST
	else:
		return ORTHOGONAL_COST

#============================================
# Heuristic
#============================================

def _octile_distance(r1: int, c1: int, r2: int, c2: int) -> float:
	"""Octile distance heuristic for 8-connected grid."""
	dr = abs(r1 - r2)
	dc = abs(c1 - c2)
	return max(dr, dc) + (1.41421356 - 1.0) * min(dr, dc)

#============================================
# A* search
#============================================

def find_path(start: tuple, goal: tuple, game_map, max_steps: int = 2000) -> list:
	"""Find a path from start to goal using A*.

	Args:
		start: (row, col) integer tuple for the starting cell.
		goal: (row, col) integer tuple for the goal cell.
		game_map: A GameMap instance with grid_height, grid_width, and get_corner_altitude().
		max_steps: Maximum number of node expansions (default 2000).

	Returns:
		A list of (row, col) tuples from start to goal inclusive, or None if no path exists
		or start/goal is on water or invalid.

	Raises:
		IndexError or ValueError if start or goal is outside the grid bounds.
	"""
	start_r, start_c = start
	goal_r, goal_c = goal

	# Bounds checking: start and goal must be within the grid
	if not (0 <= start_r < game_map.grid_height and 0 <= start_c < game_map.grid_width):
		raise IndexError(f"Start cell ({start_r}, {start_c}) out of bounds")
	if not (0 <= goal_r < game_map.grid_height and 0 <= goal_c < game_map.grid_width):
		raise IndexError(f"Goal cell ({goal_r}, {goal_c}) out of bounds")

	# Check if start and goal are walkable (not on water)
	start_alt = _get_cell_altitude(game_map, start_r, start_c)
	goal_alt = _get_cell_altitude(game_map, goal_r, goal_c)

	if start_alt <= 0:
		return None
	if goal_alt <= 0:
		return None

	# Same cell: return the cell itself
	if start == goal:
		return [start]

	# Open set: (f_score, counter, (r, c))
	# counter breaks ties deterministically (insertion order)
	counter = 0
	open_set = [(0, counter, start)]
	counter += 1

	# For node (r, c), store the f_score
	f_score = {start: 0}

	# For node (r, c), store the g_score (cost from start)
	g_score = {start: 0}

	# Closed set: set of (r, c) tuples already expanded
	closed_set = set()

	# Parent pointers for path reconstruction
	parent = {}

	# Track expanded nodes to enforce max_steps
	expanded_count = 0

	while open_set and expanded_count < max_steps:
		_, _, current = heapq.heappop(open_set)
		current_r, current_c = current

		if current in closed_set:
			continue

		closed_set.add(current)
		expanded_count += 1

		# Goal reached
		if current == goal:
			# Reconstruct path
			path = []
			node = goal
			while node in parent:
				path.append(node)
				node = parent[node]
			path.append(start)
			path.reverse()
			return path

		# Explore neighbors (8-connected)
		for dr in [-1, 0, 1]:
			for dc in [-1, 0, 1]:
				if dr == 0 and dc == 0:
					continue
				neighbor_r = current_r + dr
				neighbor_c = current_c + dc
				neighbor = (neighbor_r, neighbor_c)

				# Skip if already expanded
				if neighbor in closed_set:
					continue

				# Check if move is valid
				if not _is_valid_move(current_r, current_c, neighbor_r, neighbor_c, game_map):
					continue

				# Calculate tentative g_score
				move_cost = _move_cost(current_r, current_c, neighbor_r, neighbor_c)
				tentative_g = g_score[current] + move_cost

				# Update if this is a better path to neighbor
				if neighbor not in g_score or tentative_g < g_score[neighbor]:
					parent[neighbor] = current
					g_score[neighbor] = tentative_g
					h = _octile_distance(neighbor_r, neighbor_c, goal_r, goal_c)
					f = tentative_g + h
					f_score[neighbor] = f
					heapq.heappush(open_set, (f, counter, neighbor))
					counter += 1

	# No path found within max_steps
	return None
