"""Menu-Enter must not mutate the randomized heightmap.

Locks in the M1 fix: the previous handler called
`set_all_altitude(3)` which silently overwrote the generator output and
hid all water. After M1, the menu-Enter transition must preserve every
corner altitude exactly as `randomize()` produced it.
"""

import pygame
import populous_game.game as game_module


def _heightmap_signature(game_map):
    """Tuple-of-tuples snapshot for equality comparison."""
    return tuple(tuple(row) for row in game_map.corners)


def _post_event(key):
    """Inject a KEYDOWN event for the given pygame key."""
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))


def test_menu_enter_does_not_mutate_heightmap():
    """The menu-Enter transition leaves the randomized heightmap intact."""
    game = game_module.Game()
    # Re-randomize with a fixed seed so the snapshot is deterministic.
    game.game_map.randomize(seed=42)
    pre = _heightmap_signature(game.game_map)
    # Confirm the snapshot has both water and land; otherwise the
    # downstream assertion is uninteresting.
    has_water = any(0 in row for row in game.game_map.corners)
    has_land = any(any(v > 0 for v in row) for row in game.game_map.corners)
    assert has_water and has_land, (
        "test seed produced a uniform heightmap; pick a different seed"
    )
    # Drive a menu-Enter event through the input controller.
    _post_event(pygame.K_RETURN)
    game.input_controller.poll()
    # Snapshot afterwards.
    post = _heightmap_signature(game.game_map)
    assert post == pre, (
        "menu-Enter mutated at least one corner altitude; the M1 fix "
        "requires the generator output to be preserved"
    )


def test_menu_enter_transitions_to_playing():
    """Menu-Enter still transitions app_state to PLAYING (regression)."""
    game = game_module.Game()
    game.game_map.randomize(seed=42)
    assert game.app_state.is_menu()
    _post_event(pygame.K_RETURN)
    game.input_controller.poll()
    assert game.app_state.is_playing()


def test_menu_enter_spawns_peeps():
    """Menu-Enter still spawns initial player and enemy peeps (regression)."""
    game = game_module.Game()
    game.game_map.randomize(seed=42)
    assert len(game.peeps) == 0
    _post_event(pygame.K_RETURN)
    game.input_controller.poll()
    # Initial spawn is 10 player + 10 enemy per the menu handler.
    assert len(game.peeps) == 20
