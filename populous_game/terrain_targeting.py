"""Terrain targeting helpers for mouse-based god powers."""

import populous_game.faction as faction
import populous_game.peep_state as peep_state


def visible_bounds(game) -> tuple:
	"""Return the current visible terrain bounds."""
	return game.game_map.get_visible_bounds(game.camera.r, game.camera.c)


def is_visible_corner(game, r: int, c: int) -> bool:
	"""Return True when a terrain corner is inside the active viewport."""
	start_r, end_r, start_c, end_c = visible_bounds(game)
	return start_r <= r < end_r and start_c <= c < end_c


def live_player_peep_on_screen(game) -> bool:
	"""Return True when a live player peep is visible in the current viewport."""
	start_r, end_r, start_c, end_c = visible_bounds(game)
	for peep_obj in game.peeps:
		if peep_obj.faction_id != faction.Faction.PLAYER:
			continue
		if peep_obj.dead:
			continue
		if peep_obj.state == peep_state.PeepState.DEAD:
			continue
		r = int(peep_obj.y)
		c = int(peep_obj.x)
		if start_r <= r < end_r and start_c <= c < end_c:
			return True
	return False


def can_edit_terrain_at(game, r: int, c: int) -> bool:
	"""Return True when the player can raise/lower the targeted terrain."""
	if not is_visible_corner(game, r, c):
		return False
	if not live_player_peep_on_screen(game):
		return False
	return True
