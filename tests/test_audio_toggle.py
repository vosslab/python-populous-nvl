"""AudioManager toggle methods (M2 WP-M2-D)."""

import populous_game.audio as audio_module


def test_initial_audio_flags_default_off():
    """Fresh AudioManager has music off and SFX unmuted."""
    am = audio_module.AudioManager()
    assert am.is_music_playing is False
    assert am.is_sfx_muted is False


def test_toggle_music_flips_state():
    """toggle_music alternates is_music_playing."""
    am = audio_module.AudioManager()
    # Stays in silent mode under SDL_AUDIODRIVER=dummy without init().
    am.toggle_music()
    assert am.is_music_playing is True
    am.toggle_music()
    assert am.is_music_playing is False


def test_toggle_sfx_mute_flips_state():
    """toggle_sfx_mute alternates is_sfx_muted."""
    am = audio_module.AudioManager()
    am.toggle_sfx_mute()
    assert am.is_sfx_muted is True
    am.toggle_sfx_mute()
    assert am.is_sfx_muted is False


def test_play_sfx_respects_mute():
    """When muted, play_sfx does not invoke the underlying sound."""
    am = audio_module.AudioManager()
    am.silent = False  # pretend mixer initialized
    calls = {'count': 0}

    class _DummySound:
        def play(self):
            calls['count'] += 1

    am._sfx['ui_click'] = _DummySound()
    # Unmuted call: play once.
    am.play_sfx('ui_click')
    assert calls['count'] == 1
    # Muted call: suppressed.
    am.toggle_sfx_mute()
    am.play_sfx('ui_click')
    assert calls['count'] == 1, (
        f"play_sfx fired while muted; total calls={calls['count']}"
    )
    # Unmuted again: fires.
    am.toggle_sfx_mute()
    am.play_sfx('ui_click')
    assert calls['count'] == 2
