"""UI options (music, FX) must not change simulation outcomes.

Sleep is intentionally allowed to change tick progression and is
excluded here. Music and FX toggles must produce the exact same
simulation digest at the same seed and the same input sequence.
"""

import random
import populous_game.game as game_module
import populous_game.faction as faction


def _digest(game):
    """Hashable summary of simulation state for equality comparison."""
    return (
        tuple(tuple(row) for row in game.game_map.corners),
        tuple(
            (p.state, round(p.x, 4), round(p.y, 4), round(p.life, 3),
             p.faction_id, p.weapon_type, p.dead)
            for p in game.peeps
        ),
        tuple(
            (h.faction_id, h.destroyed, getattr(h, 'tile_r', None),
             getattr(h, 'tile_c', None))
            for h in game.game_map.houses
        ),
        game.mana_pool.get_mana(faction.Faction.PLAYER),
        game.mana_pool.get_mana(faction.Faction.ENEMY),
    )


def _boot(seed):
    g = game_module.Game()
    g.game_map.randomize(seed=seed)
    g.app_state.transition_to(g.app_state.PLAYING)
    g.peeps.clear()
    random.seed(seed + 7)
    g.spawn_initial_peeps(8)
    g.spawn_enemy_peeps(8)
    return g


def _advance(game, frames=30, dt=1.0/60.0):
    for p in list(game.peeps):
        p.update(dt)


def test_music_toggle_does_not_change_digest():
    """Toggling music does not affect the simulation outcome."""
    a = _boot(seed=1234)
    b = _boot(seed=1234)
    assert _digest(a) == _digest(b)
    # B toggles music a few times.
    b.audio_manager.toggle_music()
    b.audio_manager.toggle_music()
    b.audio_manager.toggle_music()
    # Advance both the same number of frames.
    _advance(a, 30)
    _advance(b, 30)
    assert _digest(a) == _digest(b), (
        "Music toggle changed simulation digest; UI options must be "
        "presentation-only."
    )


def test_sfx_mute_toggle_does_not_change_digest():
    """Toggling SFX mute does not affect the simulation outcome."""
    a = _boot(seed=5678)
    b = _boot(seed=5678)
    b.audio_manager.toggle_sfx_mute()
    b.audio_manager.toggle_sfx_mute()
    b.audio_manager.toggle_sfx_mute()
    _advance(a, 30)
    _advance(b, 30)
    assert _digest(a) == _digest(b)
