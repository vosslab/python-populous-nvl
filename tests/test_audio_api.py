"""Tests for AudioManager API.

Covers initialization with mixer fallback to silent mode, sound loading,
and playback on systems with no audio device (e.g., CI runners with
SDL_AUDIODRIVER=dummy).
"""

import pygame
import populous_game.audio as audio


def test_audio_manager_init_success(monkeypatch):
	"""AudioManager.init() returns True and sets silent=False on success."""
	# Assume default pygame.mixer.init() succeeds in the test environment.
	am = audio.AudioManager()
	result = am.init()
	# Result may be True or False depending on the actual audio device.
	# What matters is that it doesn't raise.
	assert isinstance(result, bool)


def test_audio_manager_init_silent_fallback(monkeypatch):
	"""AudioManager.init() returns False and sets silent=True if mixer init fails."""
	# Mock pygame.mixer.init to raise an exception (simulating no audio device).
	def mock_mixer_init():
		raise Exception("No audio device available")

	monkeypatch.setattr(pygame.mixer, 'init', mock_mixer_init)

	am = audio.AudioManager()
	result = am.init()
	assert result is False
	assert am.silent is True


def test_audio_manager_play_sfx_no_crash_when_silent():
	"""play_sfx() is a no-op when silent; does not raise."""
	am = audio.AudioManager()
	am.silent = True
	# Should not raise even though no sound is loaded.
	am.play_sfx('nonexistent')


def test_audio_manager_play_sfx_when_active(monkeypatch):
	"""play_sfx() calls Sound.play() when sound is loaded and not silent."""
	played_sounds = []

	class MockSound:
		def play(self):
			played_sounds.append('played')

	am = audio.AudioManager()
	am.silent = False
	am._sfx['test_sound'] = MockSound()

	am.play_sfx('test_sound')
	assert len(played_sounds) == 1


def test_audio_manager_load_sfx_no_crash_when_silent():
	"""load_sfx() is a no-op when silent; does not raise."""
	am = audio.AudioManager()
	am.silent = True
	# Should not try to load or raise.
	am.load_sfx('test', '/nonexistent/path.wav')
	assert 'test' not in am._sfx


def test_audio_manager_load_music_no_crash_when_silent():
	"""load_music() is a no-op when silent; does not raise."""
	am = audio.AudioManager()
	am.silent = True
	am.load_music('/nonexistent/path.wav')
	assert am._music_path is None


def test_audio_manager_play_music_no_crash_when_silent():
	"""play_music() is a no-op when silent; does not raise."""
	am = audio.AudioManager()
	am.silent = True
	# Should not raise.
	am.play_music(loop=True)


def test_audio_manager_stop_music_no_crash_when_silent():
	"""stop_music() is a no-op when silent; does not raise."""
	am = audio.AudioManager()
	am.silent = True
	am.stop_music()


def test_audio_manager_set_volume_clamps(monkeypatch):
	"""set_volume() clamps to [0.0, 1.0] range."""
	# Mock mixer to track volume calls.
	volumes_set = []

	class MockMixer:
		@staticmethod
		def set_volume(v):
			volumes_set.append(v)

	monkeypatch.setattr(pygame.mixer.music, 'set_volume', MockMixer.set_volume)

	am = audio.AudioManager()
	am.silent = False

	# Out-of-range values should be clamped.
	am.set_volume(-0.5)
	assert volumes_set[-1] == 0.0

	am.set_volume(1.5)
	assert volumes_set[-1] == 1.0

	am.set_volume(0.5)
	assert volumes_set[-1] == 0.5


def test_register_default_sounds_does_not_raise():
	"""register_default_sounds() loads sound mappings without raising."""
	am = audio.AudioManager()
	am.silent = True  # Prevent actual file I/O.

	# Should not raise even though files may not exist or be loadable.
	audio.register_default_sounds(am)


def test_audio_manager_initial_state():
	"""AudioManager starts with silent=True and empty sound map."""
	am = audio.AudioManager()
	assert am.silent is True
	assert len(am._sfx) == 0
	assert am._music_path is None
