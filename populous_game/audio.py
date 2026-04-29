"""Audio subsystem with graceful fallback to silent mode.

The bundled SFX in data/sfx/ were extracted from the Amiga original and
have inconsistent (sometimes nonsensical) sample-rate metadata; one
batch claims 443361 Hz, which pygame plays back as a high-pitched burst.
load_sfx() opens each WAV via the stdlib wave module, sanitizes the
sample rate against PLAUSIBLE_SAMPLE_RATE_BOUNDS, and builds a
pygame.mixer.Sound directly from raw frame bytes. The mixer itself is
initialized with a low-rate, mono configuration that matches the
Amiga's native playback profile.
"""

import pygame
import os
import wave
import populous_game.settings as settings

# Sane bounds for Amiga-era sample rates. Files with rates outside this
# window have broken metadata; we fall back to FALLBACK_SAMPLE_RATE.
PLAUSIBLE_SAMPLE_RATE_LOW: int = 1000
PLAUSIBLE_SAMPLE_RATE_HIGH: int = 48000
FALLBACK_SAMPLE_RATE: int = 11025

# Mixer init parameters. Mono and 16-bit signed match what pygame
# expects after we re-encode 8-bit-unsigned WAV samples.
MIXER_FREQUENCY: int = 22050
MIXER_BITSIZE: int = -16
MIXER_CHANNELS: int = 1
MIXER_BUFFER: int = 1024


