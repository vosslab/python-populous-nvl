"""Tests for the island terrain generator (classic_reference and remaster_islands profiles)."""

import pytest
import populous_game.game as game_module
import populous_game.terrain as terrain


#============================================
# Helper functions
#============================================

def _make_map(seed, profile='remaster_islands'):
    """Build a Game and randomize its map with the given seed and profile."""
    game = game_module.Game()
    game.game_map.randomize(seed=seed, profile=profile)
    return game.game_map


def _corner_grid_signature(gm):
    """Flatten the corner grid into a tuple for exact equality comparison."""
    rows = []
    for r in range(gm.grid_height + 1):
        rows.append(tuple(gm.corners[r]))
    return tuple(rows)


def _smoothness_holds(gm):
    """Check that all 8-neighbor adjacent corners differ by at most 1."""
    for r in range(gm.grid_height + 1):
        for c in range(gm.grid_width + 1):
            alt = gm.get_corner_altitude(r, c)
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr <= gm.grid_height and 0 <= nc <= gm.grid_width:
                        neighbor_alt = gm.get_corner_altitude(nr, nc)
                        if abs(alt - neighbor_alt) > 1:
                            return False
    return True


#============================================
# CLASSIC_REFERENCE profile tests
#============================================

def test_classic_deterministic_same_seed():
    """Two GameMaps with classic_reference profile and same seed are identical."""
    gm1 = _make_map(seed=42, profile='classic_reference')
    gm2 = _make_map(seed=42, profile='classic_reference')
    assert _corner_grid_signature(gm1) == _corner_grid_signature(gm2)


def test_classic_seed_variety():
    """Different seeds with classic_reference produce different maps."""
    gm1 = _make_map(seed=1, profile='classic_reference')
    gm2 = _make_map(seed=2, profile='classic_reference')
    assert _corner_grid_signature(gm1) != _corner_grid_signature(gm2)


@pytest.mark.parametrize('seed', [1, 2, 42])
def test_classic_smooth_slopes(seed):
    """8-neighbor smoothness constraint holds for classic_reference."""
    gm = _make_map(seed=seed, profile='classic_reference')
    assert _smoothness_holds(gm)


def test_classic_starts_from_water():
    """At least one corner is altitude 0 after classic_reference generation."""
    gm = _make_map(seed=1, profile='classic_reference')
    water_exists = any(
        gm.get_corner_altitude(r, c) == 0
        for r in range(gm.grid_height + 1)
        for c in range(gm.grid_width + 1)
    )
    assert water_exists


#============================================
# REMASTER_ISLANDS profile tests
#============================================

def test_remaster_deterministic_same_seed():
    """Two GameMaps with remaster_islands profile and same seed are identical."""
    gm1 = _make_map(seed=42, profile='remaster_islands')
    gm2 = _make_map(seed=42, profile='remaster_islands')
    assert _corner_grid_signature(gm1) == _corner_grid_signature(gm2)


@pytest.mark.parametrize('seed', [1, 2, 42])
def test_remaster_smooth_slopes(seed):
    """8-neighbor smoothness constraint holds for remaster_islands."""
    gm = _make_map(seed=seed, profile='remaster_islands')
    assert _smoothness_holds(gm)


@pytest.mark.parametrize('seed', [1, 2, 3, 4, 5])
def test_remaster_has_large_connected_landmass(seed):
    """Remaster profile produces at least one large connected land component."""
    gm = _make_map(seed=seed, profile='remaster_islands')
    land_tiles = gm._land_tile_set()
    components = gm._connected_components(land_tiles)
    largest = max((len(comp) for comp in components), default=0)
    assert largest >= 100, f"seed={seed}: largest component has {largest} tiles, need >= 100"


@pytest.mark.parametrize('seed', [1, 2, 3, 4, 5])
def test_remaster_passes_validation_for_fixed_seeds(seed):
    """Remaster profile passes validation for fixed test seeds."""
    gm = _make_map(seed=seed, profile='remaster_islands')
    passed = gm._validate_island_map()
    assert passed, f"seed={seed}: validation failed"


