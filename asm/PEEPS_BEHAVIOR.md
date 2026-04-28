# PEEPS_BEHAVIOR - ASM Peep Behavior Notes

This note documents the original Populous Amiga peep behavior as it is
implemented in `asm/populous_prg.asm`. It is source-based, not a
description of the current Python translation.

## Scope

Covered routines:
- `_move_peeps`
- `_move_explorer`
- `_where_do_i_go`
- `_join_forces`
- `_zero_population`
- `_place_people`
- `_place_first_people`
- `_move_magnet_peeps`
- `_set_frame`
- `_check_life`
- `_valid_move`
- `_set_town`
- `_set_battle`
- `_join_battle`
- `_do_battle`
- `_set_magnet_to`

Direct support routines and labels that shape peep behavior:
- `_get_heading`
- `_one_block_flat`
- `_make_level`
- `_battle_over`
- `_do_place_funny`
- `_set_devil_magnet`
- `_devil_effect`
- `_do_magnet`
- `_do_war`
- `_do_knight`
- `_do_swamp`
- `_do_volcano`
- `_do_quake`
- `_do_lower_point`
- `_do_raise_point`
- `_kill_effect`
- `_check_effect`

## Data Layout

The ASM uses a peep stride of `0x16` bytes.
Frequently used fields:
- `+0`: flags and state bits
- `+1`: owner / faction
- `+2`: movement substate
- `+3`: weapon / strength tier
- `+4`: life / energy
- `+6`: local timer or frame index
- `+8`: map position index
- `+A`: movement offset
- `+C`: growth / town counter
- `+E`: linked peep or alliance reference
- `+12`: remembered target position
- `+14`: auxiliary terrain marker

The source also uses per-faction tables indexed by `owner * 0x10` or
`owner * 0x2e`, plus per-peep state arrays indexed by `peep * 0x16`.

## `_move_peeps`

`_move_peeps` is the main per-frame update loop for peeps.

Entry and pre-loop behavior:
- increments `_game_turn`
- for players `0` and `1`, calls `_set_devil_magnet` and `_devil_effect`
  only when `LAB_516AC[player * 0x2e]` is zero
- recomputes per-faction population and leader tables from `good_castles`
  and `good_towns`
- clears `LAB_516CE`, `LAB_516CA`, `LAB_516C6`, and zeroes several
  local per-player scratch arrays
- if `_toggle` is nonzero, increments `LAB_52DF0[player * 0x10]`
- clears `LAB_53018/20/22` trailing records when peeps are removed
- seeds `LAB_4E1F` into a stack slot used later for frame selection
- removes dead tail entries by decrementing `_no_peeps` until the last
  record has life in `LAB_53018`
- updates `_magnet` for the active player and `_not_player` if the
  owning faction has a magnet, but only when the target faction record
  exists in `LAB_53022`
- when `_war` is nonzero, forces `_god_magnet`, `_devil_magnet`,
  `LAB_52DF6`, and `LAB_52DE6` to `0x0820`
- if bit 3 of `_sound_effect` is set, `_effect` becomes
  `_toggle + 0x43`
- if bit 7 of `_sound_effect` is set, `_effect` becomes `0x46` on the
  first activation and `_last_fire` is reloaded to `3`; otherwise
  `_last_fire` counts down to zero

Main peep loop:
- loops from `0` to `_no_peeps - 1`
- skips peeps with life `<= 0`
- adds life to `good_pop[owner]`
- computes the tile pointer as `_map_blk + peep->+8`
- if bit 4 of the peep flag byte is set:
  - and `LAB_518A7` bit 0 is set, calls `_zero_population` immediately
    and skips the rest of the record
  - otherwise, if `LAB_516AA[owner * 0x2e] == 1` and
    `LAB_518A7` bit 2 is clear or `_war` is nonzero, it marks
    `stats[owner] = 1`, stores `peep->+8 & 0x3f` and `peep->+8 >> 6`
    in `LAB_516A5/LAB_516A6`, and sets `LAB_516AC[owner * 0x2e] = 1`
  - subtracts `_walk_death * 2` from life
  - if the tile pointer byte is nonzero, clears bit 4, calls `_set_frame`,
    and continues with the post-frame branch
  - otherwise it jumps directly to the zero-population cleanup path
