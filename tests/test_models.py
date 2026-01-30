"""Tests for Pydantic models."""

import sys
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.models.player import Player
from app.models.team import Team
from app.models.game import Game
from app.models.stats import PlayerGameStats
from app.models.responses import PaginatedResponse, PlayerListResponse, APIErrorResponse, PaginationParams


class TestPlayerModel:
    """Tests for Player model."""

    def test_player_creation_valid(self):
        player = Player(
            player_id="2544",
            first_name="LeBron",
            last_name="James",
            full_name="LeBron James",
            team_id="1610612747",
            position="SF",
            jersey_number=23,
            height="6-9",
            weight=250,
            birth_date=date(1984, 12, 30),
            country="USA",
            draft_year=2003,
            draft_round=1,
            draft_number=1,
        )
        assert player.player_id == "2544"
        assert player.first_name == "LeBron"
        assert player.position == "SF"

    def test_player_optional_fields(self):
        player = Player(
            player_id="1234",
            first_name="Test",
            last_name="Player",
            full_name="Test Player",
            team_id="1610612747",
        )
        assert player.position is None
        assert player.jersey_number is None

    def test_player_position_validation(self):
        with pytest.raises(ValidationError):
            Player(
                player_id="1234",
                first_name="Test",
                last_name="Player",
                full_name="Test Player",
                team_id="1610612747",
                position="INVALID",
            )

    def test_player_jersey_number_bounds(self):
        with pytest.raises(ValidationError):
            Player(
                player_id="1234",
                first_name="Test",
                last_name="Player",
                full_name="Test Player",
                team_id="1610612747",
                jersey_number=100,
            )

    def test_player_draft_year_bounds(self):
        with pytest.raises(ValidationError):
            Player(
                player_id="1234",
                first_name="Test",
                last_name="Player",
                full_name="Test Player",
                team_id="1610612747",
                draft_year=1940,
            )

    def test_player_weight_display(self):
        player = Player(
            player_id="1234",
            first_name="Test",
            last_name="Player",
            full_name="Test Player",
            team_id="1610612747",
            weight=250,
        )
        assert player.weight_display == "250 lbs"


class TestTeamModel:
    """Tests for Team model."""

    def test_team_creation_valid(self):
        team = Team(
            team_id="1610612747",
            full_name="Los Angeles Lakers",
            abbreviation="LAL",
            nickname="Lakers",
            city="Los Angeles",
            state="California",
            year_founded=1947,
            conference="Western",
            division="Pacific",
        )
        assert team.team_id == "1610612747"
        assert team.abbreviation == "LAL"
        assert team.conference == "Western"

    def test_team_abbreviation_length(self):
        with pytest.raises(ValidationError):
            Team(
                team_id="1610612747",
                full_name="Los Angeles Lakers",
                abbreviation="LAKERS",
                nickname="Lakers",
                city="Los Angeles",
                conference="Western",
                division="Pacific",
            )

    def test_team_conference_validation(self):
        with pytest.raises(ValidationError):
            Team(
                team_id="1610612747",
                full_name="Los Angeles Lakers",
                abbreviation="LAL",
                nickname="Lakers",
                city="Los Angeles",
                conference="Invalid",
                division="Pacific",
            )

    def test_team_division_validation(self):
        with pytest.raises(ValidationError):
            Team(
                team_id="1610612747",
                full_name="Los Angeles Lakers",
                abbreviation="LAL",
                nickname="Lakers",
                city="Los Angeles",
                conference="Western",
                division="Invalid",
            )


