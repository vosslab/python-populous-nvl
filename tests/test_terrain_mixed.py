"""GameMap.randomize produces mixed water and land at boot.

After M1, a fresh game's heightmap must contain both altitude-0 corners
(water-source) and altitude>0 corners (land) on essentially every seed.
The previous menu-Enter handler hid this by calling set_all_altitude(3)
before the player saw anything.
"""

import populous_game.game as game_module


def _has_water_and_land(game_map):
    """Return True iff the corner grid contains both altitude 0 and >0."""
    has_water = False
    has_land = False
    for r in range(game_map.grid_height + 1):
        for c in range(game_map.grid_width + 1):
            v = game_map.corners[r][c]
            if v <= 0:
                has_water = True
            else:
                has_land = True
            if has_water and has_land:
                return True
    return False


# Fixed seed list, committed for reproducibility. Each must produce a
# mixed heightmap; if a future generator change breaks one of these,
# the failing seed is named explicitly in the assertion.
FIXED_SEEDS = (1, 2, 3, 4, 5, 1234, 0xdeadbeef)


def test_fixed_seeds_produce_mixed_terrain():
    """Every seed in the committed list yields water and land."""
    for seed in FIXED_SEEDS:
        game = game_module.Game()
        game.game_map.randomize(seed=seed)
        game_map = game.game_map
        assert _has_water_and_land(game_map), (
            f"seed {seed!r} produced a uniform heightmap with no mix of "
            f"water and land"
        )


def test_random_seed_sweep_mostly_mixed():
    """20 random seeds: at most 1 may fail to produce mixed terrain."""
    failures = []
    for seed in range(100, 120):
        game = game_module.Game()
        game.game_map.randomize(seed=seed)
        game_map = game.game_map
        if not _has_water_and_land(game_map):
            failures.append(seed)
    assert len(failures) <= 1, (
        f"More than one seed produced a uniform heightmap: {failures}"
    )
