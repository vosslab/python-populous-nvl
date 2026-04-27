"""Test that confirm dialog pauses simulation.

Patch M7.1: Verify is_simulation_paused() stops game.update() tick.
"""

import pytest
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from populous_game.game import Game


@pytest.fixture
def game():
	"""Boot game to PLAYING state and return snapshot helpers."""
	game = Game()
	game.app_state.transition_to(game.app_state.PLAYING)
	game.spawn_initial_peeps(5)
	game.spawn_enemy_peeps(5)
	return game


def snapshot_sim_state(game):
	"""Capture simulation state: peep positions, life, house ownership."""
	snapshot = {
		'peeps': [
			{
				'x': p.x, 'y': p.y, 'life': p.life,
				'faction_id': p.faction_id, 'state': p.state
			}
			for p in game.peeps
		],
		'houses': [
			{
				'r': h.r, 'c': h.c, 'life': h.life,
				'faction_id': h.faction_id, 'destroyed': h.destroyed
			}
			for h in game.game_map.houses
		],
		'mana': {
			fac_id: game.mana_pool.get_mana(fac_id)
			for fac_id in [1, 2]  # PLAYER=1, ENEMY=2
		},
	}
	return snapshot


def test_confirm_dialog_pauses_simulation(game):
	"""Confirm dialog open => simulation tick is skipped.

	Procedure:
	1. Record snapshot (peep positions, life, etc).
	2. Open confirm dialog via request_confirm.
	3. Call game.update(0.1) 50 times.
	4. Assert peep positions are UNCHANGED.
	5. Cancel dialog.
	6. Call game.update(0.1) once.
	7. Assert peep positions DID change (simulation resumed).
	"""
	# Step 1: Record initial snapshot
	snapshot_before = snapshot_sim_state(game)
	initial_peep_count = len(game.peeps)
	assert initial_peep_count > 0, "No peeps to test with"

	# Step 2: Open confirm dialog
	game.app_state.request_confirm(
		"Test dialog",
		on_confirm=lambda: None,
		on_cancel=lambda: None
	)
	assert game.app_state.has_confirm_dialog(), "Dialog should be open"

	# Step 3: Run 50 update ticks with dialog open
	for _ in range(50):
		# Manually advance the game loop like run() does
		if game.app_state.is_playing() and not game.app_state.is_simulation_paused():
			game.update(0.1)

	# Step 4: Verify simulation state unchanged
	snapshot_dialog_open = snapshot_sim_state(game)
	assert snapshot_dialog_open == snapshot_before, (
		"Simulation should not advance while dialog is open"
	)

	# Step 5: Cancel dialog
	game.app_state.cancel()
	assert not game.app_state.has_confirm_dialog(), "Dialog should be closed"

	# Step 6: Run one more update tick (dialog closed)
	if game.app_state.is_playing() and not game.app_state.is_simulation_paused():
		game.update(0.1)

	# Step 7: Verify simulation advanced (positions or life changed)
	snapshot_after = snapshot_sim_state(game)
	# At least one peep or house should have changed state
	changed = snapshot_after != snapshot_before
	assert changed, "Simulation should advance after dialog closes"
