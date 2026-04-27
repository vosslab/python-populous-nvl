"""Original-style password encoder/decoder for python-populous (M8).

The Amiga original used short alphabetic passwords to identify levels.
We reproduce a simple, deterministic, round-trip encoder: a scenario's
seed (as an unsigned 32-bit integer) is encoded into a 7-character
uppercase A-Z string, and decoded back to the same integer. The mapping
is base-26 over a fixed alphabet, so any 7-letter input that decodes
within range round-trips.

Padding rule: shorter strings are zero-padded ('A' = 0). Inputs longer
than 7 characters or containing non-letters raise ValueError.
"""

ALPHABET: str = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
PASSWORD_LENGTH: int = 7
MAX_SEED: int = 26 ** PASSWORD_LENGTH

#============================================

def encode_seed(seed: int) -> str:
	"""Encode a non-negative integer seed into a 7-letter uppercase password."""
	if seed < 0:
		raise ValueError('seed must be non-negative')
	if seed >= MAX_SEED:
		raise ValueError(f'seed >= {MAX_SEED} cannot be encoded in {PASSWORD_LENGTH} letters')
	chars = []
	value = seed
	for _ in range(PASSWORD_LENGTH):
		chars.append(ALPHABET[value % 26])
		value //= 26
	# Reverse so the high-order digit comes first
	password = ''.join(reversed(chars))
	return password

#============================================

def decode_password(password: str) -> int:
	"""Decode a 1..7-letter uppercase password into the original seed."""
	if not isinstance(password, str):
		raise ValueError('password must be a string')
	upper = password.upper()
	if len(upper) == 0 or len(upper) > PASSWORD_LENGTH:
		raise ValueError(f'password length must be 1..{PASSWORD_LENGTH}')
	for ch in upper:
		if ch not in ALPHABET:
			raise ValueError(f'invalid character in password: {ch!r}')
	# Left-pad with 'A' (= 0) so the value reflects high-order digits
	padded = upper.rjust(PASSWORD_LENGTH, 'A')
	value = 0
	for ch in padded:
		value = value * 26 + ALPHABET.index(ch)
	return value
