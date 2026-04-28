# Parity Gap Report

I audited the Python code against `asm/PEEPS_BEHAVIOR.md`. The current
implementation is strongest on the broad peep lifecycle, but it is still
far from the original ASM stateful movement and bookkeeping model.

The biggest mismatch is not individual functions, but representation:
the ASM logic is built around per-peep records plus shared tables, while
Python uses a small object model and scene-level helpers. That means even
when visible behavior looks similar, the hidden state transitions usually
do not line up.

## Data Model Fit

Current `Peep` can represent:

- `+1` owner as `faction_id` in `populous_game/peeps.py`
- `+3` weapon tier as `weapon_type`
- `+4` life as `life`
- `+6` timer/frame partially as `anim_frame`, `anim_timer`, `dir_timer`,
  and `build_timer`
- `+8` map position partially as `x/y`
- `+A` movement offset partially as `direction` plus computed movement delta
- `+E` linked peep/alliance partially as `target_x/target_y` or
  selection/combat references, but not as a raw link field

This is enough for animation, random wandering, and a few high-level
power interactions. It is not enough for direct porting of the ASM
branch tree.

Current model does not directly represent:

- `+0` flags/state bits as a bitfield
- `+2` movement substate
- `+C` growth/town counter as a raw per-peep counter
- `+12` remembered target
- `+14` auxiliary terrain marker

That is the main reason several ASM branches cannot be matched exactly
yet.

In practical terms:

- the Python code can say "this peep is alive and moving"
- the ASM can say "this exact record has owner X, linked peep Y, map
  owner Z, growth state C, and should now update a town, battle, or
  magnet table"
- that extra bookkeeping is what drives most of the branch behavior in
  `asm/PEEPS_BEHAVIOR.md`

## Routine-by-routine parity gaps

### `_move_peeps`

Current Python equivalent:

- Main update loop in `populous_game/game.py`, mostly through `Game.update()`
- Peep lifecycle logic in `populous_game/peeps.py`
- AI contribution in `populous_game/ai_opponent.py`
- Combat resolution in `populous_game/combat.py`

What already matches:

- Per-frame peep iteration exists
- Dead peeps are removed
- Life decays over time
- Movement, drowning, merging, and combat all exist in some form
- Enemy AI and house spawning are present

What is missing or simplified:

- No raw ASM-style flag byte
- No explicit `map_who` bookkeeping equivalent
- No direct branching by ASM peep bits
- No exact split between type `0x01`, type `0x02`, combat bit, and
  transitory bit branches
- No per-peep `+C` growth/town counter like the ASM
- No direct `+14` terrain marker bookkeeping
- No per-player `good_pop`, `good_castles`, `good_towns`, or
  `LAB_516C*`-style history updates
- No explicit `set_frame`-style return value that controls later branch
  selection
- No cleanup branch that mirrors the ASM "life <= 0" tail of the loop

Visible behavior or hidden bookkeeping:

- Mostly visible gameplay behavior
- Some hidden bookkeeping, especially ownership and link state

Risk:

- High, because this routine is the center of the whole peep system

Why this matters:

- if `_move_peeps` is wrong, every downstream routine gets called at the
  wrong time or not at all
- this routine is also where the ASM updates score, ownership, magnet
  state, town state, and death cleanup

Focused tests needed:

- Lifecycle update
- Death removal
- Drowning transition
- Merge/combat interaction
- Owner remap if model support is added

### `_move_explorer`

Current Python equivalent:

- `Game.update()` plus `_apply_combat_resolution()` in `populous_game/game.py`
- Movement orders in `populous_game/input_controller.py`
- Nearest-enemy lookup in `populous_game/selection.py`

What already matches:

- Peeps can be ordered to march
- Nearest-enemy targeting exists
- Same-faction joining exists
- Enemy contact can trigger combat

What is missing or simplified:

- No ASM-style explorer vs magnet-path split
- No `map_who` cleanup around movement
- No explicit failure timer/state path equivalent to the ASM `0x03e7` branch
- No destination-collision branching into `_join_forces`, `_set_battle`,
  `_join_battle`
