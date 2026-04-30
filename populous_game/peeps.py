import pygame
import random
import math
import populous_game.settings as settings
import populous_game.faction as faction
import populous_game.peep_state as peep_state

# Sprite size in the source sprite sheet
SPRITE_EXTRACT_SIZE = 16


def load_sprite_surfaces():
    """Charge le sprite sheet et decoupe les sprites 16x16 selon un format fixe (AmigaSprites)."""
    sheet_raw = pygame.image.load(settings.SPRITES_PATH).convert()

    # Fond vert transparent Amiga
    sheet_raw.set_colorkey((0, 49, 0))
    sheet = sheet_raw.convert_alpha()

    start_x, start_y = 11, 10
    stride_x, stride_y = 20, 20

    x_starts = [start_x + i * stride_x for i in range(16)]
    y_starts = [start_y + j * stride_y for j in range(9)]

    sprites = {}
    for r, y0 in enumerate(y_starts):
        for c, x0 in enumerate(x_starts):
            try:
                sub = sheet.subsurface(pygame.Rect(x0, y0, SPRITE_EXTRACT_SIZE, SPRITE_EXTRACT_SIZE)).copy()
            except ValueError:
                continue

            # Supprimer le fond noir residuel -> transparent
            arr = pygame.surfarray.pixels3d(sub)
            alpha = pygame.surfarray.pixels_alpha(sub)
            mask = ((arr[:, :, 0] == 0) & (arr[:, :, 1] == 0) & (arr[:, :, 2] == 0))
            alpha[mask] = 0
            del arr, alpha  # liberer les locks surfarray

            # Scale peep sprites by TERRAIN_SCALE so they match the
            # iso tile size at every preset (chunky-pixels mode). At
            # classic (TERRAIN_SCALE=1) this is the legacy 16x16; at
            # remaster the peeps render at 32x32, at large 64x64.
            target_size = settings.SPRITE_SIZE * settings.TERRAIN_SCALE
            sub = pygame.transform.scale(sub, (target_size, target_size))

            sprites[(r, c)] = sub

    return sprites


# Sprite sheet organisation (approximate from visual):
# Blue team faces different directions, row 0-1 walking,
# Red team faces different directions, row 2-3 walking,
# Row 4: fighting/special animations
# Row 5-7: more animations, items, effects
# Row 8: UI elements


# Directions en isometrique: 0=SE, 1=S, 2=SW, 3=W, 4=NW, 5=N, 6=NE, 7=E
# Simplified: we use row 0 columns for walk animation in a direction
WALK_FRAMES = {
    'N':      [(0,  0), (0,  1)],
    'NE':     [(0,  2), (0,  3)],
    'E':      [(0,  4), (0,  5)],
    'SE':     [(0,  6), (0,  7)],
    'S':      [(0,  8), (0,  9)],
    'SW':     [(0, 10), (0, 11)],
    'W':      [(0, 12), (0, 13)],
    'NW':     [(0, 14), (0, 15)],
    'IDLE':   [(0,  8), (0,  9)],
    'DROWN':  [(5,  8), (5,  9), (5, 10), (5, 11)],
}

# Export pour usage externe
PEEP_WALK_FRAMES = WALK_FRAMES


