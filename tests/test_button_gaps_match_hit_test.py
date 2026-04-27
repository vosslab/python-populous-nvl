"""Buttons documented as removed must be absent from ui_panel.buttons.

Prevents the doc and the UI from drifting. If a future patch re-adds
`_find_shield` or `_battle_over` to the hit-test map without wiring a
real handler, this test fails loudly.
"""

import os
import populous_game.game as game_module


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAPS_PATH = os.path.join(REPO_ROOT, 'docs', 'active_plans', 'm2_button_gaps.md')


def _gaps_doc_text():
    with open(GAPS_PATH, 'r') as fp:
        return fp.read()


def test_gaps_doc_exists():
    """The gaps doc must exist while any button is removed."""
    assert os.path.isfile(GAPS_PATH), (
        "docs/active_plans/m2_button_gaps.md missing; either restore "
        "the doc or re-add the missing buttons to ui_panel.buttons."
    )


def test_documented_removed_buttons_absent_from_hit_test():
    """Every button listed under '## Removed in M2' is absent from buttons."""
    game = game_module.Game()
    text = _gaps_doc_text()
    # Naive parser: look for section headings of the form "### `_name`".
    removed = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('### `') and line.endswith('`'):
            name = line[len('### `'):-1]
            if name.startswith('_'):
                removed.append(name)
    assert removed, (
        "Could not parse any removed-button names from m2_button_gaps.md; "
        "expected '### `_name`' section headings."
    )
    leaked = [name for name in removed if name in game.ui_panel.buttons]
    assert not leaked, (
        f"Buttons documented as removed are still in ui_panel.buttons: "
        f"{leaked}. Either re-implement them with a real handler and "
        f"remove from m2_button_gaps.md, or take them out of the "
        f"hit-test map."
    )