- No clear distinction between "path failed" and "entity blocked"
- No "keep moving until the direction changes" loop that the ASM uses
  before clearing state
- No persistent target memory equivalent to the `+12` field

Visible behavior or hidden bookkeeping:

- Visible gameplay behavior, but the missing collision bookkeeping is
  also hidden-state dependent

Risk:

- High

Why this matters:

- the ASM explorer path is the bridge between movement, battle,
  merging, and building
- in Python, those outcomes are spread across `Peep.update()`,
  `Game.update()`, `input_controller.py`, and `combat.py`

Focused tests needed:

- March order to target
- Collision with ally
- Collision with enemy
- Collision with ongoing battle if added

### `_where_do_i_go`

Current Python equivalent:

- `populous_game/pathfinding.py` has generic pathfinding helpers
- `Peep.update()` currently uses simple local motion, not ASM offset scanning

What already matches:

- There is movement selection logic in the codebase
- There is a validity-check pathfinding module

What is missing or simplified:

- No ASM offset-vector heuristic
- No randomized directional scan matching the source
- No `_check_life`-based local score evaluation
- No `map_blk` / `map_bk2` guided movement selection
- No `0x03e7` failure return
- No direction-byte write to a peep record
- No special handling for the `0x0f`, `0x2a`, `0x35`, `0x42`, and
  `0x2f` tile classes that the ASM uses while scanning

Visible behavior or hidden bookkeeping:

- Visible gameplay behavior

Risk:

- High

Why this matters:

- this routine is the core of the ASM movement heuristic
- without it, `march` behavior is generic pathfinding rather than the
  original local "pick the best nearby step" logic

Focused tests needed:

- Direction choice from a fixed terrain neighborhood
- Blocked-move fallback
- Valid-move selection order
- Deterministic behavior under seeded RNG

### `_join_forces`

Current Python equivalent:

- `populous_game/combat.py` `join_forces()`

What already matches:

- Same-faction peeps can merge
- Winner keeps life
- Loser dies
- Life is capped

What is missing or simplified:

- No ASM `+E` link transfer semantics
- No `_view_who` remapping
- No exact same-tile/adjacency state bookkeeping
- No weapon-tier propagation logic beyond simple winner/loser life merge
- No copy of the source peep index into a linked slot
- No owner-index-specific `good_pop` correction when the lower index
  loses
- No clearing of a source record's owner/magnet traces after merge

Visible behavior or hidden bookkeeping:

- Mostly visible gameplay behavior, plus hidden selection/link bookkeeping

Risk:

- Medium

Why this matters:

- the merge rule is not just "sum life"
- it is also part of the ASM ownership and camera bookkeeping model

Focused tests needed:

- Winner/loser choice
- Life cap
- Dead-peep rejection
- Link/selection remap if fields are added

### `_zero_population`

Current Python equivalent:

- `Peep.transition(DEAD)` plus removal in `populous_game/game.py`

What already matches:

- Dead peeps are removed
- Life becomes zero
- Selection gets cleared when the entity disappears

What is missing or simplified:

- No `map_who` cleanup
- No magnet cleanup equivalent
- No builder-specific cleanup path
- No `_set_magnet_to` equivalent
- No clearing of linked peep state
- No per-owner view target repair
- No direct zeroing of the ASM record's battle/move fields

Visible behavior or hidden bookkeeping:

- Hidden bookkeeping, with some visible side effects

Risk:

- Medium

Why this matters:

- the ASM does not just remove the peep, it also repairs surrounding
  ownership tables
- without that, later peep contact and selection can see stale state

Focused tests needed:

- Removal from peep list
- Selection invalidation
- Linked-state cleanup if added
- Magnet/owner cleanup if added

### `_place_people`

Current Python equivalent:

- `Game.spawn_initial_peeps()` and `Game.spawn_enemy_peeps()` in
  `populous_game/game.py`
- House-spawn replacements in `Game.update()`

What already matches:

- Peep allocation exists
- Faction assignment exists
- Spawn fallback to nearest land exists
- Spawned peeps get initialized with reasonable defaults

What is missing or simplified:

