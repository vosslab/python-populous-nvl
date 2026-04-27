"""Rendering engine for terrain, entities, UI, and visual effects."""

import pygame
import time
import populous_game.settings as settings


class Renderer:
	"""Handles all game frame rendering."""

	def __init__(self, game):
		"""Initialize with a reference to the Game instance."""
		self.game = game

	@staticmethod
	def faction_color(faction_id: int) -> tuple:
		"""Return RGB color for a faction ID based on palette settings."""
		palette = (settings.FACTION_COLORS_COLORBLIND_SAFE
			if settings.USE_COLORBLIND_PALETTE
			else settings.FACTION_COLORS_AMIGA_CLASSIC)
		return palette[faction_id]

	def draw_frame(self) -> None:
		"""Draw one complete game frame based on app state."""
		if self.game.app_state.is_menu():
			self._draw_menu()
		elif self.game.app_state.is_playing():
			self._draw_gameplay()
		elif self.game.app_state.is_paused():
			self._draw_gameplay()
			self._draw_pause_overlay()
		elif self.game.app_state.is_gameover():
			self._draw_gameplay()
			self._draw_gameover()

		# Draw confirm dialog on top of everything if present
		self._draw_confirm_dialog()

		# Custom cursor (Populous-style) draws on internal surface so it
		# scales with the rest of the canvas. Drawn last so it sits on
		# top of every other UI element.
		self._draw_custom_cursor()

		# Scale and flip to screen
		scaled = pygame.transform.scale(self.game.internal_surface, self.game.screen.get_size())
		self.game.screen.blit(scaled, (0, 0))
		pygame.display.flip()

	#============================================
	# Custom cursor (M7)
	#============================================

	def _draw_custom_cursor(self) -> None:
		"""Draw a Populous-style cursor sprite at the OS mouse position.

		The sprite varies by mode (papal, shield, default). Drawn onto the
		internal surface in canvas-space so it scales with the rest of the
		game when the renderer blits + scales to the OS window.
		"""
		import populous_game.peeps as peeps_module
		sprites = peeps_module.Peep.get_sprites()
		mx, my = pygame.mouse.get_pos()
		mx_internal = mx // self.game.display_scale
		my_internal = my // self.game.display_scale
		if self.game.mode_manager.papal_mode:
			cursor = sprites.get((4, 14))
		elif self.game.mode_manager.shield_mode:
			cursor = sprites.get((8, 8))
		else:
			cursor = sprites.get((4, 12))
		if cursor is None:
			return
		# Anchor sprite top-left at the cursor (matches original Amiga feel)
		self.game.internal_surface.blit(cursor, (mx_internal, my_internal))

	def _draw_gameplay(self) -> None:
		"""Draw the standard gameplay frame (terrain, entities, UI)."""
		self.game.internal_surface.fill(settings.BLACK)
		self.game.internal_surface.blit(self.game.ui_image, (0, 0))

		# Display clicked button sprite if needed
		if self.game.last_button_click is not None:
			action, t0 = self.game.last_button_click
			show_dpad = False
			# Flash if continuous D-Pad scroll
			if self.game.mode_manager.dpad_held_direction == action:
				elapsed = time.time() - self.game.mode_manager.dpad_last_flash_time
				if elapsed < settings.BUTTON_FLASH_DURATION:
					show_dpad = True
				elif elapsed < self.game.mode_manager.dpad_repeat_delay:
					show_dpad = False
				else:
					show_dpad = True  # safety, should be re-triggered by update()
			else:
				# Normal display (single click)
				if (time.time() - t0) < self.game.mode_manager.dpad_repeat_delay:
					show_dpad = True
			if show_dpad:
				# ISO mapping for D-Pad sprite display
				dpad_iso_map = {
					'N': 'NW',
					'NE': 'N',
					'E': 'NE',
					'SE': 'E',
					'S': 'SE',
					'SW': 'S',
					'W': 'SW',
					'NW': 'W',
				}
				action_affiche = dpad_iso_map.get(action, action)
				idx = self.game.button_sprite_indices.get(action_affiche)
				if idx is not None and idx < len(self.game.button_sprites):
					# Afficher le sprite à la position du bouton
					shape = self.game.ui_panel.buttons.get(action)
					if shape:
						bcx, bcy = shape['c']
						sprite = self.game.button_sprites[idx]
						sw, sh = sprite.get_size()
						pos = (int(bcx - sw // 2) + settings.DPAD_BUTTON_POSITION_ADJ, int(bcy - sh // 2))
						self.game.internal_surface.blit(sprite, pos)

		self._draw_terrain()
		self._draw_houses()
		self._draw_peeps()
		self._draw_papal_marker()
		self._draw_shield_marker_if_active()
		self._draw_minimap()
		self._draw_aoe_preview()
		self._draw_cooldown_overlay()
		self._draw_shield_panel()
		self._draw_cursor()
		self._draw_scanlines()
		self._draw_faction_feedback()
		self._draw_mode_indicator()
		self._draw_mana_readout()
		self._draw_command_queue()
		self._draw_tooltip_or_hover_help()
		self._draw_debug_overlay()

	#============================================
	# Tooltip + hover help (M7)
	#============================================

	def _draw_tooltip_or_hover_help(self) -> None:
		"""Draw the button tooltip if hovering a button, else the hover-help panel."""
		mx, my = pygame.mouse.get_pos()
		# Translate from physical screen coords to internal-surface coords
		mx_int = mx // self.game.display_scale
		my_int = my // self.game.display_scale
		action = self.game.ui_panel.hit_test_button(mx_int, my_int)
		tooltip = self.game.ui_panel.tooltip_for(action)
		if tooltip:
			self._draw_text_panel(mx_int, my_int, [tooltip])
			return
		info = self.game.ui_panel.hover_info_at(mx_int, my_int, self.game)
		if info is None:
			return
		lines = self._format_hover_info(info)
		self._draw_text_panel(mx_int, my_int, lines)

	def _format_hover_info(self, info: dict) -> list:
		"""Translate a hover_info dict into a list of display lines."""
		kind = info['kind']
		if kind == 'terrain':
			return [f"Terrain ({info['r']},{info['c']})", f"Altitude: {info['altitude']}"]
		if kind == 'peep':
			return [
				f"Peep faction {info['faction']}",
				f"State: {info['state']}",
				f"Life: {info['life']:.0f}",
			]
		if kind == 'house':
			return [
				f"House faction {info['faction']}",
				f"Type: {info['house_type']}",
				f"Life: {info['life']:.0f}",
			]
		return [str(info)]

	def _draw_text_panel(self, mx: int, my: int, lines: list) -> None:
		"""Render a small translucent text panel near the cursor."""
		font = pygame.font.SysFont(None, 12)
		surfaces = [font.render(line, True, settings.WHITE) for line in lines]
		w = max(s.get_width() for s in surfaces) + 6
		h = sum(s.get_height() for s in surfaces) + 6
		# Place panel below-right of cursor; flip if it would clip
		surf_w, surf_h = self.game.internal_surface.get_size()
		px = mx + 8
		py = my + 8
		if px + w > surf_w:
			px = mx - w - 8
		if py + h > surf_h:
			py = my - h - 8
		px = max(0, px)
		py = max(0, py)
		bg = pygame.Surface((w, h), pygame.SRCALPHA)
		bg.fill((0, 0, 0, 180))
		self.game.internal_surface.blit(bg, (px, py))
		y = py + 3
		for s in surfaces:
			self.game.internal_surface.blit(s, (px + 3, y))
			y += s.get_height()

	#============================================
	# Command queue visualization (M7)
	#============================================

	def _draw_command_queue(self) -> None:
		"""Draw thin lines from each marching player peep to its target."""
		# Local imports to keep the renderer module's top-level imports lean
		import populous_game.peep_state as peep_state
		import populous_game.faction as faction
		cam_r, cam_c = self.game.camera.r, self.game.camera.c
		color = self.faction_color(faction.Faction.PLAYER)
		for p in self.game.peeps:
			if p.faction_id != faction.Faction.PLAYER:
				continue
			if p.state != peep_state.PeepState.MARCH:
				continue
			tx = getattr(p, 'target_x', None)
			ty = getattr(p, 'target_y', None)
			if tx is None or ty is None:
				continue
			# Peep position is in (x, y) world coords; convert via game_map
			# world_to_screen takes (r, c, altitude) -- peep.x/y already are
			# the (x, y) coords used directly by the peep draw routine.
			start = self._peep_screen_pos(p, cam_r, cam_c)
			end = self._world_xy_to_screen(tx, ty, cam_r, cam_c)
			if start is None or end is None:
				continue
			pygame.draw.line(self.game.internal_surface, color, start, end, 1)

	def _peep_screen_pos(self, peep, cam_r: float, cam_c: float) -> tuple | None:
		"""Get the screen-space center of a peep sprite, or None if off-screen."""
		# Peep coords map: row = peep.y, col = peep.x in tile space; altitude
		# under the peep is read from terrain corners.
		alt = self.game.game_map.get_corner_altitude(int(peep.y), int(peep.x))
		if alt < 0:
			return None
		sx, sy = self.game.game_map.world_to_screen(peep.y, peep.x, alt, cam_r, cam_c)
		return (sx, sy)

	def _world_xy_to_screen(self, x: float, y: float, cam_r: float, cam_c: float) -> tuple | None:
		"""Convert peep target_x/target_y to screen coords, or None if invalid."""
		alt = self.game.game_map.get_corner_altitude(int(y), int(x))
		if alt < 0:
			return None
		sx, sy = self.game.game_map.world_to_screen(y, x, alt, cam_r, cam_c)
		return (sx, sy)

	#============================================

	def _draw_menu(self) -> None:
		"""Draw main menu screen."""
		self.game.internal_surface.fill(settings.BLACK)

		# Title text
		title_font = pygame.font.SysFont("consolas", 48, bold=True)
		title_text = title_font.render("POPULOUS", True, settings.WHITE)
		title_rect = title_text.get_rect(center=(self.game.internal_surface.get_width() // 2, 80))
		self.game.internal_surface.blit(title_text, title_rect)

		# Menu options
		option_font = pygame.font.SysFont("consolas", 24)
		options = ["New game", "Continue", "Quit"]
		option_y = 180
		for i, option in enumerate(options):
			color = settings.WHITE
			text = option_font.render(option, True, color)
			text_rect = text.get_rect(center=(self.game.internal_surface.get_width() // 2, option_y + i * 50))
			self.game.internal_surface.blit(text, text_rect)

	def _draw_pause_overlay(self) -> None:
		"""Draw pause overlay on top of frozen gameplay."""
		# Semi-transparent overlay
		overlay = pygame.Surface(self.game.internal_surface.get_size(), pygame.SRCALPHA)
		overlay.fill((0, 0, 0, 128))
		self.game.internal_surface.blit(overlay, (0, 0))

		# Pause text
		pause_font = pygame.font.SysFont("consolas", 48, bold=True)
		pause_text = pause_font.render("PAUSED", True, settings.WHITE)
		pause_rect = pause_text.get_rect(center=(self.game.internal_surface.get_width() // 2, self.game.internal_surface.get_height() // 2))
		self.game.internal_surface.blit(pause_text, pause_rect)

	def _draw_gameover(self) -> None:
		"""Draw game-over screen with victory or defeat message."""
		# Semi-transparent overlay
		overlay = pygame.Surface(self.game.internal_surface.get_size(), pygame.SRCALPHA)
		overlay.fill((0, 0, 0, 200))
		self.game.internal_surface.blit(overlay, (0, 0))

		# Game over status
		result_font = pygame.font.SysFont("consolas", 48, bold=True)
		result_text = self.game.app_state.gameover_result.upper() if self.game.app_state.gameover_result else "GAME OVER"
		result_color = settings.GREEN if self.game.app_state.gameover_result == 'win' else settings.RED
		result_surf = result_font.render(result_text, True, result_color)
		result_rect = result_surf.get_rect(center=(self.game.internal_surface.get_width() // 2, self.game.internal_surface.get_height() // 2 - 50))
		self.game.internal_surface.blit(result_surf, result_rect)

		# Prompt to continue
		prompt_font = pygame.font.SysFont("consolas", 20)
		prompt_text = prompt_font.render("Press Enter to restart or Q for menu", True, settings.WHITE)
		prompt_rect = prompt_text.get_rect(center=(self.game.internal_surface.get_width() // 2, self.game.internal_surface.get_height() // 2 + 50))
		self.game.internal_surface.blit(prompt_text, prompt_rect)

	def _draw_terrain(self) -> None:
		"""Draw terrain tiles."""
		cam_r, cam_c = self.game.camera.r, self.game.camera.c
		self.game.game_map.draw(self.game.internal_surface, cam_r, cam_c)

	def _draw_houses(self) -> None:
		"""Draw houses and their health displays."""
		cam_r, cam_c = self.game.camera.r, self.game.camera.c
		debug_font = pygame.font.SysFont("consolas", settings.DEBUG_FONT_SIZE, bold=True) if self.game.show_debug else None
		self.game.game_map.draw_houses(self.game.internal_surface, cam_r, cam_c, show_debug=self.game.show_debug, debug_font=debug_font)

	def _draw_peeps(self) -> None:
		"""Draw peeps and their debug info."""
		cam_r, cam_c = self.game.camera.r, self.game.camera.c
		debug_font = pygame.font.SysFont("consolas", settings.DEBUG_FONT_SIZE, bold=True) if self.game.show_debug else None
		start_r, end_r, start_c, end_c = self.game.game_map.get_visible_bounds(cam_r, cam_c)

		for p in self.game.peeps:
			if p.y < start_r or p.y >= end_r or p.x < start_c or p.x >= end_c:
				continue
			p.draw(self.game.internal_surface, cam_r, cam_c, show_debug=self.game.show_debug, debug_font=debug_font)

	def _draw_papal_marker(self) -> None:
		"""Draw papal marker (tile 5,0) after houses and peeps."""
		cam_r, cam_c = self.game.camera.r, self.game.camera.c
		papal_tile = self.game.game_map.tile_surfaces.get((5, 0))
		if papal_tile and self.game.mode_manager.papal_position is not None:
			r, c = self.game.mode_manager.papal_position
			start_r, end_r, start_c, end_c = self.game.game_map.get_visible_bounds(cam_r, cam_c)
			if start_r <= r < end_r and start_c <= c < end_c:
				alt = self.game.game_map.get_corner_altitude(r, c)
				sx, sy = self.game.game_map.world_to_screen(r, c, alt, cam_r, cam_c)
				blit_x = sx - settings.TILE_HALF_W
				blit_y = sy
				self.game.internal_surface.blit(papal_tile, (blit_x, blit_y))

	def _draw_shield_marker_if_active(self) -> None:
		"""Draw shield marker on selected entity if viewing."""
		cam_r, cam_c = self.game.camera.r, self.game.camera.c
		if self.game.selection.who is not None and self.game.selection.kind is not None:
			# Verify entity is in visible 8x8 camera zone
			r = getattr(self.game.selection.who, 'y', getattr(self.game.selection.who, 'r', -1))
			c = getattr(self.game.selection.who, 'x', getattr(self.game.selection.who, 'c', -1))
			start_r, end_r, start_c, end_c = self.game.game_map.get_visible_bounds(cam_r, cam_c)
			if start_r <= r < end_r and start_c <= c < end_c:
				self.game.ui_panel.draw_shield_marker(self.game.internal_surface, self.game.selection.who, self.game.selection.kind, cam_r, cam_c, self.game.game_map)

	def _draw_cursor(self) -> None:
		"""Draw cursor (star) on nearest terrain corner under mouse."""
		cam_r, cam_c = self.game.camera.r, self.game.camera.c
		mouse_x, mouse_y = pygame.mouse.get_pos()
		mouse_x //= self.game.display_scale
		mouse_y //= self.game.display_scale

		# Display star only if mouse is on terrain
		if self.game.view_rect.collidepoint(mouse_x, mouse_y):
			vp_x = mouse_x - self.game.view_rect.x
			vp_y = mouse_y - self.game.view_rect.y
			grid_r, grid_c = self.game.game_map.screen_to_nearest_corner(
				vp_x, vp_y, cam_r, cam_c
			)

			# Restrict star to visible bounds
			start_r, end_r, start_c, end_c = self.game.game_map.get_visible_bounds(cam_r, cam_c)
			if start_r <= grid_r < end_r and start_c <= grid_c < end_c:
				alt = self.game.game_map.get_corner_altitude(grid_r, grid_c)
				sx, sy = self.game.game_map.world_to_screen(grid_r, grid_c, alt, cam_r, cam_c)

				# Draw a simple star (6-pointed)
				star_tile = self.game.game_map.tile_surfaces.get((1, 0))
				if star_tile:
					self.game.internal_surface.blit(star_tile, (sx - settings.TILE_HALF_W, sy))

	def _draw_minimap(self) -> None:
		"""Draw minimap."""
		self.game.minimap.draw(self.game.internal_surface, self.game.game_map, self.game.camera, self.game.peeps)

	def _draw_scanlines(self) -> None:
		"""Draw scanline effect if enabled."""
		if self.game.show_scanlines and self.game.scanline_surface:
			self.game.internal_surface.blit(self.game.scanline_surface, (0, 0), special_flags=pygame.BLEND_MULT)

	def _draw_shield_panel(self) -> None:
		"""Draw shield panel (coat-of-arms) on internal surface."""
		self.game.ui_panel.draw_shield_panel(
			self.game.internal_surface,
			self.game.selection,
			self.game.weapon_sprites,
			self.game.weapon_sprite_indices,
			self.game.game_map,
			self.game.font
		)

	def _draw_faction_feedback(self) -> None:
		"""Draw faction color indicators on peeps and houses."""
		cam_r, cam_c = self.game.camera.r, self.game.camera.c
		start_r, end_r, start_c, end_c = self.game.game_map.get_visible_bounds(cam_r, cam_c)

		# Draw faction color indicator below each peep
		for p in self.game.peeps:
			if p.y < start_r or p.y >= end_r or p.x < start_c or p.x >= end_c:
				continue
			gr, gc = int(p.y), int(p.x)
			fx = p.x - gc
			fy = p.y - gr
			a_nw = self.game.game_map.get_corner_altitude(gr,     gc)
			a_ne = self.game.game_map.get_corner_altitude(gr,     gc + 1)
			a_sw = self.game.game_map.get_corner_altitude(gr + 1, gc)
			a_se = self.game.game_map.get_corner_altitude(gr + 1, gc + 1)
			alt = (1 - fx) * (1 - fy) * a_nw + fx * (1 - fy) * a_ne \
				+ (1 - fx) * fy       * a_sw + fx * fy       * a_se
			sx, sy = self.game.game_map.world_to_screen(p.y, p.x, alt, cam_r, cam_c)
			ground_y = sy + settings.TILE_HALF_H
			faction_color = self.faction_color(p.faction_id)
			pygame.draw.rect(self.game.internal_surface, faction_color, (sx - 1, ground_y + 8, 3, 3))

		# Draw faction color indicator below each house
		for house in self.game.game_map.houses:
			if house.r < start_r or house.r >= end_r or house.c < start_c or house.c >= end_c:
				continue
			alt = self.game.game_map.get_corner_altitude(house.r, house.c)
			sx, sy = self.game.game_map.world_to_screen(house.r, house.c, alt, cam_r, cam_c)
			ground_y = sy + settings.TILE_HALF_H
			faction_color = self.faction_color(house.faction_id)
			pygame.draw.rect(self.game.internal_surface, faction_color, (sx - 1, ground_y + 12, 3, 3))

	def _draw_mode_indicator(self) -> None:
		"""Draw mode indicator text in a corner (PAPAL, SHIELD, or IDLE)."""
		if not self.game.app_state.is_playing():
			return
		mode_text = "IDLE"
		if self.game.mode_manager.papal_mode:
			mode_text = "PAPAL"
		elif self.game.mode_manager.shield_mode:
			mode_text = "SHIELD"
		mode_font = pygame.font.SysFont("consolas", 14, bold=True)
		mode_surf = mode_font.render(mode_text, True, settings.WHITE)
		self.game.internal_surface.blit(mode_surf, (5, 5))

	def _draw_mana_readout(self) -> None:
		"""Draw mana readout in HUD."""
		if not self.game.app_state.is_playing():
			return
		mana = self.game.mana_pool.get_mana(self.game.player_faction_id())
		mana_text = f"MANA {int(mana)}"
		hud_font = pygame.font.SysFont("consolas", settings.HUD_FONT_SIZE, bold=True)
		mana_surf = hud_font.render(mana_text, True, settings.WHITE)
		# Position below or near mode indicator
		self.game.internal_surface.blit(mana_surf, (5, 25))

	def _draw_debug_overlay(self) -> None:
		"""Draw debug overlay with FPS and other info."""
		# This can be extended later for more debug visualization
		pass

	def _draw_aoe_preview(self) -> None:
		"""Draw AOE preview overlay when a power is pending targeting."""
		if not self.game.mode_manager.pending_power:
			return

		# Get mouse position
		mouse_x, mouse_y = pygame.mouse.get_pos()
		mouse_x //= self.game.display_scale
		mouse_y //= self.game.display_scale

		# Check if mouse is on terrain
		if not self.game.view_rect.collidepoint(mouse_x, mouse_y):
			return

		# Convert to viewport coordinates
		vp_x = mouse_x - self.game.view_rect.x
		vp_y = mouse_y - self.game.view_rect.y
		cam_r, cam_c = self.game.camera.r, self.game.camera.c

		# Get target cell
		grid_r, grid_c = self.game.game_map.screen_to_nearest_corner(
			vp_x, vp_y, cam_r, cam_c
		)

		# Get power specs
		import populous_game.powers as powers_module
		power_name = self.game.mode_manager.pending_power
		spec = powers_module.POWERS.get(power_name)
		if not spec or spec.aoe_radius == 0:
			# No AOE for this power
			return

		# Get affected cells
		affected = powers_module._cells_in_radius(grid_r, grid_c, spec.aoe_radius)

		# Get visible bounds
		start_r, end_r, start_c, end_c = self.game.game_map.get_visible_bounds(cam_r, cam_c)

		# Draw overlays on affected cells
		# Use green color for AOE preview
		aoe_color = settings.GREEN
		aoe_alpha = 80

		for (r, c) in affected:
			# Only draw if visible
			if r < start_r or r >= end_r or c < start_c or c >= end_c:
				continue

			# Get altitude at corner
			alt = self.game.game_map.get_corner_altitude(r, c)

			# Convert to screen position
			sx, sy = self.game.game_map.world_to_screen(r, c, alt, cam_r, cam_c)

			# Draw translucent colored rect at cell position
			# Each cell is roughly a diamond; draw a small rect at the center
			cell_size = 16  # approximate
			rect_w = cell_size
			rect_h = cell_size
			rect_x = int(sx - rect_w // 2)
			rect_y = int(sy - rect_h // 2)

			# Create overlay surface for this cell
			cell_overlay = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
			cell_overlay.fill((aoe_color[0], aoe_color[1], aoe_color[2], aoe_alpha))
			self.game.internal_surface.blit(cell_overlay, (rect_x, rect_y))

	def _draw_cooldown_overlay(self) -> None:
		"""Draw cooldown overlays on power buttons where cooldown is active."""
		# Map power names to button action keys
		power_to_button = {
			'volcano': '_do_volcano',
			'flood': '_do_flood',
			'quake': '_do_quake',
			'swamp': '_do_swamp',
			'papal': '_do_papal',
			'knight': '_do_knight',
		}

		# Import powers to get max cooldowns
		import populous_game.powers as powers_module

		for power_name, seconds_remaining in self.game.power_manager.cooldowns.items():
			if seconds_remaining <= 0.0:
				continue

			# Get button action key
			button_action = power_to_button.get(power_name)
			if not button_action:
				continue

			# Get button shape from ui_panel
			button_shape = self.game.ui_panel.buttons.get(button_action)
			if not button_shape:
				continue

			# Get button position and size
			bcx, bcy = button_shape['c']
			bhw, bhh = button_shape['hw'], button_shape['hh']

			# Calculate alpha based on cooldown remaining / max cooldown
			spec = powers_module.POWERS.get(power_name)
			if spec and spec.cooldown > 0.0:
				alpha = int(200 * (seconds_remaining / spec.cooldown))
				alpha = max(0, min(255, alpha))
			else:
				alpha = 100

			# Draw a diamond-shaped overlay matching the button hit-test
			# region. The previous rectangular overlay (bhw*2 x bhh*2)
			# bled into adjacent iso buttons because the button diamonds
			# tile edge-to-edge; the corners of one button's bounding box
			# overlap the centers of its four neighbors.
			overlay_w = int(bhw * 2)
			overlay_h = int(bhh * 2)
			overlay = pygame.Surface((overlay_w, overlay_h), pygame.SRCALPHA)
			diamond_pts = [
				(overlay_w // 2, 0),                  # top
				(overlay_w, overlay_h // 2),          # right
				(overlay_w // 2, overlay_h),          # bottom
				(0, overlay_h // 2),                  # left
			]
			pygame.draw.polygon(overlay, (0, 0, 0, alpha), diamond_pts)

			overlay_x = int(bcx - overlay_w // 2)
			overlay_y = int(bcy - overlay_h // 2)
			self.game.internal_surface.blit(overlay, (overlay_x, overlay_y))

	def _draw_confirm_dialog(self) -> None:
		"""Draw confirmation dialog if one is currently active."""
		if not self.game.app_state.has_confirm_dialog():
			return

		surface_w = self.game.internal_surface.get_width()
		surface_h = self.game.internal_surface.get_height()

		# Create semi-transparent panel (~60% width, ~25% height)
		panel_w = int(surface_w * 0.6)
		panel_h = int(surface_h * 0.25)
		panel_x = (surface_w - panel_w) // 2
		panel_y = (surface_h - panel_h) // 2

		# Draw semi-transparent black background
		overlay = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
		overlay.fill((0, 0, 0, 200))
		self.game.internal_surface.blit(overlay, (panel_x, panel_y))

		# Draw border
		pygame.draw.rect(self.game.internal_surface, settings.WHITE,
			(panel_x, panel_y, panel_w, panel_h), 2)

		# Render message text
		dialog_font = pygame.font.SysFont("consolas", settings.HUD_FONT_SIZE, bold=True)
		message = self.game.app_state.confirm_dialog['message']
		message_surf = dialog_font.render(message, True, settings.WHITE)
		message_rect = message_surf.get_rect(
			center=(surface_w // 2, panel_y + panel_h // 3)
		)
		self.game.internal_surface.blit(message_surf, message_rect)

		# Render Y/N prompt
		prompt_font = pygame.font.SysFont("consolas", settings.HUD_FONT_SIZE)
		prompt_text = "Y / N"
		prompt_surf = prompt_font.render(prompt_text, True, settings.WHITE)
		prompt_rect = prompt_surf.get_rect(
			center=(surface_w // 2, panel_y + panel_h * 2 // 3)
		)
		self.game.internal_surface.blit(prompt_surf, prompt_rect)
