"""Smoke tests for input_controller module."""

import populous_game.input_controller as input_controller


def test_input_controller_class_exists():
	"""Verify InputController class exists."""
	assert hasattr(input_controller, 'InputController')


def test_input_controller_has_poll():
	"""Verify InputController has poll method."""
	assert hasattr(input_controller.InputController, 'poll')


def test_input_controller_initialization():
	"""Verify InputController can be initialized."""
	# Create a mock game object with minimal attributes
	class MockGame:
		pass

	game = MockGame()
	controller = input_controller.InputController(game)
	assert controller.game is game
