# KNIGHT_REPORT - Analysis of `_do_knight` in Populous Amiga

## 1. Purpose

This report documents the ASM routine associated with the knight power in the original game code, with the goal of serving as a faithful reference for a Python implementation.

Files analyzed:
- [asm/populous_prg.asm](asm/populous_prg.asm)
- [asm/populous_prg.cnf](asm/populous_prg.cnf)
- [asm/ARCHITECTURE_REPORT.md](asm/ARCHITECTURE_REPORT.md)

## 2. Summary

ASM-confirmed behavior:
- `_do_knight` checks target validity and global state gates.
- It awards 150 points when the target matches the player.
- It writes to internal magnet/leader-related state.
- It applies a transformation to the target peep.

Python implementation behavior:
- the current code doubles a player peep's life,
- marks it with `weapon_type = 'knight'`,
- prefers the selected peep when one is already selected,
- otherwise falls back to a live player peep that the current UI can reach,
- and can send the promoted peep marching toward an enemy if one exists.

Inferred compatibility choices:
- the UI does not expose an ASM-style raw peep-id selector, so the current code
  uses the selected peep when available and otherwise falls back to a live
  player peep that fits the current interaction model.
- the knight search button keeps cycling through promoted peeps using the
  existing cursor-based UI pattern.

Remaining deviation:
- the hidden magnet/leader bookkeeping is only represented through existing
  selection and shield-target state. A dedicated low-level magnet model is not
  present in the current codebase, so that part remains approximate.

## 3. ASM Entry Point

Symbol address:
- `_do_knight`: `$0004422A` ([asm/populous_prg.cnf](asm/populous_prg.cnf))

In the assembly analysis, the routine starts by checking that the target exists and that certain game conditions allow activation.
If those conditions are not met, the function returns without doing anything.

## 4. Observed Effects

### 4.1 Target validation

The routine indexes the target from a peep identifier, then reads internal structures associated with the magnet.
If the target is not valid, the routine exits immediately.

### 4.2 Context gating

The routine tests several global states before continuing:
- drawing mode or map state,
- war or pause,
- the presence of a local flag associated with the peep.

These checks show that knight is not a simple local buff; it depends on global game context.

### 4.3 Score modification

If the target matches the player, the routine adds 150 points to the score.

Direct evidence:
- ASM comment `+150 points for knight` in [asm/populous_prg.asm](asm/populous_prg.asm)

### 4.4 Internal peep marking

The routine writes into auxiliary structures associated with the peep and the magnet.
That suggests knight is also a state transformation, not just a stat increase.

## 5. Match with the Current Python Code

The current Python path is in [populous_game/powers.py](../populous_game/powers.py).
It already does the following:
- prefers the currently selected player peep when the UI has one,
- otherwise falls back to a live player peep when the current UI
  path does not supply an explicit peep id,
- increases its life,
- marks it as a knight via `weapon_type`,
- gives it an enemy target if possible.

The shipped Python implementation now also:
- awards the 150-point knight bonus,
- refuses to activate outside active play,
- refuses to re-promote an already-knighted peep,
- keeps the knight discoverable through `_find_knight`,
- keeps button and hotkey activation on the same path.

Deliberate deviation from the ASM reference:
- the internal magnet/leader bookkeeping is only represented through the
  existing selection and shield-target state. It is documented here as an
  approximate compatibility choice, not as full ASM parity.
- knight mana cost and cooldown remain project-level balancing values;
  the ASM trace in this repo confirms the score bonus and control flow
  for `_do_knight`, but does not provide a separate cited cost/cooldown
  constant to mirror here.

## 6. Implications for a Future Implementation

If the goal is a more historically faithful translation, the work should not be limited to `powers.py`.
It will likely involve:
- [populous_game/powers.py](../populous_game/powers.py)
- [populous_game/selection.py](../populous_game/selection.py)
- [populous_game/input_controller.py](../populous_game/input_controller.py)
- [populous_game/peeps.py](../populous_game/peeps.py)
- tests for score, state, and targeting behavior
The visible gameplay contract is now implemented; any future work here is limited to deeper ASM bookkeeping if that ever becomes externally observable.

## 7. Conclusion

The ASM knight power is a transformation routine with effects on score, context, and internal peep state.
The current Python code captures the general idea, but not the full original routine.
