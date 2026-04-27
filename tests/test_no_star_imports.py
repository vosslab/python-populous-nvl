"""Test that runtime modules do not use star imports.

This test is expected to fail (xfail) on a fresh checkout because the
current codebase uses `from settings import *` in several files. The M1
cleanup work packages will make this test pass.
"""

import re
import pytest

import git_file_utils

REPO_ROOT = git_file_utils.get_repo_root()

#============================================

def _find_python_files():
	"""Yield all .py files in the repo, excluding tests/ and tools/."""
	import os
	for root, dirs, files in os.walk(REPO_ROOT):
		# Exclude test and tool directories
		dirs[:] = [d for d in dirs if d not in ('tests', 'tools', '.git', '__pycache__')]

		for fname in files:
			if fname.endswith('.py'):
				yield os.path.join(root, fname)

#============================================

@pytest.mark.xfail(strict=False)
def test_no_star_imports():
	"""No runtime module uses `from ... import *`."""
	# Pattern to match star imports at the start of a line (with optional whitespace)
	star_import_pattern = re.compile(r'^\s*from\s+\S+\s+import\s+\*')

	violations = []
	for fpath in _find_python_files():
		try:
			with open(fpath, 'r', encoding='utf-8') as f:
				for line_num, line in enumerate(f, start=1):
					if star_import_pattern.match(line):
						violations.append(f'{fpath}:{line_num}: {line.rstrip()}')
		except (IOError, UnicodeDecodeError):
			# Skip files that cannot be read
			pass

	assert not violations, (
		f'Found {len(violations)} star import(s):\n' + '\n'.join(violations)
	)
