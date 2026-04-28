"""Input handling for the game (keyboard, mouse, UI interactions)."""

import pygame
import time
import populous_game.powers as powers
import populous_game.settings as settings
import populous_game.selection as selection_module
import populous_game.peep_state as peep_state
import populous_game.faction as faction


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
		# Cursor indices for cycling find-buttons. Each remembers the
		# peep index of the last hit so a repeat click steps to the next.
		self._find_battle_cursor: int = -1
		self._find_knight_cursor: int = -1
		# Transient tooltip queue surfaced by find/go buttons when there
		# is no valid target. The renderer can read this list; tests can
		# assert it grew. Bounded length so old messages get evicted.
		self.tooltip_messages: list = []

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
			# Knight doesn't need a target; activate immediately. On
			# failure (insufficient mana, no candidate), surface a
			# tooltip so the click is never a silent no-op.
			result = self.game.power_manager.activate('knight', None)
			if not result.success:
				self._queue_tooltip(result.message or 'Knight unavailable')
		elif action == '_raise_terrain':
			self.game.mode_manager.pending_power = None
		elif action == '_sleep':
			self._handle_sleep_button()
		elif action == '_music':
			self.game.audio_manager.toggle_music()
		elif action == '_fx':
			self.game.audio_manager.toggle_sfx_mute()
		elif action == '_find_battle':
			self._handle_find_battle()
		elif action == '_find_papal':
			self._handle_find_papal(prefer_leader=True)
		elif action == '_find_knight':
			self._handle_find_knight()
		elif action == '_go_papal':
			self._handle_go_papal()
		elif action == '_go_build':
			self._handle_go_build()
		elif action == '_go_assemble':
			self._handle_go_assemble()
		elif action == '_go_fight':
			self._handle_go_fight()

	#============================================
	# Sleep button: toggle simulation pause.
	#============================================

	def _handle_sleep_button(self):
		"""Toggle pause via the existing PLAYING<->PAUSED transitions."""
		st = self.game.app_state
		if st.is_playing():
			st.transition_to(st.PAUSED)
		elif st.is_paused():
			st.transition_to(st.PLAYING)
		# In MENU / GAMEOVER, the sleep button is a no-op.

	#============================================
	# Find buttons: jump the camera onto a target. No-target -> tooltip.
	#============================================

	def _queue_tooltip(self, message: str) -> None:
		"""Append a transient user-facing message and play ui_click."""
		self.tooltip_messages.append((message, time.time()))
		# Cap the queue so it does not grow unbounded.
		if len(self.tooltip_messages) > 8:
			self.tooltip_messages = self.tooltip_messages[-8:]
		self.game.audio_manager.play_sfx('ui_click')

	def _handle_find_battle(self):
		"""Cycle camera through peeps in FIGHT state."""
		result = selection_module.find_next_battle(self.game, after_index=self._find_battle_cursor)
		if result is None:
			self._queue_tooltip('No active battle')
			return
		idx, r, c = result
		self._find_battle_cursor = idx
		self.game.camera.center_on(r, c)

	def _handle_find_papal(self, prefer_leader: bool = True):
		"""Jump camera to the papal target (leader if any, else magnet)."""
		coord = selection_module.find_papal_target(self.game, prefer_leader=prefer_leader)
		if coord is None:
			self._queue_tooltip('No papal target')
			return
		r, c = coord
		self.game.camera.center_on(r, c)

	def _handle_find_knight(self):
		"""Cycle camera through player knights."""
		result = selection_module.find_next_knight(self.game, after_index=self._find_knight_cursor)
		if result is None:
			self._queue_tooltip('No knight')
			return
		idx, r, c = result
		self._find_knight_cursor = idx
		self.game.camera.center_on(r, c)

	#============================================
	# Go buttons: bulk peep behavior orders. Existing transitions only.
	#============================================

	def _player_peeps(self):
		"""Iterate live player peeps (helper for the bulk go-handlers)."""
		for p in self.game.peeps:
			if p.dead or p.state == peep_state.PeepState.DEAD:
				continue
			if p.faction_id != faction.Faction.PLAYER:
				continue
			yield p

	def _try_transition(self, p, new_state: str) -> bool:
		"""Try a peep state transition; return True iff it fired."""
		allowed = p._ALLOWED_TRANSITIONS.get(p.state, set())
		if new_state in allowed:
			p.transition(new_state)
			return True
		return False

	def _handle_go_papal(self):
		"""Walkers march toward the papal magnet, where the matrix permits."""
		coord = self.game.mode_manager.papal_position
		if coord is None:
			self._queue_tooltip('No papal target')
			return
		pr, pc = coord
		moved = 0
		for p in self._player_peeps():
			p.target_x = float(pc)
			p.target_y = float(pr)
			if self._try_transition(p, peep_state.PeepState.MARCH):
				moved += 1
		if moved == 0:
			self._queue_tooltip('No peep can march now')

	def _handle_go_build(self):
		"""Walkers seek flat land to build, where the matrix permits."""
		moved = 0
		for p in self._player_peeps():
			if self._try_transition(p, peep_state.PeepState.SEEK_FLAT):
				moved += 1
		if moved == 0:
			self._queue_tooltip('No peep can settle now')

	def _handle_go_assemble(self):
		"""Walkers join forces (gather together), where the matrix permits."""
		moved = 0
		for p in self._player_peeps():
			if self._try_transition(p, peep_state.PeepState.JOIN_FORCES):
				moved += 1
		if moved == 0:
			self._queue_tooltip('No peep can gather now')

	def _handle_go_fight(self):
		"""Walkers march to the nearest enemy, where the matrix permits."""
		moved = 0
		for p in self._player_peeps():
			target = selection_module.find_nearest_enemy(self.game, int(p.y), int(p.x))
			if target is None:
				continue
			tr, tc = target
			p.target_x = float(tc)
			p.target_y = float(tr)
			if self._try_transition(p, peep_state.PeepState.MARCH):
				moved += 1
		if moved == 0:
			self._queue_tooltip('No enemy in range')

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
					# Menu hotkeys: N (new game), ENTER / SPACE (legacy
					# start aliases). Q / ESC quit. Any left-click also
					# starts a new game (see MOUSEBUTTONDOWN handler).
					if event.key in (pygame.K_n, pygame.K_RETURN, pygame.K_SPACE):
						# Start new game: keep the randomized mixed-terrain
						# heightmap as generated. Spawn falls back to the
						# nearest land corner via BFS when the random pick
						# is water (see game.spawn_initial_peeps).
						self.game.app_state.transition_to(self.game.app_state.PLAYING)
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
					self.game.game_map.randomize(profile=self.game.map_profile)
					self.game.spawn_initial_peeps(10)
				elif event.key == pygame.K_F4:
					self.game.game_map.set_all_altitude(1)
				elif event.key == pygame.K_F12:
					self.game.show_scanlines = not self.game.show_scanlines
				elif hasattr(event, 'unicode') and event.unicode == '§':
					self.game.show_debug = not self.game.show_debug
			elif event.type == pygame.MOUSEBUTTONDOWN:
				# Menu state: any left click starts the game. Mirror the
				# Enter / Space behavior in the keydown branch above so
				# users can click anywhere on the start page to begin.
				if self.game.app_state.is_menu():
					if event.button == 1:
						self.game.app_state.transition_to(self.game.app_state.PLAYING)
						self.game.spawn_initial_peeps(10)
						self.game.spawn_enemy_peeps(10)
					return True
				# Use event.pos (the position the user actually clicked at)
				# rather than pygame.mouse.get_pos(). This lets headless
				# scripted tests post real click positions and avoids a
				# subtle race where the cursor can move between the click
				# being queued and us polling it.
				mx, my = event.pos
				mx //= self.game.display_scale
				my //= self.game.display_scale
				# Coord-space contract for this MOUSEBUTTONDOWN handler:
				# there is one mouse-input flow with two coord-space
				# paths chosen by *what* is being hit, not by re-deriving
				# math.
				#   * (mx, my)                    : canvas-pixel space
				#                                   (HUD_SCALE-multiplied)
				#   * (logical_mx, logical_my)    : 320x200 logical space
				#
				# The HUD reads logical 320x200 coords because the
				# AmigaUI sprite is 320x200 in logical space; minimap,
				# ui_panel.hit_test_button, and ui_panel.select_at all
				# expect logical coords. Terrain hit-tests use canvas
				# pixels directly because the active ViewportTransform
				# owns the inverse projection from canvas pixels to
				# (row, col); view_rect is also in canvas pixels.
				logical_mx = mx // settings.HUD_SCALE
				logical_my = my // settings.HUD_SCALE
				# Mac trackpad ctrl+left-click compatibility. macOS
				# convention is ctrl+click as a right-click substitute,
				# but pygame reports it as button 1 with KMOD_CTRL set
				# (not as button 3). Remap to button 3 for terrain-area
				# interactions so trackpad users can lower terrain,
				# cancel powers, and exit modes the same way two-button
				# mouse users do. Menu / minimap / UI-button checks keep
				# reading raw event.button so ctrl+click on the start
				# page or on a HUD button behaves like a normal click.
				terrain_button = event.button
				if terrain_button == 1 and (pygame.key.get_mods() & pygame.KMOD_CTRL):
					terrain_button = 3
				# Check interaction minimap (if clicked on, no other action)
				if event.button == 1 and self.game.minimap.handle_click(logical_mx, logical_my, self.game.camera):
					continue
				# Check clicks on UI (compass and powers)
				ui_clicked = False
				if event.button == 1:
					action = self.game.ui_panel.hit_test_button(logical_mx, logical_my)
					if action is not None:
						self._handle_ui_click(action, held=True)
						ui_clicked = True
				if ui_clicked:
					continue
				# Shield mode: left-click on entity = apply coat-of-arms.
				# Uses terrain_button so Mac trackpad ctrl+click cancels.
				if self.game.mode_manager.shield_mode:
					if terrain_button == 1:
						entity, kind = self.game.ui_panel.select_at(logical_mx, logical_my, self.game.peeps, self.game.game_map.houses, self.game.camera, self.game.game_map)
						if entity is not None:
							self.game.selection.who = entity
							self.game.selection.kind = kind
							self.game.mode_manager.shield_target = entity
							self.game.mode_manager.shield_mode = False
						return True
					elif terrain_button == 3:
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
					# Project the click through the active viewport
					# transform; round each axis to land on the nearest
					# integer corner (matches the legacy
					# screen_to_nearest_corner semantics).
					rf, cf = self.game.viewport_transform.screen_to_world(mx, my)
					r = int(round(rf))
					c = int(round(cf))
					# Verify click is in the visible 8x8 camera zone
					start_r, end_r, start_c, end_c = self.game.game_map.get_visible_bounds(self.game.camera.r, self.game.camera.c)
					if start_r <= r <= end_r and start_c <= c <= end_c:
						if self.game.mode_manager.pending_power:
							if terrain_button == 1:
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
							elif terrain_button == 3:
								# Cancel pending power
								self.game.mode_manager.pending_power = None
								self._handle_ui_click('_raise_terrain', held=False)
							return True
						elif self.game.mode_manager.papal_mode:
							if terrain_button == 1:
								# Place/move papal (only one) on the NW case
								self.game.mode_manager.papal_position = (max(r - 1, 0), max(c - 1, 0))
								self.game.mode_manager.papal_mode = False  # Deactivate mode after click
							elif terrain_button == 3:
								# Cancel papal mode and return to raise_terrain
								self.game.mode_manager.papal_mode = False
								self._handle_ui_click('_raise_terrain', held=False)
							return True
						elif not self.game.mode_manager.papal_mode and not self.game.mode_manager.shield_mode:
							# Initial click fires one paint immediately, then
							# drag-paint waits DRAG_PAINT_INITIAL_DELAY before
							# auto-repeating. After that, paints happen every
							# DRAG_PAINT_INTERVAL. Bias the next-fire timestamp
							# so a normal click (under the initial delay) does
							# not register as multiple paints.
							grace = settings.DRAG_PAINT_INITIAL_DELAY - settings.DRAG_PAINT_INTERVAL
							if terrain_button == 1:
								self.game.game_map.raise_corner(r, c)
								self._drag_paint_button = 1
								self._drag_paint_last_time = time.time() + grace
							elif terrain_button == 3:
								self.game.game_map.lower_corner(r, c)
								self._drag_paint_button = 3
								self._drag_paint_last_time = time.time() + grace
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
		# Project drag-paint pointer through the active viewport
		# transform; round each axis to land on the nearest integer
		# corner.
		rf, cf = self.game.viewport_transform.screen_to_world(mx, my)
		r = int(round(rf))
		c = int(round(cf))
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
		# Minimap rect lives in 320x200 logical space; convert canvas
		# coords down by HUD_SCALE before hit-testing.
		logical_mx = mx // settings.HUD_SCALE
		logical_my = my // settings.HUD_SCALE
		if not self.game.minimap.rect.collidepoint(logical_mx, logical_my):
			return
		step = settings.MINIMAP_ZOOM_STEP * float(event.y)
		self.game.minimap.set_zoom(self.game.minimap.zoom + step)