@pytest.mark.parametrize('seed', [1, 2, 3, 4, 5])
def test_remaster_has_buildable_floor(seed):
    """Remaster profile produces at least 30 buildable tiles (conservative floor)."""
    gm = _make_map(seed=seed, profile='remaster_islands')
    buildable = gm._count_buildable_tiles()
    assert buildable >= 30, f"seed={seed}: only {buildable} buildable tiles, need >= 30"


#============================================
# Moat invariant (both profiles)
#============================================

@pytest.mark.parametrize('profile', ['classic_reference', 'remaster_islands'])
@pytest.mark.parametrize('seed', [1, 2, 3, 4, 5])
def test_generator_keeps_water_moat(profile, seed):
    """Water moat (altitude 0) is enforced at grid edges for both profiles."""
    gm = _make_map(seed=seed, profile=profile)
    # Rows 0, 1 and grid_height-1, grid_height must all be water
    for r in [0, 1, gm.grid_height - 1, gm.grid_height]:
        for c in range(gm.grid_width + 1):
            assert gm.get_corner_altitude(r, c) == 0, (
                f"{profile} seed={seed}: corner ({r}, {c}) is not water"
            )
    # Columns 0, 1 and grid_width-1, grid_width must all be water
    for c in [0, 1, gm.grid_width - 1, gm.grid_width]:
        for r in range(gm.grid_height + 1):
            assert gm.get_corner_altitude(r, c) == 0, (
                f"{profile} seed={seed}: corner ({r}, {c}) is not water"
            )


@pytest.mark.parametrize('profile', ['classic_reference', 'remaster_islands'])
@pytest.mark.parametrize('seed', [1, 2, 3, 4, 5])
def test_generator_edge_tiles_are_water(profile, seed):
    """All edge tiles render as water (100% coverage, not fractional)."""
    gm = _make_map(seed=seed, profile=profile)
    # Row 0 tiles (use corners from rows 0 and 1)
    for c in range(gm.grid_width):
        tile_key = gm.get_tile_key(0, c)
        assert tile_key in terrain.WATER_TILE_KEYS, (
            f"{profile} seed={seed}: tile (0, {c}) renders as {tile_key}, not water"
        )
    # Row grid_height-1 tiles (use corners from rows grid_height-1 and grid_height)
    for c in range(gm.grid_width):
        tile_key = gm.get_tile_key(gm.grid_height - 1, c)
        assert tile_key in terrain.WATER_TILE_KEYS, (
            f"{profile} seed={seed}: tile ({gm.grid_height - 1}, {c}) not water"
        )
    # Column 0 tiles (use corners from columns 0 and 1)
    for r in range(gm.grid_height):
        tile_key = gm.get_tile_key(r, 0)
        assert tile_key in terrain.WATER_TILE_KEYS, (
            f"{profile} seed={seed}: tile ({r}, 0) not water"
        )
    # Column grid_width-1 tiles (use corners from columns grid_width-1 and grid_width)
    for r in range(gm.grid_height):
        tile_key = gm.get_tile_key(r, gm.grid_width - 1)
        assert tile_key in terrain.WATER_TILE_KEYS, (
            f"{profile} seed={seed}: tile ({r}, {gm.grid_width - 1}) not water"
        )


def test_raise_propagation_respects_locked_moat():
    """Moat corners remain locked at 0 even under aggressive raise propagation."""
    gm = _make_map(seed=1, profile='classic_reference')
    # Start over with a fresh all-zero map
    gm.set_all_altitude(0)
    # Apply many raise propagations at an interior point with the island cap
    for _ in range(200):
        gm.propagate_raise(r=2, c=2, max_altitude=gm._island_max_altitude)
    # Verify moat is still intact
    for r in [0, 1, gm.grid_height - 1, gm.grid_height]:
        for c in range(gm.grid_width + 1):
            assert gm.get_corner_altitude(r, c) == 0, (
                f"Moat corner ({r}, {c}) was raised above 0"
            )


#============================================
# Default profile is remaster_islands (no profile kwarg path)
#============================================

def test_default_profile_is_remaster_islands():
    """Calling randomize without an explicit profile must hit the
    new island generator. The remaster profile validates, so the
    default must produce a passing map for a fixed seed.
    """
    game = game_module.Game()
    game.game_map.randomize(seed=42)
    assert game.game_map._validate_island_map()