- if the tile byte is zero:
  - and bit 0 of the peep is set, calls `_set_town(1)` before marking
    the peep as state `0x12`
  - if `+C >= 8`, clears `+C`
  - if bit 2 is set, calls `_set_frame`; if `_set_frame` returns nonzero
    it clears bit 2, calls `_set_frame` again, and then zero-populates
  - if the peep is type `0x01`, it calls `__check_life(owner, peep->+8)`
    and stores the result in a local threshold slot:
    - `<= 0` or a nonzero `+E` or `_war != 0` goes to the "town-like"
      path, which clears bit 0, sets bit 1, zeroes `+C` and `+A`, calls
      `_set_town(1)`, and ends the peep with `_zero_population`
    - otherwise, if the result is at least `0x0BEA`, the peep's
      `(-40 + owner*2)` counter increments and `+C` is set to `0x2A`
    - otherwise `+C` becomes `((life * 10) / 0x0131) + 0x20`
    - in both nonzero-life cases, `map_who` is written with `peep index + 1`
      when the tile is empty, and the per-faction `LAB_516C6/CA/CE`
      history tables are updated when the new value is lower or first set
    - once `+C` is large enough, the routine increments `_view_who`,
      optionally increments `_funny_done` through `_do_place_funny`,
      and adds the per-state amount from `_population_add` to `+4`
  - if `_toggle` is nonzero and the peep belongs to the local player or
    serial play is disabled, `_a_putpixel` is called at the tile with a
    color derived from the owner and faction parity
  - if `+C` equals the stored threshold and `_a_flat_block` is clear,
    `_set_town` is called
  - if type is `0x02`, `_set_frame` is called; on success, a special
    `0x35` tile zero-populates the peep and sets `_effect = 0x42`,
    otherwise the routine may convert the peep into state `0x01`,
    sync `LAB_516CA`, and call `_one_block_flat` before `_move_explorer`
  - after `_move_explorer`, if `+12` is set and the direction changes,
    `+12` is cleared
  - subtracts `_walk_death` from life
- if type is not `0x01` or `0x02`:
  - when the frame/state byte has bits `0x60` set, `_set_frame` is
    called; bit 3 set to `0x08` drives `_do_battle`, otherwise the code
    falls through
  - when bit 7 is set, `map_who` is updated if the tile is empty and
    `+6` counts down; once `+6` reaches zero, life is cleared
- after the per-peep branch, if life `<= 0`, `_zero_population` is called

End-of-loop behavior:
- after iterating all peeps, if the local player still has population in
  `good_pop`, the game ends with `__end_game(1)` when `_surender`
  matches the player
- the same check is repeated for `_not_player`, and `__end_game(0)` is
  called when appropriate
- copies `LAB_52DEA` and `LAB_52DE2` into `good_towns`, `good_castles`
  and syncs the per-faction summary arrays
- every eighth turn, if `_cheat` is set, it displays `CHEAT` and then
  clears `_cheat`

## `_move_explorer`

`_move_explorer` handles explorer-style movement.

Major branches:
- if `LAB_52DE8[owner * 0x10]` is nonzero, or the peep has a nonzero
  `+E` and `_war` is clear, it uses `_move_magnet_peeps`
- otherwise it uses `_where_do_i_go`
- if the returned direction is `0x03e7`, it sets bit 6 in the peep
  flags and sets `+6 = 7`, then returns
- otherwise it clears bit 6 from the peep, subtracts the old map-who
  owner marker if this tile belonged to the current peep, and continues

Post-move branches:
- if `LAB_516AA[owner * 0x2e] == 1`, `map_blk[tile] == 0x42`,
  `LAB_516AC[owner * 0x2e] == 0`, and `( _game_mode & 0x0c ) == 0`,
  it marks `stats[owner] = 2`, stores tile coordinates into
  `LAB_516A5/LAB_516A6`, and leaves the record in the active explorer
  state
- if the destination tile is occupied:
  - `+14` zero and `map_blk` is empty or `0x10` are the only cases that
    avoid a secondary block write to `map_bk2`
  - if the peep has `+14 != 0` and the tile matches `+C`, the routine may
    call `_make_level` and store its result in `+14`
  - if the target has `+C == 0x2a`, `LAB_516AA` is `1`,
    `+4 > 0x0131`, and `LAB_516AC` is clear, it clamps `+4` to `0x0131`
    and sets `LAB_516AC`
