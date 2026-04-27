"""No clickable button is a silent stub.

Stronger version of test_button_handler_coverage.py: instead of
checking for any state delta, this test enumerates the specific
observable channels (game state, audio state, camera, mode_manager,
pause flag, tooltip queue) and asserts each click changes at least
one of them.
"""

import populous_game.game as game_module
import populous_game.peep_state as peep_state


def _channels(game):
    """Return a tuple of every channel a button may move."""
    return (
        game.app_state.current,
        game.app_state.is_paused(),
        game.mode_manager.pending_power,
        game.mode_manager.papal_mode,
        game.mode_manager.shield_mode,
        game.audio_manager.is_music_playing,
        game.audio_manager.is_sfx_muted,
        (game.camera.r, game.camera.c),
        len(game.input_controller.tooltip_messages),
        # Peep-state distribution; bulk go-buttons move this counter.
        tuple(sum(1 for p in game.peeps if p.state == s) for s in peep_state.PeepState.ALL),
        # Knight count: _do_knight bumps weapon_type='knight' on a peep.
        sum(1 for p in game.peeps if getattr(p, 'weapon_type', None) == 'knight'),
        # Power cooldowns: a successful divine-intervention click sets
        # one. Snapshot as a sorted tuple so order is stable.
        tuple(sorted(game.power_manager.cooldowns.items())),
    )


def _prep_for(action, game):
    """Per-button preconditions so each click has work to do.

    The no-silent-stubs invariant is "every click produces an
    observable change in valid runtime conditions"; this helper sets
    up valid conditions for buttons whose effect would otherwise be a
    legitimate no-op (e.g., _raise_terrain when already in default
    mode, or a dpad click when the camera is already at the boundary).
    """
    if action == '_raise_terrain':
        # Set a pending power so _raise_terrain has something to clear.
        game.mode_manager.pending_power = 'quake'
    elif action == '_find_papal':
        # Move camera away from the magnet so the find jump is observable.
        game.camera.r, game.camera.c = 0.0, 0.0
        game.mode_manager.set_papal_position(20, 20)
    elif action in ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'):
        # Park the camera off all four edges so any dpad direction can move.
        game.camera.r = 10.0
        game.camera.c = 10.0


def test_no_button_is_silent():
    """Click each button under valid runtime conditions; one channel must move."""
    game = game_module.Game()
    game.app_state.transition_to(game.app_state.PLAYING)
    game.spawn_initial_peeps(8)
    game.spawn_enemy_peeps(8)
    # Give the player some mana so divine-intervention powers can fire.
    import populous_game.faction as faction
    game.mana_pool.add(faction.Faction.PLAYER, 1000)
    silent = []
    for action in list(game.ui_panel.buttons.keys()):
        _prep_for(action, game)
        before = _channels(game)
        game.input_controller._handle_ui_click(action, held=False)
        after = _channels(game)
        if before == after:
            silent.append(action)
    assert not silent, (
        f"Silent stubs (clicks produced no observable effect): {silent}"
    )
