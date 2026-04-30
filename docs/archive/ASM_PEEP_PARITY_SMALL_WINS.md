# ASM Peep Parity Small Wins Plan

Author: this session, 2026-04-30.

## Title and Objective

Implement the small ASM-parity wins identified from
[asm/PEEPS_BEHAVIOR.md](../../asm/PEEPS_BEHAVIOR.md) and
[asm/PEEPS_GAP_REPORT.md](../../asm/PEEPS_GAP_REPORT.md) without
attempting a full `_move_peeps` rewrite.

Objective: add the missing low-level contracts, shadow bookkeeping,
focused behavior seams, and tests needed to make later ASM peep work
safe and incremental.

## Design Philosophy

- Additive shadow state first, behavior rewrites later.
- Preserve current visible gameplay unless a cited ASM side effect is
  explicitly in scope.
- Prefer named contracts and tests over hidden compatibility assumptions.
- Keep planning terms out of durable code identifiers.
- Split implementation into parallel streams only after shared contracts
  are stable.

## Scope and Non-Goals

In scope:

- Add ASM-shaped peep shadow fields.
- Add ASM-style movement return-code helper while keeping current A*
  behavior intact.
- Add shadow `map_who` occupancy bookkeeping.
- Enforce the `0x00d0` peep allocation cap.
- Award the initial player placement score bonus.
- Improve same-faction merge bookkeeping.
- Separate ASM numeric constants from gameplay-scaled tuning constants.
- Populate combat state needed by the shield combat branch.
- Add faction magnet bookkeeping around the papal marker.
- Add focused tests and update docs/changelog.

Non-goals:

- No literal port of `_move_peeps`, `_move_explorer`, or
  `_where_do_i_go`.
- No replacement of A* pathfinding with ASM local offset scanning.
- No full battle object model.
- No save-file schema bump unless a required persistent field cannot be
  reconstructed.
- No UI redesign.

## Current State Summary

Facts from the repo:

- `Peep` has visible gameplay fields but lacks raw ASM-style fields for
  flags, movement substate, town counter, linked peep, remembered target,
  and terrain marker.
- `pathfinding._classify_move()` returns boolean plus reason, while the
  ASM `_valid_move` uses return codes `0`, `1`, `2`, and `3`.
- `GameMap` does not maintain a `map_who` equivalent.
- Spawn helpers append peeps directly and do not enforce the ASM cap
  `0x00d0`.
- `spawn_initial_peeps()` does not award the documented `+10` score per
  placed player peep.
- `combat.join_forces()` merges life but does not yet copy weapon tier
  or clear transient shadow fields.
- `settings.PEEP_LIFE_MAX` is a gameplay-scaled cap, while ASM cites
  `0x7d00` as the merge cap.
- `ui_panel._compute_peep_bar_model()` already has a combat branch seam,
  but combat resolution does not reliably set `shield_opponent`.
- Papal placement exists as `mode_manager.papal_position`, but there is
  no faction-indexed magnet table.

## Architecture Boundaries and Ownership

Components:

- Peep record component: `populous_game/peeps.py`,
  `populous_game/peep_state.py`.
- Movement contract component: `populous_game/pathfinding.py`.
- Occupancy contract component: `populous_game/terrain.py`,
  `populous_game/game.py`.
- Spawn allocator component: `populous_game/game.py`,
  `populous_game/settings.py`.
- Combat state component: `populous_game/combat.py`,
  `populous_game/game.py`, `populous_game/ui_panel.py`.
- Magnet state component: `populous_game/mode_manager.py`,
  `populous_game/input_controller.py`, `populous_game/powers.py`,
  `populous_game/selection.py`.
- Persistence compatibility component: `populous_game/save_state.py`.
- Test component: `tests/`.
- Documentation component: `docs/TODO.md`, `docs/CHANGELOG.md`,
  this plan.

Ownership:

- Code work packages: `coder`.
- Test-only packages: `tester`.
- Documentation packages: `planner`.
- Cross-component design approval: `architect`.
- Patch integration: `integrator`.
- Read-only closure audit: `reviewer`.

## Mapping: Milestones and Workstreams to Components and Patches

Milestone labels are schedule labels only. Code should use durable names
such as component, contract, table, helper, or state.

Dependency IDs:

