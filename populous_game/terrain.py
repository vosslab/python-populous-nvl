import pygame
import random
import populous_game.settings as settings


def load_tile_surfaces():
    """Charge le tileset et découpe chaque tile en surface pygame.

    Tiles are scaled by `settings.TERRAIN_SCALE` at load time so the
    blit pass downstream does not need to know which preset is active
    -- the cached surface in `tiles[(row, col)]` is already the right
    canvas-pixel size. At TERRAIN_SCALE=1 (classic) this is a no-op
    and the original 32x24 sprite is stored unchanged.
    """
    sheet_raw = pygame.image.load(settings.TILES_PATH).convert()
    sheet_raw.set_colorkey((0, 49, 0))  # Transparence pour le fond vert des tiles Amiga
    sheet = sheet_raw.convert_alpha()

    # Découpage du nouveau format AmigaTiles (32x24 pixels, décalage x=12 y=10)
    tile_w = 32
    tile_h = 24

    x_starts = [12 + i * 35 for i in range(9)]
    x_ends = [x + tile_w for x in x_starts]

    y_starts = [10 + i * 27 for i in range(8)]
    y_ends = [y + tile_h for y in y_starts]

    ref_w = tile_w
    ref_h = tile_h

    # Snapshot the active terrain scale once. Nearest-neighbor scale
    # at scale > 1 preserves the chunky-pixel look of the Amiga art.
    scale = settings.TERRAIN_SCALE

    tiles = {}
    for row in range(len(y_starts)):
        for col in range(len(x_starts)):
            # Gérer le cas de la dernière ligne restreinte sur les AmigaTiles (seulement 5 tiles)
            if row == 7 and col > 4:
                continue

            x0, x1 = x_starts[col], x_ends[col]
            y0, y1 = y_starts[row], y_ends[row]
            tw, th = x1 - x0, y1 - y0
            try:
                sub = sheet.subsurface(pygame.Rect(x0, y0, tw, th)).copy()
            except ValueError:
                continue

            if tw < ref_w or th < ref_h:
                padded = pygame.Surface((ref_w, ref_h), pygame.SRCALPHA)
                padded.blit(sub, (0, 0))
                sub = padded

            # Scale by TERRAIN_SCALE so the cached surface lives in the
            # active canvas pixel space. Skip when scale == 1 to avoid
            # an unnecessary copy.
            if scale != 1:
                scaled_w = sub.get_width() * scale
                scaled_h = sub.get_height() * scale
                sub = pygame.transform.scale(sub, (scaled_w, scaled_h))
            tiles[(row, col)] = sub
    return tiles


