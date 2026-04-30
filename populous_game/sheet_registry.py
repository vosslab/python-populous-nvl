"""Centralized atlas sheet registry.

Maps a logical role (for example, "tiles_1", "sprites_amiga", "ui") to an
ordered list of candidate sheet files plus the source scale that each
candidate is rendered at. The loader in
[populous_game/sheet_loader.py](sheet_loader.py) consumes this registry,
prefers the first existing candidate, and uses the declared
`source_scale` to multiply atlas crop rectangles into source-scaled
coordinates before extracting frames.

Source scale is declared per entry, not inferred from filename suffix or
measured pixel ratio. The Upscayl 4x copies of every active atlas live
next to the original PNGs under [data/gfx/](../../data/gfx/) with the
suffix `_upscayl_4x_high-fidelity-4x.png`. When such a file is present,
the loader extracts from it at 4x logical pixels per logical pixel and
smoothscales the cropped frame to the runtime target. When the 4x file
is missing, the original PNG drives the run with `source_scale = 1`.

The registry has no `pygame` dependency.
"""

# Standard Library
import os

# local repo modules
import populous_game.settings as settings


#============================================
# Sheet candidate type
#============================================
# Each role's "candidates" entry is a list of dicts in preference order.
# The loader picks the first candidate whose `filename` exists under
# `settings.GFX_DIR`. Each candidate declares:
#   filename: basename inside data/gfx/
#   source_scale: integer multiplier from logical atlas pixels to actual
#       sheet pixels. 1 for the original PNG, 4 for the Upscayl sheet.
# A role-level `expected_logical_size` may optionally pin the original
# atlas dimensions so the loader can sanity-check
#   surface.size == expected_logical_size * source_scale
# after load.
#
# Roles included now (registration is cheap; runtime callers can ignore
# unused sheets, but no future code should reach for ad hoc filenames):
#   tiles_1..4         AmigaTiles1..4 PNG
#   sprites_amiga      AmigaSprites1 PNG (active peep sheet)
#   sprites_generic    Sprites PNG (legacy/general sprite atlas)
#   ui                 AmigaUI HUD chrome
#   ui_click           AmigaUI_click HUD pressed-button overlay
#   buttons            ButtonUI 5x5 grid of HUD buttons
#   weapons            Weapons row of building-tier icons


def _candidates(upscayl_name: str, original_name: str) -> list:
	"""Return preferred-with-fallback candidate list.

	Args:
		upscayl_name: 4x sheet basename under GFX_DIR.
		original_name: original PNG basename under GFX_DIR.

	Returns:
		List of two candidate dicts in preference order, with the
		Upscayl 4x sheet first and the original PNG as fallback.
	"""
	# Upscayl entry is preferred when it exists on disk.
	preferred = {"filename": upscayl_name, "source_scale": 4}
	# Original PNG is the always-present fallback.
	fallback = {"filename": original_name, "source_scale": 1}
	return [preferred, fallback]


# Filename convention used by the Upscayl batch step.
_UPSCAYL_SUFFIX: str = "_upscayl_4x_high-fidelity-4x.png"


ASSET_SHEETS: dict = {
	"tiles_1": {
		"candidates": _candidates(
			"AmigaTiles1" + _UPSCAYL_SUFFIX, "AmigaTiles1.png",
		),
		"expected_logical_size": (336, 262),
	},
	"tiles_2": {
		"candidates": _candidates(
			"AmigaTiles2" + _UPSCAYL_SUFFIX, "AmigaTiles2.png",
		),
	},
	"tiles_3": {
		"candidates": _candidates(
			"AmigaTiles3" + _UPSCAYL_SUFFIX, "AmigaTiles3.png",
		),
	},
	"tiles_4": {
		"candidates": _candidates(
			"AmigaTiles4" + _UPSCAYL_SUFFIX, "AmigaTiles4.png",
		),
	},
	"sprites_amiga": {
		"candidates": _candidates(
			"AmigaSprites1" + _UPSCAYL_SUFFIX, "AmigaSprites1.png",
		),
		"expected_logical_size": (336, 262),
	},
	"sprites_generic": {
		"candidates": _candidates(
			"Sprites" + _UPSCAYL_SUFFIX, "Sprites.png",
		),
	},
	"ui": {
		"candidates": _candidates(
			"AmigaUI" + _UPSCAYL_SUFFIX, "AmigaUI.png",
		),
		"expected_logical_size": (320, 200),
	},
	"ui_click": {
		"candidates": _candidates(
			"AmigaUI_click" + _UPSCAYL_SUFFIX, "AmigaUI_click.png",
		),
	},
	"buttons": {
		"candidates": _candidates(
			"ButtonUI" + _UPSCAYL_SUFFIX, "ButtonUI.png",
		),
		"expected_logical_size": (170, 85),
	},
	"weapons": {
		"candidates": _candidates(
			"Weapons" + _UPSCAYL_SUFFIX, "Weapons.png",
		),
		"expected_logical_size": (160, 16),
	},
}


#============================================
def resolve_role(role: str) -> tuple:
	"""Resolve a role to (absolute_path, source_scale).

	Walks the role's `candidates` list in order and returns the first
	whose file exists under `settings.GFX_DIR`. The original PNG entry
	is always last and is expected to exist; if neither exists this
	raises FileNotFoundError so the caller fails loudly instead of
	silently degrading.

	Args:
		role: key into ASSET_SHEETS.

	Returns:
		A 2-tuple `(absolute_path, source_scale)`.
	"""
	# Reject typos at the boundary so future code cannot quietly fall
	# back to a default sheet.
	entry = ASSET_SHEETS[role]
	for candidate in entry["candidates"]:
		path = os.path.join(settings.GFX_DIR, candidate["filename"])
		if os.path.exists(path):
			return path, candidate["source_scale"]
	# No candidate exists; surface the missing original PNG as a clear
	# error rather than returning a phantom path.
	original = entry["candidates"][-1]["filename"]
	raise FileNotFoundError(
		f"No sheet file found for role '{role}'. "
		f"Expected at minimum '{original}' under {settings.GFX_DIR}."
	)


#============================================
def expected_logical_size(role: str):
	"""Return the role's declared logical sheet size, or None.

	Used by the loader as a sanity check: after loading the resolved
	candidate, the loader may assert that the loaded surface measures
	`expected_logical_size * source_scale`. Roles that have not been
	measured precisely return None and skip the check.
	"""
	# Look up the optional pin without papering over a missing role.
	entry = ASSET_SHEETS[role]
	return entry.get("expected_logical_size")
