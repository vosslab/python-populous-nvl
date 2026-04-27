# M2 button gaps

Tracks UI buttons removed from the clickable hit-test map during M2
because the original Populous mechanic does not exist in the current
Python codebase. Per the no-silent-stubs rule
(/Users/vosslab/.claude/plans/scalable-marinating-nebula.md), each gap
is either implemented fully or removed; tooltip-only stubs are not
allowed at milestone exit.

## Removed in M2

### `_find_shield`

- Removed from `populous_game/ui_panel.py` `self.buttons`.
- Original Populous semantics: jump the camera to the current player
  shield bearer (the walker or settlement holding the shield).
- Why removed: the codebase has no shield-bearer concept. There is no
  `peep.has_shield` attribute, no `house.has_shield` attribute, and no
  module that tracks "the shield." `populous_game/mode_manager.py`
  exposes a `shield_mode` toggle for shield-panel display, but that is
  unrelated to a positional bearer.
- To restore: add a shield-bearer concept to peeps and houses
  (decision: walker-only, structure-only, or both). When a player
  casts shield, mark the chosen peep or settlement as the bearer.
  `selection.find_shield_bearer(game)` then returns its grid coord.

### `_battle_over`

- Removed from `populous_game/ui_panel.py` `self.buttons`.
- Original icon meaning: unconfirmed at time of M2. Player guides
  variously describe the icon as "fight then settle" or as a
  cancel-fight reset.
- Why removed: per DQ-7 in the plan, no invented behavior. The repo
  has no clear matching mechanic (no global "battle" tracker, no
  cancel-fight bulk transition with a stable name).
- To restore: confirm the original icon meaning by inspecting the
  Amiga sprite or the asm reference, then either wire to an existing
  follower-mode toggle or scope a separate plan to add the missing
  mechanic.

## Notes

These removals are intentionally visible in `tests/test_no_silent_button_stubs.py`
and `tests/test_button_gaps_match_hit_test.py`. If a future patch
re-adds the button to `ui_panel.buttons` without wiring a real handler,
both tests will fail.