- every eighth game turn, if `+C == 0x2a`, `LAB_516AA == 1`, `+4 >
  0x0131`, and `LAB_516AC` is clear, the cap is applied as above
- `_cheat` can force `+4 = 0x32` when the owner matches the cheat slot
- `_mana_add` and `_weapons_add` are applied to `_magnet`, `+3`, and `+4`

Collision and ownership branches:
- when the target tile contains another peep:
  - if the target has bit 3 set, `_join_battle` is called
  - if the two peeps share an owner, `_join_forces` is called
  - otherwise `_set_battle` is called and the routine returns early
- when no target peep exists:
  - if the current peep has bit 0 set, `_set_town(0)` is called unless
    `_a_flat_block` and `_all_of_city` veto the transition
  - if `LAB_518A7` bit 1 is set and the target is the special `0x35`
    tile, the tile is converted to `0x0f` and the peep is zero-populated
    with effect `0x42`
  - if bit 2 is set, `_set_frame` is called, and if it returns nonzero
    bit 2 is cleared and `_set_frame` is called again
- after the post-move branch, `_population_add` is added to `+4`
- if the destination tile matches the stored `+C` threshold and
  `_a_flat_block` is clear, `_set_town(0)` is called

Uncertain behavior to revisit:
- `LAB_40994` through `LAB_40FCE` contains a large amount of shared
explorer state sync, including the full `_one_block_flat` and
`_make_level` interaction. The current source pass shows the branch
conditions, but the exact semantic grouping across `LAB_40994`,
`LAB_40CBE`, and `LAB_40F22` should be revisited if the Python port needs
strict parity.

## `_where_do_i_go`

`_where_do_i_go` is a local movement heuristic.

Main flow:
- initializes the best cost to `0x270f`
- seeds the five candidate slots in the local stack buffer with `5`
- iterates candidate directions in a random order on the first pass
- for each direction, calls `__valid_move` with the offset from
  `_offset_vector`

Branch logic:
- if `_valid_move` returns nonzero, the direction is skipped
- when the initial offset is legal:
  - the code prefers paths with `_map_blk == 0x0f`
  - first direction `0` performs an immediate `_check_life`
  - when `_check_life` succeeds, the current best distance and selected
    delta are stored and the routine jumps to the return path
- on the alternate search path:
  - it scans directions `9` through `16`
  - if `_valid_move` passes, `_map_bk2` at the destination is read
  - values in the range `0x21..0x2c` become the candidate score
  - scores outside that range are ignored
- if no better candidate was found, the routine falls back to the
  opposite direction tables

Data reads and writes:
- reads `_offset_vector`, `_to_offset`, `_opposite`, `_map_blk`,
  `_map_bk2`, and `_map_steps`
- writes the local best-cost slots at `-12`, `-10`, `-8`, `-6`,
  `-4`, `-2`, `-14`, `-16`, `-18`, `-20`, `-22`, `-24`, `-26`,
  `-28`, `-30`, `-32`
- writes `($15,A2)` with the selected facing byte before returning

Return conditions:
- returns `0x03e7` when no usable candidate survives the scan
- otherwise returns the selected offset from `_to_offset`

Uncertain behavior to revisit:
- `LAB_41706` to `LAB_41D72` is heavily branch-compressed and mixes
  cost comparison, tile class checks, and direction memory. If this note
  is used to port movement exactly, that span should be re-read with the
  cross-referenced offset tables open.

## `_move_magnet_peeps`

`_move_magnet_peeps` moves a peep toward a faction magnet or leader.

Branch structure:
- if `+E` is nonzero:
  - if the linked peep is on the same tile, has no life, shares the same
    owner, or has bit 7 set, the routine calls `_get_heading`
  - otherwise it derives `(-10)` and `(-12)` from the linked peep's
    tile delta and returns into the shared path
- if `+E` is zero and `_magnet[owner]` is zero, the routine falls back
  to the local heading logic using `LAB_52DE6`
- if `_magnet[owner]` is nonzero, it compares against the stored magnet
  target and, when the target is the current peep's owner slot, updates
  `_magnet` and `_view_who`