class Peep:
    _sprites = None

    @classmethod
    def get_sprites(cls):
        if cls._sprites is None:
            cls._sprites = load_sprite_surfaces()
        return cls._sprites

    def __init__(self, grid_r, grid_c, game_map, faction_id: int = faction.Faction.PLAYER):
        self.x = grid_c + 0.5
        self.y = grid_r + 0.5
        self.game_map = game_map
        self.faction = faction_id
        self.faction_id = faction_id
        self.life = 50
        self.dead = False
        self.death_timer = 0.0
        self.move_timer = 0.0
        self.dir_timer = 0.0
        self.direction = random.uniform(0, 2 * math.pi)
        self.build_timer = 0.0
        self.anim_timer = 0.0
        self.anim_frame = 0
        self.facing = 'IDLE'
        self.is_moving = False
        self.energy_yellow = 0   # barres jaunes restantes
        self.energy_orange = 1.0  # fraction de la barre orange courante (0->1)
        self.in_house = False
        self.weapon_type = 'hut' # Arme de depart : arme 0 (hut)
        self.state: str = peep_state.PeepState.IDLE
        # ASM shadow fields from asm/PEEPS_BEHAVIOR.md. They are
        # additive bookkeeping seams for future parity work and do not
        # drive visible behavior until explicit consumers are wired.
        self.asm_flags = 0
        self.movement_substate = 0
        self.town_counter = 0
        self.linked_peep = None
        self.remembered_target = None
        self.terrain_marker = None
        self.last_move_offset = 0
        self.shield_opponent = None

    #============================================
    # State machine transitions (per asm/PEEPS_REPORT.md)
    #============================================

    # DEAD is implicitly reachable from every non-DEAD state (death by absorption,
    # combat, drown, life cap, or merge). The transition() method allows
    # state -> DEAD universally; this matrix only constrains non-terminal moves.
    _ALLOWED_TRANSITIONS: dict = {
        peep_state.PeepState.IDLE: {peep_state.PeepState.WANDER, peep_state.PeepState.SEEK_FLAT, peep_state.PeepState.JOIN_FORCES, peep_state.PeepState.FIGHT, peep_state.PeepState.DROWN},
        peep_state.PeepState.WANDER: {peep_state.PeepState.IDLE, peep_state.PeepState.SEEK_FLAT, peep_state.PeepState.BUILD, peep_state.PeepState.JOIN_FORCES, peep_state.PeepState.MARCH, peep_state.PeepState.FIGHT, peep_state.PeepState.DROWN},
        peep_state.PeepState.SEEK_FLAT: {peep_state.PeepState.IDLE, peep_state.PeepState.WANDER, peep_state.PeepState.BUILD, peep_state.PeepState.DROWN},
        peep_state.PeepState.BUILD: {peep_state.PeepState.IDLE, peep_state.PeepState.WANDER, peep_state.PeepState.DROWN},
        peep_state.PeepState.GATHER: {peep_state.PeepState.IDLE, peep_state.PeepState.WANDER, peep_state.PeepState.MARCH, peep_state.PeepState.JOIN_FORCES, peep_state.PeepState.DROWN},
        peep_state.PeepState.JOIN_FORCES: {peep_state.PeepState.MARCH, peep_state.PeepState.FIGHT, peep_state.PeepState.IDLE, peep_state.PeepState.DROWN},
        peep_state.PeepState.MARCH: {peep_state.PeepState.FIGHT, peep_state.PeepState.JOIN_FORCES, peep_state.PeepState.IDLE, peep_state.PeepState.DROWN},
        peep_state.PeepState.FIGHT: {peep_state.PeepState.IDLE, peep_state.PeepState.MARCH, peep_state.PeepState.DROWN},
        peep_state.PeepState.DROWN: set(),
        peep_state.PeepState.DEAD: set(),
    }

    def transition(self, new_state: str) -> None:
        """Validate and execute a state transition. Raises ValueError on disallowed transitions."""
        if new_state not in peep_state.PeepState.ALL:
            raise ValueError(f"Invalid state: {new_state}")
        # DEAD is universally reachable from any non-DEAD state.
        if new_state == peep_state.PeepState.DEAD:
            self.state = new_state
            # Clear ASM shadow bookkeeping (linked peep, remembered
            # target, terrain marker, shield opponent, last move
            # offset) so later code cannot see stale references.
            import populous_game.peep_helpers as peep_helpers
            peep_helpers.cleanup_dead_peep(self)
            return
        if self.state == peep_state.PeepState.DEAD:
            raise ValueError(f"Disallowed transition from DEAD to {new_state}")
        if new_state not in self._ALLOWED_TRANSITIONS.get(self.state, set()):
            raise ValueError(f"Disallowed transition from {self.state} to {new_state}")
        self.state = new_state

    def update(self, dt, transform):
        # transform is a populous_game.layout.ViewportTransform. The iso
        # projection used for compass-facing selection routes through
        # transform.world_to_screen_float so no iso pixel literals live
        # in this method. All callers (game.py main loop, tests) must
        # supply a transform.
        # Handle DEAD state: no updates
        if self.state == peep_state.PeepState.DEAD:
            self.death_timer += dt
            return

        # Handle DROWN state: advance drowning animation and transition to DEAD when animation completes
        if self.state == peep_state.PeepState.DROWN:
            self.death_timer += dt
            if self.death_timer > 1.0:
                self.transition(peep_state.PeepState.DEAD)
            return

        if self.dead:
            self.death_timer += dt
            return

        # Perte de vie : 1 point par seconde
        self.life -= dt * 1.0
        if self.life <= 0:
            self.life = 0
            self.dead = True
            self.transition(peep_state.PeepState.DEAD)
            return

        self.anim_timer += dt

        # Detecter si le peep est sur une tile eau (les 4 coins de la tile a 0)
        gr_cur, gc_cur = int(self.y), int(self.x)
        if (0 <= gr_cur < self.game_map.grid_height and 0 <= gc_cur < self.game_map.grid_width):
            a0 = self.game_map.get_corner_altitude(gr_cur,     gc_cur)
            a1 = self.game_map.get_corner_altitude(gr_cur,     gc_cur + 1)
            a2 = self.game_map.get_corner_altitude(gr_cur + 1, gc_cur + 1)
            a3 = self.game_map.get_corner_altitude(gr_cur + 1, gc_cur)
            on_water = (a0 == 0 and a1 == 0 and a2 == 0 and a3 == 0)
        else:
            on_water = False

        # Animation :
        if on_water:
            # Animation loop simple sur 4 frames (5,8 a 5,11)
            if not hasattr(self, '_drown_anim_idx'):
                self._drown_anim_idx = 0
            if self.anim_timer > 0.18:
                self.anim_timer -= 0.18
                self._drown_anim_idx = (self._drown_anim_idx + 1) % 4
            self.anim_frame = self._drown_anim_idx
        else:
            if self.anim_timer > 0.3:
                self.anim_timer -= 0.3
                self.anim_frame = (self.anim_frame + 1) % 2

        # Change de direction de temps en temps
        self.dir_timer += dt
        if self.dir_timer > 2.0 + random.random() * 3.0:
            self.dir_timer = 0.0
            self.direction = random.uniform(0, 2 * math.pi)

        # Deplacement
        speed = settings.PEEP_SPEED * dt / 64.0  # Normaliser par rapport a la taille du tile
        dx = math.cos(self.direction) * speed
        dy = math.sin(self.direction) * speed

        new_x = self.x + dx
        new_y = self.y + dy

        # Rester dans les limites
        new_x = max(0.1, min(self.game_map.grid_width - 0.1, new_x))
        new_y = max(0.1, min(self.game_map.grid_height - 0.1, new_y))

        # Verifier que la destination n'est pas de l'eau
        old_x, old_y = self.x, self.y
        gr, gc = int(new_y), int(new_x)
        if 0 <= gr < self.game_map.grid_height and 0 <= gc < self.game_map.grid_width:
            alt = self.game_map.get_corner_altitude(gr, gc)
            if alt > 0:
                self.x = new_x
                self.y = new_y

        self.is_moving = (self.x != old_x or self.y != old_y)

        # Detecter si le peep est sur une tile eau (les 4 coins de la tile a 0)
        gr_cur, gc_cur = int(self.y), int(self.x)
        if (0 <= gr_cur < self.game_map.grid_height and 0 <= gc_cur < self.game_map.grid_width):
            a0 = self.game_map.get_corner_altitude(gr_cur,     gc_cur)
            a1 = self.game_map.get_corner_altitude(gr_cur,     gc_cur + 1)
            a2 = self.game_map.get_corner_altitude(gr_cur + 1, gc_cur + 1)
            a3 = self.game_map.get_corner_altitude(gr_cur + 1, gc_cur)
            on_water = (a0 == 0 and a1 == 0 and a2 == 0 and a3 == 0)
        else:
            on_water = False

        # Mettre a jour la direction visuelle (8 directions)
        if on_water:
            self.facing = 'DROWN'
            if self.state != peep_state.PeepState.DROWN:
                self.transition(peep_state.PeepState.DROWN)
        elif self.is_moving:
            # Project the world-space movement delta into screen space
            # via the ViewportTransform. Camera and altitude offsets are
            # linear, so they cancel for a delta and we only need two
            # projections of the same world point with and without the
            # delta. dx is the col delta, dy is the row delta.
            bx, by = transform.world_to_screen_float(self.y, self.x, 0)
            ax, ay = transform.world_to_screen_float(self.y + dy, self.x + dx, 0)
            screen_dx = ax - bx
            screen_dy = ay - by
            angle = math.degrees(math.atan2(screen_dy, screen_dx)) % 360
            dirs = ['E', 'SE', 'S', 'SW', 'W', 'NW', 'N', 'NE']
            self.facing = dirs[int((angle + 22.5) / 45) % 8]
        else:
            self.facing = 'IDLE'

        # Construction
        self.build_timer += dt

    def try_build_house(self):
        if self.build_timer < 5.0:
            return None

        gr, gc = int(self.y), int(self.x)
        if self.game_map.can_place_house_initial(gr, gc):
            self.build_timer = 0.0
            from populous_game.houses import House
            # Determine max life of the building (hut by default)
            max_life = House.MAX_HEALTHS[0]
            # Estimate building type from terrain
            score, valid_tiles = self.game_map.get_flat_area_score(gr, gc, current_house=None)
            thresholds = [0, 1, 2, 5, 8, 11, 14, 19, 22, 24]
            max_tier = 0
            for i, thresh in enumerate(thresholds):
                if score >= thresh:
                    max_tier = i
            max_tier = min(len(House.TYPES) - 1, max_tier)
            max_life = House.MAX_HEALTHS[max_tier]

            # Si le peep a plus de vie que la vie max du batiment, on genere un peep avec l'excedent
            excess_life = self.life - max_life
            house = House(gr, gc, life=min(self.life, max_life), faction_id=self.faction)
            self.game_map.add_house(house)
            self.in_house = True
            self.life = 0
            self.dead = True
            # Peep becomes a house, so set state directly without transition validation
            self.state = peep_state.PeepState.DEAD
            # Mirror the cleanup that transition() runs for normal
            # death so shadow bookkeeping is consistent for both paths.
            import populous_game.peep_helpers as peep_helpers
            peep_helpers.cleanup_dead_peep(self)

            if excess_life > 0:
                # Cherche une case adjacente libre pour le peep excedentaire
                offsets = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
                for dr, dc in offsets:
                    nr, nc = gr + dr, gc + dc
                    if 0 <= nr < self.game_map.grid_height and 0 <= nc < self.game_map.grid_width:
                        # On verifie que la case n'est pas de l'eau et pas deja occupee par une maison
                        alt = self.game_map.get_corner_altitude(nr, nc)
                        occupied = any((nr, nc) in h.occupied_tiles for h in self.game_map.houses)
                        if alt > 0 and not occupied:
                            new_peep = Peep(nr, nc, self.game_map, faction_id=self.faction)
                            new_peep.life = excess_life
                            # _pending_peep is optional; initialized only when peeps exceed house capacity
                            self.game_map._pending_peep = getattr(self.game_map, '_pending_peep', [])
                            self.game_map._pending_peep.append(new_peep)
                            break
            return house
        return None

    def draw(self, surface, transform, show_debug=False, debug_font=None):
        # Iso projection flows through the supplied
        # populous_game.layout.ViewportTransform; the transform owns the
        # camera position so cam_x / cam_y are no longer parameters.
        # Sprite-anchor offsets (centering rule, foot-to-corner shift)
        # come from populous_game.sprite_geometry.SPRITE_ANCHORS so this
        # method holds no per-sprite pixel literals beyond the drowning
        # bobbing offset (animation, not iso geometry).
        # Lazy import: sprite_geometry imports peeps at module load, so
        # importing it at module top here would create a circular import.
        import populous_game.sprite_geometry as sprite_geometry

        gr, gc = int(self.y), int(self.x)
        fx = self.x - gc  # fraction horizontale dans la tile
        fy = self.y - gr  # fraction verticale dans la tile

        # Interpolation bilineaire de l'altitude selon la position dans la tile
        if (0 <= gr < self.game_map.grid_height and 0 <= gc < self.game_map.grid_width):
            a_nw = self.game_map.get_corner_altitude(gr,     gc)
            a_ne = self.game_map.get_corner_altitude(gr,     gc + 1)
            a_sw = self.game_map.get_corner_altitude(gr + 1, gc)
            a_se = self.game_map.get_corner_altitude(gr + 1, gc + 1)
            alt = (1 - fx) * (1 - fy) * a_nw + fx * (1 - fy) * a_ne \
                + (1 - fx) * fy       * a_sw + fx * fy       * a_se
        else:
            alt = 0

        # Ground anchor (iso projection of the world corner under the peep).
        sx, sy = transform.world_to_screen(self.y, self.x, alt)

        # Anchor metadata (dy from corner to feet, centering convention).
        # The meta key is selected by sprite_geometry; for now all peep
        # states share 'peep_default'.
        anchor_meta = sprite_geometry.SPRITE_ANCHORS[sprite_geometry._peep_anchor_key(self)]

        sprites = self.get_sprites()
        frames = WALK_FRAMES.get(self.facing, WALK_FRAMES['IDLE'])
        if self.facing == 'DROWN':
            # Animation pingpong sur 4 frames
            anim_len = 4
            # self.anim_frame est deja l'indice pingpong (0,1,2,3,2,1...)
            frame_key = (5, 8 + self.anim_frame)
        else:
            anim_len = len(frames)
            frame_key = frames[self.anim_frame % anim_len]
        sprite = sprites.get(frame_key)

        if sprite is not None:
            # Translate ground anchor + sprite size into top-left blit
            # pixel via the shared sprite_geometry helper. No iso or
            # centering literals appear in this method.
            sw, sh = sprite.get_size()
            blit_x, blit_y = sprite_geometry._apply_anchor((sx, sy), anchor_meta, (sw, sh))
            if self.dead:
                # Teinter en rouge pour les morts
                tinted = sprite.copy()
                tinted.fill((255, 0, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(tinted, (blit_x, blit_y))
            else:
                surface.blit(sprite, (blit_x, blit_y))
            # Affichage debug de la vie
            if show_debug and debug_font is not None:
                life_text = debug_font.render(f"{int(self.life)}", True, (255,255,0) if not self.dead else (255,0,0))
                text_x = sx - life_text.get_width() // 2
                text_y = blit_y - 16
                surface.blit(life_text, (text_x, text_y))
        else:
            # Fallback : petit cercle. Apply the same sprite-anchor
            # rule via sprite_geometry so the fallback diamond sits
            # where the real sprite would.
            fb_w, fb_h = sprite_geometry.PEEP_FALLBACK_SIZE
            blit_x, blit_y = sprite_geometry._apply_anchor((sx, sy), anchor_meta, (fb_w, fb_h))
            # The drawn circle's center sits at the foot point so it
            # visually replaces the bottom-aligned sprite.
            cx = blit_x + fb_w // 2
            cy = blit_y + fb_h
            pygame.draw.circle(surface, (255, 220, 120), (cx, cy), 3)
            if show_debug and debug_font is not None:
                life_text = debug_font.render(f"{int(self.life)}", True, (255,255,0))
                text_x = cx - life_text.get_width() // 2
                text_y = cy - 24
                surface.blit(life_text, (text_x, text_y))

    def is_removable(self):
        if self.in_house:
            return True
        return self.dead and self.death_timer > 3.0
