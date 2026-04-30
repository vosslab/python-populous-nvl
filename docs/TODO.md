# TODO

## Pending

- Read [asm/PEEPS_GAP_REPORT.md](../asm/PEEPS_GAP_REPORT.md) for the
  full Python parity gap report against `asm/PEEPS_BEHAVIOR.md`.
- Next implementation item: add an explicit peep record layer with the
  ASM fields needed for `_move_peeps`, `_move_explorer`, and
  `_set_town`.
- Active plan for the current ASM-parity small wins:
  [docs/active_plans/ASM_PEEP_PARITY_SMALL_WINS.md](active_plans/ASM_PEEP_PARITY_SMALL_WINS.md).
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
