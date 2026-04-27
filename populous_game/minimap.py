import pygame
import populous_game.settings as settings

class Minimap:
    def __init__(self, x=10, y=10):
        # Position of the minimap on the screen
        self.x = x
        self.y = y
        self.width = settings.GRID_WIDTH + settings.GRID_HEIGHT  # Losange width = 64 + 64 = 128
        self.height = (settings.GRID_WIDTH + settings.GRID_HEIGHT) // 2  # Losange height = 64
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        # UI-only zoom factor (does not affect simulation). Adjusted by the
        # mouse wheel when the cursor is over the minimap.
        self.zoom: float = settings.MINIMAP_ZOOM_DEFAULT

    def set_zoom(self, z: float) -> None:
        """Clamp and set the minimap zoom factor."""
        if z < settings.MINIMAP_ZOOM_MIN:
            z = settings.MINIMAP_ZOOM_MIN
        if z > settings.MINIMAP_ZOOM_MAX:
            z = settings.MINIMAP_ZOOM_MAX
        self.zoom = float(z)

    def draw(self, surface, game_map, camera, peeps=None):
        if peeps is None:
            peeps = []

        # Effet de clignotement basé sur le temps (cycle de 0.5 seconde)
        blink = (pygame.time.get_ticks() % 500) > 250

        # The minimap art is fixed-size in the AmigaUI sprite (the
        # ~128x64 iso losange the original Amiga drew per-tile pixels
        # into). To make it scale with the HUD at non-classic presets,
        # we render every minimap pixel into a NATIVE-size scratch
        # surface, then upscale that surface by HUD_SCALE and blit it
        # at the scaled destination position. The pixel-projection
        # math stays in native-logical coordinates so the existing
        # iso losange formula (px = c + 64 - r, py = (c + r) // 2) is
        # unchanged. This is the same trick the renderer uses for the
        # AmigaUI HUD itself: render once at native size, scale once.
        scale = settings.HUD_SCALE
        scratch = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        # Terrain pixels (one per (r, c) tile, iso-projected onto the
        # scratch surface in native coords).
        for r in range(settings.GRID_HEIGHT):
            for c in range(settings.GRID_WIDTH):
                a0 = game_map.get_corner_altitude(r, c)
                a1 = game_map.get_corner_altitude(r, c + 1)
                a2 = game_map.get_corner_altitude(r + 1, c + 1)
                a3 = game_map.get_corner_altitude(r + 1, c)
                if a0 == 0 and a1 == 0 and a2 == 0 and a3 == 0:
                    color = (0, 0, 200)
                else:
                    # Slope shading: light comes from upper-left in iso.
                    slope = (a2 - a0) + (a1 - a3)
                    if slope > 0:
                        color = (120, 200, 0)
                    elif slope < 0:
                        color = (0, 90, 0)
                    else:
                        color = (0, 150, 0)
                # Native-coords iso projection inside the scratch
                # surface (no self.x / self.y here -- those are the
                # destination offsets and are applied at blit time).
                px = c + 64 - r
                py = (c + r) // 2
                scratch.set_at((px, py), color)

        # Houses blink white when on.
        if blink:
            for house in game_map.houses:
                r, c = house.r, house.c
                scratch.set_at((c + 64 - r, (c + r) // 2), settings.WHITE)
            for peep in peeps:
                r_int, c_int = int(peep.y), int(peep.x)
                if 0 <= r_int < settings.GRID_HEIGHT and 0 <= c_int < settings.GRID_WIDTH:
                    scratch.set_at((c_int + 64 - r_int, (c_int + r_int) // 2), settings.BLUE)

        # Camera viewport losange (the 8x8 tile region the player sees).
        r_cam = int(camera.r)
        c_cam = int(camera.c)
        s = settings.VISIBLE_TILE_COUNT
        p1 = (c_cam + 64 - r_cam, (c_cam + r_cam) // 2)
        p2 = ((c_cam + s) + 64 - r_cam, ((c_cam + s) + r_cam) // 2)
        p3 = ((c_cam + s) + 64 - (r_cam + s), ((c_cam + s) + (r_cam + s)) // 2)
        p4 = (c_cam + 64 - (r_cam + s), (c_cam + (r_cam + s)) // 2)
        pygame.draw.polygon(scratch, settings.WHITE, [p1, p2, p3, p4], 1)

        # Upscale the native-size scratch surface to HUD_SCALE and
        # blit at the destination position (also scaled). At classic
        # (HUD_SCALE == 1) this is a no-op pixel copy.
        if scale == 1:
            surface.blit(scratch, (self.x, self.y))
        else:
            scaled = pygame.transform.scale(
                scratch, (self.width * scale, self.height * scale)
            )
            surface.blit(scaled, (self.x * scale, self.y * scale))

    def handle_click(self, mouse_x, mouse_y, camera):
        # Vérifie si le clic est dans le bounding box de la minimap
        if self.rect.collidepoint(mouse_x, mouse_y):
            # --- Interaction du clic (_zoom_map) ---
            # "Transformation Inverse : D0 = mousex / 2, Soustrait 32"

            # Position relative dans le losange
            rel_x = mouse_x - self.x
            rel_y = mouse_y - self.y

            # Formule mathématique pure pour inverser l'isométrique pixel 2D -> Tuiles
            # Y_pixel = (c + r) / 2 => c + r = 2 * Y_pixel
            # X_pixel = (c + 64) - r => c - r = X_pixel - 64
            # => 2c = 2 * Y_pixel + X_pixel - 64 => c = Y_pixel + (X_pixel - 64) / 2
            # => 2r = 2 * Y_pixel - (X_pixel - 64) => r = Y_pixel - (X_pixel - 64) / 2

            c = rel_y + (rel_x - 64) / 2
            r = rel_y - (rel_x - 64) / 2

            # Excentrer de 4 tuiles (moitié de la vue 8x8) pour centrer le clic
            c -= 4
            r -= 4

            # "La vue principale du joueur couvre un bloc de 8x8... bride le décalage à 56"
            # clamp entries
            c = max(0, min(56, int(c)))
            r = max(0, min(56, int(r)))

            # Mise à jour de la caméra
            camera.c = float(c)
            camera.r = float(r)
            return True
        return False
