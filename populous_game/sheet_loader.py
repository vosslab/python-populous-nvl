"""Source-scale-aware atlas sheet loader and frame extractor.

Pairs with [populous_game/sheet_registry.py](sheet_registry.py). Two
public entry points:

- `load_sheet(role, color_key=None)` returns `(surface, source_scale)`.
  Loads the resolved sheet through `pygame.image.load()`, optionally
  sets a color key on the raw surface (matching the legacy Amiga
  green background trick), then converts to SRCALPHA. The result is
  cached per `(role, color_key)`.
- `extract_frame(role, logical_rect, runtime_size, *,
  scale_filter='smooth', color_key=None, post_mask=None)` extracts a
  single atlas cell. The logical crop rectangle is multiplied by
  `source_scale` to land in actual sheet pixels; the cropped surface
  is optionally passed through a per-frame mask in source-scaled
  space; finally it is resized to `runtime_size` with smoothscale
  (default) or nearest-neighbor.

The whole atlas is never resized as a unit. Crop happens at source
resolution; the only resize step is per-frame.
"""

# Standard Library

# PIP3 modules
import pygame

# local repo modules
import populous_game.sheet_registry as sheet_registry


# Cache of (role, color_key) -> (surface, source_scale) loaded sheets.
_SHEET_CACHE: dict = {}

# Cache of (role, logical_rect, runtime_size, scale_filter) -> Surface.
# This per-frame cache assumes a single mask logic per (role, rect).
# Callers passing a `post_mask` should not request two different masked
# outputs at the same key in the same process; the cache does not key
# on the mask identity.
_FRAME_CACHE: dict = {}


#============================================
def load_sheet(role: str, color_key=None) -> tuple:
	"""Load (and cache) the sheet for `role`.

	Args:
		role: key into `sheet_registry.ASSET_SHEETS`.
		color_key: optional `(r, g, b)` color to mark transparent on
			the raw surface before it is converted to SRCALPHA.
			Matches the legacy `(0, 49, 0)` Amiga-green trick used by
			the terrain and peep loaders.

	Returns:
		`(surface, source_scale)` where surface is an SRCALPHA
		`pygame.Surface` and source_scale is the integer multiplier
		from logical atlas pixels to actual sheet pixels (1 for the
		original PNG, 4 for the Upscayl 4x sheet).
	"""
	# Look up a previously loaded sheet first; pygame.image.load() and
	# convert_alpha() are non-trivial so we want one load per role per
	# color key per process.
	cache_key = (role, color_key)
	if cache_key in _SHEET_CACHE:
		return _SHEET_CACHE[cache_key]

	path, source_scale = sheet_registry.resolve_role(role)
	# Load the raw surface so the color-key step matches legacy
	# behavior: set_colorkey on a converted (non-alpha) surface, then
	# upgrade to SRCALPHA so per-pixel alpha is available downstream.
	raw = pygame.image.load(path).convert()
	if color_key is not None:
		raw.set_colorkey(color_key)
	sheet = raw.convert_alpha()

	# Sanity check the loaded sheet against the role's declared logical
	# size. A mismatch usually means an upstream tool re-exported the
	# atlas at a different size and the runtime would then crop the
	# wrong region. Fail loudly so the issue surfaces at startup.
	expected = sheet_registry.expected_logical_size(role)
	if expected is not None:
		actual_w, actual_h = sheet.get_size()
		exp_w, exp_h = expected
		want_w = exp_w * source_scale
		want_h = exp_h * source_scale
		if (actual_w, actual_h) != (want_w, want_h):
			raise ValueError(
				f"Sheet '{role}' at {path} is {actual_w}x{actual_h} "
				f"but expected {want_w}x{want_h} "
				f"(logical {exp_w}x{exp_h} * source_scale {source_scale})"
			)

	_SHEET_CACHE[cache_key] = (sheet, source_scale)
	return sheet, source_scale


