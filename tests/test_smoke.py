"""Smoke test for the Populous game.

Verifies that the game boots in headless mode, runs for 2.0 seconds without
raising exceptions, and renders at least 60 frames (targeting 60 FPS).
"""

import time
import sys

# local repo modules
import git_file_utils

REPO_ROOT = git_file_utils.get_repo_root()
sys.path.insert(0, REPO_ROOT)

#============================================

def test_game_boots_headless():
	"""Game initializes and runs for 2.0 seconds without exceptions."""
	# Import after conftest has set SDL env vars
	from populous_game.game import Game

	game = Game()
	start_time = time.time()
	elapsed = 0.0
	frame_count = 0

	# Run the game loop for 2.0 seconds (16.67ms per frame at 60 FPS)
	dt_target = 1.0 / 60.0
	while elapsed < 2.0:
		game.update(dt_target)
		game.draw()
		frame_count += 1
		elapsed = time.time() - start_time

	# Assert at least 60 frames rendered in 2.0 seconds (60 FPS target)
	assert frame_count >= 60, (
		f'Expected at least 60 frames in 2.0s; got {frame_count}'
	)

	# Verify game state is sane after running
	assert hasattr(game, 'screen'), 'Game should have a screen surface'
	assert game.screen is not None, 'Screen surface should not be None'
