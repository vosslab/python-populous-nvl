#!/usr/bin/env python3
"""Bulk-convert WAV files to MP3 files with lame.

Defaults to converting every `.wav` in a source directory into a
parallel output directory, preserving the original basename and using
the `.mp3` extension.

The Amiga-extracted WAVs in `data/sfx/` sometimes carry nonsensical
sample-rate metadata (for example 443 kHz) that lame would honor and
encode into a broken MP3 (audible as buzzing). Before encoding, we
sanitize WAV headers whose declared rate is outside a plausible range,
matching the policy in `populous_game/audio.py`.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
import tempfile
import wave


# Mirrors PLAUSIBLE_SAMPLE_RATE_LOW/HIGH and FALLBACK_SAMPLE_RATE in
# populous_game/audio.py. Duplicated here so this tool does not have to
# import pygame just to share three integers.
PLAUSIBLE_SAMPLE_RATE_LOW: int = 1000
PLAUSIBLE_SAMPLE_RATE_HIGH: int = 48000
FALLBACK_SAMPLE_RATE: int = 11025


def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Bulk-convert WAV files to MP3 files with lame."
	)
	parser.add_argument(
		"source_dir",
		nargs="?",
		default="data/sfx",
		help="Directory containing input WAV files (default: data/sfx).",
	)
	parser.add_argument(
		"output_dir",
		nargs="?",
		default="data/mp3",
		help="Directory to write MP3 files (default: data/mp3).",
	)
	parser.add_argument(
		"--bitrate",
		default="V2",
		help="LAME quality preset or bitrate flag (default: V2).",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Print the lame commands without running them.",
	)
	return parser.parse_args()


def iter_wav_files(source_dir: pathlib.Path) -> list[pathlib.Path]:
	"""Return WAV files in source_dir in sorted order."""
	return sorted(
		path
		for path in source_dir.iterdir()
		if path.is_file() and path.suffix.lower() == ".wav"
	)


def build_mp3_path(source_path: pathlib.Path, source_dir: pathlib.Path, output_dir: pathlib.Path) -> pathlib.Path:
	"""Map a source WAV path to its destination MP3 path."""
	relative_path = source_path.relative_to(source_dir)
	return (output_dir / relative_path).with_suffix(".mp3")


def sanitize_wav(source_path: pathlib.Path) -> tuple[pathlib.Path, bool]:
	"""Return a path with a plausible sample-rate header.

	If `source_path` already declares a sample rate inside
	[PLAUSIBLE_SAMPLE_RATE_LOW, PLAUSIBLE_SAMPLE_RATE_HIGH], return it
	unchanged with did_rewrite=False. Otherwise write a new temp WAV
	with the same channels, sample width, and raw PCM frames but with
	framerate forced to FALLBACK_SAMPLE_RATE, and return that path with
	did_rewrite=True. The caller is responsible for removing the temp
	file when did_rewrite is True.
	"""
	with wave.open(str(source_path), "rb") as wf:
		channels = wf.getnchannels()
		width = wf.getsampwidth()
		rate = wf.getframerate()
		frames = wf.readframes(wf.getnframes())
	if PLAUSIBLE_SAMPLE_RATE_LOW <= rate <= PLAUSIBLE_SAMPLE_RATE_HIGH:
		return source_path, False
	# Create a temp WAV with corrected header, same PCM bytes
	fd, tmp_name = tempfile.mkstemp(suffix=".wav", prefix="sanitized_")
	os.close(fd)
	tmp_path = pathlib.Path(tmp_name)
	with wave.open(str(tmp_path), "wb") as out:
		out.setnchannels(channels)
		out.setsampwidth(width)
		out.setframerate(FALLBACK_SAMPLE_RATE)
		out.writeframes(frames)
	return tmp_path, True


def convert_file(source_path: pathlib.Path, output_path: pathlib.Path, bitrate: str, dry_run: bool) -> None:
	"""Convert one WAV file with lame, sanitizing the WAV header first."""
	output_path.parent.mkdir(parents=True, exist_ok=True)
	if dry_run:
		# Show the intent against the original path; skip sanitation in dry-run
		command = ["lame", f"-{bitrate}", str(source_path), str(output_path)]
		print(" ".join(command))
		return
	encode_path, did_rewrite = sanitize_wav(source_path)
	command = ["lame", f"-{bitrate}", str(encode_path), str(output_path)]
	try:
		result = subprocess.run(command, check=False)
		if result.returncode != 0:
			raise RuntimeError(f"lame failed for {source_path} -> {output_path} (exit {result.returncode})")
	finally:
		# Only delete a temp WAV we created; never delete the original input
		if did_rewrite:
			encode_path.unlink(missing_ok=True)


def main() -> int:
	"""Convert all WAV files in the source directory."""
	args = parse_args()
	source_dir = pathlib.Path(args.source_dir)
	output_dir = pathlib.Path(args.output_dir)
	if not source_dir.is_dir():
		raise NotADirectoryError(f"source directory does not exist: {source_dir}")
	wav_files = iter_wav_files(source_dir)
	if not wav_files:
		print(f"No WAV files found in {source_dir}", file=sys.stderr)
		return 1
	for source_path in wav_files:
		output_path = build_mp3_path(source_path, source_dir, output_dir)
		convert_file(source_path, output_path, args.bitrate, args.dry_run)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
