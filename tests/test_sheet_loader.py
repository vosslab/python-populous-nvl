"""Pin sheet_loader.extract_frame crop + resize semantics."""

import pygame
import populous_game.sheet_loader as sheet_loader


def _init_pygame():
	pygame.init()
	pygame.display.set_mode((1, 1))


def test_extract_frame_returns_runtime_size():
	"""Cropped surface must match requested runtime size exactly."""
	_init_pygame()
	sheet_loader.clear_caches()
	# Real role from the registry; runtime size mirrors the tile-cache
	# contract `(32 * TERRAIN_SCALE, 24 * TERRAIN_SCALE)` for scale 1.
	out = sheet_loader.extract_frame(
		"tiles_1",
		(12, 10, 32, 24),
		(32, 24),
		scale_filter='nearest',
		color_key=(0, 49, 0),
	)
	assert out.get_size() == (32, 24)


def test_extract_frame_runtime_size_independent_of_source_scale():
	"""Same runtime size whether the resolved sheet is 1x or 4x."""
	_init_pygame()
	sheet_loader.clear_caches()
	out = sheet_loader.extract_frame(
		"tiles_1",
		(12, 10, 32, 24),
		(64, 48),
		scale_filter='smooth',
		color_key=(0, 49, 0),
	)
	assert out.get_size() == (64, 48)


def test_extract_frame_caches_repeated_calls():
	"""Repeated calls with the same key return the same surface."""
	_init_pygame()
	sheet_loader.clear_caches()
	args = ("tiles_1", (12, 10, 32, 24), (32, 24))
	a = sheet_loader.extract_frame(*args, scale_filter='nearest', color_key=(0, 49, 0))
	b = sheet_loader.extract_frame(*args, scale_filter='nearest', color_key=(0, 49, 0))
	assert a is b


def test_load_sheet_returns_source_scale():
	"""load_sheet reports the resolved source_scale."""
	_init_pygame()
	sheet_loader.clear_caches()
	surface, source_scale = sheet_loader.load_sheet("tiles_1", color_key=(0, 49, 0))
	assert isinstance(surface, pygame.Surface)
	assert source_scale in (1, 4)


def test_post_mask_runs_in_source_scaled_space():
	"""post_mask receives the cropped surface BEFORE final resize."""
	_init_pygame()
	sheet_loader.clear_caches()
	captured = {}

	def capture_size(surface):
		captured['w'], captured['h'] = surface.get_size()

	sheet_loader.extract_frame(
		"sprites_amiga",
		(11, 10, 16, 16),
		(16, 16),
		scale_filter='smooth',
		color_key=(0, 49, 0),
		post_mask=capture_size,
	)
	# At source_scale==1 the cropped surface is 16x16; at 4x it is 64x64.
	# Either way, the captured size must be 16 * source_scale per axis.
	_, source_scale = sheet_loader.load_sheet("sprites_amiga", color_key=(0, 49, 0))
	assert (captured['w'], captured['h']) == (16 * source_scale, 16 * source_scale)
