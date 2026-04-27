"""UI panel display and interaction (shield panel, coat-of-arms, buttons)."""

import pygame
import populous_game.settings as settings
import populous_game.peeps as peep
import populous_game.sprite_geometry as sprite_geometry


class UIPanel:
	"""Handles UI button hit-testing, shield panel rendering, and entity marker display."""

	def __init__(self, game):
		"""Initialize UI panel with game reference."""
		self.game = game
		# Button definitions: action name -> {'c': (cx, cy), 'hw': hw, 'hh': hh}
		cx, cy = settings.UI_PANEL_BASE_CENTER_X, settings.UI_PANEL_BASE_CENTER_Y  # Base center
		dx, dy = settings.UI_PANEL_BUTTON_DX, settings.UI_PANEL_BUTTON_DY    # Isometric offset
		hw, hh = settings.UI_PANEL_BUTTON_HW, settings.UI_PANEL_BUTTON_HH    # Isometric size for buttons
		self.buttons = {
			# --- Row 0 (9 actions) ---
			'_raise_terrain': {'c': (cx + dx*2, cy + dy*2), 'hw': hw, 'hh': hh},
			'_do_volcano':    {'c': (cx - dx*3, cy - dy*3), 'hw': hw, 'hh': hh},
			'_do_knight':     {'c': (cx - dx*2, cy - dy*2), 'hw': hw, 'hh': hh},
			'_do_flood':      {'c': (cx - dx*3, cy - dy*5), 'hw': hw, 'hh': hh},
			'_do_quake':      {'c': (cx - dx*1, cy - dy*3), 'hw': hw, 'hh': hh},
			'_do_swamp':      {'c': (cx - dx*3, cy - dy*1), 'hw': hw, 'hh': hh},
			'_do_papal':      {'c': (cx + dx*1, cy + dy*3), 'hw': hw, 'hh': hh},
			'_do_shield':     {'c': (cx + dx*3, cy + dy*1), 'hw': hw, 'hh': hh},
			'_find_battle':   {'c': (cx + dx*3, cy + dy*3), 'hw': hw, 'hh': hh},
			# _find_shield: removed in M2 per docs/active_plans/m2_button_gaps.md
			# (no shield-bearer concept exists in the current peep code).
			'_find_papal':    {'c': (cx + dx*4, cy + dy*2), 'hw': hw, 'hh': hh},
			'_find_knight':   {'c': (cx + dx*5, cy + dy*3), 'hw': hw, 'hh': hh},
			'W':              {'c': (cx - dx*2, cy),        'hw': hw, 'hh': hh},
			'NW':             {'c': (cx - dx*1, cy - dy),   'hw': hw, 'hh': hh},
			'N':              {'c': (cx,        cy - dy*2), 'hw': hw, 'hh': hh},
			'NE':             {'c': (cx + dx*1, cy - dy*1), 'hw': hw, 'hh': hh},
			'E':              {'c': (cx + dx*2, cy),        'hw': hw, 'hh': hh},
			'SW':             {'c': (cx - dx*1, cy + dy*1), 'hw': hw, 'hh': hh},
			'S':              {'c': (cx,        cy + dy*2), 'hw': hw, 'hh': hh},
			'SE':             {'c': (cx + dx*1, cy + dy*1), 'hw': hw, 'hh': hh},
			'_go_papal':      {'c': (cx - dx*3, cy + dy*1), 'hw': hw, 'hh': hh},
			'_go_build':      {'c': (cx - dx*2, cy + dy*2), 'hw': hw, 'hh': hh},
			'_go_assemble':   {'c': (cx - dx*1, cy + dy*3), 'hw': hw, 'hh': hh},
			'_go_fight':      {'c': (cx - dx*3, cy + dy*3), 'hw': hw, 'hh': hh},
			# _battle_over: removed in M2 per docs/active_plans/m2_button_gaps.md
			# (original icon meaning unconfirmed; no matching repo mechanic).
			# Bottom-right HUD audio + sleep icons (320x200 logical coords).
			# Geometry estimated from the AmigaUI.png sprite; the
			# tools/draw_button_overlay.py debug script (M2 review) renders
			# these rects on top of the HUD for visual confirmation.
			'_fx':            {'c': (250, 189), 'hw': 10, 'hh': 6},
			'_music':         {'c': (275, 189), 'hw': 10, 'hh': 6},
			'_sleep':         {'c': (304, 189), 'hw': 10, 'hh': 6},
		}

	def hit_test_button(self, mx, my) -> str | None:
		"""Hit-test a mouse coord against the diamond-shaped UI buttons.

		Returns the action whose diamond center is closest to (mx, my) when
		multiple diamonds overlap (which they do at panel edges; iso buttons
		share corners). Returns None if no button is hit.
		"""
		best_action = None
		best_score = settings.UI_PANEL_DIAMOND_THRESHOLD
		for action, shape in self.buttons.items():
			bcx, bcy = shape['c']
			bhw, bhh = shape['hw'], shape['hh']
			# Diamond-distance: 0 at center, 1.0 at the edge along the axes
			score = (abs(mx - bcx) / float(bhw) + abs(my - bcy) / float(bhh))
			if score <= best_score:
				best_score = score
				best_action = action
		return best_action

	def select_at(self, mx, my, peeps, houses, camera, game_map) -> tuple:
		"""Hit-test entities at (mx, my). Return (entity, kind) or (None, None).

		mx, my arrive in logical-space coords (matching the rest of
		ui_panel's hit-tests). Sprite rects from sprite_geometry are
		built from canvas-pixel coords via the active ViewportTransform,
		so we scale the click point up by HUD_SCALE before colliding so
		the hover/click rect lines up with the visible sprite at every
		canvas preset. At classic (HUD_SCALE == 1) this is a no-op.
		"""
		# Camera arg is kept for back-compat with existing callsites;
		# entity geometry now flows through self.game.viewport_transform.
		del camera
		transform = self.game.viewport_transform
		# Scale the click into canvas-pixel space so it matches the rect
		# coord space returned by sprite_geometry.
		px = mx * settings.HUD_SCALE
		py = my * settings.HUD_SCALE
		best_target = None
		best_type = None
		best_dist = float('inf')

		for house in houses:
			if house.destroyed:
				continue
			rect = sprite_geometry.get_house_sprite_rect(house, transform, game_map)
			if rect.collidepoint(px, py):
				dx = px - rect.centerx
				dy = py - rect.centery
				d2 = dx * dx + dy * dy
				if d2 < best_dist:
					best_dist = d2
					best_target = house
					best_type = 'house'

		for p in peeps:
			if p.dead:
				continue
			rect = sprite_geometry.get_peep_sprite_rect(p, transform, game_map)
			if rect.collidepoint(px, py):
				dx = px - rect.centerx
				dy = py - rect.centery
				d2 = dx * dx + dy * dy
				if d2 < best_dist:
					best_dist = d2
					best_target = p
					best_type = 'peep'

		if best_target is not None:
			return (best_target, best_type)
		return (None, None)

	#============================================
	# Tooltip and hover-help (M7)
	#============================================

	def tooltip_for(self, action: str | None) -> str | None:
		"""Return tooltip text for a UI button action, or None if no tooltip."""
		if action is None:
			return None
		return settings.BUTTON_TOOLTIPS.get(action)

	def hover_info_at(self, mx: int, my: int, game) -> dict | None:
		"""Return a dict describing what is under the cursor, or None.

		Search order: peep, house, terrain. Hover info is rendered as a
		small panel near the cursor by renderer._draw_hover_help; it never
		influences the simulation.
		"""
		# Entity hit-test first (peeps and houses)
		entity, kind = self.select_at(mx, my, game.peeps, game.game_map.houses, game.camera, game.game_map)
		if entity is not None and kind == 'peep':
			info = {
				'kind': 'peep',
				'faction': entity.faction_id,
				'state': entity.state,
				'life': float(entity.life),
			}
			return info
		if entity is not None and kind == 'house':
			info = {
				'kind': 'house',
				'faction': entity.faction_id,
				'house_type': entity.building_type,
				'life': float(entity.life),
			}
			return info

		# Fall back to terrain corner under the cursor.
		if not game.view_rect.collidepoint(mx, my):
			return None
		# Round the float (row, col) returned by screen_to_world to the
		# nearest integer corner. mx / my arrive in 320x200 logical
		# space; the transform expects canvas-pixel space, so scale up
		# by HUD_SCALE before projecting.
		px = mx * settings.HUD_SCALE
		py = my * settings.HUD_SCALE
		rf, cf = game.viewport_transform.screen_to_world(px, py)
		r = int(round(rf))
		c = int(round(cf))
		alt = game.game_map.get_corner_altitude(r, c)
		if alt < 0:
			return None
		info = {
			'kind': 'terrain',
			'altitude': int(alt),
			'r': int(r),
			'c': int(c),
		}
		return info

	def draw_shield_marker(self, surface, target, target_type, cam_r, cam_c, game_map):
		"""Draw shield sprite above selected entity."""
		# cam_r / cam_c remain in the signature for back-compat with
		# the renderer caller; entity geometry now flows through the
		# game's viewport_transform.
		del cam_r, cam_c
		transform = self.game.viewport_transform
		sprites = peep.Peep.get_sprites()
		shield_sprite = sprites.get((8, 8))
		if shield_sprite is None:
			return

		if target_type == 'peep':
			rect = sprite_geometry.get_peep_sprite_rect(target, transform, game_map)
			# On peep as if holding it (slightly offset)
			x = rect.centerx + settings.UI_SHIELD_MARKER_PEEP_X
			y = rect.centery - shield_sprite.get_height() // 2 + settings.UI_SHIELD_MARKER_PEEP_Y
			surface.blit(shield_sprite, (x, y))
			return

		# For castle, place shield like other buildings but on center case (r, c)
		if getattr(target, 'building_type', None) == 'castle':
			center_r = getattr(target, 'r', 0)
			center_c = getattr(target, 'c', 0)
			alt = game_map.get_corner_altitude(center_r, center_c)
			sx, sy = transform.world_to_screen(center_r, center_c, alt)
			# Simulate a virtual rect for center case. Tile dims are
			# in BASE px so the rect must scale by TERRAIN_SCALE to
			# match the cached scaled tile sprites.
			scale = settings.TERRAIN_SCALE
			rect = pygame.Rect(
				sx - settings.TILE_HALF_W * scale, sy,
				settings.TILE_WIDTH * scale, settings.TILE_HEIGHT * scale,
			)
			x = rect.centerx - shield_sprite.get_width() // 2 + settings.UI_SHIELD_MARKER_OFFSET_X
			y = rect.top - shield_sprite.get_height() - 2 + settings.UI_SHIELD_MARKER_OFFSET_Y
			surface.blit(shield_sprite, (x, y))
			return

		rect = sprite_geometry.get_house_sprite_rect(target, transform, game_map)
		# Generic offset for other buildings
		x = rect.centerx - shield_sprite.get_width() // 2 + settings.UI_SHIELD_MARKER_OFFSET_X
		y = rect.top - shield_sprite.get_height() - 2 + settings.UI_SHIELD_MARKER_OFFSET_Y
		surface.blit(shield_sprite, (x, y))

	def draw_shield_panel(self, surface, selection, weapon_sprites, weapon_sprite_indices, game_map, font):
		"""Draw shield panel (coat-of-arms with info) on surface."""
		if selection.who is None or selection.kind is None:
			return

		sprites = peep.Peep.get_sprites()

		# Coordinates derived from 4 parts of coat-of-arms (top-right, UI starts at x=256)
		blason_tl = (271, 4)   # Top-Left (Colony)
		blason_tr = (287, 2)   # Top-Right (Weapon)
		blason_bl = (271, 23)  # Bottom-Left (Sprite/Animation)
		blason_br = (287, 19)  # Bottom-Right (Energy)

		# 1. Blue colony (4,8) or red (4,9) -> for now take blue
		colony_sprite = sprites.get((4, 8))
		if selection.kind == 'peep' and getattr(selection.who, 'is_enemy', False):
			colony_sprite = sprites.get((4, 9))
		if colony_sprite:
			surface.blit(colony_sprite, blason_tl)

		# 2. Weapon represented by sprite
		weapon_idx = None
		if selection.kind == 'house':
			weapon_idx = weapon_sprite_indices.get(selection.who.building_type, None)
		elif selection.kind == 'peep':
			weapon_idx = weapon_sprite_indices.get(selection.who.weapon_type, None)
		if weapon_idx is not None and 0 <= weapon_idx < len(weapon_sprites):
			sprite = weapon_sprites[weapon_idx]
			# Center sprite in top-right quadrant
			x = blason_tr[0] + 2
			y = blason_tr[1] + 1
			surface.blit(sprite, (x, y))
		else:
			# Fallback: gray letter
			weapon = self._get_weapon_name(selection.who, selection.kind)
			weapon_letter = 'N'  # None
			if weapon != 'None':
				weapon_letter = weapon[0].upper()
			w_text = font.render(weapon_letter, True, (240, 240, 240))
			surface.blit(w_text, (blason_tr[0] + 6, blason_tr[1] + 2))

		# 3. Animated peep sprite, or animated flag for building
		show_flag = (selection.kind == 'house')
		# If peep under construction (in_house = True or similar), also show flag
		if selection.kind == 'peep' and selection.who.in_house:
			show_flag = True

		if not show_flag:
			from populous_game.peeps import PEEP_WALK_FRAMES
			facing = selection.who.facing
			anim = PEEP_WALK_FRAMES.get(facing, PEEP_WALK_FRAMES['IDLE'])
			frame_idx = selection.who.anim_frame % len(anim)
			peep_idx = anim[frame_idx]
			peep_sprite = sprites.get(peep_idx)
			if peep_sprite:
				surface.blit(peep_sprite, blason_bl)
		else:
			# Bâtiment ou peep en construction : drapeau animé (4,0 et 4,1)
			frame_idx = int(pygame.time.get_ticks() / 200) % 2
			flag_sprite = sprites.get((4, frame_idx))
			if flag_sprite:
				# Décaler le drapeau de 3px vers la gauche pour les bâtiments
				blason_flag = (blason_bl[0] - 3, blason_bl[1])
				surface.blit(flag_sprite, blason_flag)

		# 4. Shield bars for building: power (yellow) and health (orange)
		if selection.kind == 'house':
			self._draw_house_bars(surface, selection, blason_br)
		else:
			self._draw_peep_bars(surface, selection, blason_br)

	def _draw_house_bars(self, surface, selection, blason_br):
		"""Draw power and health bars for a house."""
		from populous_game.houses import House
		building_type = selection.who.building_type
		tier = House.TYPES.index(building_type) if building_type in House.TYPES else 0
		# Power: GROWTH_SPEEDS (1 to 16)
		power = House.GROWTH_SPEEDS[tier]
		max_power = max(House.GROWTH_SPEEDS)
		ratio_yellow = min(1.0, max(0.0, power / max_power))
		# Health: current life / max life
		life = float(selection.who.life)
		max_life = float(selection.who.max_life)
		ratio_orange = min(1.0, max(0.0, life / max_life))
		bar_w = 4
		bar_max_h = 16
		rect1_x = blason_br[0] + 3
		rect2_x = blason_br[0] + 11
		bar_bg_y = blason_br[1] + 3
		# Background
		pygame.draw.rect(surface, (102, 102, 102), (rect1_x, bar_bg_y, bar_w, bar_max_h))
		pygame.draw.rect(surface, (102, 102, 102), (rect2_x, bar_bg_y, bar_w, bar_max_h))
		# Yellow bar = power
		bar1_h = int(bar_max_h * ratio_yellow)
		bar1_y = bar_bg_y + (bar_max_h - bar1_h)
		if bar1_h > 0:
			pygame.draw.rect(surface, (255, 220, 0), (rect1_x, bar1_y, bar_w, bar1_h))
		# Orange bar = health
		bar2_h = int(bar_max_h * ratio_orange)
		bar2_y = bar_bg_y + (bar_max_h - bar2_h)
		if bar2_h > 0:
			pygame.draw.rect(surface, (255, 140, 0), (rect2_x, bar2_y, bar_w, bar2_h))

	def _draw_peep_bars(self, surface, selection, blason_br):
		"""Draw health bars for a peep."""
		life = float(selection.who.life)
		hundreds = int(life // 100)
		max_hundreds = 10.0
		ratio_yellow = min(1.0, max(0.0, hundreds / max_hundreds))
		units = life % 100
		ratio_orange = min(1.0, max(0.0, units / 99.0))
		bar_w = 4
		bar_max_h = 16
		rect1_x = blason_br[0] + 3
		rect2_x = blason_br[0] + 11
		bar_bg_y = blason_br[1] + 3
		pygame.draw.rect(surface, (102, 102, 102), (rect1_x, bar_bg_y, bar_w, bar_max_h))
		pygame.draw.rect(surface, (102, 102, 102), (rect2_x, bar_bg_y, bar_w, bar_max_h))
		bar1_h = int(bar_max_h * ratio_yellow)
		bar1_y = bar_bg_y + (bar_max_h - bar1_h)
		if bar1_h > 0:
			pygame.draw.rect(surface, (255, 220, 0), (rect1_x, bar1_y, bar_w, bar1_h))
		bar2_h = int(bar_max_h * ratio_orange)
		bar2_y = bar_bg_y + (bar_max_h - bar2_h)
		if bar2_h > 0:
			pygame.draw.rect(surface, (255, 140, 0), (rect2_x, bar2_y, bar_w, bar2_h))

	def _get_weapon_name(self, target, target_type):
		"""Get weapon name for display in coat-of-arms."""
		if target_type == 'house':
			by_type = {
				'hut': 'A',
				'house_small': 'B',
				'house_medium': 'C',
				'castle_small': 'D',
				'castle_medium': 'E',
				'castle_large': 'F',
				'fortress_small': 'G',
				'fortress_medium': 'H',
				'fortress_large': 'I',
				'castle': 'J',
			}
			return by_type.get(target.building_type, 'None')

		life = float(target.life)
		if life < 20:
			return 'Mains nues'
		if life < 40:
			return 'Baton'
		if life < 70:
			return 'Epee courte'
		if life < 100:
			return 'Epee'
		return 'Arc'
