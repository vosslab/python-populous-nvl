"""Test that the root populous.py launcher stub functions correctly.

Launches the game via subprocess in headless mode, kills it after 2 seconds,
and verifies it exits cleanly (exit code 0 or terminated by signal).
"""

import subprocess
import signal
import os
import time

import git_file_utils

REPO_ROOT = git_file_utils.get_repo_root()

#============================================

def test_root_launcher_headless():
	"""python3 populous.py boots and exits cleanly under headless conditions."""
	env = os.environ.copy()
	env['SDL_VIDEODRIVER'] = 'dummy'
	env['SDL_AUDIODRIVER'] = 'dummy'

	# Use Popen to spawn the process so we can control its lifetime
	process = subprocess.Popen(
		['python3', 'populous.py'],
		cwd=REPO_ROOT,
		env=env,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
	)

	# Let it run for 2 seconds, then terminate gracefully
	time.sleep(2.0)

	# Send SIGTERM and wait up to 3 seconds for clean exit
	process.send_signal(signal.SIGTERM)
	try:
		process.wait(timeout=3.0)
	except subprocess.TimeoutExpired:
		# If it doesn't exit, force kill it
		process.kill()
		process.wait()

	# Assert exit code is 0 (clean exit) or -15 (SIGTERM)
	# returncode is negative for signal termination: -signal_number
	exit_code = process.returncode
	assert exit_code == 0 or exit_code == -signal.SIGTERM, (
		f'Expected exit code 0 or {-signal.SIGTERM}; got {exit_code}'
	)
