"""Per-frame post-mask helpers for atlas extraction.

The legacy Amiga atlases used an exact-match background of `(0, 49, 0)`
that the runtime keyed out via `pygame.Surface.set_colorkey`. The 4x
Upscayl sheets are AI-upscaled, which interpolates the background into
a band of near-green pixels (for example `(1, 50, 0)`, `(0, 48, 1)`)
that an exact-match colorkey misses. The result is a green halo around
every iso tile and peep when the 4x sheet is in play.

These helpers run as `extract_frame(..., post_mask=...)` callbacks in
source-scaled space (after subsurface, before the final smoothscale).
At source_scale == 1 the helpers are essentially no-ops because the
exact-green pixels were already keyed to alpha 0 at sheet-load time;
at source_scale == 4 they catch the interpolated near-green band and
drop it to alpha 0 before the downscale, keeping silhouettes crisp.
"""

# Standard Library

# PIP3 modules
import pygame


# Tolerance window for "Amiga dim-green background" pixels. The Amiga
# original is exactly `(0, 49, 0)`. The window must be wide enough to
# catch Upscayl's AI interpolation drift but narrow enough to spare
# foreground greens (trees, flags, peep clothing). Picked from sampling
# the Upscayl sheets: their background sits around `(0..6, 35..70, 0..6)`.
_GREEN_R_MAX: int = 20
_GREEN_B_MAX: int = 20
_GREEN_MIN: int = 20
_GREEN_MAX: int = 80
# Foreground greens are saturated; the dim background green has g much
# greater than r and b but stays under ~70. Require g to dominate r/b.
_GREEN_DOMINANCE: int = 15


#============================================
def amiga_green_background_to_alpha(surface: pygame.Surface) -> None:
	"""Drop near-`(0, 49, 0)` background pixels to alpha 0.

	Mutates `surface` in place. Intended for use as a per-frame
	post-mask on AmigaTiles and AmigaSprites cells.
	"""
	# pixels3d / pixels_alpha return numpy views that lock the surface;
	# release the locks via `del` before the surface is used again.
	arr = pygame.surfarray.pixels3d(surface)
	alpha = pygame.surfarray.pixels_alpha(surface)
	# Cast green to a wider int so the dominance subtraction does not
	# wrap around in uint8 arithmetic.
	r = arr[:, :, 0]
	g = arr[:, :, 1].astype('int16')
	b = arr[:, :, 2]
	mask = (
		(r <= _GREEN_R_MAX)
		& (b <= _GREEN_B_MAX)
		& (g >= _GREEN_MIN)
		& (g <= _GREEN_MAX)
		& (g - r.astype('int16') >= _GREEN_DOMINANCE)
		& (g - b.astype('int16') >= _GREEN_DOMINANCE)
	)
	alpha[mask] = 0
	del arr, alpha


#============================================
def residual_black_to_alpha(surface: pygame.Surface) -> None:
	"""Drop pure-black pixels to alpha 0.

	Mirrors the legacy mask used on AmigaSprites cells: pixels with
	`r == g == b == 0` are letterbox/background residue after the
	green colorkey runs and must be transparent.
	"""
	arr = pygame.surfarray.pixels3d(surface)
	alpha = pygame.surfarray.pixels_alpha(surface)
	mask = (
		(arr[:, :, 0] == 0)
		& (arr[:, :, 1] == 0)
		& (arr[:, :, 2] == 0)
	)
	alpha[mask] = 0
	del arr, alpha


#============================================
def amiga_green_and_black_to_alpha(surface: pygame.Surface) -> None:
	"""Combined mask: drop near-green background AND residual black.

	Used by the peep loader because AmigaSprites cells need both the
	green-background mask and the legacy residual-black mask.
	"""
	amiga_green_background_to_alpha(surface)
	residual_black_to_alpha(surface)
