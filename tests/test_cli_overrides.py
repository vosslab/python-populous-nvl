"""Tests for the populous launcher CLI overrides.

Covers:
- Preset switch re-derives mirror constants in `settings`.
- Direct `--size` override updates INTERNAL_WIDTH/HEIGHT only.
- Visible-tile override updates VISIBLE_TILE_COUNT.
- `--size` parser rejects malformed input.
- Fit-screen math returns the expected integer scale for a known monitor.

Each test uses try/finally to restore the active preset so global
settings mutations do not leak into subsequent tests.
"""

# Standard Library
import argparse

# PIP3 modules
import pytest

# local repo modules
import populous_game.cli as cli
import populous_game.settings as settings


def _make_args(**overrides) -> argparse.Namespace:
	"""Build a default-populated Namespace with optional overrides."""
	defaults = dict(
		preset=None,
		size=None,
		window_scale=None,
		fit_screen=False,
		visible_tiles=None,
		seed=None,
		screenshot=None,
	)
	defaults.update(overrides)
	return argparse.Namespace(**defaults)


def _snapshot_preset() -> tuple:
	"""Return the four mirror constants so we can restore them later."""
	return (
		settings.ACTIVE_CANVAS_PRESET,
		settings.INTERNAL_WIDTH,
		settings.INTERNAL_HEIGHT,
		settings.HUD_SCALE,
		settings.VISIBLE_TILE_COUNT,
	)


def _restore_preset(snap: tuple) -> None:
	"""Restore the four mirror constants from a snapshot tuple."""
	settings.ACTIVE_CANVAS_PRESET = snap[0]
	settings.INTERNAL_WIDTH = snap[1]
	settings.INTERNAL_HEIGHT = snap[2]
	settings.HUD_SCALE = snap[3]
	settings.VISIBLE_TILE_COUNT = snap[4]


def test_apply_preset_remaster_sets_mirrors():
	"""--preset remaster switches all four mirror constants."""
	snap = _snapshot_preset()
	try:
		cli.apply_args_to_settings(_make_args(preset='remaster'))
		assert settings.INTERNAL_WIDTH == 640
		assert settings.HUD_SCALE == 2
	finally:
		_restore_preset(snap)


def test_apply_size_overrides_dimensions():
	"""--size 640x400 sets INTERNAL_WIDTH/HEIGHT only."""
	snap = _snapshot_preset()
	try:
		cli.apply_args_to_settings(_make_args(size='640x400'))
		assert settings.INTERNAL_WIDTH == 640
		assert settings.INTERNAL_HEIGHT == 400
	finally:
		_restore_preset(snap)


def test_apply_visible_tiles():
	"""--visible-tiles 14 sets settings.VISIBLE_TILE_COUNT."""
	snap = _snapshot_preset()
	try:
		cli.apply_args_to_settings(_make_args(visible_tiles=14))
		assert settings.VISIBLE_TILE_COUNT == 14
	finally:
		_restore_preset(snap)


def test_size_parser_rejects_no_x():
	"""parse_size raises ValueError when x separator is missing."""
	with pytest.raises(ValueError):
		cli.parse_size('640')


def test_size_parser_rejects_missing_height():
	"""parse_size raises ValueError when height is empty."""
	with pytest.raises(ValueError):
		cli.parse_size('640x')


def test_size_parser_rejects_non_numeric():
	"""parse_size raises ValueError on non-numeric input."""
	with pytest.raises(ValueError):
		cli.parse_size('axb')


def test_fit_screen_picks_largest_integer():
	"""fit_screen_scale returns the largest N that fits both axes."""
	# 320x200 internal, 1920x1200 monitor, default 95%/90% margins.
	# Width fits 1920*0.95 / 320 = 5.7 -> 5; height fits 1200*0.90 / 200 = 5.4 -> 5.
	scale = cli.fit_screen_scale(320, 200, 1920, 1200)
	assert scale == 5


def test_fit_screen_minimum_scale_is_one():
	"""fit_screen_scale never drops below 1 even on tiny monitors."""
	# 320x200 internal canvas already exceeds a 200x200 viewport.
	scale = cli.fit_screen_scale(320, 200, 200, 200)
	assert scale == 1


def test_apply_seed_does_not_touch_settings():
	"""--seed is consumed by Game(), not by apply_args_to_settings."""
	snap = _snapshot_preset()
	try:
		cli.apply_args_to_settings(_make_args(seed=42))
		# All four mirror constants untouched.
		assert _snapshot_preset() == snap
	finally:
		_restore_preset(snap)
