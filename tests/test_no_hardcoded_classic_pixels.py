"""Lint: production code must not hard-code the classic 320 / 200 canvas.

Once the M4 canvas modernization landed, the only place where the
literal `320` or `200` should describe the classic canvas is the
`CANVAS_PRESETS` dictionary in `populous_game/settings.py` and the
docstrings in `populous_game/layout.py`. Any other hit is a regression.

The matcher tolerates coincidental literals (alpha=200, time-based
mod-200 ticks, color tuples, PEEP_LIFE_MAX=200) via a narrow per-line
whitelist. If you find a new coincidence, extend the whitelist rather
than rewriting the constant in production code.
"""

# Standard Library
import os
import re

# local repo modules
import populous_game


# Matches a bare 320 or 200 not adjacent to another digit.
_LITERAL_PATTERN = re.compile(r'(?<![0-9])(320|200)(?![0-9])')

# Files that may legitimately mention the classic literal. Anchored to
# the package root so a future `populous_game/scenarios/settings.py` does
# not silently inherit the whitelist.
_FILE_WHITELIST = {
	'settings.py',
	'layout.py',
}

# Substrings that mark a line as non-canvas-pixel (coincidental literals).
_LINE_SUBSTRING_WHITELIST = (
	'CANVAS_PRESETS',
	'INTERNAL_WIDTH',
	'INTERNAL_HEIGHT',
	'alpha',          # e.g. overlay.fill((0, 0, 0, 200))
	'time.get_ticks', # e.g. frame_idx = ... / 200
	'PEEP_LIFE_MAX',
)


def _scan_for_violations():
	"""Return list of '<path>:<line>: <text>' for hits not in the whitelist."""
	pkg_dir = os.path.dirname(populous_game.__file__)
	violations = []
	for root, dirs, files in os.walk(pkg_dir):
		# Skip cache directories.
		if '__pycache__' in root:
			continue
		for fname in files:
			if not fname.endswith('.py'):
				continue
			fpath = os.path.join(root, fname)
			# Whitelist applies only to files directly under the package
			# root (not subpackages with the same basename).
			rel = os.path.relpath(fpath, pkg_dir)
			if rel in _FILE_WHITELIST:
				continue
			with open(fpath, 'r', encoding='utf-8') as fh:
				for lineno, line in enumerate(fh, start=1):
					if not _LITERAL_PATTERN.search(line):
						continue
					stripped = line.strip()
					# Comment-only lines are documentation, not code.
					if stripped.startswith('#'):
						continue
					# Per-line substring whitelist (color tuples, alpha, etc.).
					if any(s in line for s in _LINE_SUBSTRING_WHITELIST):
						continue
					# Coincidental color tuples like (0, 0, 200) or (200, 0, 0):
					# strip out any bare RGB tuple from the inspected portion.
					code_part = line.split('#', 1)[0]
					sanitized = re.sub(r'\([^)]*\)', '', code_part)
					if not _LITERAL_PATTERN.search(sanitized):
						continue
					violations.append(f"{fpath}:{lineno}: {stripped}")
	return violations


def test_no_hardcoded_classic_pixels_in_production():
	"""No bare 320 / 200 outside the canvas preset definition."""
	violations = _scan_for_violations()
	assert violations == [], (
		"Found bare 320/200 literals in production files. Replace with "
		"settings.INTERNAL_WIDTH / INTERNAL_HEIGHT or extend the whitelist "
		"if the literal is coincidental:\n  " + "\n  ".join(violations)
	)
