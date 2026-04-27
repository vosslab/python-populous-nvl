import sys
import os

# Gestion du dossier de base compatible PyInstaller
if getattr(sys, 'frozen', False):
    # Exécution via PyInstaller
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# === Internal rendering canvas ===
# These describe the internal rendering surface, not the OS window.
# The internal surface is fixed at the AmigaUI sprite-sheet dimensions
# (320x200), then scaled up by display_scale * RESOLUTION_SCALE for
# the on-screen window. Pre-M2 code mutated these at runtime to match
# the loaded UI image; the M2 cleanup removed that mutation, so they
# must already match the internal canvas or MAP_OFFSET_X/Y end up
# pointing off-canvas and the terrain pass renders nothing visible.
SCREEN_WIDTH: int = 320
SCREEN_HEIGHT: int = 200

# === Couleurs ===
BLACK: tuple = (0, 0, 0)
WHITE: tuple = (255, 255, 255)
RED: tuple = (200, 0, 0)
GREEN: tuple = (0, 180, 0)
BLUE: tuple = (0, 0, 200)
GRAY: tuple = (128, 128, 128)
BROWN: tuple = (139, 69, 19)

# === Grille ===
GRID_WIDTH: int = 64
GRID_HEIGHT: int = 64

# === Altitude ===
ALTITUDE_MIN: int = 0
ALTITUDE_MAX: int = 7
ALTITUDE_PIXEL_STEP: int = 1

# === Tile isométrique ===
TILE_WIDTH: int = 32
TILE_HEIGHT: int = 24
TILE_HALF_W: int = 16
TILE_HALF_H: int = 8

# === Iso terrain origin within the AmigaUI viewport hole ===
# These mark the screen position of the (cam_r, cam_c) corner of the
# rendered iso diamond. With 8 visible tiles in each iso direction, the
# diamond extends 8*TILE_HALF_W = 128 px to the left and right of
# MAP_OFFSET_X, and 8*TILE_HALF_H = 64 px down from MAP_OFFSET_Y.
#
# The viewport hole in the AmigaUI panel is itself iso-shaped and offset
# from the canvas center -- the panel chrome occupies the bottom-left
# (dpad, powers) and top-right (shield, status). Empirically, the
# diamond aligns with the hole at MAP_OFFSET_X = 192, MAP_OFFSET_Y = 64.
# Use tools/sweep_map_offset.py to re-tune visually if the AmigaUI image
# changes.
MAP_OFFSET_X: int = 192
MAP_OFFSET_Y: int = 64

# === Chemins ===
# Get the repo root (one level up from populous_game/)
REPO_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GFX_DIR: str = os.path.join(REPO_ROOT, "data", "gfx")
SFX_DIR: str = os.path.join(REPO_ROOT, "data", "sfx")
TILES_PATH: str = os.path.join(GFX_DIR, "AmigaTiles1.PNG")
SPRITES_PATH: str = os.path.join(GFX_DIR, "AmigaSprites1.PNG")

# === Tiles spritesheet grid (lignes rouges dans Tiles.PNG) ===
TILES_V_LINES: list = [(65,66),(132,133),(199,200),(266,267),(333,334),(400,401),(467,468),(534,535),(601,602)]
TILES_H_LINES: list = [(48,49),(98,99),(148,149),(198,199),(248,249),(298,299),(348,349)]

# === Sprites ===
SPRITE_SIZE: int = 16

# === Mapping des tiles terrain ===
# Les coins d'une case : A=top(NW), B=right(NE), C=bottom(SE), D=left(SW)
# Clé = (delta_A, delta_B, delta_C, delta_D) par rapport à l'altitude min
# Tiles pentes pour altitude >= 2
# Clé = (delta_NW, delta_NE, delta_SE, delta_SW) par rapport à l'altitude min
SLOPE_TILES: dict = {
    (1, 0, 0, 0): (0, 1),   # NW
    (0, 1, 0, 0): (0, 2),   # NE
    (1, 1, 0, 0): (0, 3),   # NW+NE
    (0, 0, 1, 0): (0, 4),   # SE
    (1, 0, 1, 0): (0, 5),   # NW+SE
    (0, 1, 1, 0): (0, 6),   # NE+SE
    (1, 1, 1, 0): (0, 7),   # NW+NE+SE (SW abaissé)
    (0, 0, 0, 1): (0, 8),   # SW
    (1, 0, 0, 1): (1, 0),   # NW+SW
    (0, 1, 0, 1): (1, 1),   # NE+SW
    (1, 1, 0, 1): (1, 2),   # NW+NE+SW (SE abaissé)
    (0, 0, 1, 1): (1, 3),   # SE+SW
    (1, 0, 1, 1): (1, 4),   # NW+SE+SW (NE abaissé)
    (0, 1, 1, 1): (1, 5),   # NE+SE+SW (NW abaissé)
}

