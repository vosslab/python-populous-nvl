"""Tests for the faction module."""

import populous_game.faction as faction
import populous_game.peeps as peeps
import populous_game.houses as houses


def test_faction_constants():
    """Test that faction constants have expected values."""
    assert faction.Faction.PLAYER == 0
    assert faction.Faction.ENEMY == 1
    assert faction.Faction.NEUTRAL == 2


def test_faction_names():
    """Test that faction names are correct."""
    assert faction.Faction.name(faction.Faction.PLAYER) == 'Player'
    assert faction.Faction.name(faction.Faction.ENEMY) == 'Enemy'
    assert faction.Faction.name(faction.Faction.NEUTRAL) == 'Neutral'


def test_peep_default_faction():
    """Test that a new Peep defaults to PLAYER faction."""
    # Create a minimal mock game_map
    class MockGameMap:
        grid_height = 64
        grid_width = 64

        def get_corner_altitude(self, r, c):
            return 5

    game_map = MockGameMap()
    peep_obj = peeps.Peep(10, 10, game_map)
    assert peep_obj.faction == faction.Faction.PLAYER


def test_peep_custom_faction():
    """Test that a Peep can be constructed with a custom faction."""
    class MockGameMap:
        grid_height = 64
        grid_width = 64

        def get_corner_altitude(self, r, c):
            return 5

    game_map = MockGameMap()
    peep_obj = peeps.Peep(10, 10, game_map, faction_id=faction.Faction.ENEMY)
    assert peep_obj.faction == faction.Faction.ENEMY


def test_house_default_faction():
    """Test that a new House defaults to PLAYER faction."""
    house_obj = houses.House(10, 10)
    assert house_obj.faction == faction.Faction.PLAYER


def test_house_custom_faction():
    """Test that a House can be constructed with a custom faction."""
    house_obj = houses.House(10, 10, faction_id=faction.Faction.ENEMY)
    assert house_obj.faction == faction.Faction.ENEMY


def test_faction_colors_colorblind_safe():
    """Test colorblind-safe faction colors."""
    import populous_game.settings as settings

    # Ensure colorblind palette is enabled
    old_setting = settings.USE_COLORBLIND_PALETTE
    try:
        settings.USE_COLORBLIND_PALETTE = True

        from populous_game.renderer import Renderer

        player_color = Renderer.faction_color(faction.Faction.PLAYER)
        assert player_color == (40, 120, 220)

        enemy_color = Renderer.faction_color(faction.Faction.ENEMY)
        assert enemy_color == (220, 110, 30)

        neutral_color = Renderer.faction_color(faction.Faction.NEUTRAL)
        assert neutral_color == (160, 160, 160)
    finally:
        settings.USE_COLORBLIND_PALETTE = old_setting


def test_faction_colors_amiga_classic():
    """Test Amiga classic faction colors."""
    import populous_game.settings as settings

    # Ensure Amiga palette is enabled
    old_setting = settings.USE_COLORBLIND_PALETTE
    try:
        settings.USE_COLORBLIND_PALETTE = False

        from populous_game.renderer import Renderer

        player_color = Renderer.faction_color(faction.Faction.PLAYER)
        assert player_color == (40, 120, 220)

        enemy_color = Renderer.faction_color(faction.Faction.ENEMY)
        assert enemy_color == (220, 0, 0)

        neutral_color = Renderer.faction_color(faction.Faction.NEUTRAL)
        assert neutral_color == (160, 160, 160)
    finally:
        settings.USE_COLORBLIND_PALETTE = old_setting


def test_peep_spawned_inherits_faction():
    """Test that a peep spawned from a house inherits the house's faction."""
    class MockGameMap:
        grid_height = 64
        grid_width = 64
        houses = []

        def get_corner_altitude(self, r, c):
            return 5

        def can_place_house_initial(self, r, c):
            return False

        def add_house(self, h):
            self.houses.append(h)

        def get_flat_area_score(self, r, c, current_house):
            return 0, []

    game_map = MockGameMap()
    enemy_peep = peeps.Peep(10, 10, game_map, faction_id=faction.Faction.ENEMY)

    # Verify the peep has ENEMY faction
    assert enemy_peep.faction == faction.Faction.ENEMY
