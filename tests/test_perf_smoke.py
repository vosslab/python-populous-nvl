"""Performance smoke test for game loop."""

import pygame
import time
import sys

sys.path.insert(0, '/Users/vosslab/nsh/python-populous')

from populous_game.game import Game

# Performance threshold: 50ms per frame (generous for headless pygame)
# At 60 FPS, we target 16.7ms, but headless can be slower
PERF_THRESHOLD_MS = 50.0
NUM_ITERATIONS = 10
TARGET_DT = 1.0 / 60.0  # 60 FPS nominal


def test_perf_frame_time():
	"""
	Measure average frame time for Game.update() + renderer.draw_frame().
	Assert average is under the performance threshold.
	"""
	pygame.init()
	pygame.display.set_mode((1, 1))

	try:
		game = Game()
		game.camera.r = 0.0
		game.camera.c = 0.0

		# Warm-up iteration (not counted)
		game.update(TARGET_DT)
		game.renderer.draw_frame()

		# Measure iterations
		frame_times = []
		for _ in range(NUM_ITERATIONS):
			t_start = time.perf_counter()
			game.update(TARGET_DT)
			game.renderer.draw_frame()
			t_end = time.perf_counter()

			elapsed_ms = (t_end - t_start) * 1000.0
			frame_times.append(elapsed_ms)

		# Calculate statistics
		avg_ms = sum(frame_times) / len(frame_times)
		max_ms = max(frame_times)
		min_ms = min(frame_times)

		# Report
		print("\nPerformance Smoke Test:")
		print(f"  Iterations: {NUM_ITERATIONS}")
		print(f"  Min frame time: {min_ms:.2f} ms")
		print(f"  Avg frame time: {avg_ms:.2f} ms")
		print(f"  Max frame time: {max_ms:.2f} ms")
		print(f"  Threshold: {PERF_THRESHOLD_MS:.2f} ms")

		# Assert average is under threshold
		assert avg_ms < PERF_THRESHOLD_MS, \
			f"Average frame time {avg_ms:.2f} ms exceeds threshold {PERF_THRESHOLD_MS:.2f} ms"

	finally:
		pygame.quit()


if __name__ == '__main__':
	test_perf_frame_time()
	print("Performance smoke test passed.")