TILE_WATER: tuple = (0, 0)
TILE_WATER_2: tuple = (1, 7)       # 2e frame d'animation de l'eau
TILE_FLAT: tuple = (1, 6)
TILE_CONSTRUCTED: tuple = (3, 4)

# Tiles pentes pour altitude basse (= 1, juste au-dessus de l'eau)
# Même ordre de deltas que SLOPE_TILES, de (1,8) à (3,3)
SLOPE_TILES_LOW: dict = {
    (1, 0, 0, 0): (1, 8),
    (0, 1, 0, 0): (2, 0),
    (1, 1, 0, 0): (2, 1),
    (0, 0, 1, 0): (2, 2),
    (1, 0, 1, 0): (2, 3),
    (0, 1, 1, 0): (2, 4),
    (1, 1, 1, 0): (2, 5),
    (0, 0, 0, 1): (2, 6),
    (1, 0, 0, 1): (2, 7),
    (0, 1, 0, 1): (2, 8),
    (1, 1, 0, 1): (3, 0),
    (0, 0, 1, 1): (3, 1),
    (1, 0, 1, 1): (3, 2),
    (0, 1, 1, 1): (3, 3),
}

# === Tiles bâtiments (de (3,6) à (4,4)) ===
BUILDING_TILES: dict = {
    'hut': (3, 6),
    'house_small': (3, 7),
    'house_medium': (3, 8),
    'castle_small': (4, 0),
    'castle_medium': (4, 1),
    'castle_large': (4, 2),
    'fortress_small': (4, 3),
    'fortress_medium': (4, 4),
    'fortress_large': (4, 5),
}

# === Château 3x3 (tiles (4,5) à (4,8)) ===
CASTLE_9_TILES: dict = {
    'corner': (4, 5),
    'center': (4, 6),
    'side_lr': (4, 7),   # côtés gauche/droite
    'side_tb': (4, 8),   # côtés haut/bas
}

# === Tiles objets (ligne 5) ===
OBJECT_TILES: dict = {
    'volcano': (5, 0),
    'cross': (5, 1),
    'mountain_small': (5, 2),
    'mountain_large': (5, 3),
    'tree_small': (5, 4),
    'tree_medium': (5, 5),
    'tree_large': (5, 6),
    'bush': (5, 7),
}

# === Peep ===
PEEP_SPEED: float = 30.0

# === UI Configuration ===
HUD_FONT_SIZE: int = 16
DEBUG_FONT_SIZE: int = 14
RESOLUTION_SCALE: int = 1  # 1 = normal, 2 = double-size pixels

# === UI Panel (Shield/Info) ===
UI_PANEL_BASE_CENTER_X: int = 64
UI_PANEL_BASE_CENTER_Y: int = 168
UI_PANEL_BUTTON_DX: int = 16  # Isometric X offset
UI_PANEL_BUTTON_DY: int = 8   # Isometric Y offset
UI_PANEL_BUTTON_HW: int = 16  # Isometric width (half)
UI_PANEL_BUTTON_HH: int = 8   # Isometric height (half)
UI_PANEL_DIAMOND_THRESHOLD: float = 1.0  # Collision threshold for diamond buttons

# === UI Shield Marker Positions ===
UI_SHIELD_MARKER_OFFSET_X: int = 11
UI_SHIELD_MARKER_OFFSET_Y: int = 23
UI_SHIELD_MARKER_PEEP_X: int = -1
UI_SHIELD_MARKER_PEEP_Y: int = 2

#============================================
# Combat constants (rules contract; tunable per asm/PEEPS_REPORT.md)
#============================================

PEEP_LIFE_REFERENCE: float = 50.0  # baseline life for damage-scaling math
PEEP_LIFE_MAX: float = 200.0       # cap when joining forces (TODO: cite asm/PEEPS_REPORT.md section 4.4)
COMBAT_PEEP_DPS: float = 10.0      # damage per second peep-vs-peep at reference life
COMBAT_HOUSE_DPS: float = 4.0      # damage per second peep-vs-house at reference life

