"""Pin sheet_registry resolution and fallback behavior."""

import os
import populous_game.sheet_registry as sheet_registry


def test_all_roles_resolve_to_existing_files():
	"""Every registered role must resolve to a real file under GFX_DIR."""
	for role in sheet_registry.ASSET_SHEETS:
		path, source_scale = sheet_registry.resolve_role(role)
		assert os.path.exists(path), f"role {role} resolved to missing {path}"
		assert source_scale in (1, 4)


def test_upscayl_preferred_when_present(tmp_path, monkeypatch):
	"""resolve_role picks the 4x candidate when both files exist."""
	# Stub a tiny GFX_DIR with both candidates for tiles_1 so the test
	# is independent of the real assets.
	stub_dir = tmp_path
	upscayl = stub_dir / "AmigaTiles1_upscayl_4x_high-fidelity-4x.png"
	original = stub_dir / "AmigaTiles1.png"
	upscayl.write_bytes(b"x")
	original.write_bytes(b"x")
	monkeypatch.setattr(sheet_registry.settings, "GFX_DIR", str(stub_dir))
	path, source_scale = sheet_registry.resolve_role("tiles_1")
	assert path.endswith("_upscayl_4x_high-fidelity-4x.png")
	assert source_scale == 4


def test_fallback_when_upscayl_missing(tmp_path, monkeypatch):
	"""resolve_role returns the original PNG with source_scale 1."""
	stub_dir = tmp_path
	original = stub_dir / "AmigaTiles1.png"
	original.write_bytes(b"x")
	monkeypatch.setattr(sheet_registry.settings, "GFX_DIR", str(stub_dir))
	path, source_scale = sheet_registry.resolve_role("tiles_1")
	assert path == str(original)
	assert source_scale == 1


def test_missing_both_raises(tmp_path, monkeypatch):
	"""Loud failure when even the original PNG is missing."""
	monkeypatch.setattr(sheet_registry.settings, "GFX_DIR", str(tmp_path))
	try:
		sheet_registry.resolve_role("tiles_1")
	except FileNotFoundError:
		return
	raise AssertionError("expected FileNotFoundError when no candidate exists")


def test_required_roles_registered():
	"""Plan-required roles are present so future code never invents filenames."""
	required = {
		"tiles_1", "tiles_2", "tiles_3", "tiles_4",
		"sprites_amiga", "sprites_generic",
		"ui", "ui_click", "buttons", "weapons",
	}
	assert required.issubset(set(sheet_registry.ASSET_SHEETS))
