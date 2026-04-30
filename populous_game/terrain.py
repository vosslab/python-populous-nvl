import pygame
import random
import collections
import numpy
import populous_game.settings as settings


# NumPy is used as an internal implementation detail of the island
# generator and its analysis helpers (masks, validation, scoring).
# The public GameMap API stays on list-of-lists corners in this
# milestone; renderers, powers, peeps, and input code are not asked
# to index NumPy arrays directly. A later refactor may convert
# self.corners to numpy.ndarray(dtype=numpy.uint8) once the island
# generator is stable.


#============================================
# Generator profile data
#============================================
# IslandProfile bundles the parameters that distinguish CLASSIC_REFERENCE
# from REMASTER_ISLANDS. Both profiles share the same growth engine in
# GameMap._randomize_islands; only these knobs change. Numbers below
# are starting points for screenshot tuning, not load-bearing.

class IslandProfile:
    def __init__(
        self, *,
        blob_specs,
        peak_target,
        min_walk_steps,
        walk_budget,
        seed_margin,
        seed_min_spacing,
        validate,
        max_attempts,
    ):
        self.blob_specs = blob_specs            # tuple of (x_spread, y_spread)
        self.peak_target = peak_target          # int, altitude that stops a blob
        self.min_walk_steps = min_walk_steps    # int, blob may not stop before
        self.walk_budget = walk_budget          # int, max raise calls per blob
        self.seed_margin = seed_margin          # int, edge buffer for seed picks
        self.seed_min_spacing = seed_min_spacing  # int, chebyshev distance
        self.validate = validate                # bool, run quality gates + retry
        self.max_attempts = max_attempts        # int, retry cap when validating


# Amiga-faithful three-blob walker. Stops each blob at first peak.
# No validation gates -- this profile is the historical reference.
CLASSIC_REFERENCE = IslandProfile(
    blob_specs=((4, 2), (2, 4), (3, 3)),
    peak_target=6,
    min_walk_steps=0,
    walk_budget=2000,
    seed_margin=4,
    seed_min_spacing=0,
    validate=False,
    max_attempts=1,
)

# Fewer, longer-growing walkers for 1-3 large inhabitable islands.
# Validation + deterministic salted retries reject popcorn output.
REMASTER_ISLANDS = IslandProfile(
    blob_specs=((5, 3), (3, 5), (4, 4)),
    peak_target=7,
    # Tuning notes: a single propagate_raise to peak 7 from a
    # fresh seed creates a ~7-ring smooth pyramid (~150 corners).
    # Each subsequent walker step near the peak lifts ~1 ring
    # outward via the cascade. 20 post-peak steps per walker
    # x 3 walkers targets ~25-40% land fraction on a 64x64 map,
    # i.e., distinct islands surrounded by water rather than a
    # continent. Numbers remain screenshot-tunable.
    min_walk_steps=20,
    walk_budget=120,
    seed_margin=10,
    seed_min_spacing=18,
    validate=True,
    max_attempts=8,
)


#============================================
# Validation thresholds (remaster_islands profile)
#============================================
# Tunable. Pulled to module scope so tests can pin individual gates
# without hard-coding magic numbers in the validator body.
VALIDATION_LAND_TILE_FRACTION_MIN: float = 0.20
VALIDATION_LAND_TILE_FRACTION_MAX: float = 0.65
VALIDATION_LARGEST_COMPONENT_FRACTION_MIN: float = 0.50
VALIDATION_MAJOR_COMPONENT_TILES: int = 60
VALIDATION_MAJOR_COMPONENT_COUNT_MIN: int = 1
VALIDATION_MAJOR_COMPONENT_COUNT_MAX: int = 3
VALIDATION_TINY_FRAGMENT_TILES: int = 4
VALIDATION_TINY_FRAGMENT_COUNT_MAX: int = 6
VALIDATION_BUILDABLE_TILES_MIN: int = 80
VALIDATION_SPAWNABLE_TILES_MIN: int = 30


