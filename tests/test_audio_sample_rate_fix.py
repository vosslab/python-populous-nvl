"""Tests that the SFX loader sanitizes implausible sample rates (M8 audio fix).

Regression: a batch of bundled WAVs claim 443361 Hz, which pygame plays
back as a tenth-of-a-second burst of static. The audio loader now
overrides any sample rate outside [PLAUSIBLE_SAMPLE_RATE_LOW,
PLAUSIBLE_SAMPLE_RATE_HIGH] to FALLBACK_SAMPLE_RATE before building the
Sound.
"""

import os
import wave
import struct

import pygame
import populous_game.audio as audio_module


def test_implausible_sample_rate_replaced(tmp_path):
	"""A WAV whose header claims 443361 Hz is loaded as if it were the fallback rate."""
	# Build a synthetic 8-bit mono WAV with the broken sample rate metadata
	wav_path = tmp_path / 'broken.wav'
	with wave.open(str(wav_path), 'wb') as wf:
		wf.setnchannels(1)
		wf.setsampwidth(1)
		wf.setframerate(443361)  # the broken rate
		# 200 unsigned-8-bit samples (~0.45ms at 443kHz, ~18ms at 11025Hz)
		wf.writeframes(struct.pack('200B', *([128] * 200)))

	# Init mixer in dummy mode so this works headless
	os.environ['SDL_AUDIODRIVER'] = 'dummy'
	pygame.mixer.quit()
	mgr = audio_module.AudioManager()
	mgr.init()

	# Load it via the sanitizing loader
	mgr.load_sfx('broken', str(wav_path))
	assert 'broken' in mgr._sfx
	sound = mgr._sfx['broken']
	# At the fallback rate (11025 Hz) 200 samples should be ~18 ms; at 443 kHz
	# they'd be ~0.45 ms. We only need to verify it is well above 1 ms.
	length_ms = sound.get_length() * 1000.0
	assert length_ms > 1.0


def test_loader_handles_missing_file_gracefully(tmp_path):
	"""A missing file produces no entry in the SFX table and no exception."""
	pygame.mixer.quit()
	mgr = audio_module.AudioManager()
	mgr.init()
	missing_path = tmp_path / 'this_file_should_not_exist.wav'
	mgr.load_sfx('missing', str(missing_path))
	assert 'missing' not in mgr._sfx