- No ASM-style peep-table allocator
- No raw `0x00d0`-style cap enforcement in a peep allocator
- No replacement path tied to magnet ownership
- No direct initialization of ASM auxiliary tables
- No map ownership write on spawn
- No state or frame initialization from ASM fields
- No "replace existing peep at the magnet" branch

Visible behavior or hidden bookkeeping:

- Mostly hidden bookkeeping

Risk:

- Medium

Why this matters:

- spawn is where the ASM seeds ownership and early state
- if it is only a constructor call, later routines never see the same
  starting conditions

Focused tests needed:

- Spawn count and faction correctness
- Water fallback
- Cap behavior
- Replacement path if magnet support is added

### `_place_first_people`

Current Python equivalent:

- `Game.spawn_initial_peeps()` and scenario/bootstrap setup in
  `populous_game/game.py`

What already matches:

- Initial spawning exists
- Terrain-aware placement exists
- Enemy spawning exists

What is missing or simplified:

- No ASM tile-scanning algorithm
- No score bonus per placed peep
- No exact spawn-heuristic parity
- No multi-pass fallback logic based on ASM map state tables
- No search order tied to the ASM tile windows
- No count-down placement quota behavior
- No direct relation to `map_who`/`map_blk` cleanliness checks

Visible behavior or hidden bookkeeping:

- Visible gameplay behavior, but heavily simplified

Risk:

- Medium to high

Why this matters:

- the ASM routine is not "spawn N peeps somewhere"
- it is a placement algorithm with score and tile-class side effects

Focused tests needed:

- Initial population count
- Spawn placement legality
- Score side effect if implemented
- Fallback scanning

### `_set_battle` / `_join_battle` / `_do_battle`

Current Python equivalent:

- `combat.damage_peep_vs_peep()` and `Game._apply_combat_resolution()`
  in `populous_game/combat.py` and `populous_game/game.py`

What already matches:

- Enemy peeps damage each other
- Peep-vs-house combat exists
- Dead peeps are removed
- Same-faction merge exists

What is missing or simplified:

- No explicit battle state machine separate from normal fight
- No join-battle semantics
- No battle-specific bookkeeping fields
- No explicit battle object or persistent battle record
- No branch-specific state transitions for battle entry and exit
- No battle index retention or target remapping
- No support for the ASM behavior where battles can join or split

Visible behavior or hidden bookkeeping:

- Mostly visible gameplay behavior, but battle state bookkeeping is
  hidden and absent

Risk:

- High

Why this matters:

- battle in the ASM is a stateful contact system, not just damage ticks
- the modern code can resolve combat outcomes, but it cannot reproduce
  the original battle bookkeeping yet

Focused tests needed:

- Enemy contact creates combat outcome
- Same-faction contact merges
- Battle state persistence if added
- Battle cleanup if a dedicated state is introduced

### `_move_magnet_peeps`

Current Python equivalent:

- None in Python as a dedicated routine
- Partial approximation through `mode_manager.papal_position`, `go_papal`,
  and march-target assignment in `populous_game/input_controller.py`

What already matches:

- There is a papal/magnet concept
- Peeps can be marched toward a target point

What is missing or simplified:

- No faction magnet table
- No magnet-anchored movement override
- No direct peep-table magnet displacement logic
- No owner slot lookup before movement
- No fallback to the linked peep's coordinates when magnet state is
  absent
- No interaction with `_view_who` or hidden leader tracking

Visible behavior or hidden bookkeeping:

- Mostly hidden bookkeeping, with visible march behavior partially present

Risk:

- High

Why this matters:

- magnet movement is one of the most distinctive non-generic behaviors
  in the ASM
- it is the path that makes peeps feel "guided" rather than just
  wandering

Focused tests needed:

- Magnet target march
- Magnet override precedence
- Magnet cleanup on death/remap

### `_check_life`

Current Python equivalent:

- No direct equivalent
- Some rough analogs exist in growth / life / bar logic, but not a
  shared ASM helper

What already matches:

- Life and growth are represented
- Some score and bar logic uses life-like values

What is missing or simplified:

- No shared construction/life scoring helper
- No direct rep of the ASM function
- No consumer-specific branching around `check_life`
- No direct tie to `_set_frame`
- No use of `_all_of_city` or `_a_flat_block`
- No city-support counting around neighboring tiles

Visible behavior or hidden bookkeeping:

- Hidden bookkeeping / shared scoring logic

Risk:

- High

Why this matters:

- this is one of the main shared helpers that multiple ASM branches use
- it is also the bridge between raw life and town/build animation

Focused tests needed:

- Deterministic score outputs
- Threshold behavior at `0x0bea`
- Reject/accept cases

### `_valid_move`

Current Python equivalent:

- `populous_game/pathfinding.py` `_is_valid_move()` is the closest analog

What already matches:

- There is a valid-move helper
- Terrain checks exist

What is missing or simplified:

- No exact ASM `map_blk` / `map_bk2` semantics
- No direct use in peep movement selection
- No offset-vector scanning integration
- No return-code distinction between open, blocked, and special tiles
- No wrapping of directional offsets the way the ASM does

Visible behavior or hidden bookkeeping:

- Visible gameplay behavior

Risk:

- High

Why this matters:

- many later branches assume the ASM return codes, not a boolean
- if the legality helper is different, movement parity will drift even
  if higher-level code is correct

Focused tests needed:

- Known invalid terrain transitions
- Flat-ground validity
- Water rejection
- Boundary cases

### `_set_town`

Current Python equivalent:

- `Peep.try_build_house()` plus house creation in `populous_game/peeps.py`
- House updates in `populous_game/houses.py`

What already matches:

- Peeps can build houses
- Growth/build timers exist
- House life and spawn behavior exist

What is missing or simplified:

- No ASM `+C` town counter equivalent
- No exact state gating around the builder path
- No direct low-level town bookkeeping
- No exact build state transitions matching the source
- No `_map_blk` or `_map_bk2` rewrite pass around the building site
- No `+0` / `+2` / `+C` state choreography that the ASM uses while
  building
- No score or ownership update tied to the builder transition

Visible behavior or hidden bookkeeping:

- Visible gameplay behavior, but with missing low-level bookkeeping

Risk:

- Medium to high

Why this matters:

- the ASM build path is more than "spawn a house"
- it is also a state transition and a map rewrite

Focused tests needed:

- Build transition
- Build timer expiry
- House creation
- Population / life transfer behavior

## Highest-risk missing pieces

- raw peep state bits / fields
- `_valid_move`
- `_where_do_i_go`
- `_move_explorer`
- `_check_life`
- dedicated battle state bookkeeping
- magnet movement bookkeeping

## Recommended implementation order

1. Add the missing peep-side bookkeeping fields and state-bit
   representation.
2. Implement `_valid_move` / `_where_do_i_go` parity next.
3. Then wire `_move_explorer` and `_join_forces` to those fields.
4. Add `_check_life` and `_set_frame` once the data model is in place.
5. Add `_move_magnet_peeps`, `_set_town`, `_set_battle`, and
   `_join_battle`.
6. Finish with `_place_people` and `_place_first_people`.

That sequence gives the largest structural unlock, because it unblocks
most of the other peep routines without starting from a UI or combat
edge case.

## Test gaps

Current Python tests do not cover ASM parity at the control-flow level.

Missing test coverage:

- `_valid_move` return codes
- `_check_life` terrain and city-support thresholds
- `_set_frame` timer thresholds and state-dependent return values
- `_set_town` map rewrite behavior
- `_set_battle` / `_join_battle` / `_do_battle` state and ownership side effects
- `_move_peeps` branch selection based on flags, life, and magnet state
- `_move_explorer` and `_move_magnet_peeps` movement selection
- `_place_people` replacement semantics and cap behavior

Suggested test shape:

- add narrow unit tests around each ASM branch family before adding
  broad integration tests
- keep one fixture that exposes a peep record and the relevant global
  tables so branch effects can be asserted directly
- use small deterministic maps to verify `map_who`, `magnet`, and
  `view_who` changes
- add one test per return-code family first, then add contact and
  cleanup tests that depend on those return codes
- prefer fixture-level assertions on table mutation over broad
  screenshot tests