#============================================
# Tile-key sets used by morphology and validation
#============================================
WATER_TILE_KEYS: tuple = (settings.TILE_WATER, settings.TILE_WATER_2)


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
        self.map_who = self._new_map_who_table()
        # ASM map_blk / map_bk2 shadow code layer (additive; not read
        # by production movement yet). One ASM tile-class byte per
        # tile cell, sized grid_height x grid_width. Kept in sync
        # with corner mutations via set_corner_altitude(),
        # _enforce_height_constraints(), set_all_altitude(),
        # add_house(), and the public recompute_shadow_codes() helper.
        self.shadow_blk = self._new_shadow_table()
        self.shadow_bk2 = self._new_shadow_table()
        self.recompute_shadow_codes()
        self.water_timer = 0.0
        self.water_frame = 0
        self.flag_frame = 0

    def _new_map_who_table(self):
        """Return a zero-filled ASM-style occupancy table."""
        return [
            [0 for _ in range(self.grid_width)]
            for _ in range(self.grid_height)
        ]

    def reset_map_who(self):
        """Clear shadow peep occupancy bookkeeping."""
        self.map_who = self._new_map_who_table()

    def recompute_map_who(self, peeps):
        """Rebuild shadow occupancy from the live peep list."""
        self.reset_map_who()
        for index, peep_obj in enumerate(peeps):
            if getattr(peep_obj, 'dead', False):
                continue
            if getattr(peep_obj, 'state', None) == 'dead':
                continue
            r = int(peep_obj.y)
            c = int(peep_obj.x)
            if 0 <= r < self.grid_height and 0 <= c < self.grid_width:
                if self.map_who[r][c] == 0:
                    self.map_who[r][c] = index + 1

    def _new_shadow_table(self):
        """Return a zero-filled tile-class shadow table."""
        return [
            [settings.ASM_TILE_WATER for _ in range(self.grid_width)]
            for _ in range(self.grid_height)
        ]

    def _classify_tile(self, r, c):
        """Compute the ASM tile-class code for tile (r, c).

        The classification is a working hypothesis pending the WP-G2
        atlas/audit work: water when all four corners are at 0, rock
        when any corner reaches ALTITUDE_MAX, flat when all four
        corners are equal (and above water), slope otherwise. Houses
        re-stamp 0x35 over the tiles they occupy in
        recompute_shadow_codes().
        """
        # Tile (r, c) is bounded by corners (r, c), (r, c+1),
        # (r+1, c), (r+1, c+1).
        a = self.corners[r][c]
        b = self.corners[r][c + 1]
        c2 = self.corners[r + 1][c]
        d = self.corners[r + 1][c + 1]
        if a == 0 and b == 0 and c2 == 0 and d == 0:
            return settings.ASM_TILE_WATER
        peak = settings.ALTITUDE_MAX
        if a >= peak or b >= peak or c2 >= peak or d >= peak:
            return settings.ASM_TILE_ROCK
        if a == b == c2 == d:
            return settings.ASM_TILE_FLAT
        return settings.ASM_TILE_SLOPE

    def _update_shadow_for_corner(self, r, c):
        """Refresh the (up to four) tiles that touch corner (r, c)."""
        for tr in (r - 1, r):
            if 0 <= tr < self.grid_height:
                for tc in (c - 1, c):
                    if 0 <= tc < self.grid_width:
                        code = self._classify_tile(tr, tc)
                        self.shadow_blk[tr][tc] = code
                        self.shadow_bk2[tr][tc] = code

    def recompute_shadow_codes(self):
        """Rebuild shadow_blk / shadow_bk2 from the current corners
        and house occupancy. Idempotent; safe to call after any bulk
        terrain mutation.
        """
        for r in range(self.grid_height):
            for c in range(self.grid_width):
                code = self._classify_tile(r, c)
                self.shadow_blk[r][c] = code
                self.shadow_bk2[r][c] = code
        # Houses stamp a town tile-class code over their footprint.
        # House.occupied_tiles, when present, is an iterable of (r, c).
        for house in self.houses:
            tiles = getattr(house, 'occupied_tiles', None)
            if tiles is None:
                tile_r = getattr(house, 'tile_r', None)
                tile_c = getattr(house, 'tile_c', None)
                if tile_r is None or tile_c is None:
                    continue
                tiles = ((tile_r, tile_c),)
            for hr, hc in tiles:
                if 0 <= hr < self.grid_height and 0 <= hc < self.grid_width:
                    self.shadow_blk[hr][hc] = settings.ASM_TILE_TOWN
                    self.shadow_bk2[hr][hc] = settings.ASM_TILE_TOWN

    def get_corner_altitude(self, r, c):
        if 0 <= r <= self.grid_height and 0 <= c <= self.grid_width:
            return self.corners[r][c]
        return -1

    def set_corner_altitude(self, r, c, value):
        if 0 <= r <= self.grid_height and 0 <= c <= self.grid_width:
            clamped = max(settings.ALTITUDE_MIN, min(value, settings.ALTITUDE_MAX))
            if self.corners[r][c] != clamped:
                self.corners[r][c] = clamped
                # Keep the ASM shadow tile-class layer in sync with
                # every altitude write. The shadow arrays are not
                # initialized until __init__ finishes setting them.
                if hasattr(self, 'shadow_blk'):
                    self._update_shadow_for_corner(r, c)
                return True
        return False

    def propagate_raise(self, r, c, visited=None, max_altitude=None):
        # max_altitude is None or a callable (r, c) -> int giving the
        # per-corner altitude cap. None means no cap (use the global
        # ALTITUDE_MAX clamp inside set_corner_altitude). Existing
        # gameplay callers pass None and see bit-exact behavior with
        # the pre-predicate implementation.
        #
        # Why a cap callable instead of a boolean can_raise: a hard
        # boolean refusal at locked corners breaks smoothness. When
        # the cascade tries to step down from interior altitude N
        # into a moat-locked corner at 0, a boolean refuse leaves an
        # N-step cliff. A per-corner cap fixes this naturally: the
        # moat caps at 0, the next ring caps at 1, the next at 2,
        # and so on -- the cascade ramps down to water instead of
        # hitting a wall.
        if visited is None:
            visited = set()
        if (r, c) in visited:
            return
        visited.add((r, c))
        current = self.get_corner_altitude(r, c)
        if max_altitude is not None:
            cap = max_altitude(r, c)
            if current >= cap:
                return
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
                        self.propagate_raise(nr, nc, visited, max_altitude)

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
        # Bulk smoothing bypassed set_corner_altitude; resync shadows.
        if hasattr(self, 'shadow_blk'):
            self.recompute_shadow_codes()

    def set_all_altitude(self, value):
        for r in range(self.grid_height + 1):
            for c in range(self.grid_width + 1):
                self.corners[r][c] = value
        # Bulk overwrite bypassed set_corner_altitude; resync shadows.
        if hasattr(self, 'shadow_blk'):
            self.recompute_shadow_codes()

    def randomize(self, seed=None, profile="remaster_islands"):
        """Generate an island heightmap. Dispatches on `profile`.

        Args:
            seed: Optional integer seed for deterministic generation.
                Same seed + same profile produces the same map. When
                None, a fresh random.Random() is used so module-global
                state is not consumed.
            profile: Generator profile selector. One of:
                "remaster_islands"   - default. Tuned for 1-3 large
                                       smooth inhabitable islands
                                       with morphology cleanup and
                                       validation retries.
                "classic_reference"  - Amiga-like three-blob walker
                                       with water moat. Reference
                                       behavior, no validation gates.
        """
        # One rng for the whole call. Never touch the module-global
        # stream from inside the generator paths.
        rng = random.Random(seed) if seed is not None else random.Random()
        if profile == "remaster_islands":
            self._randomize_islands(rng, REMASTER_ISLANDS)
        elif profile == "classic_reference":
            self._randomize_islands(rng, CLASSIC_REFERENCE)
        else:
            raise ValueError(f"Unknown randomize profile: {profile!r}")

    #============================================
    # Island-growth engine: shared by classic_reference and
    # remaster_islands profiles. Starts from all water and grows
    # smooth pyramidal landmasses with constrained raises. The water
    # moat (rows/cols 0,1 and grid-1,grid) is enforced by the
    # _island_max_altitude cap (corners ramp from 0 at the moat to
    # ALTITUDE_MAX deep inland) AND by walker clamping -- defense
    # in depth.
    #============================================
    def _island_max_altitude(self, r, c):
        # Per-corner altitude cap for the island generator. Encodes
        # the one-tile water moat AND a smooth ramp inland. The two
        # outermost corner rings (rows 0,1 and grid-1,grid; matching
        # cols) cap at 0 -- this guarantees every edge tile renders
        # as water (top-edge tiles read corners from rows 0 AND 1).
        # The next ring caps at 1, the next at 2, and so on, so the
        # cascade ramps DOWN to water along the boundary instead of
        # cliffing. Cap is min(ALTITUDE_MAX, distance_to_edge - 1).
        dist = min(r, self.grid_height - r, c, self.grid_width - c)
        if dist <= 1:
            return 0
        cap = dist - 1
        if cap > settings.ALTITUDE_MAX:
            cap = settings.ALTITUDE_MAX
        return cap

    def _randomize_islands(self, rng, profile):
        if not profile.validate:
            self._run_island_attempt(rng, profile)
            return
        # Validating profile: keep the highest-scoring attempt across
        # max_attempts deterministic salted retries. The rng has
        # already advanced past failed attempts, so each retry
        # explores fresh state without losing reproducibility.
        best_corners = None
        best_score = float("-inf")
        best_metrics = None
        for attempt_index in range(profile.max_attempts):
            self._run_island_attempt(rng, profile)
            self._morphology_cleanup()
            # Validation runs on the post-cleanup rendered tile map,
            # NOT on the target mask -- grow-only realization may not
            # achieve the full target before its budget runs out.
            passed, score, metrics = self._score_island_map()
            if passed:
                return
            if score > best_score:
                best_score = score
                best_metrics = metrics
                best_corners = [row[:] for row in self.corners]
        # No attempt passed every gate. Restore the best-scoring
        # attempt as a safety valve and log seed/profile/score so a
        # follow-up tuning pass knows what failed. Fixed-seed tests
        # are expected to hit the early-return above; this path is
        # only for runtime resilience.
        if best_corners is not None:
            self.corners = best_corners
        print(
            f"[terrain.randomize] WARNING: no attempt passed "
            f"validation; using best score={best_score:.3f} "
            f"metrics={best_metrics}"
        )

    def _run_island_attempt(self, rng, profile):
        # One generation pass: water-fill, pick seeds, run each walker.
        # Used by both the validating retry loop and the non-validating
        # classic profile (classic just calls this once).
        self.set_all_altitude(0)
        seeds = self._pick_island_seeds(rng, profile)
        for (r, c), (base_x, base_y) in zip(seeds, profile.blob_specs):
            # Jitter spreads by +/-1 each blob so identical blob_specs
            # entries (e.g. two (3,3) walkers) still produce visually
            # distinct islands across calls.
            x_spread = max(1, base_x + rng.choice((-1, 0, 1)))
            y_spread = max(1, base_y + rng.choice((-1, 0, 1)))
            self._grow_island(rng, r, c, x_spread, y_spread, profile)

    def _pick_island_seeds(self, rng, profile):
        # Hard floor of 2 enforces the moat regardless of
        # profile.seed_margin; the walker clamp uses the same floor.
        margin = max(2, profile.seed_margin)
        lo_r = margin
        hi_r = self.grid_height - margin
        lo_c = margin
        hi_c = self.grid_width - margin
        min_spacing = profile.seed_min_spacing
        seeds = []
        seed_attempts_per_blob = 50
        for _ in profile.blob_specs:
            r, c = lo_r, lo_c
            for _ in range(seed_attempts_per_blob):
                r = rng.randrange(lo_r, hi_r + 1)
                c = rng.randrange(lo_c, hi_c + 1)
                # chebyshev distance >= min_spacing from every prior seed
                ok = all(
                    max(abs(r - sr), abs(c - sc)) >= min_spacing
                    for sr, sc in seeds
                )
                if ok:
                    break
            seeds.append((r, c))
        return seeds

    def _grow_island(self, rng, r, c, x_spread, y_spread, profile):
        # Walker stays inside the moat-safe interior. The raise
        # primitive ALSO enforces the moat via the
        # _island_max_altitude cap -- this clamp is the quality-of-
        # life half of a defense-in-depth pair. Either alone would
        # suffice.
        lo_r = 2
        hi_r = self.grid_height - 2
        lo_c = 2
        hi_c = self.grid_width - 2
        max_altitude = self._island_max_altitude
        for step in range(profile.walk_budget):
            self.propagate_raise(r, c, max_altitude=max_altitude)
            # Stop only after BOTH min_walk_steps elapsed AND the
            # peak target reached. classic_reference sets
            # min_walk_steps=0 (Amiga: stop at first peak).
            # remaster_islands sets a large minimum so the blob keeps
            # spreading after first peak -- "fewer, longer-growing
            # walkers" actually true.
            if (step >= profile.min_walk_steps
                    and self.get_corner_altitude(r, c) >= profile.peak_target):
                return
            c += rng.randint(-x_spread, x_spread)
            r += rng.randint(-y_spread, y_spread)
            c = max(lo_c, min(hi_c, c))
            r = max(lo_r, min(hi_r, r))
        # Budget exhausted without reaching peak. Accept whatever
        # grew. With realistic budgets this only fires for pinned
        # configurations; a slightly under-target island is still
        # playable, and a hard crash on map generation is worse.

    #============================================
    # Morphology cleanup (remaster profile only). Grow-only: this
    # pass joins narrow water cracks and absorbs near-touching blobs.
    # It does NOT lower terrain to remove specks -- speck control is
    # handled by validation + retry. A future milestone can add a
    # constrained propagate_lower path for direct speck removal.
    #============================================
    def _morphology_cleanup(self):
        grown = self._land_tile_mask()
        closed = self._close_mask(grown)
        target = self._filter_components(closed)
        # Tiles in target but not in grown become land via constrained
        # raises. Tiles in grown but not in target stay as-is for now.
        self._realise_mask_diff(grown, target)

    def _corner_array(self):
        # Single conversion entry point: every NumPy path in the
        # generator/validator starts from this snapshot. asarray
        # avoids an extra copy if self.corners is already an ndarray
        # (a later milestone may convert the storage; keeping this
        # call here makes that migration localized).
        return numpy.asarray(self.corners, dtype=numpy.uint8)

    def _water_tile_array(self):
        # Boolean (grid_height, grid_width) array. True where the
        # tile renders as water. A tile is water iff all 4 corners
        # are altitude 0 -- mirrors get_tile_key's water branch.
        alt = self._corner_array()
        nw = alt[:-1, :-1]
        ne = alt[:-1, 1:]
        sw = alt[1:, :-1]
        se = alt[1:, 1:]
        return (nw == 0) & (ne == 0) & (sw == 0) & (se == 0)

    def _land_tile_mask(self):
        # Set of (r, c) tile coordinates that render as non-water.
        # The player experiences the rendered tile surface, so
        # validation and morphology operate on tiles, not corners.
        water = self._water_tile_array()
        rows, cols = numpy.where(~water)
        return set(zip(rows.tolist(), cols.tolist()))

    def _dilate(self, mask):
        # 8-neighbor dilation, but never grow into edge tiles -- the
        # moat invariant must survive morphology.
        out = set(mask)
        for r, c in mask:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr = r + dr
                    nc = c + dc
                    if (1 <= nr < self.grid_height - 1
                            and 1 <= nc < self.grid_width - 1):
                        out.add((nr, nc))
        return out

    def _erode(self, mask):
        # A tile keeps land status only if all 8 neighbors are also
        # in mask. Used after dilation to form a closing.
        out = set()
        for r, c in mask:
            ok = True
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if (r + dr, c + dc) not in mask:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                out.add((r, c))
        return out

    def _close_mask(self, mask):
        # Closing = dilate then erode. Joins narrow water cracks and
        # fills 1-tile holes; bulk shape unchanged.
        return self._erode(self._dilate(mask))

    def _filter_components(self, mask):
        # Keep up to MAJOR_COMPONENT_COUNT_MAX components by size,
        # each at least MAJOR_COMPONENT_TILES tiles. Drops tiny
        # specks at the mask level; validator catches anything that
        # slips through realisation.
        components = self._connected_components(mask)
        components.sort(key=len, reverse=True)
        keep = set()
        for comp in components[:VALIDATION_MAJOR_COMPONENT_COUNT_MAX]:
            if len(comp) >= VALIDATION_MAJOR_COMPONENT_TILES:
                keep |= comp
        return keep

    def _realise_mask_diff(self, current, target):
        # Tiles that should become land but currently render as water:
        # raise interior corners until the tile is non-water OR a
        # per-tile budget is exhausted. propagate_raise builds the
        # ramp smoothly, so newly-grown coast does not introduce
        # cliffs.
        max_altitude = self._island_max_altitude
        # Cap on TOTAL propagate_raise calls across all "should be
        # land" tiles. Prevents pathological mask diffs from running
        # for thousands of cascading raises -- if morphology asked for
        # more land than this budget can realize, validation will
        # fail and the retry loop picks a fresh seed.
        global_raise_budget = 250
        for r, c in (target - current):
            for _ in range(8):
                # Corner (r+1, c+1) is the SE corner of tile (r, c)
                # and is guaranteed interior because the dilation
                # step refused to grow into edge tiles.
                self.propagate_raise(r + 1, c + 1, max_altitude=max_altitude)
                if self.get_tile_key(r, c) not in WATER_TILE_KEYS:
                    break
                global_raise_budget -= 1
                if global_raise_budget <= 0:
                    return

    #============================================
    # Validation (remaster profile only). Operates on the rendered
    # tile map, not on raw corner altitudes.
    #============================================
    def _edge_tiles_all_water(self):
        # Vectorized: a tile is water iff all 4 corners are 0. Check
        # the four edge rows/columns of the water-tile boolean array.
        water = self._water_tile_array()
        return bool(
            water[0, :].all()
            and water[-1, :].all()
            and water[:, 0].all()
            and water[:, -1].all()
        )

    def _connected_components(self, tile_set):
        # Iterative BFS over 4-neighbors. Returns a list of sets.
        # No recursion -- the caller may pass thousands of tiles.
        unvisited = set(tile_set)
        components = []
        while unvisited:
            seed = next(iter(unvisited))
            unvisited.discard(seed)
            queue = collections.deque([seed])
            comp = {seed}
            while queue:
                r, c = queue.popleft()
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nb = (r + dr, c + dc)
                    if nb in unvisited:
                        unvisited.discard(nb)
                        comp.add(nb)
                        queue.append(nb)
            components.append(comp)
        return components

    def _land_tile_set(self):
        # Same as _land_tile_mask. Aliased for clarity at validator
        # call sites; both names appear in the plan.
        return self._land_tile_mask()

    def _count_buildable_tiles(self):
        # A tile is buildable when its 4 corners are equal and > 0
        # (flat land, not water). Validator runs before any houses
        # are placed, so the house-occupancy check from
        # is_flat_and_buildable is intentionally omitted here.
        alt = self._corner_array()
        nw = alt[:-1, :-1]
        ne = alt[:-1, 1:]
        sw = alt[1:, :-1]
        se = alt[1:, 1:]
        flat = (nw == ne) & (nw == sw) & (nw == se) & (nw > 0)
        return int(flat.sum())

    def _count_spawnable_tiles(self):
        # Mirrors the rule used by Game.spawn_initial_peeps via
        # find_nearest_land: spawning succeeds at any tile with at
        # least one land corner. Counts starting candidates on the
        # generated map.
        alt = self._corner_array()
        nw = alt[:-1, :-1]
        ne = alt[:-1, 1:]
        sw = alt[1:, :-1]
        se = alt[1:, 1:]
        any_land = (nw > 0) | (ne > 0) | (sw > 0) | (se > 0)
        return int(any_land.sum())

    def _validate_island_map(self):
        passed, _, _ = self._score_island_map()
        return passed

    def _score_island_map(self):
        # Returns (passed, score, metrics_dict). The retry loop in
        # _randomize_islands keeps the highest-scoring attempt as a
        # fallback. score is just total_land_tiles for now -- it is
        # only used to break ties between failing attempts, never to
        # accept a passing one.
        metrics = {}
        # Hard fail: any non-water edge tile breaks the moat.
        if not self._edge_tiles_all_water():
            metrics['edge_water'] = False
            return (False, 0.0, metrics)
        metrics['edge_water'] = True
        land_tiles = self._land_tile_set()
        components = self._connected_components(land_tiles)
        if not components:
            metrics['no_land'] = True
            return (False, 0.0, metrics)
        total_tiles = self.grid_height * self.grid_width
        total_land = sum(len(comp) for comp in components)
        largest = max(len(comp) for comp in components)
        major_count = sum(
            1 for comp in components
            if len(comp) >= VALIDATION_MAJOR_COMPONENT_TILES
        )
        tiny_count = sum(
            1 for comp in components
            if len(comp) <= VALIDATION_TINY_FRAGMENT_TILES
        )
        land_fraction = total_land / total_tiles
        largest_fraction = largest / total_land
        buildable = self._count_buildable_tiles()
        spawnable = self._count_spawnable_tiles()
        metrics.update({
            'land_fraction': land_fraction,
            'largest_fraction': largest_fraction,
            'major_count': major_count,
            'tiny_count': tiny_count,
            'buildable': buildable,
            'spawnable': spawnable,
        })
        passed = (
            VALIDATION_LAND_TILE_FRACTION_MIN <= land_fraction
            and land_fraction <= VALIDATION_LAND_TILE_FRACTION_MAX
            and largest_fraction >= VALIDATION_LARGEST_COMPONENT_FRACTION_MIN
            and VALIDATION_MAJOR_COMPONENT_COUNT_MIN <= major_count
            and major_count <= VALIDATION_MAJOR_COMPONENT_COUNT_MAX
            and tiny_count <= VALIDATION_TINY_FRAGMENT_COUNT_MAX
            and buildable >= VALIDATION_BUILDABLE_TILES_MIN
            and spawnable >= VALIDATION_SPAWNABLE_TILES_MIN
        )
        # Score: weight buildable + connectedness so the fallback
        # prefers playable maps over fragmented ones.
        score = float(buildable) + 100.0 * largest_fraction
        return (passed, score, metrics)

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
        # House placement changes tile classification for the
        # footprint; resync the shadow code layer.
        if hasattr(self, 'shadow_blk'):
            self.recompute_shadow_codes()
