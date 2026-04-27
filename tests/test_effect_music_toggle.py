"""Music button toggles audio.is_music_playing (M3 WP-M3-C).

Asserts the game's own state flag rather than `pygame.mixer.music.get_busy()`,
which is unreliable under SDL_AUDIODRIVER=dummy.
"""

import tools.headless_runner as runner


def test_music_button_toggles_state():
    """Click _music: is_music_playing flips True. Click again: flips False."""
    game = runner.boot_game_for_tests(state='gameplay', seed=7777, players=2, enemies=2)
    assert game.audio_manager.is_music_playing is False
    game.input_controller._handle_ui_click('_music')
    assert game.audio_manager.is_music_playing is True
    game.input_controller._handle_ui_click('_music')
    assert game.audio_manager.is_music_playing is False