- if the linked target's `+14` is set, the routine also copies the
  magnet-facing state into `LAB_516C2` and `LAB_516C0`

Behavioral effects:
- `LAB_52DE6` and `_magnet` are used as the leader coordinates
- the routine prefers directions that reduce both x and y distance
  relative to the magnet target
- it uses `_valid_move` on candidate offsets generated from
  `_to_offset` / `_opposite`
- if the destination tile has a matching `_map_blk` and the linked peep
  is a builder, it preserves the facing byte in `+15`
- on success it writes the chosen facing byte to `+15` and returns the
  chosen offset
- on failure it returns `0x03e7`

Uncertain behavior to revisit:
- the `LAB_41A9E` through `LAB_41CF6` branch ladder combines linked-peep
  steering, magnet ownership, and direction preference. The exact
  priority ordering among the fallback candidates is readable in ASM but
  still worth a second semantic pass if Python parity is the goal.

## `_join_forces`

`_join_forces` merges two same-faction peeps.

Branch behavior:
- resolves the source and destination peeps from the two indexes
- if the source has a nonzero `+E` and the destination is not type `1`,
  the destination inherits the source's `+E`
- adds life values together and clamps the target at `0x7d00`
- updates `_view_who` when the source was the current view target
- if the source index is greater than the destination index, subtracts
  the source life from `good_pop[owner]`
- copies the stronger `+3` weapon tier into the destination
- zeroes the source life
- clears bit 7 from the destination and clears its `+C`

Reads and writes:
- reads and writes `+4`, `+3`, `+E`, `+8`, `+C`, and flags
- reads `_magnet`, `_view_who`, and `good_pop`

Early return:
- if the source has `+E` and the destination peep is type `1`, the
  routine returns after the inheritance check without merging life

## `_zero_population`

`_zero_population` removes a peep and clears its traces.

Branch behavior:
- sets `+4` to zero immediately
- if the peep is type `8`, clears bit 3 from the peep pointed to by
  `+6`
- if bit 0 is set, calls `_set_town(1)`
- clears `map_who` at the main tile when the recorded owner matches
  the peep's owner slot
- clears `map_who` again at `tile - +A` when the recorded owner matches
- if the peep is the current owner of `_magnet`, clears that magnet
  entry and calls `_set_magnet_to(tile, owner)` to re-anchor it
- clears `_view_who` when the current view target is this peep

Side effects:
- no score changes
- may indirectly change town state through `_set_town(1)`
- may change magnet target state through `_set_magnet_to`

## `_place_people`

`_place_people` allocates or replaces a peep.

Entry checks:
- returns immediately if `_no_peeps >= 0x00d0`
- if the caller passed a nonzero `+E` and the current tile already has a
  magnet for the owner, the existing peep is zero-populated first

Initialization branches:
- otherwise the current `_no_peeps` value becomes the new peep index and
  `_no_peeps` is incremented
- initializes `LAB_5301A`, `LAB_53018`, `LAB_5301C`, `LAB_53015`,
  `LAB_53016`, `LAB_53017`, `LAB_5301E`, `LAB_53020`, `LAB_53022`
- sets peep type `+2 = 0x02`
- sets `+20 = 0xff`
- if a magnet placement is active, `_magnet[owner]` is updated to
  `new index + 1`
- stores `+0?` initial state through `_set_frame`

Spawn side effects:
- writes `map_who[tile] = new index + 1`
- stores the passed tile in `+8`
- stores the passed x/y in `+A` and `+C`
- calls `_set_frame` at the end of successful initialization
- on replacement, the old peep is zero-populated before the new peep is
  written into the same tile

## `_place_first_people`

`_place_first_people` places the initial population.

Branch behavior:
- computes the initial count from conquest / serial / menu state
- if `_player == 0`, awards `+10 * count` to `_score`
- scans `_map_blk` from `0x0080` upward for spawn tiles with byte `0x0f`
  and calls `_place_people` until the quota is met
- if there are still peeps remaining, scans `_map_blk` from `0x0000`
  upward for free valid tiles in the same way
- if the conquest mode branch is active, it uses `conq_07_enemypop`
  instead of the default count logic
- if `_player == 1`, also awards `+10 * count` to `_score`
- the final search scans downward from `0x0f80` and then upward from
  `0x1000` for free tiles, again calling `_place_people`

