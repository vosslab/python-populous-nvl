
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pygame

# Import game elements
import populous_game.settings as settings
from populous_game.game_map import GameMap
from populous_game.house import House
from populous_game.peep import Peep

class PositioningTest:
    def __init__(self):
        pygame.init()
        # Screen resolution for test tool
        self.screen_width = 1000
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Alignment Test Tool - Populous")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)

        self.buildings = House.TYPES
        self.selected_idx = 0
        self.buttons = []

        # Initialize button layout
        self.setup_ui()

        # Initialize reduced GameMap for test (large enough for margins)
        self.game_map = GameMap(15, 15)
        self.peep = None

        self.spawn_scene()

    def setup_ui(self):
        self.buttons = []
        start_y = 50
        for i, b_type in enumerate(self.buildings):
            rect = pygame.Rect(10, start_y + i * 35, 200, 30)
            self.buttons.append((rect, b_type, i))

    def spawn_scene(self):
        """Create flat terrain and instantiate building and peep for alignment test."""
        # Base natural terrain (altitude 1)
        self.game_map.set_all_altitude(1)
        self.game_map.houses.clear()

        # Choose an anchor point
        h_r, h_c = 4, 4

        # Score thresholds over 24 adjacent tiles
        thresholds = [0, 1, 2, 5, 8, 11, 14, 19, 22, 24]
        required_score = thresholds[self.selected_idx]

        # Central platform (building) is always constructed
        self.game_map.corners[h_r][h_c] = 2
        self.game_map.corners[h_r][h_c+1] = 2
        self.game_map.corners[h_r+1][h_c+1] = 2
        self.game_map.corners[h_r+1][h_c] = 2

        # Terrain expansion order (up to 24 tiles adjacent for a 5x5 centered on building)
        offsets = [(dr, dc) for dr in range(-2, 3) for dc in range(-2, 3) if not (dr == 0 and dc == 0)]
        # Sort by distance from center for natural concentric expansion
        offsets.sort(key=lambda p: p[0]**2 + p[1]**2)

        for i in range(required_score):
            dr, dc = offsets[i]
            tr = h_r + dr
            tc = h_c + dc
            # Raise corners to altitude 2 to create flat plateau
            self.game_map.corners[tr][tc] = 2
            self.game_map.corners[tr][tc+1] = 2
            self.game_map.corners[tr+1][tc+1] = 2
            self.game_map.corners[tr+1][tc] = 2

        # Add building
        house = House(h_r, h_c)
        # Force initial update to calculate occupied terrain
        # (and set initial lifecycle corresponding to selected_idx)
        house.life = thresholds[self.selected_idx] * 15.0 if self.selected_idx > 0 else 10.0
        house.update(0.1, self.game_map)
        house.building_type = self.buildings[self.selected_idx]
        self.game_map.houses.append(house)

        # Simulate a peep on or just in front of the building
        self.peep = Peep(h_r, h_c, self.game_map)

        # Fix Peep coordinates so it is centered on its tile
        self.peep.x = h_c + 0.5
        self.peep.y = h_r + 0.5
        self.peep.direction = 0

    def handle_click(self, pos):
        for rect, b_type, idx in self.buttons:
            if rect.collidepoint(pos):
                self.selected_idx = idx
                self.spawn_scene()
                return

    def run(self):
        running = True
        while running:
            # Even without movement, tick for animations if needed
            self.clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)

            # 1) Draw map on off-screen surface (to allow zooming)
            map_surface = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
            map_surface.fill((40, 40, 40))

            cam_r, cam_c = 0, 0

            self.game_map.draw(map_surface, cam_r, cam_c)
            self.game_map.draw_houses(map_surface, cam_r, cam_c)
            if self.peep:
                self.peep.draw(map_surface, cam_r, cam_c)

            # Extract centered view on building for zoom (x3)
            sx, sy = self.game_map.world_to_screen(4, 4, 2, cam_r, cam_c)
            view_w, view_h = 260, 200  # Captured area, 260x3 = 780 (screen width), 200x3 = 600
            view_rect = pygame.Rect(sx - view_w // 2, sy - view_h // 2, view_w, view_h)
            view_rect.clamp_ip(map_surface.get_rect())

            sub = map_surface.subsurface(view_rect)
            scaled_sub = pygame.transform.scale(sub, (view_rect.width * 3, view_rect.height * 3))

            # Apply to screen (black background)
            self.screen.fill((20, 20, 20))
            # Place zoomed map to right of UI (UI width ~220)
            self.screen.blit(scaled_sub, (220, 0))

            # 2) Draw UI (background for buttons to keep them readable)
            pygame.draw.rect(self.screen, (20, 20, 20), (0, 0, 220, self.screen_height))
            title = self.font.render("Buildings", True, settings.WHITE)
            self.screen.blit(title, (10, 10))

            for rect, b_type, idx in self.buttons:
                color = (100, 150, 100) if idx == self.selected_idx else (80, 80, 80)
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, settings.WHITE, rect, 1)
                text = self.font.render(b_type, True, settings.WHITE)
                self.screen.blit(text, (rect.x + 5, rect.y + 5))

            # Additional instructions
            thresholds = [0, 1, 2, 5, 8, 11, 14, 19, 22, 24]
            required_score = thresholds[self.selected_idx]
            info_text1 = self.font.render(f"House at (4, 4) - Alt 2 (terrain score: {required_score}/24)", True, settings.WHITE)
            info_text2 = self.font.render("Peep at (4.5, 4.5)", True, settings.WHITE)
            self.screen.blit(info_text1, (250, 10))
            self.screen.blit(info_text2, (250, 30))

            pygame.display.flip()

        pygame.quit()

if __name__ == '__main__':
    app = PositioningTest()
    app.run()
