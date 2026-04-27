#!/usr/bin/env python3
import pygame
import sys
import random
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from populous_game.game_map import GameMap
import populous_game.settings as settings

# Default window dimensions
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

#============================================

def create_map(size):
	"""Create new GameMap with base surface."""
	game_map = GameMap(size, size)
	# Add some basic random altitude to see relief
	for r in range(size):
		for c in range(size):
			if random.random() > 0.8:
				game_map.raise_corner(r, c)
	return game_map

#============================================

def main():
	pygame.init()
	screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
	pygame.display.set_caption("Map Viewer (1:1 Scale)")
	clock = pygame.time.Clock()

	# Roughly center isometric display in middle of screen
	settings.MAP_OFFSET_X = WINDOW_WIDTH // 2
	settings.MAP_OFFSET_Y = 100

	# Available sizes
	map_sizes = {
		pygame.K_1: 8,
		pygame.K_2: 16,
		pygame.K_3: 32,
		pygame.K_4: 64
	}

	current_size = 8
	current_map = create_map(current_size)

	running = True
	while running:
		dt = clock.tick(60) / 1000.0

		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			elif event.type == pygame.KEYDOWN:
				if event.key in map_sizes:
					current_size = map_sizes[event.key]
					current_map = create_map(current_size)
					print(f"Generating {current_size}x{current_size} map...")

		# Update base animations (water)
		current_map.update(dt)

		# Strict 1:1 rendering
		screen.fill((0, 0, 0))

		# Classic isometric display
		for r in range(current_map.grid_height):
			for c in range(current_map.grid_width):
				tile_key = current_map.get_tile_key(r, c)
				tile_surf = current_map.tile_surfaces.get(tile_key)

				if tile_surf:
					a = current_map.get_corner_altitude(r, c)
					px, py = current_map.world_to_screen(r, c, a)
					screen.blit(tile_surf, (px, py))

		# Display information
		font = pygame.font.SysFont("consolas", 16)
		text = font.render(f"Map: {current_size}x{current_size} | Scale: 1:1 (Fixed) | Keys: 1, 2, 3, 4", True, (255, 255, 255))
		screen.blit(text, (10, 10))

		pygame.display.flip()

	pygame.quit()
	sys.exit()

#============================================

if __name__ == "__main__":
	main()
