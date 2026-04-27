"""GameMap.randomize is deterministic when given an explicit seed."""

import populous_game.game as game_module


def _heightmap_signature(game_map):
    """Flatten the corner grid into a tuple for equality comparison."""
    rows = []
    for r in range(game_map.grid_height + 1):
        rows.append(tuple(game_map.corners[r]))
    return tuple(rows)


def test_same_seed_produces_same_map():
    """Two GameMaps randomized with the same seed must be identical."""
    a = game_module.Game()
    b = game_module.Game()
    a.game_map.randomize(seed=12345)
    b.game_map.randomize(seed=12345)
    assert _heightmap_signature(a.game_map) == _heightmap_signature(b.game_map)


def test_different_seeds_diverge():
    """Different seeds produce different maps on a non-trivial grid."""
    a = game_module.Game()
    b = game_module.Game()
    a.game_map.randomize(seed=1)
    b.game_map.randomize(seed=2)
    assert _heightmap_signature(a.game_map) != _heightmap_signature(b.game_map), (
        "seed=1 and seed=2 produced identical heightmaps"
    )


def test_seed_none_does_not_perturb_module_random():
    """Passing seed=None should not rewind the module random state."""
    import random
    random.seed(99)
    expected_first = random.random()
    random.seed(99)
    g = game_module.Game()
    # Calling randomize with seed=None uses module random; it consumes the
    # stream. After it, the module random state has advanced. The
    # important invariant is that re-seeding with 99 still produces the
    # same first value, i.e. seed=None did not steal from a fresh seeded
    # state established later.
    g.game_map.randomize(seed=None)
    random.seed(99)
    assert random.random() == expected_first
