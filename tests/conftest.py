"""Shared fixtures for ETL pipeline tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# =============================================================================
# FastAPI Test Client
# =============================================================================


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


# =============================================================================
# Mock time.sleep to speed up tests
# =============================================================================


@pytest.fixture(autouse=True)
def mock_time_sleep():
    """Mock time.sleep to speed up tests."""
    with patch("time.sleep") as mock:
        yield mock


# =============================================================================
# Mock Database Fixtures
# =============================================================================


@pytest.fixture
def mock_db_connection():
    """Mock database connection fixture."""
    mock_conn = MagicMock()
    mock_conn.execute = MagicMock()
    mock_conn.rowcount = 1
    mock_conn.close = MagicMock()
    mock_conn.executemany = MagicMock()
    return mock_conn


@pytest.fixture
def mock_get_db_connection(mock_db_connection):
    """Mock get_db_connection function - patches all ETL modules."""
    # Patch where it's used in ETL modules
    with (
        patch("scripts.etl_teams.get_db_connection") as mock_teams,
        patch("scripts.etl_players.get_db_connection") as mock_players,
        patch("scripts.etl_games.get_db_connection") as mock_games,
        patch("scripts.etl_stats.get_db_connection") as mock_stats,
    ):
        mock_teams.return_value = mock_db_connection
        mock_players.return_value = mock_db_connection
        mock_games.return_value = mock_db_connection
        mock_stats.return_value = mock_db_connection
        # Return a mock that has return_value pointing to the connection
        # This maintains compatibility with existing tests
        combined_mock = MagicMock()
        combined_mock.return_value = mock_db_connection
        combined_mock.__individual_mocks__ = {
            "teams": mock_teams,
            "players": mock_players,
            "games": mock_games,
            "stats": mock_stats,
        }
        yield combined_mock


@pytest.fixture
def mock_close_db_connection():
    """Mock close_db_connection function - patches all ETL modules."""
    # Patch where it's used in ETL modules
    with (
        patch("scripts.etl_teams.close_db_connection") as mock_teams,
        patch("scripts.etl_players.close_db_connection") as mock_players,
        patch("scripts.etl_games.close_db_connection") as mock_games,
        patch("scripts.etl_stats.close_db_connection") as mock_stats,
    ):
        # Return a mock that tracks calls, plus individual mocks
        combined_mock = MagicMock()
        combined_mock.__individual_mocks__ = {
            "teams": mock_teams,
            "players": mock_players,
            "games": mock_games,
            "stats": mock_stats,
        }
        yield combined_mock


@pytest.fixture
def mock_database(mock_get_db_connection, mock_close_db_connection, mock_db_connection):
    """Combined mock database fixture."""
    return {
        "get_connection": mock_get_db_connection,
        "close_connection": mock_close_db_connection,
        "connection": mock_db_connection,
        # Provide access to individual mocks per module
        "teams_get_db_connection": mock_get_db_connection.__individual_mocks__["teams"],
        "players_get_db_connection": mock_get_db_connection.__individual_mocks__["players"],
        "games_get_db_connection": mock_get_db_connection.__individual_mocks__["games"],
        "stats_get_db_connection": mock_get_db_connection.__individual_mocks__["stats"],
        "teams_close_db_connection": mock_close_db_connection.__individual_mocks__["teams"],
        "players_close_db_connection": mock_close_db_connection.__individual_mocks__["players"],
        "games_close_db_connection": mock_close_db_connection.__individual_mocks__["games"],
        "stats_close_db_connection": mock_close_db_connection.__individual_mocks__["stats"],
    }


# =============================================================================
# Sample Data Fixtures - Teams
# =============================================================================


@pytest.fixture
def sample_team_data():
    """Sample raw team data from nba_api static teams."""
    return [
        {
            "id": 1610612738,
            "full_name": "Boston Celtics",
            "abbreviation": "BOS",
            "nickname": "Celtics",
            "city": "Boston",
            "state": "Massachusetts",
            "year_founded": 1946,
        },
        {
            "id": 1610612747,
            "full_name": "Los Angeles Lakers",
            "abbreviation": "LAL",
            "nickname": "Lakers",
            "city": "Los Angeles",
            "state": "California",
            "year_founded": 1947,
        },
        {
            "id": 1610612741,
            "full_name": "Chicago Bulls",
            "abbreviation": "CHI",
            "nickname": "Bulls",
            "city": "Chicago",
            "state": "Illinois",
            "year_founded": 1966,
        },
    ]


@pytest.fixture
def sample_team_dataframe(sample_team_data):
    """Sample team data as DataFrame."""
    return pd.DataFrame(sample_team_data)


@pytest.fixture
def sample_transformed_team_data():
    """Sample transformed team data matching database schema."""
    return [
        {
            "team_id": 1610612738,
            "full_name": "Boston Celtics",
            "abbreviation": "BOS",
            "nickname": "Celtics",
            "city": "Boston",
            "state": "Massachusetts",
            "year_founded": 1946,
            "conference": "Eastern",
            "division": "Atlantic",
        },
        {
            "team_id": 1610612747,
            "full_name": "Los Angeles Lakers",
            "abbreviation": "LAL",
            "nickname": "Lakers",
            "city": "Los Angeles",
            "state": "California",
            "year_founded": 1947,
            "conference": "Western",
            "division": "Pacific",
        },
        {
            "team_id": 1610612741,
            "full_name": "Chicago Bulls",
            "abbreviation": "CHI",
            "nickname": "Bulls",
            "city": "Chicago",
            "state": "Illinois",
            "year_founded": 1966,
            "conference": "Eastern",
            "division": "Central",
        },
    ]


# =============================================================================
# Sample Data Fixtures - Players
# =============================================================================


@pytest.fixture
def sample_player_api_data():
    """Sample raw player data from nba_api CommonAllPlayers."""
    return {
        "PERSON_ID": [2544, 201939, 1628983],
        "DISPLAY_FIRST_LAST": ["LeBron James", "Stephen Curry", "Shai Gilgeous-Alexander"],
        "TEAM_ID": [1610612747, 1610612744, 1610612760],
        "TEAM_NAME": ["Lakers", "Warriors", "Thunder"],
        "TEAM_ABBREVIATION": ["LAL", "GSW", "OKC"],
        "ROSTERSTATUS": [1, 1, 1],
        "FROM_YEAR": [2003, 2009, 2018],
        "TO_YEAR": [2025, 2025, 2025],
    }


@pytest.fixture
def sample_player_dataframe(sample_player_api_data):
    """Sample player data as DataFrame."""
    return pd.DataFrame(sample_player_api_data)


@pytest.fixture
def sample_player_with_all_fields():
    """Sample player data with all available fields."""
    return {
        "PERSON_ID": [2544],
        "DISPLAY_FIRST_LAST": ["LeBron James"],
        "FIRST_NAME": ["LeBron"],
        "LAST_NAME": ["James"],
        "TEAM_ID": [1610612747],
        "TEAM_NAME": ["Lakers"],
        "POSITION": ["F"],
        "HEIGHT": ["6-9"],
        "WEIGHT": ["250"],
        "BIRTH_DATE": ["1984-12-30"],
        "COUNTRY": ["USA"],
        "JERSEY": ["23"],
        "DRAFT_YEAR": ["2003"],
        "DRAFT_ROUND": ["1"],
        "DRAFT_NUMBER": ["1"],
    }


@pytest.fixture
def sample_player_with_all_fields_df(sample_player_with_all_fields):
    """Sample player data with all fields as DataFrame."""
    return pd.DataFrame(sample_player_with_all_fields)


# =============================================================================
# Sample Data Fixtures - Games
# =============================================================================


@pytest.fixture
def sample_game_api_data():
    """Sample raw game data from nba_api LeagueGameFinder.

    Note: Each game appears twice (once for each team).
    """
    return {
        "GAME_ID": ["0022400001", "0022400001", "0022400002", "0022400002"],
        "GAME_DATE": ["2024-10-22", "2024-10-22", "2024-10-22", "2024-10-22"],
        "TEAM_ID": [1610612738, 1610612752, 1610612755, 1610612749],
        "TEAM_ABBREVIATION": ["BOS", "NYK", "PHI", "MIL"],
        "TEAM_NAME": ["Boston Celtics", "New York Knicks", "Philadelphia 76ers", "Milwaukee Bucks"],
        "MATCHUP": ["BOS vs. NYK", "NYK @ BOS", "PHI vs. MIL", "MIL @ PHI"],
        "PTS": [132, 109, 117, 118],
        "WL": ["W", "L", "L", "W"],
        "SEASON_ID": ["22024", "22024", "22024", "22024"],
    }


@pytest.fixture
def sample_game_dataframe(sample_game_api_data):
    """Sample game data as DataFrame."""
    return pd.DataFrame(sample_game_api_data)


@pytest.fixture
def sample_transformed_game_data():
    """Sample transformed game data matching database schema."""
    return [
        {
            "game_id": "0022400001",
            "season": 2024,
            "season_type": "Regular Season",
            "game_date": pd.to_datetime("2024-10-22").date(),
            "home_team_id": 1610612738,
            "away_team_id": 1610612752,
            "home_score": 132,
            "away_score": 109,
            "winner_team_id": 1610612738,
            "status": "final",
        },
        {
            "game_id": "0022400002",
            "season": 2024,
            "season_type": "Regular Season",
            "game_date": pd.to_datetime("2024-10-22").date(),
            "home_team_id": 1610612755,
            "away_team_id": 1610612749,
            "home_score": 117,
            "away_score": 118,
            "winner_team_id": 1610612749,
            "status": "final",
        },
    ]


# =============================================================================
# Sample Data Fixtures - Player Stats
# =============================================================================


@pytest.fixture
def sample_player_stats_api_data():
    """Sample raw player game stats from nba_api PlayerGameLogs."""
    return {
        "PLAYER_ID": [2544, 2544, 201939],
        "PLAYER_NAME": ["LeBron James", "LeBron James", "Stephen Curry"],
        "TEAM_ID": [1610612747, 1610612747, 1610612744],
        "TEAM_ABBREVIATION": ["LAL", "LAL", "GSW"],
        "GAME_ID": ["0022400001", "0022400005", "0022400001"],
        "GAME_DATE": ["2024-10-22", "2024-10-24", "2024-10-22"],
        "MIN": [34.5, 36.2, 32.1],
        "PTS": [25, 32, 28],
        "FGM": [10, 12, 9],
        "FGA": [18, 22, 19],
        "FG_PCT": [0.556, 0.545, 0.474],
        "FG3M": [3, 4, 5],
        "FG3A": [7, 8, 12],
        "FG3_PCT": [0.429, 0.5, 0.417],
        "FTM": [2, 4, 5],
        "FTA": [3, 5, 6],
        "FT_PCT": [0.667, 0.8, 0.833],
        "OREB": [1, 2, 0],
        "DREB": [8, 6, 5],
        "REB": [9, 8, 5],
        "AST": [8, 9, 7],
        "STL": [1, 2, 1],
        "BLK": [0, 1, 0],
        "TOV": [4, 3, 2],
        "PF": [2, 3, 2],
        "PLUS_MINUS": [12, 8, -5],
    }


@pytest.fixture
def sample_player_stats_dataframe(sample_player_stats_api_data):
    """Sample player stats as DataFrame."""
    return pd.DataFrame(sample_player_stats_api_data)


@pytest.fixture
def sample_transformed_player_stats():
    """Sample transformed player stats matching database schema."""
    return [
        {
            "stat_id": 12345,  # Generated from hash
            "game_id": "0022400001",
            "player_id": 2544,
            "team_id": 1610612747,
            "minutes_played": 34.5,
            "points": 25,
            "rebounds_offensive": 1,
            "rebounds_defensive": 8,
            "assists": 8,
            "steals": 1,
            "blocks": 0,
            "turnovers": 4,
            "personal_fouls": 2,
            "fg_made": 10,
            "fg_attempted": 18,
            "fg3_made": 3,
            "fg3_attempted": 7,
            "ft_made": 2,
            "ft_attempted": 3,
        },
    ]


# =============================================================================
# Mock NBA API Endpoints
# =============================================================================


@pytest.fixture
def mock_common_all_players(sample_player_dataframe):
    """Mock CommonAllPlayers endpoint."""
    with patch("scripts.etl_players.CommonAllPlayers") as mock_class:
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [sample_player_dataframe]
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_league_game_finder(sample_game_dataframe):
    """Mock LeagueGameFinder endpoint."""
    with patch("scripts.etl_games.LeagueGameFinder") as mock_class:
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [sample_game_dataframe]
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_player_game_logs(sample_player_stats_dataframe):
    """Mock PlayerGameLogs endpoint."""
    with patch("scripts.etl_stats.PlayerGameLogs") as mock_class:
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [sample_player_stats_dataframe]
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_get_teams(sample_team_data):
    """Mock get_teams static function."""
    with patch("scripts.etl_teams.get_teams") as mock:
        mock.return_value = sample_team_data
        yield mock


# =============================================================================
# ETL Module Mocks for run_all_etl tests
# =============================================================================


@pytest.fixture
def mock_etl_modules():
    """Mock all individual ETL modules for run_all_etl tests."""
    with (
        patch("scripts.run_all_etl.run_teams_etl") as mock_teams,
        patch("scripts.run_all_etl.run_players_etl") as mock_players,
        patch("scripts.run_all_etl.run_games_etl") as mock_games,
        patch("scripts.run_all_etl.run_stats_etl") as mock_stats,
    ):
        # Set up default success returns
        mock_teams.return_value = {
            "status": "success",
            "extracted": 30,
            "loaded": 30,
            "error": None,
        }
        mock_players.return_value = {
            "status": "success",
            "extracted": 500,
            "loaded": 500,
            "error": None,
        }
        mock_games.return_value = {
            "status": "success",
            "extracted": 2460,
            "loaded": 1230,
            "season": "2024-25",
            "season_type": "Regular Season",
            "error": None,
        }
        mock_stats.return_value = {
            "status": "success",
            "extracted": 15000,
            "loaded": 15000,
            "season": "2024-25",
            "season_type": "Regular Season",
            "error": None,
        }

        yield {
            "teams": mock_teams,
            "players": mock_players,
            "games": mock_games,
            "stats": mock_stats,
        }


@pytest.fixture
def mock_set_app_metadata():
    """Mock set_app_metadata function."""
    with patch("scripts.run_all_etl.set_app_metadata") as mock:
        yield mock