class AudioManager:
	"""Manages audio playback with graceful fallback to silent mode."""

	def __init__(self):
		"""Initialize audio manager without initializing mixer.
		Mixer is initialized on demand in init() to support headless/CI environments."""
		self.silent = True
		self._sfx = {}
		self._music_path = None
		# UI-driven audio toggles. is_music_playing reflects whether the
		# music button has been turned on; is_sfx_muted gates play_sfx().
		# Both default off so a fresh boot is silent unless settings.
		# MUSIC_AUTOSTART asks otherwise (Game wires that up at boot).
		self.is_music_playing = False
		self.is_sfx_muted = False

	def init(self) -> bool:
		"""Initialize pygame.mixer. Returns False if mixer init fails (silent mode).
		On CI or headless systems where no audio device exists, this falls back
		gracefully to silent mode instead of raising."""
		try:
			pygame.mixer.init(
				frequency=MIXER_FREQUENCY,
				size=MIXER_BITSIZE,
				channels=MIXER_CHANNELS,
				buffer=MIXER_BUFFER,
			)
			self.silent = False
			return True
		except Exception:
			# Mixer init failed (no audio device, SDL_AUDIODRIVER=dummy, etc.).
			# Fall back to silent mode gracefully.
			self.silent = True
			return False

	def load_sfx(self, name: str, path: str) -> None:
		"""Load a sound effect by name. No-op if silent."""
		if self.silent:
			return
		sound = self._build_sound_from_wav(path)
		if sound is not None:
			self._sfx[name] = sound

	def _build_sound_from_wav(self, path: str):
		"""Open a WAV, sanitize its sample rate, and return a pygame.Sound.

		Returns None on read failure rather than raising, so a single bad
		file does not crash the whole audio init.
		"""
		try:
			wf = wave.open(path, 'rb')
		except (wave.Error, FileNotFoundError, OSError):
			return None
		try:
			channels = wf.getnchannels()
			width = wf.getsampwidth()
			rate = wf.getframerate()
			frames = wf.readframes(wf.getnframes())
		finally:
			wf.close()
		# Implausible rate -> assume Amiga playback rate
		if rate < PLAUSIBLE_SAMPLE_RATE_LOW or rate > PLAUSIBLE_SAMPLE_RATE_HIGH:
			rate = FALLBACK_SAMPLE_RATE
		# Resample by stride/repeat to roughly match the mixer rate so
		# pygame's internal mixer does not have to upsample-by-10.
		samples = self._convert_to_signed_16(frames, width)
		if rate != MIXER_FREQUENCY:
			samples = self._linear_resample(samples, rate, MIXER_FREQUENCY)
		# Mixer is mono; downmix if necessary
		if channels == 2:
			samples = bytes(samples[i] for i in range(0, len(samples), 2))
		try:
			return pygame.mixer.Sound(buffer=samples)
		except (pygame.error, TypeError):
			return None

	@staticmethod
	def _convert_to_signed_16(frames: bytes, width: int) -> bytes:
		"""Convert raw WAV frames to signed-16 little-endian bytes."""
		# 8-bit WAV is unsigned (centered at 128); 16-bit and up are signed
		if width == 1:
			out = bytearray(len(frames) * 2)
			for i, byte in enumerate(frames):
				value = (byte - 128) * 256  # rescale unsigned 8-bit to signed 16-bit
				if value < -32768:
					value = -32768
				elif value > 32767:
					value = 32767
				out[i*2]     = value & 0xff
				out[i*2 + 1] = (value >> 8) & 0xff
			return bytes(out)
		if width == 2:
			return frames  # already signed-16 little-endian (assumed)
		# Unknown width: pad/truncate to 16-bit silence rather than crashing
		return b'\x00' * (len(frames) * (2 // max(width, 1)))

	@staticmethod
	def _linear_resample(samples_16le: bytes, in_rate: int, out_rate: int) -> bytes:
		"""Cheap nearest-sample resampler from in_rate to out_rate (16-bit LE mono)."""
		if in_rate == out_rate or in_rate <= 0:
			return samples_16le
		# Number of input samples
		in_count = len(samples_16le) // 2
		out_count = max(1, (in_count * out_rate) // in_rate)
		out = bytearray(out_count * 2)
		for i in range(out_count):
			src = (i * in_rate) // out_rate
			if src >= in_count:
				src = in_count - 1
			out[i*2]     = samples_16le[src*2]
			out[i*2 + 1] = samples_16le[src*2 + 1]
		return bytes(out)

	def load_music(self, path: str) -> None:
		"""Register music path for later playback. No-op if silent."""
		if self.silent:
			return
		self._music_path = path

	def play_sfx(self, name: str) -> None:
		"""Play a sound effect by name. No-op if silent, muted, or name not loaded."""
		if self.silent or self.is_sfx_muted or name not in self._sfx:
			return
		try:
			self._sfx[name].play()
		except Exception:
			# Playback failed; silent mode absorbs it.
			pass

	def play_music(self, loop: bool = True) -> None:
		"""Play background music. No-op if silent or no music path set.

		Sets is_music_playing=True so the UI music button reflects state.
		"""
		if self.silent or self._music_path is None:
			return
		try:
			pygame.mixer.music.load(self._music_path)
			pygame.mixer.music.play(-1 if loop else 0)
			self.is_music_playing = True
		except Exception:
			# Music playback failed; silent mode absorbs it.
			pass

	def stop_music(self) -> None:
		"""Stop background music. Always clears is_music_playing."""
		# Clear the UI flag even when silent, so toggle behavior works in
		# headless tests where mixer init is a no-op.
		self.is_music_playing = False
		if self.silent:
			return
		try:
			pygame.mixer.music.stop()
		except Exception:
			pass

	def toggle_music(self) -> bool:
		"""Toggle background music on/off. Returns the new is_music_playing.

		Wired to the _music UI button. In silent mode the flag still
		flips so tests can assert toggle behavior without a real mixer.
		"""
		if self.is_music_playing:
			self.stop_music()
		else:
			# When silent, play_music returns early without setting the
			# flag; flip it here so toggle observably moves state.
			if self.silent:
				self.is_music_playing = True
			else:
				self.play_music()
		return self.is_music_playing

	def toggle_sfx_mute(self) -> bool:
		"""Toggle SFX mute on/off. Returns the new is_sfx_muted.

		Wired to the _fx UI button. play_sfx() returns early when muted.
		"""
		self.is_sfx_muted = not self.is_sfx_muted
		return self.is_sfx_muted

	def set_volume(self, volume: float) -> None:
		"""Set master volume (0.0 to 1.0). Clamps to valid range."""
		if self.silent:
			return
		volume = max(0.0, min(1.0, volume))
		try:
			pygame.mixer.music.set_volume(volume)
		except Exception:
			pass


#============================================
def register_default_sounds(audio: AudioManager) -> None:
	"""Register logical event names mapped to SFX files.
	Maps 10 core game events to extracted Populous Amiga sound samples."""
	sfx_dir = settings.SFX_DIR

	# Mapping of event names to audio filenames.
	# The filenames are chosen deterministically from available .wav files
	# in data/sfx/ extracted from the original Populous game.
	sound_mappings = {
		'peep_spawn': 'Populous & Populous - The Promised Lands (1991)(Electronic Arts)[cr QTX][f Black Monks][a2]__0002f40c_0005da_009.wav',
		'peep_drown': 'Populous & Populous - The Promised Lands (1991)(Electronic Arts)[cr QTX][f Black Monks][a2]__0002f40c_0005da_010.wav',
		'terrain_raise': 'Populous & Populous - The Promised Lands (1991)(Electronic Arts)[cr QTX][f Black Monks][a2]__0002f40c_0005dc_009.wav',
		'terrain_lower': 'Populous & Populous - The Promised Lands (1991)(Electronic Arts)[cr QTX][f Black Monks][a2]__00033cf8_000534_001.wav',
		'building_upgrade': 'Populous & Populous - The Promised Lands (1991)(Electronic Arts)[cr QTX][f Black Monks][a2]__00033cf8_000534_002.wav',
		'building_destroy': 'Populous & Populous - The Promised Lands (1991)(Electronic Arts)[cr QTX][f Black Monks][a2]__00033cf8_000536_001.wav',
		'papal_place': 'Populous & Populous - The Promised Lands (1991)(Electronic Arts)[cr QTX][f Black Monks][a2]__0002918a_001286_003.wav',
		'shield_toggle': 'Populous & Populous - The Promised Lands (1991)(Electronic Arts)[cr QTX][f Black Monks][a2]__0002918c_001282_011.wav',
		'ui_click': 'Populous & Populous - The Promised Lands (1991)(Electronic Arts)[cr QTX][f Black Monks][a2]__0002918c_001282_013.wav',
	}
	# No music track is bundled with the repo. The Amiga extraction in
	# data/sfx/ contains only short SFX samples (max ~50 ms); the music
	# button stays a no-op until a real track is dropped into data/mp3/.

	for event_name, filename in sound_mappings.items():
		path = os.path.join(sfx_dir, filename)
		audio.load_sfx(event_name, path)
#============================================