#============================================
def extract_frame(
	role: str,
	logical_rect,
	runtime_size: tuple,
	*,
	scale_filter: str = 'smooth',
	color_key=None,
	post_mask=None,
) -> pygame.Surface:
	"""Extract one atlas cell into a runtime-sized surface.

	Crop semantics:
	- The logical_rect is in original logical atlas coordinates.
	- Each (x, y, w, h) component is multiplied by source_scale before
	  the subsurface call, so the same logical rect works for a 1x
	  original PNG and a 4x Upscayl sheet.
	- The cropped surface is optionally passed through `post_mask` in
	  source-scaled space (before the final resize), so masks like
	  the residual-black -> alpha pass on AmigaSprites still apply
	  cleanly even when the source is 4x.
	- The cropped surface is then resized to `runtime_size` with
	  smoothscale by default (matches Upscayl's high-fidelity look) or
	  nearest-neighbor when `scale_filter='nearest'` (used for chunky
	  pixel art on the original 1x sheet, hit-test masks, etc.).

	Args:
		role: key into `sheet_registry.ASSET_SHEETS`.
		logical_rect: `(x, y, w, h)` or pygame.Rect in original logical
			atlas coordinates.
		runtime_size: `(width, height)` for the cached output surface.
		scale_filter: 'smooth' (default) or 'nearest'.
		color_key: optional color-key passed through to `load_sheet`.
		post_mask: optional callable `mask(surface) -> None` invoked
			on the cropped surface in source-scaled space before the
			final resize. Used by the peep loader to drop residual
			black to alpha 0.

	Returns:
		A `pygame.Surface` of size `runtime_size`.
	"""
	# Normalize logical_rect into a 4-tuple and the cache key so callers
	# may pass a pygame.Rect or a plain tuple interchangeably.
	if isinstance(logical_rect, pygame.Rect):
		lx, ly, lw, lh = (
			logical_rect.x,
			logical_rect.y,
			logical_rect.w,
			logical_rect.h,
		)
	else:
		lx, ly, lw, lh = logical_rect
	rect_key = (int(lx), int(ly), int(lw), int(lh))
	rs_key = (int(runtime_size[0]), int(runtime_size[1]))
	cache_key = (role, rect_key, rs_key, scale_filter)
	if post_mask is None and cache_key in _FRAME_CACHE:
		return _FRAME_CACHE[cache_key]

	sheet, source_scale = load_sheet(role, color_key=color_key)

	# Multiply the logical rect into source-scaled coordinates so the
	# same atlas metadata works for 1x and 4x sheets without changing.
	src_rect = pygame.Rect(
		lx * source_scale,
		ly * source_scale,
		lw * source_scale,
		lh * source_scale,
	)
	# subsurface() returns a view sharing pixels with the parent; copy()
	# detaches so callers can mutate alpha without scribbling on the
	# shared sheet.
	sub = sheet.subsurface(src_rect).copy()

	# Apply caller-provided per-frame mask in source-scaled space. The
	# residual-black -> alpha pass on AmigaSprites lands here and runs
	# at 4x resolution before downscale, which preserves silhouette
	# cleanliness through smoothscale.
	if post_mask is not None:
		post_mask(sub)

	# Final resize: smoothscale gives clean downscaled visuals from 4x
	# Upscayl art; nearest preserves the chunky-pixels look from 1x.
	if sub.get_size() != rs_key:
		if scale_filter == 'smooth':
			out = pygame.transform.smoothscale(sub, rs_key)
		elif scale_filter == 'nearest':
			out = pygame.transform.scale(sub, rs_key)
		else:
			raise ValueError(
				f"Unknown scale_filter '{scale_filter}'. "
				"Expected 'smooth' or 'nearest'."
			)
	else:
		out = sub

	if post_mask is None:
		_FRAME_CACHE[cache_key] = out
	return out


#============================================
def clear_caches() -> None:
	"""Drop sheet and frame caches.

	Used by tests that mutate `settings.TERRAIN_SCALE` /
	`settings.HUD_SCALE` mid-process and need a fresh load. Production
	code should not need this.
	"""
	_SHEET_CACHE.clear()
	_FRAME_CACHE.clear()
