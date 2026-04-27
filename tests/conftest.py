"""Pytest configuration for populous tests.

This module sets headless SDL environment variables before any tests run,
allowing pygame to initialize without a display or audio device. This is
required for testing on headless systems (CI, servers).

It also injects the repo root into sys.path so tests can import
`populous_game.*` regardless of where pytest was invoked.
"""

import os
import sys
import subprocess

#============================================
# Repo root on sys.path
#============================================

_REPO_ROOT = subprocess.check_output(
	['git', 'rev-parse', '--show-toplevel'],
	text=True,
).strip()
if _REPO_ROOT not in sys.path:
	sys.path.insert(0, _REPO_ROOT)

#============================================
# Headless pygame setup
#============================================

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