- `DEP-PEEP-RECORD`: peep shadow fields and constants exist.
- `DEP-MOVE-CODES`: movement return-code helper exists.
- `DEP-MAP-WHO`: shadow occupancy table exists.
- `DEP-SPAWN-CAP`: peep allocation cap helper exists.
- `DEP-COMBAT-SEAM`: combat state sets fight/opponent metadata.
- `DEP-MAGNET-TABLE`: faction magnet table exists.
- `DEP-TEST-GATE`: focused tests cover the new contracts.

Mapping:

- Milestone A maps to Peep record, Movement contract, Settings, and
  Occupancy contract components. Expected patches: Patch 1, Patch 2,
  Patch 3.
- Milestone B maps to Spawn allocator and Occupancy contract components.
  Expected patches: Patch 4, Patch 5.
- Milestone C maps to Combat state and Magnet state components.
  Expected patches: Patch 6, Patch 7, Patch 8.
- Milestone D maps to Test and Documentation components. Expected
  patches: Patch 9, Patch 10.

## Milestone Plan

### Milestone A: Add Shared Contracts

Depends on: none.

Deliverables:

- Peep shadow fields initialized with safe defaults.
- ASM numeric constants named separately from gameplay-scaled tuning.
- `valid_move_code()` helper available without changing existing A* API.
- `GameMap.map_who` allocated and resettable.

Done checks:

- Existing pathfinding tests pass unchanged.
- New unit tests assert peep field defaults, movement code mapping, and
  `map_who` dimensions/reset behavior.
- No save round-trip regression.

Entry criteria:

- none.

Exit criteria:

- `DEP-PEEP-RECORD`, `DEP-MOVE-CODES`, and `DEP-MAP-WHO` are satisfied.

### Milestone B: Wire Spawn and Occupancy Behavior

Depends on:

- `DEP-PEEP-RECORD`: spawn must initialize shadow fields.
- `DEP-MAP-WHO`: spawn and cleanup use occupancy bookkeeping.

Deliverables:

- Single peep allocation helper enforces the `0x00d0` cap.
- Initial player spawn awards `+10` per placed player peep.
- `map_who` can be recomputed after spawn, update, merge, and removal.
- Tests cover cap, score bonus, and occupancy table contents.

Done checks:

- Focused spawn tests pass.
- Existing menu/start spawn tests pass.
- Save/load tests pass with no schema bump unless explicitly approved.

Entry criteria:

- Milestone A exit criteria complete.

Exit criteria:

- `DEP-SPAWN-CAP` is satisfied.

### Milestone C: Wire Combat, Merge, and Magnet Seams

Depends on:

- `DEP-PEEP-RECORD`: merge and combat cleanup need shadow fields.
- `DEP-MAP-WHO`: combat/merge cleanup must not leave stale occupancy.
- `DEP-SPAWN-CAP`: spawned peeps must share the same allocation path.

Deliverables:

- `join_forces()` copies stronger weapon tier and clears winner transient
  fields.
- Enemy contact sets `FIGHT` state where legal and assigns
  `shield_opponent` for HUD combat bars.
- Faction magnet table is initialized, updated on papal placement, and
  cleared/reset on game reset.
- Tests cover merge tier propagation, shield combat branch activation,
  and magnet table updates.

Done checks:

- Existing combat and shield-panel tests pass.
- `_find_battle` still finds fighting peeps.
- Papal button/hotkey tests pass.

Entry criteria:

- Milestone B exit criteria complete.

Exit criteria:

- `DEP-COMBAT-SEAM` and `DEP-MAGNET-TABLE` are satisfied.

### Milestone D: Close Tests, Docs, and Regression Gates

Depends on:

- `DEP-PEEP-RECORD`: required for field tests.
- `DEP-MOVE-CODES`: required for movement code tests.
- `DEP-MAP-WHO`: required for occupancy tests.
- `DEP-SPAWN-CAP`: required for spawn cap tests.
- `DEP-COMBAT-SEAM`: required for combat UI tests.
- `DEP-MAGNET-TABLE`: required for magnet tests.

Deliverables:

- Focused parity tests are committed for every implemented seam.
- `docs/TODO.md` points at the completed or next active parity item.
- `docs/CHANGELOG.md` records patches and any deferred decisions.
- Reviewer verifies plan conformance.

Done checks:

