"""Pin lengths and known values of the ASM directional/tile tables.

Each constant is ported verbatim from asm/populous_prg.asm. See the
comments in populous_game/settings.py for source addresses.
"""

import populous_game.settings as settings


def test_asm_opposite_length_and_involution():
	"""_opposite has 8 entries and is its own involution."""
	assert len(settings.ASM_OPPOSITE) == 8
	# Direction 0 should map to 4 (north <-> south style flip).
	assert settings.ASM_OPPOSITE[0] == 4
	# Applying _opposite twice returns the original direction.
	for d in range(8):
		assert settings.ASM_OPPOSITE[settings.ASM_OPPOSITE[d]] == d


def test_asm_to_offset_length_and_known_values():
	"""_to_offset has 8 signed flat-byte deltas on the 64-wide map."""
	assert len(settings.ASM_TO_OFFSET) == 8
	# Direction 0 walks one row up: -64 in a 64-wide flat map.
	assert settings.ASM_TO_OFFSET[0] == -64
	# Direction 4 walks one row down: +64.
	assert settings.ASM_TO_OFFSET[4] == 64


def test_asm_offset_vector_length_and_anchor():
	"""_offset_vector has 25 entries; first short is 0x0000."""
	assert len(settings.ASM_OFFSET_VECTOR) == 25
	# First entry is the zero offset (self).
	assert settings.ASM_OFFSET_VECTOR[0] == 0
	# Trailing DC.W short is 0xff7f -> signed -129.
	assert settings.ASM_OFFSET_VECTOR[-1] == -129


def test_asm_big_city_length_and_min_max():
	"""_big_city has 9 entries within a tight 41..44 range."""
	assert len(settings.ASM_BIG_CITY) == 9
	assert min(settings.ASM_BIG_CITY) == 41
	assert max(settings.ASM_BIG_CITY) == 44
