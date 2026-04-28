#!/usr/bin/env python3

import pygame
import random
import os
import populous_game.settings as settings
import populous_game.terrain as terrain
import populous_game.peeps as peep
import populous_game.faction as faction
import populous_game.peep_state as peep_state
import populous_game.camera as camera
import populous_game.minimap as minimap
import populous_game.assets as assets
import populous_game.input_controller as input_controller
import populous_game.mode_manager as mode_manager
import populous_game.selection as selection
import populous_game.renderer as renderer
import populous_game.ui_panel as ui_panel
import populous_game.audio as audio
import populous_game.app_state as app_state
import populous_game.combat as combat
import populous_game.ai_opponent as ai_opponent
import populous_game.powers as powers
import populous_game.mana_pool as mana_pool
import populous_game.keymap as keymap
import populous_game.layout as layout_module

class Game:
	def move_camera_direction(self, direction):
		# Move camera according to direction
		self.camera.move_direction(direction)

	def player_faction_id(self) -> int:
		"""Return the player faction ID."""
		return faction.Faction.PLAYER
	def __init__(self, display_scale: int | None = None, seed: int | None = None,
			debug_layout: bool = False,
			map_profile: str = 'remaster_islands'):
		self.map_profile = map_profile
		# Load keymap (user config or defaults)
		self.keymap = keymap.load_keymap()
		# M6 Patch 8: --debug-layout overlay flag. When True, the renderer
		# draws diagnostic geometry (HUD/map-well/clip rects, terrain
		# anchor, visible tile centers, button hit-boxes) on every frame.
		self.debug_layout = bool(debug_layout)

		# Create mode manager for papal, shield, and D-Pad state
		self.mode_manager = mode_manager.ModeManager()

		# Create app state machine
		self.app_state = app_state.AppState()

		# Create audio manager
		self.audio_manager = audio.AudioManager()
		self.audio_manager.init()
		audio.register_default_sounds(self.audio_manager)
		# Optionally auto-start background music. Default False so a fresh
		# boot is silent; the user can flip this via settings.MUSIC_AUTOSTART.
		if settings.MUSIC_AUTOSTART:
			self.audio_manager.play_music()

		pygame.init()
		self.clock = pygame.time.Clock()
		self.font = pygame.font.SysFont("consolas", settings.HUD_FONT_SIZE)

		# Load UI to determine screen size
		ui_path = os.path.join(settings.GFX_DIR, "AmigaUI.png")
		ui_raw = pygame.image.load(ui_path)
		# Initialisation des zones interactives de l'interface ---
		# The internal canvas size is driven by the active CANVAS_PRESET
		# (settings.INTERNAL_WIDTH/HEIGHT), not by the AmigaUI sprite
		# dimensions. At classic preset these match the sprite (320x200);
		# at remaster/large the canvas is bigger and the HUD sprite is
		# upscaled at blit time below.
		self.base_size = (settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT)
		# Discard `ui_raw` after sizing -- assets.get_ui_image() returns
		# the canonical image used for blitting.
		del ui_raw
		# CLI-supplied display_scale overrides the legacy default of 3
		# (which produced a 960x600 window at classic preset). The default
		# behavior is preserved when no override is given.
		if display_scale is None:
			self.display_scale = 3
		else:
			self.display_scale = int(display_scale)

		# Apply resolution scale from settings
		final_scale = self.display_scale * settings.RESOLUTION_SCALE

		# Initialiser l'écran basé sur l'UI avec l'échelle d'affichage
		self.screen = pygame.display.set_mode((self.base_size[0] * final_scale, self.base_size[1] * final_scale))
		pygame.display.set_caption("Populous")

		# Load all assets now that display is set up
		assets.load_all()
		self.ui_image = assets.get_ui_image()
		# Cache a presized HUD blit surface once so the per-frame
		# renderer reuses it without paying a transform.scale cost. When
		# HUD_SCALE > 1 the 320x200 AmigaUI sprite is upscaled to the
		# internal canvas size; at HUD_SCALE == 1 the cached surface is
		# `self.ui_image` itself, so behavior at classic preset is
		# byte-identical to pre-patch.
		if settings.HUD_SCALE > 1:
			self.hud_blit_surface = pygame.transform.scale(
				self.ui_image,
				(settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT),
			)
		else:
			self.hud_blit_surface = self.ui_image
		self.internal_surface = pygame.Surface(self.base_size)
		self.internal_surface.blit(self.hud_blit_surface, (0, 0))

		# Dimensions de la zone de render (plein écran à l'échelle 1).
		# The view rect spans the full internal canvas so terrain math
		# stays consistent with the HUD blit above.
		self.view_rect = pygame.Rect(0, 0, settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT)

		# Note: screen dimensions are determined by UI size, but we do not
		# mutate module attributes. Each module reads settings.X directly.

		self.camera = camera.Camera()
		# Snapshot the active canvas layout once. The layout never
		# changes mid-session (preset is fixed at boot), so a per-frame
		# rebuild is unnecessary; only the camera-dependent transform
		# is rebuilt each draw().
		self.layout = layout_module.active_layout()
		# Build an initial ViewportTransform so any pre-draw caller can
		# project safely. draw() refreshes this every frame.
		self.viewport_transform = layout_module.build_viewport_transform(
			self.layout, self.camera, settings.VISIBLE_TILE_COUNT
		)
		self.game_map = terrain.GameMap(settings.GRID_WIDTH, settings.GRID_HEIGHT)
		# Honor CLI seed override for deterministic terrain. None falls
		# back to the wall-clock seeded path used by the existing run().
		if seed is None:
			self.game_map.randomize(profile=self.map_profile)
		else:
			self.game_map.randomize(seed=int(seed), profile=self.map_profile)
		# Apply the flat-water debug pass once at boot. The same helper
		# runs again whenever _reset_game re-randomizes so a
		# DEBUG_FLAT_WATER session stays flat across menu->play cycles.
		self._maybe_flatten_for_debug()
		self.minimap = minimap.Minimap(0, 0) # Position de la minimap

		# Get weapon sprites from asset registry
		self.weapon_sprites = assets.get_weapon_sprites()
		self.weapon_sprite_indices = assets.get_weapon_sprite_indices()
		self.peeps = []
		self.score = 0
		self.running = True
		self.show_debug = True
		self.show_scanlines = False

		# Create selection object for viewed entity
		self.selection = selection.Selection()

		self.scanline_surface = None
		self._update_scanline_surface()

		# Initialize button feedback (sprite)
		self.last_button_click = None

		# Get button sprites from asset registry
		self.button_sprites = assets.get_button_sprites()
		self.button_sprite_indices = assets.get_button_sprite_indices()

		# Create UI panel for shield panel rendering and button hit-testing
		self.ui_panel = ui_panel.UIPanel(self)

		# Create input controller
		self.input_controller = input_controller.InputController(self)

		# Create renderer
		self.renderer = renderer.Renderer(self)

		# Create AI opponent
		self.ai_opponent = ai_opponent.AIOpponent(self)

		# Create mana pool and power manager
		self.mana_pool = mana_pool.ManaPool([faction.Faction.PLAYER, faction.Faction.ENEMY])
		self.power_manager = powers.PowerManager(self)


	def _update_scanline_surface(self):
		w, h = self.screen.get_size()
		self.scanline_surface = pygame.Surface((w, h), pygame.SRCALPHA)
		self.scanline_surface.fill((0, 0, 0, 0))
		for y in range(0, h, max(1, self.display_scale)):
			pygame.draw.line(self.scanline_surface, (0, 0, 0, 100), (0, y), (w, y), 1)

	def spawn_initial_peeps(self, count: int, faction_id: int = None) -> None:
		"""Spawn initial peeps for a faction near top-left of the grid.

		If the random pick is water, fall back to the nearest land corner
		via breadth-first search. Spawns the requested count; raises
		RuntimeError if the map has no land at all.

		Args:
			count: Number of peeps to spawn.
			faction_id: Faction ID (defaults to Faction.PLAYER).
		"""
		# Layout-debug mode: flat water means no land exists; skip peep
		# spawn entirely so pressing N to start does not crash.
		if settings.DEBUG_FLAT_WATER:
			return
		if faction_id is None:
			faction_id = faction.Faction.PLAYER
		for _ in range(count):
			r = random.randint(0, settings.GRID_HEIGHT - 1)
			c = random.randint(0, settings.GRID_WIDTH - 1)
			# If pick is water, find the nearest land corner.
			if self.game_map.get_corner_altitude(r, c) <= 0:
				land = self.game_map.find_nearest_land(r, c)
				if land is None:
					raise RuntimeError(
						"Cannot spawn peep: no land tile exists on the map"
					)
				r, c = land
			self.peeps.append(peep.Peep(r, c, self.game_map, faction_id=faction_id))

	def spawn_enemy_peeps(self, count: int = 5) -> None:
		"""Spawn enemy peeps near bottom-right of the grid.

		Per M5 Wave 3: enemies spawn opposite corner from player. Falls
		back to nearest land via BFS if the random pick is water; raises
		RuntimeError if the map has no land at all.
		"""
		# Layout-debug mode: flat water has no land; skip spawn.
		if settings.DEBUG_FLAT_WATER:
			return
		for _ in range(count):
			r = random.randint(settings.GRID_HEIGHT // 2, settings.GRID_HEIGHT - 1)
			c = random.randint(settings.GRID_WIDTH // 2, settings.GRID_WIDTH - 1)
			if self.game_map.get_corner_altitude(r, c) <= 0:
				land = self.game_map.find_nearest_land(r, c)
				if land is None:
					raise RuntimeError(
						"Cannot spawn enemy peep: no land tile exists on the map"
					)
				r, c = land
			self.peeps.append(peep.Peep(r, c, self.game_map, faction_id=faction.Faction.ENEMY))

	def _check_game_over(self) -> None:
		"""Check win/lose conditions and transition to GAMEOVER state if met.

		WIN: All enemy peeps dead AND all enemy houses destroyed.
		LOSE: All player peeps dead AND all player houses destroyed.
		"""
		if not self.app_state.is_playing():
			return  # Only check during gameplay
		if self.app_state.is_gameover():
			return  # Already in gameover state
		# Layout-debug mode: flat water has no peeps so the empty-faction
		# rule would auto-win every frame. Skip the check so the user
		# can sit on the rendered diamond and inspect alignment.
		if settings.DEBUG_FLAT_WATER:
			return
		enemy_peeps = [p for p in self.peeps
			if p.faction_id == faction.Faction.ENEMY
			and p.state != peep_state.PeepState.DEAD]
		enemy_houses = [h for h in self.game_map.houses
			if h.faction_id == faction.Faction.ENEMY
			and not h.destroyed]
		player_peeps = [p for p in self.peeps
			if p.faction_id == faction.Faction.PLAYER
			and p.state != peep_state.PeepState.DEAD]
		player_houses = [h for h in self.game_map.houses
			if h.faction_id == faction.Faction.PLAYER
			and not h.destroyed]
		# WIN: no living enemies remain
		if len(enemy_peeps) == 0 and len(enemy_houses) == 0:
			self.app_state.gameover_result = 'win'
			self.app_state.transition_to(self.app_state.GAMEOVER)
			return
		# LOSE: no living player units remain
		if len(player_peeps) == 0 and len(player_houses) == 0:
			self.app_state.gameover_result = 'lose'
			self.app_state.transition_to(self.app_state.GAMEOVER)
			return

	def _maybe_flatten_for_debug(self) -> None:
		"""Zero every corner altitude when settings.DEBUG_FLAT_WATER is set.

		Layout-debug knob: forces the iso terrain to a flat blue diamond
		so the rendered well shape is unambiguous against the AmigaUI
		HUD chrome. Off by default. Not exposed via the CLI per the
		argparse-minimalism rule in docs/PYTHON_STYLE.md -- flip the
		settings constant when debugging map-well alignment.
		"""
		if not settings.DEBUG_FLAT_WATER:
			return
		gm = self.game_map
		for r in range(gm.grid_height + 1):
			for c in range(gm.grid_width + 1):
				gm.corners[r][c] = 0

	def _reset_game(self):
		"""Reset game state for a new session or return to menu."""
		self.peeps.clear()
		self.game_map.houses.clear()
		self.score = 0
		for name in self.power_manager.cooldowns:
			self.power_manager.cooldowns[name] = 0.0
		self.mana_pool = mana_pool.ManaPool([faction.Faction.PLAYER, faction.Faction.ENEMY])
		self.game_map.randomize(profile=self.map_profile)
		self._maybe_flatten_for_debug()
		self.selection.who = None
		self.selection.kind = None
		self.mode_manager.papal_mode = False
		self.mode_manager.shield_mode = False
		self.mode_manager.papal_position = None
		self.mode_manager.shield_target = None
		self.input_controller.reset_find_cursors()

	def _apply_combat_resolution(self, dt: float) -> None:
		"""Apply combat resolution: peep-vs-peep, peep-vs-house, force joining.

		Per asm/PEEPS_REPORT.md sections 4.3-4.4: peeps on the same tile or
		adjacent tiles may engage in combat or force joining.
		"""
		# O(n^2) peep-vs-peep combat (acceptable for small peep counts)
		for i, peep_a in enumerate(self.peeps):
			for peep_b in self.peeps[i + 1 :]:
				# Check if peeps share a tile or are within 1 grid cell
				dist_sq = (peep_a.x - peep_b.x) ** 2 + (peep_a.y - peep_b.y) ** 2
				if dist_sq < 1.0:
					# Same faction: attempt join_forces
					if peep_a.faction_id == peep_b.faction_id:
						combat.join_forces(peep_a, peep_b)
					# Enemy factions: apply mutual damage
					else:
						combat.damage_peep_vs_peep(peep_a, peep_b, dt)
						combat.damage_peep_vs_peep(peep_b, peep_a, dt)

		# Peep-vs-house combat (peeps adjacent to enemy houses)
		for peep_a in self.peeps:
			for house in self.game_map.houses:
				dist_sq = (peep_a.x - house.c) ** 2 + (peep_a.y - house.r) ** 2
				if dist_sq < 2.0:  # Within ~1.4 grid cells
					combat.damage_peep_vs_house(peep_a, house, dt)

	def run(self):
		# Hide OS cursor; the renderer draws a Populous-style sprite cursor
		# on the internal surface (so it scales with the rest of the canvas
		# and tracks across menu, gameplay, and panel UI). Prior code drew
		# the cursor on the full-resolution screen at internal-canvas coords
		# AFTER pygame.display.flip(), so it appeared in the upper-left
		# quadrant only and lagged one frame -- effectively invisible.
		pygame.mouse.set_visible(False)
		# Boot to menu state; gameplay starts when user presses Enter
		while self.running:
			dt = self.clock.tick(60) / 1000.0
			self.events()
			if self.app_state.is_playing() and not self.app_state.is_simulation_paused():
				# Apply time scale for fast-forward mode
				scaled_dt = dt * self.app_state.time_scale
				self.update(scaled_dt)
			self.draw()


	def events(self):
		# Delegate input handling to input controller
		self.running = self.input_controller.poll()

	def update(self, dt):
		import time
		# Continuous D-Pad scroll UI
		if self.mode_manager.dpad_held_direction:
			self.mode_manager.dpad_held_timer -= dt
			if self.mode_manager.dpad_held_timer <= 0.0:
				self.move_camera_direction(self.mode_manager.dpad_held_direction)
				self.mode_manager.dpad_held_timer = self.mode_manager.dpad_repeat_delay
				self.mode_manager.dpad_last_flash_time = time.time()

		self.camera.update(dt)
		self.game_map.update(dt)
		for p in self.peeps:
			p.update(dt, self.viewport_transform)
			if not p.dead:
				new_house = p.try_build_house()
				if new_house is not None and self.selection.kind == 'peep' and self.selection.who == p:
					self.selection.who = new_house
					self.selection.kind = 'house'
		# Add excess peeps generated during construction
		if hasattr(self.game_map, '_pending_peep'):
			self.peeps.extend(self.game_map._pending_peep)
			self.game_map._pending_peep.clear()

		# Apply combat resolution: peep-vs-peep, peep-vs-house, force joining
		self._apply_combat_resolution(dt)

		self.peeps = [p for p in self.peeps if not p.is_removable()]

		# AI opponent decision-making
		self.ai_opponent.update(dt)

		# Update power manager cooldowns and mana pool
		self.power_manager.update(dt)
		self.mana_pool.regen_from_houses(self.game_map.houses, dt)

		# Houses: update and spawn peeps
		new_peeps = []
		houses_to_keep = []
		for house in self.game_map.houses:
			house.update(dt, self.game_map)
			if house.destroyed:
				# Terrain no longer flat, destroy house and recover peep with faction and capped life
				self.audio_manager.play_sfx('building_destroy')
				new_peep = peep.Peep(house.r, house.c, self.game_map, faction_id=house.faction)
				new_peep.life = min(house.life, settings.PEEP_LIFE_MAX)
				new_peep.weapon_type = house.building_type
				new_peeps.append(new_peep)
				if self.selection.kind == 'house' and self.selection.who == house:
					self.selection.who = new_peep
					self.selection.kind = 'peep'
			else:
				houses_to_keep.append(house)
				if house.can_spawn_peep():
					self.audio_manager.play_sfx('peep_spawn')
					new_peep = peep.Peep(house.r, house.c, self.game_map, faction_id=house.faction)
					# Give building weapon to spawning peep
					new_peep.weapon_type = house.building_type
					# Peep exits with building max health
					new_peep.life = house.max_life
					new_peeps.append(new_peep)
					# Building returns to 1 health
					house.life = 1.0
		self.game_map.houses = houses_to_keep
		self.peeps.extend(new_peeps)

		# Keep selection valid if target still exists.
		if self.selection.kind == 'peep' and self.selection.who not in self.peeps:
			self.selection.who = None
			self.selection.kind = None
		elif self.selection.kind == 'house' and self.selection.who not in self.game_map.houses:
			self.selection.who = None
			self.selection.kind = None

		# Check win/lose conditions
		self._check_game_over()

	def draw(self):
		# Refresh the viewport transform once per frame. The camera moves
		# between frames, but layout / preset state is static, so we
		# rebuild only the camera-dependent transform here.
		self.viewport_transform = layout_module.build_viewport_transform(
			self.layout, self.camera, settings.VISIBLE_TILE_COUNT
		)
		# Delegate to renderer; OS cursor is visible (see run() comment).
		self.renderer.draw_frame()
		self._draw_debug_overlay()

	def _draw_debug_overlay(self) -> None:
		"""Draw debug overlay on final screen."""
		if not self.show_debug:
			return

		mouse_x, mouse_y = pygame.mouse.get_pos()
		mouse_x //= self.display_scale
		mouse_y //= self.display_scale
		cam_r, cam_c = self.camera.r, self.camera.c

		alt_text = "N/A"
		grid_r, grid_c = -1, -1
		if self.view_rect.collidepoint(mouse_x, mouse_y):
			# Round the float (row, col) returned by screen_to_world to
			# the nearest integer corner; this preserves the legacy
			# screen_to_nearest_corner semantics now that the math
			# lives in ViewportTransform.
			rf, cf = self.viewport_transform.screen_to_world(mouse_x, mouse_y)
			grid_r = int(round(rf))
			grid_c = int(round(cf))
			alt = self.game_map.get_corner_altitude(grid_r, grid_c)
			if alt != -1:
				alt_text = str(alt)

		debug_texts = [
			f"FPS: {self.clock.get_fps():.1f}",
			f"Scale: x{self.display_scale}",
			f"Mouse: ({mouse_x}, {mouse_y})",
			f"Corner: ({grid_r}, {grid_c}) Alt: {alt_text}",
			f"Camera R/C: ({cam_r:.2f}, {cam_c:.2f})",
			f"Peeps: {len(self.peeps)}",
			f"Houses: {len(self.game_map.houses)}"
		]
		bold_font = pygame.font.SysFont("consolas", 16, bold=True)
		for i, text in enumerate(debug_texts):
			surf = bold_font.render(text, True, settings.WHITE)
			self.screen.blit(surf, (10, 10 + 18 * i))

		if self.show_scanlines and self.scanline_surface:
			self.screen.blit(self.scanline_surface, (0, 0))


#============================================
def main() -> None:
	"""Run the game."""
	game = Game()
	game.run()
#============================================

if __name__ == '__main__':
	main()
