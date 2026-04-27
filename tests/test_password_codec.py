"""Tests for password encoder/decoder (M8)."""

import pytest
import populous_game.password_codec as codec


def test_encode_zero_is_all_a():
	"""Seed 0 encodes to seven A's."""
	assert codec.encode_seed(0) == 'AAAAAAA'


def test_round_trip_small_seeds():
	"""Encoding then decoding returns the original seed for small values."""
	for seed in (0, 1, 25, 26, 100, 12345, 999999):
		password = codec.encode_seed(seed)
		assert codec.decode_password(password) == seed


def test_decode_lowercase_accepted():
	"""Lowercase passwords are accepted (normalized to uppercase)."""
	password = codec.encode_seed(12345)
	assert codec.decode_password(password.lower()) == 12345


def test_decode_padded_short_password():
	"""Short passwords are zero-padded on the high-order side."""
	# 'B' = 1, padded to 'AAAAAAB' = 1
	assert codec.decode_password('B') == 1


def test_decode_invalid_character_raises():
	"""Decoding non-letters raises ValueError."""
	with pytest.raises(ValueError):
		codec.decode_password('ABC123!')


def test_encode_overflow_raises():
	"""Seeds beyond MAX_SEED raise ValueError."""
	with pytest.raises(ValueError):
		codec.encode_seed(codec.MAX_SEED)
