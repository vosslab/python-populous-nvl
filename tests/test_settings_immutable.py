"""Test that settings constants remain immutable after importing other modules.

This test is expected to fail (xfail) on a fresh checkout because the
current populous.py mutates settings.SCREEN_WIDTH and other module constants
at runtime. The M1 cleanup work package will fix these mutations and make
this test pass.
"""

import sys
import pytest

import git_file_utils

REPO_ROOT = git_file_utils.get_repo_root()
sys.path.insert(0, REPO_ROOT)

#============================================

@pytest.mark.xfail(strict=False)
def test_settings_unchanged_after_imports():
	"""Settings constants should not change after importing other modules."""
	# Import settings first and snapshot the constants
	import populous_game.settings as settings

	# Record the constants we want to protect
	original_screen_width = settings.SCREEN_WIDTH
	original_screen_height = settings.SCREEN_HEIGHT
	original_grid_width = settings.GRID_WIDTH
	original_grid_height = settings.GRID_HEIGHT
	original_tile_width = settings.TILE_WIDTH
	original_tile_height = settings.TILE_HEIGHT

	# Now import other runtime modules (which may mutate settings)
	try:
		import populous
		import populous_game.game_map
		import populous_game.peep
		import populous_game.house
		import populous_game.camera
		import populous_game.minimap
		# Touch the modules to satisfy pyflakes (imports are for side effects)
		_ = [populous, populous_game.game_map, populous_game.peep,
			populous_game.house, populous_game.camera, populous_game.minimap]
	except ImportError:
		# If imports fail, skip the mutation check
		# (during refactoring, some modules may not be importable yet)
		pytest.skip('Could not import all modules')

	# Verify settings constants are unchanged
	assert settings.SCREEN_WIDTH == original_screen_width, (
		f'SCREEN_WIDTH mutated: {original_screen_width} -> {settings.SCREEN_WIDTH}'
	)
	assert settings.SCREEN_HEIGHT == original_screen_height, (
		f'SCREEN_HEIGHT mutated: {original_screen_height} -> {settings.SCREEN_HEIGHT}'
	)
	assert settings.GRID_WIDTH == original_grid_width, (
		f'GRID_WIDTH mutated: {original_grid_width} -> {settings.GRID_WIDTH}'
	)
	assert settings.GRID_HEIGHT == original_grid_height, (
		f'GRID_HEIGHT mutated: {original_grid_height} -> {settings.GRID_HEIGHT}'
	)
	assert settings.TILE_WIDTH == original_tile_width, (
		f'TILE_WIDTH mutated: {original_tile_width} -> {settings.TILE_WIDTH}'
	)
	assert settings.TILE_HEIGHT == original_tile_height, (
		f'TILE_HEIGHT mutated: {original_tile_height} -> {settings.TILE_HEIGHT}'
	)
