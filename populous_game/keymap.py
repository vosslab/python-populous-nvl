"""Keymap management: load, save, and apply user keybindings.

Key remapping with config file (~/.config/python-populous/keys.yaml).
Falls back to defaults if config is missing or malformed.
"""

import os
import yaml


def default_keymap() -> dict:
	"""Return default keybindings (all actions must be present).

	Each entry maps an action name to a pygame key name (e.g., 'escape', 'v').
	"""
	return {
		'pause': 'escape',
		'menu_quit': 'q',
		'menu_start': 'return',
		'fast_forward': '`',
		'power_papal': 'p',
		'power_volcano': 'v',
		'power_flood': 'f',
		'power_quake': 'q',
		'power_swamp': 's',
		'power_knight': 'k',
	}


def keymap_path() -> str:
	"""Return the path to the keymap config file.

	Expands ~ to user home directory.
	"""
	config_dir = os.path.expanduser('~/.config/python-populous')
	return os.path.join(config_dir, 'keys.yaml')


def load_keymap() -> dict:
	"""Load keymap from config file, falling back to defaults.

	If the config file is missing or malformed YAML, returns defaults.
	User overrides in the config file are merged over defaults.
	"""
	defaults = default_keymap()
	config_file = keymap_path()

	# If no config file, return defaults
	if not os.path.exists(config_file):
		return defaults

	# Try to load the YAML file
	try:
		with open(config_file, 'r') as f:
			user_config = yaml.safe_load(f)
	except (yaml.YAMLError, OSError):
		# Malformed YAML or file I/O error: return defaults
		return defaults

	# If the file parsed but is not a dict, return defaults
	if not isinstance(user_config, dict):
		return defaults

	# Merge user overrides over defaults (user values take precedence)
	result = defaults.copy()
	for key, value in user_config.items():
		if isinstance(value, str):
			result[key] = value

	return result


def save_keymap(keymap: dict) -> None:
	"""Save keymap to config file.

	Creates parent directories if needed.
	"""
	config_file = keymap_path()
	config_dir = os.path.dirname(config_file)

	# Create parent directories if needed
	if config_dir and not os.path.exists(config_dir):
		os.makedirs(config_dir, exist_ok=True)

	# Write the keymap as YAML
	with open(config_file, 'w') as f:
		yaml.dump(keymap, f, default_flow_style=False)
