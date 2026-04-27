"""Input handling for the game (keyboard, mouse, UI interactions)."""

import pygame
import time
import populous_game.powers as powers
import populous_game.settings as settings


class InputController:
	"""Manages input events and routes them to the game."""

	def __init__(self, game):
		"""Initialize with a reference to the Game instance."""
		self.game = game
		# Drag-paint state: while a mouse button is held over the viewport,
		# the controller repeatedly raises (LMB) or lowers (RMB) terrain at
		# the cursor at DRAG_PAINT_INTERVAL pacing.
		self._drag_paint_button: int | None = None
		self._drag_paint_last_time: float = 0.0

	def _handle_ui_click(self, action, held=False):
		"""Handle a UI button click (compass, powers)."""
		self.game.last_button_click = (action, time.time())
		# Cancel any special mode if another action is selected
		if action != '_do_papal':
			self.game.mode_manager.papal_mode = False
		if action != '_do_shield':
			self.game.mode_manager.shield_mode = False
		if action in ['N', 'S', 'E', 'W', 'NW', 'NE', 'SW', 'SE']:
			if held:
				self.game.mode_manager.dpad_held_direction = action
				self.game.mode_manager.dpad_held_timer = 0.0  # immediate scroll
				self.game.mode_manager.dpad_last_flash_time = time.time()
			self.game.move_camera_direction(action)
		elif action == '_do_papal':
			self.game.mode_manager.papal_mode = True
		elif action == '_do_shield':
			self.game.mode_manager.shield_mode = True
		elif action == '_do_volcano':
			# Set pending power for targeting
			self.game.mode_manager.pending_power = 'volcano'
		elif action == '_do_flood':
			self.game.mode_manager.pending_power = 'flood'
		elif action == '_do_quake':
			self.game.mode_manager.pending_power = 'quake'
		elif action == '_do_swamp':
			self.game.mode_manager.pending_power = 'swamp'
		elif action == '_do_knight':
			# Knight doesn't need a target; activate immediately
			self.game.power_manager.activate('knight', None)
		elif action == '_raise_terrain':
			self.game.mode_manager.pending_power = None
		# Stub remaining commands for future implementation
		elif action in ['_find_battle', '_find_shield', '_find_papal', '_find_knight',
			'_go_papal', '_go_build', '_go_assemble', '_go_fight', '_battle_over']:
			pass  # Stubbed for M7

	def poll(self) -> bool:
		"""Poll input events. Return False if user requested quit."""
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				return False
			elif event.type == pygame.KEYDOWN:
				# Confirm dialog input takes priority
				if self.game.app_state.has_confirm_dialog():
					if event.key == pygame.K_y or event.key == pygame.K_RETURN:
						self.game.app_state.confirm()
						return True
					elif event.key == pygame.K_n or event.key == pygame.K_ESCAPE:
						self.game.app_state.cancel()
						return True
					# Any other key is ignored while confirm dialog open
					continue

				# Handle state machine transitions
				if self.game.app_state.is_menu():
					if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
						# Start new game: raise the whole map above water before
						# spawning so peeps have land to walk on. Without this
						# the default all-zeros heightmap leaves the viewport
						# entirely under water.
						self.game.app_state.transition_to(self.game.app_state.PLAYING)
						self.game.game_map.set_all_altitude(3)
						self.game.spawn_initial_peeps(10)
						self.game.spawn_enemy_peeps(10)
						return True
					elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
						return False
				elif self.game.app_state.is_playing():
					if event.key == pygame.K_ESCAPE:
						# Pause game
						self.game.app_state.transition_to(self.game.app_state.PAUSED)
						return True
				elif self.game.app_state.is_paused():
					if event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
						# Resume game
						self.game.app_state.transition_to(self.game.app_state.PLAYING)
						return True
					elif event.key == pygame.K_q:
						# Return to menu
						self.game._reset_game()
						self.game.app_state.transition_to(self.game.app_state.MENU)
						return True
				elif self.game.app_state.is_gameover():
					if event.key == pygame.K_RETURN:
						# Return to menu (can restart from there)
						self.game._reset_game()
						self.game.app_state.transition_to(self.game.app_state.MENU)
						return True
					elif event.key == pygame.K_q:
						# Also return to menu
						self.game._reset_game()
						self.game.app_state.transition_to(self.game.app_state.MENU)
						return True

				# Debug keys (only in PLAYING state)
				if self.game.app_state.is_playing():
					if event.key == pygame.K_F11:
						# Win (debug)
						self.game.app_state.gameover_result = 'win'
						self.game.app_state.transition_to(self.game.app_state.GAMEOVER)
						return True
					elif event.key == pygame.K_F10:
						# Lose (debug)
						self.game.app_state.gameover_result = 'lose'
						self.game.app_state.transition_to(self.game.app_state.GAMEOVER)
						return True

				# Power hotkeys (only in PLAYING state, not while confirm dialog open)
				if self.game.app_state.is_playing() and not self.game.app_state.has_confirm_dialog():
					# Build a lookup: key name -> power name
					power_actions = {}
					for power_name in ['papal', 'volcano', 'flood', 'quake', 'swamp', 'knight']:
						key_name = self.game.keymap.get(f'power_{power_name}')
						if key_name:
							power_actions[key_name] = power_name

					# Check if the pressed key matches any power hotkey
					pressed_key_name = pygame.key.name(event.key).lower()
					if pressed_key_name in power_actions:
						power_name = power_actions[pressed_key_name]
						# Handle papal and knight (activate immediately, no targeting)
						if power_name == 'knight':
							self.game.power_manager.activate('knight', None)
							return True
						elif power_name == 'papal':
							target = self.game.mode_manager.papal_position if self.game.mode_manager.papal_position else None
							self.game.power_manager.activate('papal', target)
							return True
						else:
							# Volcano, flood, quake, swamp: set pending power for targeting
							self.game.mode_manager.pending_power = power_name
							return True

					# Fast-forward toggle (backtick by default)
					fast_forward_key = self.game.keymap.get('fast_forward', 'backquote')
					if pressed_key_name == fast_forward_key:
						# Toggle between 1.0x and 4.0x
						if self.game.app_state.time_scale == 1.0:
							self.game.app_state.time_scale = 4.0
						else:
							self.game.app_state.time_scale = 1.0
						return True

				# Regular gameplay input (only in PLAYING state)
				if not self.game.app_state.is_playing():
					continue

				if event.key == pygame.K_ESCAPE:
					return False
				elif event.key == pygame.K_TAB:
					self.game.display_scale = (self.game.display_scale % 4) + 1
					self.game.screen = pygame.display.set_mode((self.game.base_size[0] * self.game.display_scale, self.game.base_size[1] * self.game.display_scale))
					self.game._update_scanline_surface()
				elif event.key == pygame.K_F1:
					self.game.peeps.clear()
				elif event.key == pygame.K_F2:
					self.game.game_map.houses.clear()
				elif event.key == pygame.K_F3:
					self.game.peeps.clear()
					self.game.game_map.houses.clear()
					self.game.game_map.randomize()
					self.game.spawn_initial_peeps(10)
				elif event.key == pygame.K_F4:
					self.game.game_map.set_all_altitude(1)
				elif event.key == pygame.K_F12:
					self.game.show_scanlines = not self.game.show_scanlines
				elif hasattr(event, 'unicode') and event.unicode == '§':
					self.game.show_debug = not self.game.show_debug
			elif event.type == pygame.MOUSEBUTTONDOWN:
				# Use event.pos (the position the user actually clicked at)
				# rather than pygame.mouse.get_pos(). This lets headless
				# scripted tests post real click positions and avoids a
				# subtle race where the cursor can move between the click
				# being queued and us polling it.
				mx, my = event.pos
				mx //= self.game.display_scale
				my //= self.game.display_scale
				# Check interaction minimap (if clicked on, no other action)
				if event.button == 1 and self.game.minimap.handle_click(mx, my, self.game.camera):
					continue
				# Check clicks on UI (compass and powers)
				ui_clicked = False
				if event.button == 1:
					action = self.game.ui_panel.hit_test_button(mx, my)
					if action is not None:
						self._handle_ui_click(action, held=True)
						ui_clicked = True
				if ui_clicked:
					continue
				# Shield mode: left-click on entity = apply coat-of-arms
				if self.game.mode_manager.shield_mode:
					if event.button == 1:
						entity, kind = self.game.ui_panel.select_at(mx, my, self.game.peeps, self.game.game_map.houses, self.game.camera, self.game.game_map)
						if entity is not None:
							self.game.selection.who = entity
							self.game.selection.kind = kind
							self.game.mode_manager.shield_target = entity
							self.game.mode_manager.shield_mode = False
						return True
					elif event.button == 3:
						# Cancel shield mode and return to raise_terrain
						self.game.mode_manager.shield_mode = False
						self._handle_ui_click('_raise_terrain', held=False)
						return True
				# Right-click on entity: (disabled, replaced by _do_shield)
				# entity, kind = self.game.ui_panel.select_at(mx, my, self.game.peeps, self.game.game_map.houses, self.game.camera, self.game.game_map)
				# if event.button == 3 and entity is not None:
				#     continue
				# Mouse clicks (allowed everywhere since viewport is fullscreen)
				if self.game.view_rect.collidepoint(mx, my):
					vp_x = mx - self.game.view_rect.x
					vp_y = my - self.game.view_rect.y
					r, c = self.game.game_map.screen_to_nearest_corner(
						vp_x, vp_y, self.game.camera.r, self.game.camera.c
					)
					# Verify click is in the visible 8x8 camera zone
					start_r, end_r, start_c, end_c = self.game.game_map.get_visible_bounds(self.game.camera.r, self.game.camera.c)
					if start_r <= r <= end_r and start_c <= c <= end_c:
						if self.game.mode_manager.pending_power:
							if event.button == 1:
								# Activate pending power at target
								power_name = self.game.mode_manager.pending_power
								power_spec = powers.POWERS.get(power_name)
								# Check if power requires confirmation
								if power_spec and power_spec.requires_confirm:
									# Open confirm dialog instead of activating immediately
									def do_activate():
										self.game.power_manager.activate(power_name, (r, c))
									self.game.app_state.request_confirm(
										f"Cast {power_name}? (Y/N)",
										on_confirm=do_activate,
										on_cancel=lambda: None
									)
								else:
									# Activate immediately
									self.game.power_manager.activate(power_name, (r, c))
								self.game.mode_manager.pending_power = None
							elif event.button == 3:
								# Cancel pending power
								self.game.mode_manager.pending_power = None
								self._handle_ui_click('_raise_terrain', held=False)
							return True
						elif self.game.mode_manager.papal_mode:
							if event.button == 1:
								# Place/move papal (only one) on the NW case
								self.game.mode_manager.papal_position = (max(r - 1, 0), max(c - 1, 0))
								self.game.mode_manager.papal_mode = False  # Deactivate mode after click
							elif event.button == 3:
								# Cancel papal mode and return to raise_terrain
								self.game.mode_manager.papal_mode = False
								self._handle_ui_click('_raise_terrain', held=False)
							return True
						elif not self.game.mode_manager.papal_mode and not self.game.mode_manager.shield_mode:
							if event.button == 1:
								self.game.game_map.raise_corner(r, c)
								self._drag_paint_button = 1
								self._drag_paint_last_time = time.time()
							elif event.button == 3:
								self.game.game_map.lower_corner(r, c)
								self._drag_paint_button = 3
								self._drag_paint_last_time = time.time()
			elif event.type == pygame.MOUSEBUTTONUP:
				# Click release: stop continuous scroll and drag-paint
				self.game.mode_manager.dpad_held_direction = None
				self._drag_paint_button = None
			elif event.type == pygame.MOUSEMOTION:
				self._handle_drag_paint(event)
			elif event.type == pygame.MOUSEWHEEL:
				self._handle_mouse_wheel(event)
		return True

	#============================================
	# M7: drag-to-paint terrain + mouse-wheel minimap zoom
	#============================================

	def _handle_drag_paint(self, event) -> None:
		"""Continue raising/lowering terrain while a mouse button is held."""
		if self._drag_paint_button is None:
			return
		if self.game.app_state.is_simulation_paused():
			return
		now = time.time()
		if now - self._drag_paint_last_time < settings.DRAG_PAINT_INTERVAL:
			return
		self._drag_paint_last_time = now
		mx, my = event.pos
		mx //= self.game.display_scale
		my //= self.game.display_scale
		if not self.game.view_rect.collidepoint(mx, my):
			return
		vp_x = mx - self.game.view_rect.x
		vp_y = my - self.game.view_rect.y
		r, c = self.game.game_map.screen_to_nearest_corner(
			vp_x, vp_y, self.game.camera.r, self.game.camera.c
		)
		start_r, end_r, start_c, end_c = self.game.game_map.get_visible_bounds(
			self.game.camera.r, self.game.camera.c
		)
		if not (start_r <= r <= end_r and start_c <= c <= end_c):
			return
		if (self.game.mode_manager.pending_power
			or self.game.mode_manager.papal_mode
			or self.game.mode_manager.shield_mode):
			return
		if self._drag_paint_button == 1:
			self.game.game_map.raise_corner(r, c)
		elif self._drag_paint_button == 3:
			self.game.game_map.lower_corner(r, c)

	def _handle_mouse_wheel(self, event) -> None:
		"""Adjust minimap zoom when the wheel scrolls over the minimap."""
		mx, my = pygame.mouse.get_pos()
		mx //= self.game.display_scale
		my //= self.game.display_scale
		if not self.game.minimap.rect.collidepoint(mx, my):
			return
		step = settings.MINIMAP_ZOOM_STEP * float(event.y)
		self.game.minimap.set_zoom(self.game.minimap.zoom + step)
