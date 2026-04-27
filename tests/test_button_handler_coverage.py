"""Every button in ui_panel.buttons must route to a real handler.

Locks in the no-silent-stubs rule (M2 WP-M2-B): the previous `pass`
stub branch in `input_controller._handle_ui_click` allowed clicks to
no-op silently. After M2, every action key must produce a behavior
delta when clicked.
"""

import populous_game.game as game_module


def _snapshot(game):
    """Capture the bag of state fields that count as a behavior delta."""
    return {
        'app_state': game.app_state.current,
        'pending_power': game.mode_manager.pending_power,
        'papal_mode': game.mode_manager.papal_mode,
        'shield_mode': game.mode_manager.shield_mode,
        'last_button_click': game.last_button_click,
        'camera_r': game.camera.r,
        'camera_c': game.camera.c,
        'is_music_playing': game.audio_manager.is_music_playing,
        'is_sfx_muted': game.audio_manager.is_sfx_muted,
        'tooltip_count': len(game.input_controller.tooltip_messages),
    }


def test_every_button_has_a_real_handler():
    """Clicking each button changes at least one observable field."""
    game = game_module.Game()
    game.app_state.transition_to(game.app_state.PLAYING)
    game.spawn_initial_peeps(5)
    failures = []
    for action in list(game.ui_panel.buttons.keys()):
        pre = _snapshot(game)
        game.input_controller._handle_ui_click(action, held=False)
        post = _snapshot(game)
        if pre == post:
            failures.append(action)
    assert not failures, (
        f"Buttons routed to a no-op handler (silent stubs): {failures}. "
        f"Either wire a real behavior or remove the button from "
        f"ui_panel.buttons."
    )
