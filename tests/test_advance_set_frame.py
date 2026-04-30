"""Pin behavior of the advance_set_frame() helper."""

import populous_game.peep_helpers as peep_helpers


def test_no_threshold_crossing_returns_false():
	"""Stepping within a non-threshold band does not flag success."""
	result = peep_helpers.advance_set_frame(0x10, step=1)
	assert result.counter == 0x11
	assert result.success is False


def test_first_threshold_flags_success():
	"""Crossing 0x2A flags success."""
	result = peep_helpers.advance_set_frame(0x29, step=1)
	assert result.counter == 0x2A
	assert result.success is True


def test_each_threshold_flags_success():
	"""Each documented threshold flags success when crossed."""
	for threshold in peep_helpers.ASM_SET_FRAME_THRESHOLDS:
		result = peep_helpers.advance_set_frame(threshold - 1, step=1)
		assert result.success is True


def test_counter_wraps_past_final_threshold():
	"""The counter wraps so success keeps firing on later loops."""
	final = peep_helpers.ASM_SET_FRAME_THRESHOLDS[-1]
	result = peep_helpers.advance_set_frame(final + 1, step=1)
	# Wrap is modulo (final + 1), so counter is small again.
	assert 0 <= result.counter <= final


def test_step_skipping_threshold_still_flags_success():
	"""A step that jumps over a threshold still flags success."""
	result = peep_helpers.advance_set_frame(0x28, step=4)
	# 0x28 + 4 = 0x2C; crossed 0x2A.
	assert result.success is True
