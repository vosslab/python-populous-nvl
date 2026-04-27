"""Sleep button toggles simulation pause (M2 WP-M2-E)."""

import populous_game.game as game_module


def test_sleep_pauses_from_playing():
    """In PLAYING, click _sleep -> PAUSED."""
    g = game_module.Game()
    g.app_state.transition_to(g.app_state.PLAYING)
    g.input_controller._handle_ui_click('_sleep')
    assert g.app_state.is_paused()


def test_sleep_resumes_from_paused():
    """In PAUSED, click _sleep -> PLAYING."""
    g = game_module.Game()
    g.app_state.transition_to(g.app_state.PLAYING)
    g.input_controller._handle_ui_click('_sleep')
    assert g.app_state.is_paused()
    g.input_controller._handle_ui_click('_sleep')
    assert g.app_state.is_playing()


def test_sleep_in_menu_is_noop():
    """In MENU, sleep does nothing (defensive)."""
    g = game_module.Game()
    assert g.app_state.is_menu()
    g.input_controller._handle_ui_click('_sleep')
    assert g.app_state.is_menu()