class GameMap:
    def __init__(self, grid_width, grid_height):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.corners = [
            [0 for _ in range(grid_width + 1)]
            for _ in range(grid_height + 1)
        ]
        self.houses = []
        self.tile_surfaces = load_tile_surfaces()
        self.water_timer = 0.0
        self.water_frame = 0
        self.flag_frame = 0

    def get_corner_altitude(self, r, c):
        if 0 <= r <= self.grid_height and 0 <= c <= self.grid_width:
            return self.corners[r][c]
        return -1

    def set_corner_altitude(self, r, c, value):
        if 0 <= r <= self.grid_height and 0 <= c <= self.grid_width:
            clamped = max(settings.ALTITUDE_MIN, min(value, settings.ALTITUDE_MAX))
            if self.corners[r][c] != clamped:
                self.corners[r][c] = clamped
                return True
        return False

    def propagate_raise(self, r, c, visited=None):
        if visited is None:
            visited = set()
        if (r, c) in visited:
            return
        visited.add((r, c))
        current = self.get_corner_altitude(r, c)
        new_alt = current + 1
        if not self.set_corner_altitude(r, c, new_alt):
            return
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr <= self.grid_height and 0 <= nc <= self.grid_width:
                    if new_alt - self.get_corner_altitude(nr, nc) > 1:
                        self.propagate_raise(nr, nc, visited)

    def propagate_lower(self, r, c, visited=None):
        if visited is None:
            visited = set()
        if (r, c) in visited:
            return
        visited.add((r, c))
        current = self.get_corner_altitude(r, c)
        new_alt = current - 1
        if not self.set_corner_altitude(r, c, new_alt):
            return
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr <= self.grid_height and 0 <= nc <= self.grid_width:
                    if self.get_corner_altitude(nr, nc) - new_alt > 1:
                        self.propagate_lower(nr, nc, visited)

    def raise_corner(self, r, c):
        self.propagate_raise(r, c)

    def lower_corner(self, r, c):
        self.propagate_lower(r, c)

    def update(self, dt):
        """Met à jour les animations (eau)."""
        self.water_timer += dt
        if self.water_timer >= 0.5:
            self.water_timer -= 0.5
            self.water_frame = 1 - self.water_frame
            self.flag_frame = 1 - self.flag_frame

    def get_tile_key(self, r, c):
        a0 = self.get_corner_altitude(r, c)
        a1 = self.get_corner_altitude(r, c + 1)
        a2 = self.get_corner_altitude(r + 1, c + 1)
        a3 = self.get_corner_altitude(r + 1, c)
        min_alt = min(a0, a1, a2, a3)

        if a0 == a1 == a2 == a3 == 0:
            return settings.TILE_WATER if self.water_frame == 0 else settings.TILE_WATER_2

        d = (
            min(1, a0 - min_alt),
            min(1, a1 - min_alt),
            min(1, a2 - min_alt),
            min(1, a3 - min_alt),
        )

        if min_alt == 0:
            tile_map = settings.SLOPE_TILES_LOW
        else:
            tile_map = settings.SLOPE_TILES

        tile = tile_map.get(d, settings.TILE_FLAT)
        if tile == settings.TILE_FLAT:
            for h in self.houses:
                if (r, c) in h.occupied_tiles:
                    return settings.TILE_CONSTRUCTED
        return tile

    def draw_tile(self, surface, r, c, transform):
        # Project terrain corners through the supplied ViewportTransform
        # so iso math lives in one place (populous_game/layout.py). The
        # transform already snapshots camera_row / camera_col at frame
        # build time; cam args are no longer needed here.
        a0 = self.get_corner_altitude(r, c)
        a1 = self.get_corner_altitude(r, c + 1)
        a2 = self.get_corner_altitude(r + 1, c + 1)
        a3 = self.get_corner_altitude(r + 1, c)
        min_alt = min(a0, a1, a2, a3)

        tile_key = self.get_tile_key(r, c)
        tile_surf = self.tile_surfaces.get(tile_key)
        if tile_surf is None:
            return

        # transform.world_to_screen(r, c, alt) returns the corner top
        # point (NW vertex of the iso diamond); shift left by half a
        # canvas-scaled tile so the sprite anchor lands on the diamond
        # center. TILE_HALF_W is in BASE/logical px, so multiply by
        # TERRAIN_SCALE to match the (already-scaled) tile surface.
        scale = settings.TERRAIN_SCALE
        half_w = settings.TILE_HALF_W * scale
        half_h = settings.TILE_HALF_H * scale
        sx, sy = transform.world_to_screen(r, c, min_alt)
        blit_x = sx - half_w
        if tile_key == settings.TILE_FLAT or tile_key == settings.TILE_CONSTRUCTED:
            # Flat tiles render at corner-y + half_h so they sit
            # centered on the iso diamond instead of the corner peak.
            blit_y = sy + half_h
        else:
            blit_y = sy

        # Stack TILE_FLAT copies underneath to fill the visible side
        # faces. gap is the pixel distance from the rendered tile down
        # to ground level (alt=0).
        _, sy0 = transform.world_to_screen(r, c, 0)
        gap = sy0 - blit_y
        n_copies = gap // half_h
        if n_copies > 0:
            flat_surf = self.tile_surfaces.get(settings.TILE_FLAT)
            if flat_surf is not None:
                # Bottom-to-top so the topmost face ends up nearest the
                # rendered tile.
                for k in range(n_copies, 0, -1):
                    surface.blit(flat_surf, (blit_x, blit_y + k * half_h))

        surface.blit(tile_surf, (blit_x, blit_y))

    def get_visible_bounds(self, cam_r, cam_c):
        start_r = int(cam_r)
        start_c = int(cam_c)
        # Viewport extent scales with the active canvas preset's VISIBLE_TILE_COUNT
        n = settings.VISIBLE_TILE_COUNT
        end_r = min(self.grid_height, start_r + n)
        end_c = min(self.grid_width, start_c + n)
        return start_r, end_r, start_c, end_c

    def draw(self, surface, transform):
        # transform carries the camera position and the active visible
        # tile budget; honor both so terrain culling stays in sync with
        # whatever projection the renderer just built for this frame.
        cam_r = transform.camera_row
        cam_c = transform.camera_col
        start_r = int(cam_r)
        start_c = int(cam_c)
        n = transform.visible_tiles
        end_r = min(self.grid_height, start_r + n)
        end_c = min(self.grid_width, start_c + n)

        for r in range(start_r, end_r):
            for c in range(start_c, end_c):
                self.draw_tile(surface, r, c, transform)

    def get_flat_area_score(self, r, c, current_house=None):
        # Retourne la liste des tuiles planes adjacentes à (r, c) valides pour la construction
        a = self.get_corner_altitude(r, c)
        b = self.get_corner_altitude(r, c + 1)
        c_ = self.get_corner_altitude(r + 1, c + 1)
        d = self.get_corner_altitude(r + 1, c)

        if not (a == b == c_ == d and a > 0):
            return -1, []  # La tuile centrale n'est plus plane

        base_alt = a
        valid_tiles = []

        # Pour le tri par distance
        offsets = [(dr, dc) for dr in range(-2, 3) for dc in range(-2, 3) if not (dr == 0 and dc == 0)]
        offsets.sort(key=lambda p: p[0]**2 + p[1]**2)

        for dr, dc in offsets:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.grid_height and 0 <= nc < self.grid_width:
                na = self.get_corner_altitude(nr, nc)
                nb = self.get_corner_altitude(nr, nc + 1)
                nc_ = self.get_corner_altitude(nr + 1, nc + 1)
                nd = self.get_corner_altitude(nr + 1, nc)
                if na == nb == nc_ == nd == base_alt:
                    valid_tiles.append((nr, nc))

        return len(valid_tiles), valid_tiles

    def draw_houses(self, surface, transform, show_debug=False, debug_font=None):
        # transform owns the camera; derive culling bounds from it.
        cam_r = transform.camera_row
        cam_c = transform.camera_col
        start_r = int(cam_r)
        start_c = int(cam_c)
        n = transform.visible_tiles
        end_r = min(self.grid_height, start_r + n)
        end_c = min(self.grid_width, start_c + n)

        from populous_game.peeps import Peep
        peep_sprites = Peep.get_sprites()
        flag_surf = peep_sprites.get((4, self.flag_frame))

        for house in sorted(self.houses, key=lambda h: h.r + h.c):
            if house.r < start_r or house.r >= end_r or house.c < start_c or house.c >= end_c:
                continue

            if house.building_type == 'castle':
                offsets = [
                    (0, 0, settings.CASTLE_9_TILES['center']), (-1, -1, settings.CASTLE_9_TILES['corner']),     (-1, 0, settings.CASTLE_9_TILES['side_tb']),     (-1, 1, settings.CASTLE_9_TILES['corner']),
                    (0, -1, settings.CASTLE_9_TILES['side_lr']),            (0, 1, settings.CASTLE_9_TILES['side_lr']),
                    (1, -1, settings.CASTLE_9_TILES['corner']),      (1, 0, settings.CASTLE_9_TILES['side_tb']),      (1, 1, settings.CASTLE_9_TILES['corner'])
                ]
                offsets.sort(key=lambda x: (house.r + x[0]) + (house.c + x[1]))
                # TILE_HALF_W is base px; cached tile surfaces are
                # already scaled by TERRAIN_SCALE so the blit offset
                # must scale to match.
                half_w = settings.TILE_HALF_W * settings.TERRAIN_SCALE
                for dr, dc, tile_key in offsets:
                    nr, nc = house.r + dr, house.c + dc
                    # Only draw castle tiles that are within visible bounds
                    if start_r <= nr < end_r and start_c <= nc < end_c:
                        alt = self.get_corner_altitude(nr, nc)
                        tile_surf = self.tile_surfaces.get(tile_key)
                        if tile_surf is not None:
                            sx, sy = transform.world_to_screen(nr, nc, alt)
                            surface.blit(tile_surf, (sx - half_w, sy))
                if flag_surf is not None:
                    sx, sy = transform.world_to_screen(house.r, house.c, self.get_corner_altitude(house.r, house.c))
                    surface.blit(flag_surf, (sx, sy))
                # Affichage debug vie chateau (centre)
                if show_debug and debug_font is not None:
                    sx, sy = transform.world_to_screen(house.r, house.c, self.get_corner_altitude(house.r, house.c))
                    life_text = debug_font.render(f"{int(house.life)}", True, (0,255,255))
                    text_x = sx - life_text.get_width() // 2
                    text_y = sy - 24
                    surface.blit(life_text, (text_x, text_y))
                continue

            alt = self.get_corner_altitude(house.r, house.c)
            tile_key = settings.BUILDING_TILES.get(house.building_type, settings.BUILDING_TILES["hut"])
            tile_surf = self.tile_surfaces.get(tile_key)
            if tile_surf is None:
                continue
            sx, sy = transform.world_to_screen(house.r, house.c, alt)
            # Cached tile surfaces are already scaled by TERRAIN_SCALE;
            # multiply the half-tile offset to match the canvas px.
            half_w = settings.TILE_HALF_W * settings.TERRAIN_SCALE
            blit_x = sx - half_w
            blit_y = sy
            surface.blit(tile_surf, (blit_x, blit_y))

            # Drapeau d'equipe anime (sprites 4,0 et 4,1)
            if flag_surf is not None:
                flag_x = blit_x + half_w
                flag_y = blit_y
                surface.blit(flag_surf, (flag_x, flag_y))

            # Affichage debug vie batiment
            if show_debug and debug_font is not None:
                life_text = debug_font.render(f"{int(house.life)}", True, (0,255,255))
                text_x = sx - life_text.get_width() // 2
                text_y = blit_y - 24
                surface.blit(life_text, (text_x, text_y))

    def _enforce_height_constraints(self):
        """Passe de lissage : garantit que tous les voisins à 8 directions diffèrent de max 1."""
        changed = True
        while changed:
            changed = False
            for r in range(self.grid_height + 1):
                for c in range(self.grid_width + 1):
                    for dr, dc in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr <= self.grid_height and 0 <= nc <= self.grid_width:
                            if self.corners[r][c] - self.corners[nr][nc] > 1:
                                self.corners[r][c] = self.corners[nr][nc] + 1
                                changed = True

    def set_all_altitude(self, value):
        for r in range(self.grid_height + 1):
            for c in range(self.grid_width + 1):
                self.corners[r][c] = value

    def randomize(self, min_level=0, max_level=7, seed=None):
        """Generate a mixed-altitude heightmap.

        Args:
            min_level: Minimum corner altitude. Default 0 (water).
            max_level: Maximum corner altitude. Default 7.
            seed: Optional integer seed for deterministic generation. Same
                seed produces the same map. None uses the module-global
                random state.
        """
        # Use a private rng instance so an explicit seed does not perturb
        # the module-global random.random stream used elsewhere.
        rng = random.Random(seed) if seed is not None else random
        self.corners[0][0] = rng.randint(min_level, max_level)
        for c in range(1, self.grid_width + 1):
            prev = self.corners[0][c - 1]
            self.corners[0][c] = max(min_level, min(max_level, prev + rng.choice([-1, 0, 1])))
        for r in range(1, self.grid_height + 1):
            prev = self.corners[r - 1][0]
            self.corners[r][0] = max(min_level, min(max_level, prev + rng.choice([-1, 0, 1])))
            for c in range(1, self.grid_width + 1):
                left = self.corners[r][c - 1]
                up = self.corners[r - 1][c]
                lo = max(min_level, left - 1, up - 1)
                hi = min(max_level, left + 1, up + 1)
                base = max(lo, min(hi, (left + up) // 2 + rng.choice([-1, 0, 1])))
                self.corners[r][c] = base
        self._enforce_height_constraints()

    def find_nearest_land(self, r, c):
        """Breadth-first search for the nearest land corner from (r, c).

        Returns (r2, c2) of the closest corner with altitude > 0, or None
        if no land exists anywhere on the map. Used by peep spawning so
        walkers do not require pre-flattened terrain.
        """
        # Already on land? Return the input coordinate.
        if 0 <= r <= self.grid_height and 0 <= c <= self.grid_width:
            if self.corners[r][c] > 0:
                return (r, c)
        # BFS over the corner grid; corners go 0..grid_height inclusive.
        visited = set()
        if 0 <= r <= self.grid_height and 0 <= c <= self.grid_width:
            visited.add((r, c))
            queue = [(r, c)]
        else:
            # Out-of-bounds start; treat as water at (0, 0) for BFS seeding.
            visited.add((0, 0))
            queue = [(0, 0)]
        head = 0
        while head < len(queue):
            cr, cc = queue[head]
            head += 1
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = cr + dr, cc + dc
                if (nr, nc) in visited:
                    continue
                if not (0 <= nr <= self.grid_height and 0 <= nc <= self.grid_width):
                    continue
                visited.add((nr, nc))
                if self.corners[nr][nc] > 0:
                    return (nr, nc)
                queue.append((nr, nc))
        return None

    def is_flat_and_buildable(self, r, c):
        if r < 0 or c < 0 or r >= self.grid_height or c >= self.grid_width:
            return False
        a = self.get_corner_altitude(r, c)
        b = self.get_corner_altitude(r, c + 1)
        c_ = self.get_corner_altitude(r + 1, c + 1)
        d = self.get_corner_altitude(r + 1, c)
        if a == b == c_ == d and a > 0:
            # Vérifier qu'aucune maison ne réclame déjà cette tuile
            for h in self.houses:
                if (r, c) in h.occupied_tiles:
                    return False
            return True
        return False

    def _get_construction_offsets(self, scan_size=25):
        """Offsets de voisinage discrets autour du centre, triés du plus proche au plus lointain."""
        offsets = [
            (dr, dc)
            for dr in range(-2, 3)
            for dc in range(-2, 3)
            if not (dr == 0 and dc == 0)
        ]
        offsets.sort(key=lambda p: p[0] * p[0] + p[1] * p[1])
        return offsets[: max(0, min(scan_size, len(offsets)))]

    def can_place_house_initial(self, r, c):
        """Validation de pose initiale: centre plat + buffer de voisinage anti-proximité."""
        if not self.is_flat_and_buildable(r, c):
            return False

        # Phase initiale proche du comportement original: scan large (25 positions max).
        for dr, dc in self._get_construction_offsets(25):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < self.grid_height and 0 <= nc < self.grid_width):
                continue

            # Interdit de construire si le voisinage immédiat contient déjà un centre de ville.
            for h in self.houses:
                if (h.r, h.c) == (nr, nc):
                    return False

            # Interdit aussi si la case est déjà revendiquée par une ville existante.
            for h in self.houses:
                if (nr, nc) in h.occupied_tiles:
                    return False

        return True

    def add_house(self, house):
        self.houses.append(house)