Tile conditions:
- one branch requires `_map_blk[tile] == 0x0f`
- another branch requires `_map_blk[tile]` nonzero and `map_who[tile]`
  zero
- each placement call passes the current remaining count as the
  leading argument so `_place_people` can record the owner index

Score side effects:
- player 0 and player 1 each receive `+10` per placed peep in the
  corresponding branch

## `_set_frame`

`_set_frame` advances or resets a peep's animation / state timer.

Branch behavior:
- returns `0` immediately when `+4 <= 0`
- if type is `0x02`, increments `+C`; once `+C` reaches `7`, it resets
  `+C` to `0` and returns `1`
- if bit 4 is set, increments `+C`; values below `0x5d` return `0`,
  values `0x5d..0x60` continue, and values above `0x60` clamp back to
  `0x5d` and return `1`
- if bit 3 is set, the routine computes a frame threshold based on the
  linked peep and owner:
  - when both linked peeps have `+E`, returns `0x8a`
  - when only the source has `+E`, returns `0x82` or `0x86`
  - otherwise uses `0x46`
  - increments `+C` and clamps it to the threshold, returning `1` when
    the threshold is reached
- if type is `0x01`, calls `_check_life(tile, owner)` and maps the
  result:
  - `>= 0x0bea` -> `+C = 0x2a`
  - otherwise `+C = ((life * 10) / 0x0131) + 0x20`
- if bit 2 is set, increments `+C`; values `0x55..0x58` continue, values
  above `0x58` return `1`
- if bits `0x60` are set, increments `+C`; values `0x65..0x66` continue,
  values above `0x66` clamp to `0x65` and return `1`
- all other paths return `0`

## `_check_life`

`_check_life` computes a local growth / support value around a tile.

Branch behavior:
- clears `_all_of_city` and `_a_flat_block`
- iterates all offsets from `_offset_vector`
- if `_valid_move` returns `2`, subtracts `0xfff1` from the running
  score and keeps scanning
- if `_valid_move` returns nonzero and not `2`, returns `0`
- when the main tile is `0x0f`, sets `_a_flat_block`
- when the tile is `0x2a` and the neighboring tile values are in
  `0x29..0x2c`, increments `_all_of_city`
- if `D5 < 9`, a `0x2a` in `_map_bk2` with `0x29..0x2c` in `_map_bk1`
  counts as city support
- later branches count additional support only when the secondary tile
  bytes exceed `0x20`
- returns the accumulated `D4` score

Known uncertainty:
- `LAB_4DE10` onward continues the support scan and the exact weighting
  of the remaining branches should be revisited if a later pass needs a
  literal port of the city-support heuristic.

## `_valid_move`

`_valid_move` is the low-level tile legality check.

Branch behavior:
- returns `1` when the move goes off-grid in either axis
- returns `1` when the adjusted target x is outside `0..0x3f`
- returns `3` when the destination tile in `_map_blk` is zero
- returns `2` when the destination tile in `_map_blk` is `0x2f`
- returns `0` for all other in-bounds, non-blocked tiles

Reads:
- `_map_blk` only, plus the passed `to` and `delta` arguments

## `_set_town`

`_set_town` updates the town footprint and clears or writes surrounding
map bookkeeping.

Top-level branches:
- if the caller passes state `0`, the routine skips the special cleanup
  and goes straight to the final view / map path
- when `+C == 0x2a`, it walks a 0x19-entry loop over `_offset_vector`
  and `_map_bk2`
- otherwise, when `+C != 0x2a`, it walks a shorter `0x11`-entry loop and
  writes `big_city` values into `_map_bk2` for the first nine entries

Per-offset behavior:
- uses `_valid_move` on each offset against the peep's tile
- when `_valid_move` fails, clears `_map_bk2` at the target for some
  offsets
- when the corresponding `_map_blk` tile matches the peep's owner tile
  value plus `0x1f`, the block is rewritten to `0x0f`
- at the end of the `+C == 0x2a` branch, clears `_map_bk2[tile]`

Final cleanup:
- if the town marker is active, `_map_bk2[tile]` is cleared
- returns through `_42682` after restoring registers

