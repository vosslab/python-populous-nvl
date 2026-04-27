"""Canvas-preset parity: simulation digest must be identical across presets.

The canvas preset is a presentation-only setting (M4 canvas modernization).
Switching from `classic` to `remaster` or `large` must not alter terrain
altitudes, peep positions, peep states, or mana balances. This test boots
a Game at each preset with the same seed, advances a fixed number of ticks
without injecting any input, and compares the simulation digest.
"""

# Standard Library
import random

# local repo modules
import populous_game.faction as faction
import populous_game.settings as settings
import tools.headless_runner as runner


def _set_preset(name):
	"""Mutate the five mirror constants in settings to match a preset."""
	preset = settings.CANVAS_PRESETS[name]
	settings.ACTIVE_CANVAS_PRESET = name
	settings.INTERNAL_WIDTH = preset[0]
	settings.INTERNAL_HEIGHT = preset[1]
	settings.HUD_SCALE = preset[2]
	settings.VISIBLE_TILE_COUNT = preset[3]
	settings.TERRAIN_SCALE = preset[4]


def _digest(game):
	"""Hashable summary of simulation state for equality comparison."""
	corners = tuple(tuple(row) for row in game.game_map.corners)
	peeps = tuple(
		(p.state, round(p.x, 4), round(p.y, 4), round(p.life, 3),
		 p.faction_id, p.weapon_type, p.dead)
		for p in game.peeps
	)
	mana_player = game.mana_pool.get_mana(faction.Faction.PLAYER)
	mana_enemy = game.mana_pool.get_mana(faction.Faction.ENEMY)
	return (corners, peeps, mana_player, mana_enemy)


def _boot_and_run(preset, seed, ticks):
	"""Switch preset, boot a deterministic Game, run ticks, return digest."""
	original = settings.ACTIVE_CANVAS_PRESET
	try:
		_set_preset(preset)
		# Reseed Python's RNG so spawn placement is identical regardless of
		# any RNG draw the previous Game.__init__ performed in this process.
		random.seed(seed)
		game = runner.boot_game_for_tests(state='gameplay', seed=seed,
			players=4, enemies=4)
		runner.step_frames(game, n=ticks)
		return _digest(game)
	finally:
		_set_preset(original)


def test_classic_vs_remaster_same_digest():
	"""Classic and remaster produce identical simulation state at same seed."""
	digest_classic = _boot_and_run('classic', seed=4242, ticks=30)
	digest_remaster = _boot_and_run('remaster', seed=4242, ticks=30)
	assert digest_classic == digest_remaster, (
		"Canvas preset must be presentation-only; remaster digest differs "
		"from classic at seed=4242."
	)


def test_classic_vs_large_same_digest():
	"""Classic and large produce identical simulation state at same seed."""
	digest_classic = _boot_and_run('classic', seed=4242, ticks=30)
	digest_large = _boot_and_run('large', seed=4242, ticks=30)
	assert digest_classic == digest_large, (
		"Canvas preset must be presentation-only; large digest differs "
		"from classic at seed=4242."
	)