class TestGameModel:
    """Tests for Game model."""

    def test_game_creation_valid(self):
        game = Game(
            game_id="0022400001",
            season=2024,
            season_type="Regular Season",
            game_date=date(2024, 10, 22),
            home_team_id="1610612738",
            away_team_id="1610612752",
            home_score=132,
            away_score=109,
            winner_team_id="1610612738",
            status="final",
        )
        assert game.game_id == "0022400001"
        assert game.season == 2024
        assert game.status == "final"

    def test_game_season_type_validation(self):
        with pytest.raises(ValidationError):
            Game(
                game_id="0022400001",
                season=2024,
                season_type="Invalid",
                game_date=date(2024, 10, 22),
                home_team_id="1610612738",
                away_team_id="1610612752",
            )

    def test_game_status_validation(self):
        with pytest.raises(ValidationError):
            Game(
                game_id="0022400001",
                season=2024,
                season_type="Regular Season",
                game_date=date(2024, 10, 22),
                home_team_id="1610612738",
                away_team_id="1610612752",
                status="invalid",
            )

    def test_game_is_completed(self):
        game = Game(
            game_id="0022400001",
            season=2024,
            season_type="Regular Season",
            game_date=date(2024, 10, 22),
            home_team_id="1610612738",
            away_team_id="1610612752",
            status="final",
        )
        assert game.is_completed is True

    def test_game_is_live(self):
        game = Game(
            game_id="0022400001",
            season=2024,
            season_type="Regular Season",
            game_date=date(2024, 10, 22),
            home_team_id="1610612738",
            away_team_id="1610612752",
            status="live",
        )
        assert game.is_live is True

    def test_game_point_differential(self):
        game = Game(
            game_id="0022400001",
            season=2024,
            season_type="Regular Season",
            game_date=date(2024, 10, 22),
            home_team_id="1610612738",
            away_team_id="1610612752",
            home_score=132,
            away_score=109,
            status="final",
        )
        assert game.point_differential == 23


class TestPlayerGameStatsModel:
    """Tests for PlayerGameStats model."""

    def test_stats_creation_valid(self):
        stats = PlayerGameStats(
            stat_id=12345,
            game_id="0022400001",
            player_id="2544",
            team_id="1610612747",
            minutes_played=34.5,
            points=25,
            rebounds_offensive=1,
            rebounds_defensive=8,
            assists=8,
            steals=1,
            blocks=0,
            turnovers=4,
            personal_fouls=2,
            fg_made=10,
            fg_attempted=18,
            fg3_made=3,
            fg3_attempted=7,
            ft_made=2,
            ft_attempted=3,
        )
        assert stats.stat_id == 12345
        assert stats.points == 25
        assert stats.rebounds_total == 9

    def test_stats_fg_pct_calculation(self):
        stats = PlayerGameStats(
            stat_id=12345,
            game_id="0022400001",
            player_id="2544",
            team_id="1610612747",
            fg_made=10,
            fg_attempted=20,
        )
        assert stats.fg_pct == 0.5

    def test_stats_fg_pct_zero_attempts(self):
        stats = PlayerGameStats(
            stat_id=12345,
            game_id="0022400001",
            player_id="2544",
            team_id="1610612747",
            fg_made=0,
            fg_attempted=0,
        )
        assert stats.fg_pct is None

    def test_stats_fg3_pct_calculation(self):
        stats = PlayerGameStats(
            stat_id=12345,
            game_id="0022400001",
            player_id="2544",
            team_id="1610612747",
            fg3_made=3,
            fg3_attempted=9,
        )
        assert stats.fg3_pct == 0.333

    def test_stats_ft_pct_calculation(self):
        stats = PlayerGameStats(
            stat_id=12345,
            game_id="0022400001",
            player_id="2544",
            team_id="1610612747",
            ft_made=4,
            ft_attempted=5,
        )
        assert stats.ft_pct == 0.8

    def test_stats_rebounds_total(self):
        stats = PlayerGameStats(
            stat_id=12345,
            game_id="0022400001",
            player_id="2544",
            team_id="1610612747",
            rebounds_offensive=3,
            rebounds_defensive=7,
        )
        assert stats.rebounds_total == 10


class TestResponseModels:
    """Tests for response models."""

    def test_paginated_response_creation(self):
        items = [Player(player_id="1", first_name="Test", last_name="Player", full_name="Test Player", team_id="123")]
        response = PaginatedResponse(items=items, total=1, page=1, page_size=20, pages=1)
        assert response.total == 1
        assert response.page == 1

    def test_player_list_response_creation(self):
        items = [Player(player_id="1", first_name="Test", last_name="Player", full_name="Test Player", team_id="123")]
        response = PlayerListResponse(items=items, total=1, page=1, page_size=20, pages=1)
        assert len(response.items) == 1

    def test_api_error_response_creation(self):
        error = APIErrorResponse(error_code="NOT_FOUND", message="Resource not found")
        assert error.error_code == "NOT_FOUND"
        assert error.message == "Resource not found"

    def test_pagination_params_defaults(self):
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 20

    def test_pagination_params_validation(self):
        with pytest.raises(ValidationError):
            PaginationParams(page=0)