Uncertain behavior to revisit:
- the `LAB_4246E`/`LAB_424C2` loops are similar but not identical and
  drive different `_map_bk2` rewriting. If the Python port needs exact
  town-shape fidelity, that section should be re-read with the caller
  context open.

## `_set_battle`

`_set_battle` marks two peeps as being in battle.

Branch behavior:
- peep `A` becomes type/state `0x08`
- peep `B` gets bit 3 set in its flag byte
- both peeps store each other's indexes in `+6`
- `_set_frame` is called for both peeps
- `_view_who` is advanced if the battle target was the current view
- if the attacker index is greater than the defender index, subtracts
  the attacker life from `good_pop[owner]`
- when the attacker has `+E`, the link is copied to the defender
- if the attacker's `+3` is higher, the defender inherits it
- attacker life is cleared at the end
- `map_who` is updated on the defender tile depending on whether the
  defender is a builder or not

## `_join_battle`

`_join_battle` merges a third peep into an existing battle.

Branch behavior:
- if the peeps do not share an owner, the join target index is replaced
  by the defender's `+6`
- life is merged with the same `0x7d00` cap used in `_join_forces`
- `_magnet` and `_view_who` are updated when the source was the
  currently tracked target
- if the source index is greater than the defender index, subtracts
  life from `good_pop[owner]`
- copies `+E` and stronger `+3` to the defender
- clears source life at the end

## `_do_battle`

`_do_battle` applies battle damage, updates animations, and determines
the battle end state.

Branch behavior:
- draws a pixel at the battle location with a color based on `_toggle`
- uses two calls to `__newrand` and `__divs` to compute separate damage
  values for the two combatants
- the peep with the larger random outcome takes the larger damage
- both peeps call `_set_frame`
- if both life values drop to zero, both peeps are zero-populated
- otherwise `_battle_over` is called for the peep that died
- when both are still alive, `_battle_over` is not called

Side effects:
- `+4` life values are reduced
- battle-ending cleanup is delegated to `_battle_over`

## `_set_magnet_to`

`_set_magnet_to` writes a faction magnet position.

Branch behavior:
- returns immediately when `_pause` is nonzero
- otherwise stores the passed tile into `LAB_52DE6[owner * 0x10]`
- if owner is `0`, updates `_god_magnet`
- otherwise updates `_devil_magnet`

## Numeric constants

Important values visible in the source:
- `0x16`: peep stride
- `0x00d0`: population cap
- `0x03e7`: movement failure code
- `0x7d00`: life cap during peep fusion
- `0x0bea`: strong-life threshold
- `0x0131` and `0x20`: life-to-frame normalization constants
- `0x0f`: buildable flat tile marker
- `0x2a`: town core tile marker
- `0x35`: special tile that can zero-populate on explorer contact
- `0x42`: special tile written by explorer/battle cleanup
- `0x43`, `0x46`, `0x49`, `0x4b`, `0x4c`, `0x4d`: score / effect IDs
- `0x55`, `0x5d`, `0x60`, `0x65`, `0x66`: animation clamp thresholds

## Likely missing from this note

Routines and labels that still look peep-relevant and deserve another
pass:
- `_do_place_funny`
- `_one_block_flat`
- `_make_level`
- `_battle_over`
- `_do_devil_magnet`
- `_do_devil_effect`
- `_do_magnet`
- `_do_war`
- `_do_knight`
- `_do_swamp`
- `_do_volcano`
- `_do_quake`
- `_do_lower_point`
- `_do_raise_point`
- `_get_heading`
- the `LAB_40994` through `LAB_40FCE` explorer block, especially the
  `LAB_40CBE`, `LAB_40DB4`, `LAB_40F22`, and `LAB_40FD2` branch joins
- the `LAB_41D72` and `LAB_41FAA` return paths in `_where_do_i_go`
- the battle cleanup span inside `_battle_over` after `LAB_4283A`
- the `LAB_4DE2A` onward tail of `_check_life`

## Practical summary

The original ASM peep system is a stateful update loop with:
- explicit ownership bookkeeping
- local movement heuristics rather than global pathfinding
- merging and battle initiation on contact
- removal and cleanup paths that clear linked state
- spawn logic that can replace peeps under magnet-driven conditions

The peep behavior is not a single simple movement routine. It is a
collection of update, merge, battle, ownership, and spawn rules that
share the same peep record layout.
