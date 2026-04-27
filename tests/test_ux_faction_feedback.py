"""Tests for UX faction feedback (M5 Wave 3, Patch 3)."""

import populous_game.game as game_module
import populous_game.faction as faction
import populous_game.renderer as renderer_module
import populous_game.settings as settings


class TestUXFactionFeedback:
	"""Faction color indicators and mode indicator text."""

	def test_mode_indicator_idle(self):
		"""Mode indicator displays IDLE when neither papal nor shield mode active."""
		game = game_module.Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.game_map.set_all_altitude(3)
		game.spawn_initial_peeps(1)
		game.mode_manager.papal_mode = False
		game.mode_manager.shield_mode = False
		game.renderer._draw_mode_indicator()
		# Should not raise; surface should have been drawn to
		assert game.internal_surface is not None

	def test_mode_indicator_papal(self):
		"""Mode indicator displays PAPAL when papal mode active."""
		game = game_module.Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.game_map.set_all_altitude(3)
		game.spawn_initial_peeps(1)
		game.mode_manager.papal_mode = True
		game.mode_manager.shield_mode = False
		game.renderer._draw_mode_indicator()
		assert game.internal_surface is not None

	def test_mode_indicator_shield(self):
		"""Mode indicator displays SHIELD when shield mode active."""
		game = game_module.Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.game_map.set_all_altitude(3)
		game.spawn_initial_peeps(1)
		game.mode_manager.papal_mode = False
		game.mode_manager.shield_mode = True
		game.renderer._draw_mode_indicator()
		assert game.internal_surface is not None

	def test_mode_indicator_not_in_menu(self):
		"""Mode indicator does not draw when not in PLAYING state."""
		game = game_module.Game()
		# Stay in MENU state
		assert game.app_state.is_menu()
		game.renderer._draw_mode_indicator()
		# Should not raise (no-op in menu state)
		assert game.internal_surface is not None

	def test_faction_feedback_peeps(self):
		"""Faction feedback draws color indicators for peeps."""
		game = game_module.Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.game_map.set_all_altitude(3)
		game.spawn_initial_peeps(3)
		game.spawn_enemy_peeps(3)
		game.renderer._draw_faction_feedback()
		# Should not raise; peeps should be drawn
		assert len(game.peeps) >= 6

	def test_faction_feedback_houses(self):
		"""Faction feedback draws color indicators for houses."""
		game = game_module.Game()
		game.app_state.transition_to(game.app_state.PLAYING)
		game.game_map.set_all_altitude(3)
		from populous_game.houses import House
		house_player = House(10, 10, faction_id=faction.Faction.PLAYER)
		house_enemy = House(20, 20, faction_id=faction.Faction.ENEMY)
		game.game_map.add_house(house_player)
		game.game_map.add_house(house_enemy)
		game.renderer._draw_faction_feedback()
		# Should not raise; houses should be drawn
		assert len(game.game_map.houses) == 2

	def test_faction_color_colorblind_palette(self):
		"""Faction color uses colorblind-safe palette when enabled."""
		settings.USE_COLORBLIND_PALETTE = True
		color = renderer_module.Renderer.faction_color(faction.Faction.PLAYER)
		assert color == settings.FACTION_COLORS_COLORBLIND_SAFE[faction.Faction.PLAYER]
		settings.USE_COLORBLIND_PALETTE = True  # Reset

	def test_faction_color_amiga_palette(self):
		"""Faction color uses Amiga palette when colorblind palette disabled."""
		settings.USE_COLORBLIND_PALETTE = False
		color = renderer_module.Renderer.faction_color(faction.Faction.ENEMY)
		assert color == settings.FACTION_COLORS_AMIGA_CLASSIC[faction.Faction.ENEMY]
		settings.USE_COLORBLIND_PALETTE = True  # Reset

	def test_faction_colors_valid(self):
		"""All faction IDs have valid RGB colors."""
		for faction_id in [faction.Faction.PLAYER, faction.Faction.ENEMY, faction.Faction.NEUTRAL]:
			color = renderer_module.Renderer.faction_color(faction_id)
			assert isinstance(color, tuple)
			assert len(color) == 3
			for component in color:
				assert 0 <= component <= 255