- Focused pytest commands pass.
- Repo-wide pyflakes gate passes.
- Reviewer notes no missing acceptance gate.

Entry criteria:

- Milestone C exit criteria complete.

Exit criteria:

- `DEP-TEST-GATE` is satisfied and the plan can be archived or updated
  to point to the next ASM peep implementation plan.

## Workstream Breakdown

### Workstream 1: Peep Record and Numeric Contracts

Goal: add additive ASM-shaped fields and constants without changing
runtime behavior.

Owner: `coder`.

Work packages: 6.

Interfaces:

- Needs: ASM field list from `asm/PEEPS_BEHAVIOR.md`.
- Provides: field defaults and constants for other streams.

Expected patches:

- Patch 1: peep record component add shadow fields.
- Patch 2: settings component clarify ASM constants.

### Workstream 2: Movement and Occupancy Contracts

Goal: expose low-level movement return codes and shadow occupancy table.

Owner: `coder`.

Work packages: 6.

Interfaces:

- Needs: no production behavior changes from Workstream 1.
- Provides: `valid_move_code()` and `map_who` APIs.

Expected patches:

- Patch 3: movement contract add return-code helper.
- Patch 4: occupancy contract add table allocation/recompute.

### Workstream 3: Spawn and Score Wiring

Goal: route peep creation through a cap-aware helper and add the cited
initial player score side effect.

Owner: `coder`.

Work packages: 6.

Interfaces:

- Needs: peep field defaults and `map_who` table.
- Provides: cap-aware spawn behavior for combat, houses, and reset flows.

Expected patches:

- Patch 5: spawn allocator enforce cap and score bonus.

### Workstream 4: Combat and Shield State

Goal: make current combat populate the ASM-like state used by merge and
shield UI seams.

Owner: `coder`.

Work packages: 6.

Interfaces:

- Needs: peep shadow fields and occupancy recompute.
- Provides: stronger merge bookkeeping and fight/opponent state.

Expected patches:

- Patch 6: combat state improve merge and fight metadata.

### Workstream 5: Magnet State

Goal: add faction-indexed magnet bookkeeping that wraps the current
papal position behavior.

Owner: `coder`.

Work packages: 6.

Interfaces:

- Needs: faction constants and reset flow.
- Provides: magnet table for future `_move_magnet_peeps` work.

Expected patches:

- Patch 7: magnet state add table and command wiring.

### Workstream 6: Tests

Goal: add focused tests for every new contract and behavior seam.

Owner: `tester`.

Work packages: 8.

Interfaces:

- Needs: callable contracts from Workstreams 1 through 5.
- Provides: acceptance gates and regression coverage.

Expected patches:

- Patch 8: tests movement, occupancy, spawn, combat, magnet.

### Workstream 7: Integration, Review, and Docs

Goal: integrate patches, run focused gates, and close documentation.

Owner: `integrator` with `reviewer` audit.

Work packages: 6.

Interfaces:

- Needs: all implementation and test patches.
- Provides: merged patch sequence, changelog, TODO update, closure note.

Expected patches:

- Patch 9: documentation update.
- Patch 10: integration fixes and closure notes if needed.

## Work Package Specs

### WP-PR-01: Add peep shadow fields

Owner: `coder`.

Touch points: `populous_game/peeps.py`, `tests/test_peep_state_rules.py`.

Acceptance criteria:

- Every new peep has defaults for ASM flags, movement substate, town
  counter, linked peep, remembered target, terrain marker, and last move
  offset.
- Defaults do not alter current draw/update behavior.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_peep_state_rules.py
```

Dependencies: none.

### WP-PR-02: Name ASM peep constants

Owner: `coder`.

Touch points: `populous_game/settings.py`, `tests/test_combat_rules.py`.

Acceptance criteria:

- `ASM_PEEP_RECORD_STRIDE`, `ASM_PEEP_CAP`, `ASM_PEEP_MERGE_LIFE_CAP`,
  and `ASM_MOVE_FAILED_CODE` exist.
- Existing gameplay constants keep current behavior unless explicitly
  changed by another package.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_combat_rules.py
```

Dependencies: none.

### WP-MV-01: Add movement return-code helper

Owner: `coder`.

Touch points: `populous_game/pathfinding.py`,
`tests/test_pathfinding_legality.py`.

Acceptance criteria:

- Helper returns ASM-shaped codes for out-of-bounds, water/empty,
  rock/block placeholder, and open land.
- Existing `_is_valid_move()` behavior remains unchanged.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_pathfinding_legality.py tests/test_pathfinding.py
```

Dependencies: WP-PR-02.

### WP-MV-02: Preserve A* public API

Owner: `tester`.

Touch points: `tests/test_pathfinding.py`, `tests/test_pathfinding_legality.py`.

Acceptance criteria:

- Existing A* path tests still assert path/no-path behavior.
- New code tests do not require callers to use return codes.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_pathfinding.py tests/test_pathfinding_legality.py
```

Dependencies: WP-MV-01.

### WP-OW-01: Allocate occupancy table

Owner: `coder`.

Touch points: `populous_game/terrain.py`, `tests/test_peep_spawn_finds_land.py`.

Acceptance criteria:

- `GameMap` initializes a 64 by 64 `map_who` table of zeros.
- `GameMap` exposes reset/recompute helpers without changing rendering.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_peep_spawn_finds_land.py
```

Dependencies: WP-PR-02.

### WP-OW-02: Recompute occupancy from peeps

Owner: `coder`.

Touch points: `populous_game/game.py`, `populous_game/terrain.py`.

Acceptance criteria:

- Live peeps write `index + 1` to their current tile.
- Dead or out-of-bounds peeps do not write occupancy.
- Recompute runs after spawn, merge/removal, and update cleanup.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_peep_spawn_finds_land.py tests/test_join_forces.py
```

Dependencies: WP-OW-01.

### WP-SP-01: Add cap-aware peep allocator

Owner: `coder`.

Touch points: `populous_game/game.py`, `populous_game/settings.py`.

Acceptance criteria:

- All Game-level peep creation paths use one helper.
- Helper refuses creation at `ASM_PEEP_CAP`.
- Existing no-land errors remain unchanged.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_peep_spawn_finds_land.py tests/test_menu_enter_preserves_randomized_heightmap.py
```

Dependencies: WP-PR-02.

### WP-SP-02: Award initial placement score

Owner: `coder`.

Touch points: `populous_game/game.py`, `tests/test_peep_spawn_finds_land.py`.

Acceptance criteria:

- Player initial spawn adds `10` score per placed player peep.
- Enemy spawn does not mutate the player-visible score unless an
  explicit design decision changes that.
- Reset still returns score to zero.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_peep_spawn_finds_land.py tests/test_state_machine_integration.py
```

Dependencies: WP-SP-01.

### WP-SP-03: Route house peep creation through allocator

Owner: `coder`.

Touch points: `populous_game/game.py`, `populous_game/peeps.py`.

Acceptance criteria:

- House spawn and destroyed-house recovery honor the same cap.
- Pending excess peeps from house construction honor the cap.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_combat_rules.py tests/test_preparity_smoke.py
```

Dependencies: WP-SP-01.

### WP-CB-01: Copy merge weapon tier

Owner: `coder`.

Touch points: `populous_game/combat.py`, `tests/test_join_forces.py`.

Acceptance criteria:

- Winner receives the stronger weapon tier.
- Existing life-cap and dead-loser behavior remain unchanged.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_join_forces.py
```

Dependencies: WP-PR-01.

### WP-CB-02: Clear merge transient fields

Owner: `coder`.

Touch points: `populous_game/combat.py`, `tests/test_join_forces.py`.

Acceptance criteria:

- Winner clears remembered target, terrain marker, and transient move
  offset when merge succeeds.
- Loser is still transitioned to dead through the existing path.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_join_forces.py tests/test_smoke_ui_buttons.py
```

Dependencies: WP-CB-01.

### WP-CB-03: Populate fight state metadata

Owner: `coder`.

Touch points: `populous_game/game.py`, `populous_game/combat.py`,
`tests/test_combat_rules.py`.

Acceptance criteria:

- Enemy peeps in contact enter or remain in `FIGHT` when legal.
- Both peeps expose `shield_opponent` while both are alive.
- Dead/completed combat clears or invalidates stale opponent metadata.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_combat_rules.py tests/test_ui_panel.py tests/test_selection.py
```

Dependencies: WP-PR-01.

### WP-MG-01: Add faction magnet table

Owner: `coder`.