# === Faction colors ===
FACTION_COLORS_COLORBLIND_SAFE: dict = {
    0: (40, 120, 220),    # PLAYER -- blue (safe)
    1: (220, 110, 30),    # ENEMY -- orange (safe pair with blue)
    2: (160, 160, 160),   # NEUTRAL -- gray
}
FACTION_COLORS_AMIGA_CLASSIC: dict = {
    0: (40, 120, 220),    # PLAYER -- blue (placeholder; tune later)
    1: (220, 0, 0),       # ENEMY -- red (Amiga classic)
    2: (160, 160, 160),   # NEUTRAL -- gray
}
USE_COLORBLIND_PALETTE: bool = True  # default per plan

# === Rendering ===
SCANLINE_ALPHA: int = 100  # Alpha for scanline overlay
BUTTON_FLASH_DURATION: float = 0.15  # Seconds
DPAD_REPEAT_DELAY: float = 0.2  # Seconds between scrolls
DPAD_BUTTON_POSITION_ADJ: int = 1  # Pixel adjustment for button sprite display

#============================================
# AI opponent constants (v1 heuristics, per asm/PEEPS_REPORT.md)
#============================================

AI_TICK_INTERVAL: float = 1.0       # seconds between AI decisions
AI_BUILD_LIFE_THRESHOLD: float = 30.0
AI_MARCH_THRESHOLD: int = 6         # enemy population to trigger massed march
AI_MARCH_BATCH: int = 4

#============================================
# Power constants (rules-faithful per asm/CONSTRUCTION_REPORT.md;
# values are interim pending precise asm citation)
#============================================

POWER_PAPAL_COST: float = 5.0
POWER_PAPAL_COOLDOWN: float = 1.0
POWER_VOLCANO_COST: float = 80.0
POWER_VOLCANO_COOLDOWN: float = 30.0
POWER_VOLCANO_RADIUS: int = 3
POWER_FLOOD_COST: float = 60.0
POWER_FLOOD_COOLDOWN: float = 25.0
POWER_FLOOD_RADIUS: int = 4
POWER_QUAKE_COST: float = 50.0
POWER_QUAKE_COOLDOWN: float = 20.0
POWER_QUAKE_RADIUS: int = 5
POWER_SWAMP_COST: float = 40.0
POWER_SWAMP_COOLDOWN: float = 15.0
POWER_SWAMP_RADIUS: int = 2
POWER_KNIGHT_COST: float = 100.0
POWER_KNIGHT_COOLDOWN: float = 60.0
POWER_TERRAIN_COST: float = 1.0
POWER_TERRAIN_COOLDOWN: float = 0.0
INITIAL_MANA: float = 100.0
MANA_REGEN_PER_HOUSE_PER_SEC: float = 0.5

#============================================
# UI tooltip text. Keyed by ui_panel.buttons action name.
#============================================

BUTTON_TOOLTIPS: dict = {
    '_do_papal':      'Papal Magnet (P): peeps walk to a chosen tile',
    '_do_volcano':    'Volcano (V): erupts and raises terrain',
    '_do_flood':      'Flood (F): floods the chosen area',
    '_do_quake':      'Earthquake (Q): drops terrain in a wide area',
    '_do_swamp':      'Swamp (S): creates lethal swamp tiles',
    '_do_knight':     'Knight (K): converts a peep to a strong fighter',
    '_do_shield':     'Shield: toggle shield panel info mode',
    '_raise_terrain': 'Raise terrain (left click)',
    '_find_battle':   'Find battle: center view on the nearest combat',
    '_find_papal':    'Find papal magnet',
    '_find_shield':   'Find shield marker',
    '_find_knight':   'Find knight peep',
    '_go_papal':      'Send peeps to the papal magnet',
    '_go_build':      'Send peeps to find flat land and build',
    '_go_assemble':   'Group peeps together (join forces)',
    '_go_fight':      'Send peeps to fight the nearest enemy',
    '_battle_over':   'Battle resolution overview',
    'N':              'Scroll viewport north',
    'NE':             'Scroll viewport north-east',
    'E':              'Scroll viewport east',
    'SE':             'Scroll viewport south-east',
    'S':              'Scroll viewport south',
    'SW':             'Scroll viewport south-west',
    'W':              'Scroll viewport west',
    'NW':             'Scroll viewport north-west',
}

#============================================
# Drag-paint terrain timing
#============================================

DRAG_PAINT_INTERVAL: float = 0.05  # seconds between paint events when dragging

#============================================
# Minimap zoom
#============================================

MINIMAP_ZOOM_MIN: float = 0.5
MINIMAP_ZOOM_MAX: float = 3.0
MINIMAP_ZOOM_STEP: float = 0.1
MINIMAP_ZOOM_DEFAULT: float = 1.0
