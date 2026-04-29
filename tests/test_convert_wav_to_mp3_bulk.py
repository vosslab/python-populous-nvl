"""Tests for the bulk WAV-to-MP3 converter."""

import wave
import importlib.util
import pathlib


def load_converter():
	"""Load the converter script as a module from its file path."""
	script_path = pathlib.Path("tools/convert_wav_to_mp3_bulk.py").resolve()
	spec = importlib.util.spec_from_file_location("convert_wav_to_mp3_bulk", script_path)
	module = importlib.util.module_from_spec(spec)
	assert spec is not None
	assert spec.loader is not None
	spec.loader.exec_module(module)
	return module


def test_build_mp3_path_preserves_relative_name():
	"""build_mp3_path() keeps relative directories and swaps suffix."""
	converter = load_converter()
	source_dir = pathlib.Path("/repo/data/sfx")
	source_path = pathlib.Path("/repo/data/sfx/subdir/example.wav")
	output_dir = pathlib.Path("/repo/data/mp3")
	assert converter.build_mp3_path(source_path, source_dir, output_dir) == pathlib.Path("/repo/data/mp3/subdir/example.mp3")


def test_iter_wav_files_filters_and_sorts(tmp_path):
	"""iter_wav_files() returns only WAV files in sorted order."""
	converter = load_converter()
	(tmp_path / "b.wav").write_bytes(b"")
	(tmp_path / "a.wav").write_bytes(b"")
	(tmp_path / "skip.txt").write_bytes(b"")
	files = converter.iter_wav_files(tmp_path)
	assert [path.name for path in files] == ["a.wav", "b.wav"]


def _write_wav(path: pathlib.Path, rate: int) -> None:
	"""Write a tiny 8-bit mono WAV with the given declared sample rate."""
	with wave.open(str(path), "wb") as wf:
		wf.setnchannels(1)
		wf.setsampwidth(1)
		wf.setframerate(rate)
		wf.writeframes(bytes([128, 130, 126, 128]))


def test_sanitize_wav_passes_through_plausible_rate(tmp_path):
	"""A WAV with a plausible sample rate is returned unchanged."""
	converter = load_converter()
	src = tmp_path / "ok.wav"
	_write_wav(src, 11025)
	result, did_rewrite = converter.sanitize_wav(src)
	assert did_rewrite is False
	assert result == src


def test_sanitize_wav_rewrites_implausible_rate(tmp_path):
	"""A WAV with a bogus sample rate produces a sanitized temp copy."""
	converter = load_converter()
	src = tmp_path / "bogus.wav"
	_write_wav(src, 443361)
	result, did_rewrite = converter.sanitize_wav(src)
	assert did_rewrite is True
	assert result != src
	with wave.open(str(result), "rb") as wf:
		assert wf.getframerate() == converter.FALLBACK_SAMPLE_RATE
	result.unlink()
