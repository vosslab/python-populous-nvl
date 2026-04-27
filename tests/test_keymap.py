"""Test keymap loading, saving, and merging.

Patch M7.3: Keymap module with config file support.
"""

import yaml
from unittest.mock import patch
import populous_game.keymap as keymap


def test_default_keymap_has_all_actions():
	"""default_keymap() returns dict with all required actions."""
	km = keymap.default_keymap()
	required = [
		'pause', 'menu_quit', 'menu_start', 'fast_forward',
		'power_papal', 'power_volcano', 'power_flood', 'power_quake',
		'power_swamp', 'power_knight'
	]
	for action in required:
		assert action in km, f"Missing action: {action}"
		assert isinstance(km[action], str), f"Key for {action} should be string"


def test_load_keymap_returns_defaults_when_file_missing(tmp_path, monkeypatch):
	"""load_keymap() returns defaults when config file doesn't exist."""
	# Mock keymap_path to point to a nonexistent file
	fake_path = tmp_path / 'nonexistent.yaml'
	with patch('populous_game.keymap.keymap_path', return_value=str(fake_path)):
		result = keymap.load_keymap()
		assert result == keymap.default_keymap()


def test_load_keymap_merges_user_overrides(tmp_path, monkeypatch):
	"""load_keymap() merges user config over defaults."""
	# Create a user config file with one override
	config_file = tmp_path / 'keys.yaml'
	user_config = {'power_volcano': 'x'}
	with open(config_file, 'w') as f:
		yaml.dump(user_config, f)

	with patch('populous_game.keymap.keymap_path', return_value=str(config_file)):
		result = keymap.load_keymap()
		# Should have the override
		assert result['power_volcano'] == 'x'
		# Should have defaults for other keys
		assert result['power_flood'] == keymap.default_keymap()['power_flood']
		assert result['pause'] == keymap.default_keymap()['pause']


def test_load_keymap_returns_defaults_on_malformed_yaml(tmp_path):
	"""load_keymap() returns defaults when YAML is malformed."""
	# Create a malformed YAML file
	config_file = tmp_path / 'keys.yaml'
	with open(config_file, 'w') as f:
		f.write("this: is: bad: yaml: syntax:")

	with patch('populous_game.keymap.keymap_path', return_value=str(config_file)):
		result = keymap.load_keymap()
		assert result == keymap.default_keymap()


def test_load_keymap_returns_defaults_when_file_is_not_dict(tmp_path):
	"""load_keymap() returns defaults when YAML is not a dict."""
	# Create a YAML file that's a list, not a dict
	config_file = tmp_path / 'keys.yaml'
	with open(config_file, 'w') as f:
		yaml.dump(['a', 'b', 'c'], f)

	with patch('populous_game.keymap.keymap_path', return_value=str(config_file)):
		result = keymap.load_keymap()
		assert result == keymap.default_keymap()


def test_save_keymap_creates_file(tmp_path):
	"""save_keymap() creates config file and saves keymap."""
	config_file = tmp_path / 'keys.yaml'
	test_keymap = keymap.default_keymap()
	test_keymap['power_volcano'] = 'z'

	with patch('populous_game.keymap.keymap_path', return_value=str(config_file)):
		keymap.save_keymap(test_keymap)
		assert config_file.exists()

		# Load the file and verify
		with open(config_file, 'r') as f:
			saved = yaml.safe_load(f)
		assert saved['power_volcano'] == 'z'


def test_save_keymap_creates_parent_directories(tmp_path):
	"""save_keymap() creates parent directories if needed."""
	config_dir = tmp_path / 'deeply' / 'nested' / 'path'
	config_file = config_dir / 'keys.yaml'
	test_keymap = keymap.default_keymap()

	with patch('populous_game.keymap.keymap_path', return_value=str(config_file)):
		keymap.save_keymap(test_keymap)
		assert config_file.exists()
		assert config_dir.exists()


def test_keymap_round_trip(tmp_path):
	"""save then load restores the keymap."""
	config_file = tmp_path / 'keys.yaml'
	original = keymap.default_keymap()
	original['power_volcano'] = 'z'
	original['power_flood'] = 'w'

	with patch('populous_game.keymap.keymap_path', return_value=str(config_file)):
		keymap.save_keymap(original)
		loaded = keymap.load_keymap()
		assert loaded == original
