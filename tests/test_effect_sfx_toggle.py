"""FX button toggles audio.is_sfx_muted; play_sfx respects the mute (M3 WP-M3-C).

Patches the underlying mixer.Sound.play call to count invocations
rather than relying on pygame.mixer.music.get_busy() under
SDL_AUDIODRIVER=dummy.
"""

import tools.headless_runner as runner


def test_fx_button_toggles_mute():
    game = runner.boot_game_for_tests(state='gameplay', seed=8888, players=2)
    assert game.audio_manager.is_sfx_muted is False
    game.input_controller._handle_ui_click('_fx')
    assert game.audio_manager.is_sfx_muted is True
    game.input_controller._handle_ui_click('_fx')
    assert game.audio_manager.is_sfx_muted is False


def test_play_sfx_suppressed_while_muted():
    """When muted via the FX button, subsequent play_sfx is suppressed."""
    game = runner.boot_game_for_tests(state='gameplay', seed=9999, players=2)
    am = game.audio_manager
    am.silent = False  # pretend mixer initialized so play_sfx attempts to play
    calls = {'count': 0}

    class _DummySound:
        def play(self):
            calls['count'] += 1

    am._sfx['ui_click'] = _DummySound()
    # Unmuted: fires.
    am.play_sfx('ui_click')
    assert calls['count'] == 1
    # Click _fx to mute.
    game.input_controller._handle_ui_click('_fx')
    am.play_sfx('ui_click')
    assert calls['count'] == 1, (
        "play_sfx fired while FX button toggled mute on"
    )
    # Click _fx again to un-mute.
    game.input_controller._handle_ui_click('_fx')
    am.play_sfx('ui_click')
    assert calls['count'] == 2
