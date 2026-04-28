# TODO

## Pending

- NumPy-backed terrain model. Move `GameMap.corners` from
  list-of-lists to `numpy.ndarray(dtype=numpy.uint8)` shape
  `(grid_height + 1, grid_width + 1)`. Also convert `_map_alt` and
  `_map_blk` (when added) to ndarrays. Preserve the existing
  `GameMap` public API (`get_corner_altitude`, `set_corner_altitude`,
  `get_tile_key`, `propagate_raise`, terrain helpers) -- callers in
  the renderer, powers, peeps, and input modules continue to use
  those methods, not raw indexing. Phase 2 may migrate the renderer
  through stable helper methods. Phase 3 may add a vectorized
  `_make_map` / tile metadata rebuild. Guardrail: simulation output
  must not change. Defer until the island generator (added
  2026-04-28) is screenshot-stable.
- peep health bar / shield-panel life readout: align
  `ui_panel._draw_peep_bars()` with the ASM shield routine in
  `asm/populous_prg.asm` (`_show_the_shield`).
  Implementation checklist:
  1. Current Python behavior in `ui_panel._draw_peep_bars()`:
     - reads `selection.who.life`
     - calls `_compute_peep_bar_model(selection)` and draws the
       resulting bars into the existing shield-panel slot
     - uses fixed bar positions/colors, but the actual widths now come
       from the helper seam rather than hard-coded 100/10/1 segments
  2. ASM branches in `_show_the_shield`:
     - general peep branch: live peep life bar rendering
     - combat branch: split life bars for peep and opponent
     - special type-1 branch: `check_life`-driven life bars
  3. Exact bar inputs from the source:
     - general branch:
       - peep field read: `peep[+4]`
       - if `life > 0x1000`:
         - `primary = life // 0x0400`
         - `secondary = life % 0x0400`
       - otherwise:
         - `primary = life // 0x0100`
         - `secondary = (life % 0x0100) // 0x0010`
       - the helper treats both values as bar widths; draw code clamps
         the rendered height to the bar slot
     - combat branch:
       - reads `peep[+4]` and opponent `peep[+4]`
       - final widths:
         - `barA = (lifeA * 16) // (lifeA + lifeB)`
         - `barB = (lifeB * 16) // (lifeA + lifeB)`
     - special type-1 branch:
       - reads `check_life(peep[+1], peep[+8])`
       - if return is `0`, force to `1`
       - if return is `0x0bea`, the first bar is full (`10` in the ASM
         call sequence)
       - otherwise `bar = (check_life * 16) // 0x0131`
       - second bar uses `(peep[+4] * 16) // check_life`, clamped to
         `0..16`
       - division uses integer truncation, matching the ASM `DIVS` /
         `DIVU` behavior
  4. Branch selection in Python:
     - general branch: default for peeps when no more specific state is
       available
     - combat branch: `selection.kind == 'peep'`,
       `selection.who.state == 'fight'`, and `selection.who.shield_opponent`
       is present
     - special type-1 branch: `selection.kind == 'peep'` and
       `selection.who.check_life_value` is present
     - current Python peep fields used: `life`, `state`, `weapon_type`,
       optional `shield_opponent`, optional `check_life_value`
  5. Current Python behavior that already matches ASM:
     - the shield panel is peep-centric and uses the current selected
       entity
     - life values are read from the live peep object
     - peep life still decays in the normal update loop
  6. Current Python behavior that differs from ASM:
     - the current code does not yet infer combat/type-1 branch state
       from the exact ASM peep flags; it uses the best available model
       seam
     - the helper is an approximation over the current Python model,
       not a raw struct decode of the ASM record
  7. Smallest patch plan:
     - keep the existing shield panel layout and peep-centric selection
       path
     - keep `_compute_peep_bar_model(selection)` as the numeric seam
     - drive `_draw_peep_bars()` from that helper without introducing a
       new health subsystem
  8. Focused tests:
     - unit test the general branch against a peep with life above and
       below `0x1000`
     - unit test the combat branch with two peeps of known life values
     - unit test the type-1 branch by stubbing `check_life_value`
     - keep the existing shield-panel label test and add branch-specific
       model assertions instead of broad screenshot diffs
- Peep behavior case: build
- Peep behavior case: gather
- Peep behavior case: fight
- Add sound to actions/powers/combat
- Create enemies
- Add a home page and game mode/password selection
- Add a gameover page
- Create battles
- Implement peeps moving system `_move_peeps`, `_move_explorer`, `_where_do_i_go`
- Add trees and rocks plus logic to remove
- bug: castle drawing on terrain edges. The castle is always drawn as a full unit,
  even if it shall not be seen partially out of the 8x8 map.
- bug: mouse sprite is drawn behind the shield sprites. It shall be the opposite.

## Done

01. Add a game window and the ability to scroll to the edges of the terrain
02. Add the star sprite for terrain control
03. Manage peeps 1: Add two energy bars above (one yellow, one orange);
    1 yellow pixel = one full orange bar
04. Manage peeps 2: Correct peep animations in each direction
05. Correct edge effect: Add dirt to the edges of the terrain to avoid black
    (flat surfaces can be stacked to fill black spaces)
06. Manage buildings 5: Display buildings in the background first
07. Use AmigaSprites
08. Use the AmigaUI
09. Rework the mechanism for displaying the map above the background
10. Refactor the map and height control
11. Adjust mouse movement and the isometric transformation (distance detection)
12. Manage buildings 1: Demolish a building if the terrain is not flat
13. Manage buildings 4: Each building has a population growth rate. A list of
    population output frequencies and energy growth rates is required.
14. Manage buildings 2: Evaluate if there is sufficient space for a building
15. Create a minimap
16. Relocate screen using minimap
17. Manage buildings 3: Setting up the castle
18. Take into account multi key (map scrolling in 8 directions possible)
19. Added powers buttons plus emboss when clicking
20. Added pointer logic for various actions (terrain, papal, shield)
21. Add the `?` option Display "shield" for information
22. Place a papal magnet case
23. Add weapon system
24. Moving in cardinal direction shall move 1 block instead of 2
25. Correct drowning animation (use 4 sprites)
26. Peep life is not changing on the display (shield)
27. House health bar (yellow as a function of level, increasing orange as a
    function of life)
28. Modify health bar with a border