Touch points: `populous_game/mode_manager.py`, `tests/test_mode_manager.py`.

Acceptance criteria:

- Mode manager initializes one magnet slot per active faction.
- Existing `papal_position` remains available for compatibility.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_mode_manager.py
```

Dependencies: WP-PR-02.

### WP-MG-02: Wire papal placement to magnet table

Owner: `coder`.

Touch points: `populous_game/input_controller.py`,
`populous_game/powers.py`, `tests/test_powers_rules.py`,
`tests/test_power_hotkeys.py`.

Acceptance criteria:

- Papal UI placement updates the player magnet slot.
- Papal power activation updates the same table.
- Existing papal marker tests continue to pass.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_powers_rules.py tests/test_power_hotkeys.py tests/test_screenshot_clicking.py
```

Dependencies: WP-MG-01.

### WP-MG-03: Reset magnet state

Owner: `coder`.

Touch points: `populous_game/game.py`, `populous_game/mode_manager.py`,
`tests/test_state_machine_integration.py`.

Acceptance criteria:

- New game/menu reset clears or reinitializes magnet table.
- `_find_papal` keeps existing behavior.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_state_machine_integration.py tests/test_selection.py
```

Dependencies: WP-MG-01.

### WP-SV-01: Verify save compatibility

Owner: `tester`.

Touch points: `populous_game/save_state.py`, `tests/test_save_round_trip.py`.

Acceptance criteria:

- Shadow fields either reconstruct on load or are explicitly persisted
  with a schema bump approved by `architect`.
- Current schema tests pass unless a schema bump is approved.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_save_round_trip.py
```

Dependencies: WP-PR-01, WP-MG-01.

### WP-TS-01: Test peep record defaults

Owner: `tester`.

Touch points: `tests/test_peep_state_rules.py`.

Acceptance criteria:

- New peep defaults are asserted directly.
- Tests do not assert fragile private method names.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_peep_state_rules.py
```

Dependencies: WP-PR-01.

### WP-TS-02: Test movement return codes

Owner: `tester`.

Touch points: `tests/test_pathfinding_legality.py`.

Acceptance criteria:

- Tests cover open, blocked/water, out-of-bounds, and reserved rock
  code paths.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_pathfinding_legality.py
```

Dependencies: WP-MV-01.

### WP-TS-03: Test occupancy table

Owner: `tester`.

Touch points: `tests/test_peep_spawn_finds_land.py`,
`tests/test_preparity_smoke.py`.

Acceptance criteria:

- Tests assert map occupancy after spawn and after dead-peep cleanup.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_peep_spawn_finds_land.py tests/test_preparity_smoke.py
```

Dependencies: WP-OW-02.

### WP-TS-04: Test spawn cap and score

Owner: `tester`.

Touch points: `tests/test_peep_spawn_finds_land.py`,
`tests/test_state_machine_integration.py`.

Acceptance criteria:

- Tests assert cap enforcement.
- Tests assert player initial score bonus and reset behavior.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_peep_spawn_finds_land.py tests/test_state_machine_integration.py
```

Dependencies: WP-SP-02.

### WP-TS-05: Test merge and combat metadata

Owner: `tester`.

Touch points: `tests/test_join_forces.py`, `tests/test_combat_rules.py`,
`tests/test_ui_panel.py`.

Acceptance criteria:

- Tests assert stronger weapon propagation.
- Tests assert `shield_opponent` drives combat branch math.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_join_forces.py tests/test_combat_rules.py tests/test_ui_panel.py
```

Dependencies: WP-CB-03.

### WP-TS-06: Test magnet table

Owner: `tester`.

Touch points: `tests/test_mode_manager.py`, `tests/test_powers_rules.py`,
`tests/test_selection.py`.

Acceptance criteria:

- Tests assert papal placement and power activation update player magnet.
- Tests assert reset restores deterministic magnet state.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_mode_manager.py tests/test_powers_rules.py tests/test_selection.py
```

Dependencies: WP-MG-03.

### WP-IN-01: Integrate focused gates

Owner: `integrator`.

Touch points: implementation patches and focused tests.

Acceptance criteria:

- All focused commands listed above pass.
- No patch touches more than two components without being split.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_peep_state_rules.py tests/test_pathfinding_legality.py tests/test_peep_spawn_finds_land.py tests/test_join_forces.py tests/test_combat_rules.py tests/test_mode_manager.py tests/test_powers_rules.py tests/test_save_round_trip.py
```

Dependencies: WP-TS-01, WP-TS-02, WP-TS-03, WP-TS-04, WP-TS-05,
WP-TS-06.

### WP-IN-02: Run lint gate

Owner: `maintainer`.

Touch points: repo-wide lint tests.

Acceptance criteria:

- Pyflakes gate passes.
- ASCII and indentation gates pass for touched files.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_pyflakes_code_lint.py tests/test_ascii_compliance.py tests/test_indentation.py
```

Dependencies: WP-IN-01.

### WP-DC-01: Update documentation

Owner: `planner`.

Touch points: `docs/TODO.md`, `docs/CHANGELOG.md`, this plan.

Acceptance criteria:

- TODO points at the next active parity item.
- Changelog uses Patch labels for implementation summaries.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_ascii_compliance.py -k docs
```

Dependencies: WP-IN-01.

### WP-RV-01: Audit plan closure

Owner: `reviewer`.

Touch points: read-only review of patches, tests, docs, and this plan.

Acceptance criteria:

- Reviewer confirms every in-scope small win has either shipped or has a
  documented deferral.
- No undocumented behavior regression remains.

Verification commands:

```bash
source source_me.sh && python3 -m pytest tests/test_preparity_smoke.py
```

Dependencies: WP-IN-02, WP-DC-01.

## Work Package Template

Use this template for any additional packages:

- Work package title: verb plus object.
- Owner: one of `coder`, `tester`, `planner`, `architect`, `reviewer`,
  `orchestrator`, `parallelizer`, `integrator`, `maintainer`,
  `monitor`, or `scheduler`.
- Touch points: files or components.
- Acceptance criteria: concrete pass/fail checks.
- Verification commands: exact Bash commands using
  `source source_me.sh && python3`.
- Dependencies: work package IDs or `none`.

## Acceptance Criteria and Gates

Acceptance criteria:

- All ten small wins are implemented or explicitly deferred by
  `architect`.
- Existing gameplay tests for pathfinding, spawn, combat, UI panel,
  powers, and save round-trip pass.
- No new public behavior depends on hidden environment variables.
- New code identifiers avoid planning terms such as milestone,
  workstream, and work package.
- Documentation and changelog identify the shipped patches.

Gates:

- Unit gate: focused unit tests listed in work packages pass.
- Integration gate: combined focused pytest command in WP-IN-01 passes.
- Regression gate: pyflakes, ASCII, and indentation checks pass for
  touched files.
- Release gate: reviewer confirms every small win maps to a test or a
  documented deferral.

## Test and Verification Strategy

Unit checks:

- Peep field defaults.
- Movement return-code mapping.
- Occupancy table reset and recompute.
- Spawn cap and score mutation.
- Merge tier propagation and transient cleanup.
- Magnet table updates.

Integration checks:

- Menu start spawning.
- House spawn/destroy recovery.
- Combat resolution and shield panel branch.
- Papal placement through UI and power paths.
- Save/load reconstruction.

Smoke/system checks:

- `tests/test_preparity_smoke.py`.
- Existing UI button smoke tests when button behavior is touched.

Failure semantics:

- Any focused test failure blocks the next milestone.
- Any save schema incompatibility requires `architect` approval before
  implementation proceeds.
- Any change that alters A* output outside the new return-code helper is
  a regression unless deliberately approved.

## Migration and Compatibility Policy

- Add fields and tables with defaults before consumers depend on them.
- Keep current public APIs stable unless a new helper is explicitly
  additive.
- Save files remain schema version 1 unless a field must be persisted
  and cannot be reconstructed.
- `PEEP_LIFE_MAX` keeps current gameplay-scaled behavior until a
  separate balance decision changes it.
- `ASM_PEEP_MERGE_LIFE_CAP` documents source parity and is not used to
  rescale gameplay life without `architect` approval.
- Legacy direct peep appends may be deleted only after all Game-level
  creation paths route through the allocator and tests cover cap
  behavior.

Rollback strategy:

- Revert behavior patches independently by component.
- Shadow fields, constants, and tests can remain if a behavior patch is
  rolled back because they are additive contracts.
- If fight-state wiring destabilizes combat, keep merge improvements and
  defer the combat seam behind a documented plan update.

## Risk Register and Mitigations

| Risk | Impact | Trigger | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| Shadow fields become fake parity | Medium | Fields are added but never tested | reviewer | Require direct default tests and consumers in later patches |
| A* behavior changes accidentally | High | Existing pathfinding tests fail | coder | Keep `valid_move_code()` additive and leave `_is_valid_move()` semantics unchanged |
| Spawn cap drops peeps silently | Medium | Count tests no longer match requested spawn | coder | Return explicit success/failure from allocator and test cap boundary |
| Score bonus changes gameover tests | Medium | Reset or menu tests fail | tester | Add reset score test and limit bonus to player initial placement |
| `map_who` becomes stale | High | Occupancy test fails after merge/removal | coder | Recompute from live peeps at safe points before incremental writes |
| Combat state transition raises errors | High | Invalid transition from current peep state | coder | Check transition matrix before setting `FIGHT`; leave state unchanged if illegal but still test expected paths |
| Magnet table duplicates papal state inconsistently | Medium | Papal tests disagree on target | coder | Make papal setter the single write path for both compatibility position and table |
| Save schema churn | Medium | Save round-trip fails | architect | Prefer reconstruction; require approval for schema bump |
| Patch collision in `game.py` | Medium | Spawn, occupancy, combat, and magnet all edit `game.py` | integrator | Serialize `game.py` patches after shared contracts; parallelize tests and adjacent modules |

## Rollout and Release Checklist

- Patch 1 through Patch 3 land shared contracts.
- Focused contract tests pass.
- Patch 4 and Patch 5 wire spawn/occupancy.
- Focused spawn and save tests pass.
- Patch 6 through Patch 8 wire combat and magnet state.
- Focused combat, shield, papal, and selection tests pass.
- Patch 9 updates docs and changelog.
- Patch 10 integrates final fixes if needed.
- Reviewer signs off that every small win is shipped or deferred.
- Plan is archived or updated to point to the next ASM peep parity plan.

## Documentation Close-Out Requirements

- `docs/CHANGELOG.md` must include Patch labels and test evidence.
- `docs/TODO.md` must remove completed small-win items or point to the
  next active parity gap.
- This plan must be updated with completion status or moved to an
  archive path after closure.
- Any deferral must cite owner, reason, and next dependency.

## Patch Plan and Reporting Format

- Patch 1: peep record component add ASM shadow fields.
- Patch 2: settings component separate ASM constants from gameplay
  tuning.
- Patch 3: movement contract add return-code helper.
- Patch 4: occupancy contract add `map_who` table and recompute.
- Patch 5: spawn allocator enforce cap and initial score bonus.
- Patch 6: combat state improve merge bookkeeping.
- Patch 7: combat state populate fight and shield opponent metadata.
- Patch 8: magnet state add faction table and papal wiring.
- Patch 9: tests cover contracts and behavior seams.
- Patch 10: tests, migration, docs, integration closure.

Required stream handoff format:

```text
Status: complete|blocked|failed
Report Path: <orchestrator-assigned-report-path>
Summary:
- ...
- ...
- ...
Validation Status: pass|fail
Blocking Issues:
- none|...
```

Required report file sections:

- Assumptions.
- Decisions.
- Concrete next steps.
- Changed files.
- Validation performed.

## Parallel Execution Mode

Execution mode: orchestration-first, then real parallel execution.

Shared prerequisites in Milestone A should land before dispatching
behavior work. After that, Workstreams 3, 4, 5, and 6 can run in
parallel if `game.py` edits are serialized by `integrator`.

Do not dispatch two coding streams that both edit `populous_game/game.py`
at the same time. Parallelize adjacent module work and tests instead.

## Open Questions and Decisions Needed

- `architect`: confirm that `ASM_PEEP_MERGE_LIFE_CAP = 0x7d00` should
  remain documentation-only for now while `PEEP_LIFE_MAX` stays
  gameplay-scaled.
- `architect`: confirm that initial score bonus applies only to player
  visible score, not enemy spawn bookkeeping.
- `architect`: decide whether `map_who` should remain recomputed each
  update or move to incremental writes after tests stabilize.
- `reviewer`: decide whether this plan can close after the ten small
  wins or should stay open for the next `_where_do_i_go` implementation.
