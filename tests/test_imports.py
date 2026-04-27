"""Test that all populous_game modules can be imported without side effects."""

import importlib


def test_import_assets():
	"""Import assets module."""
	mod = importlib.import_module('populous_game.assets')
	assert hasattr(mod, 'load_all')
	assert hasattr(mod, 'get_ui_image')


def test_import_camera():
	"""Import camera module."""
	mod = importlib.import_module('populous_game.camera')
	assert hasattr(mod, 'Camera')


def test_import_input_controller():
	"""Import input_controller module."""
	mod = importlib.import_module('populous_game.input_controller')
	assert hasattr(mod, 'InputController')


def test_import_mode_manager():
	"""Import mode_manager module."""
	mod = importlib.import_module('populous_game.mode_manager')
	assert hasattr(mod, 'ModeManager')


def test_import_selection():
	"""Import selection module."""
	mod = importlib.import_module('populous_game.selection')
	assert hasattr(mod, 'Selection')


def test_import_renderer():
	"""Import renderer module."""
	mod = importlib.import_module('populous_game.renderer')
	assert hasattr(mod, 'Renderer')


def test_import_terrain():
	"""Import terrain module."""
	mod = importlib.import_module('populous_game.terrain')
	assert hasattr(mod, 'GameMap')


def test_import_peeps():
	"""Import peeps module."""
	mod = importlib.import_module('populous_game.peeps')
	assert hasattr(mod, 'Peep')


def test_import_houses():
	"""Import houses module."""
	mod = importlib.import_module('populous_game.houses')
	assert hasattr(mod, 'House')


def test_import_minimap():
	"""Import minimap module."""
	mod = importlib.import_module('populous_game.minimap')
	assert hasattr(mod, 'Minimap')


def test_import_settings():
	"""Import settings module."""
	mod = importlib.import_module('populous_game.settings')
	assert hasattr(mod, 'GRID_WIDTH')
