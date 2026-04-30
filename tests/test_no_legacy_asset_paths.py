"""Guard against runtime loaders reading the legacy TILES_PATH/SPRITES_PATH.

After the upscayl-runtime migration, no module under `populous_game/`
should reach for `settings.TILES_PATH` or `settings.SPRITES_PATH`
directly. Those constants are either deleted or kept only as deprecated
aliases inside `settings.py`. This guard greps the package and fails if
a regression reintroduces a direct read.

`settings.py` is allowlisted because the constant definitions (or
deprecated aliases derived from `ASSET_SHEETS`) live there.
"""

import os

import tests.git_file_utils as git_file_utils


_LEGACY_NAMES = ("TILES_PATH", "SPRITES_PATH")
_ALLOWED_FILES = {"settings.py"}


def _iter_runtime_modules():
	repo_root = git_file_utils.get_repo_root()
	pkg = os.path.join(repo_root, "populous_game")
	for name in os.listdir(pkg):
		if not name.endswith(".py"):
			continue
		if name in _ALLOWED_FILES:
			continue
		yield os.path.join(pkg, name)


def test_no_runtime_module_reads_legacy_path_constants():
	"""Fail loudly if any runtime loader bypasses the registry."""
	offenders = []
	for path in _iter_runtime_modules():
		with open(path, "r") as handle:
			text = handle.read()
		for legacy in _LEGACY_NAMES:
			needle = f"settings.{legacy}"
			if needle in text:
				offenders.append((os.path.basename(path), legacy))
	assert offenders == [], (
		"Runtime modules must use sheet_registry, not legacy "
		f"settings.* path constants. Offenders: {offenders}"
	)
