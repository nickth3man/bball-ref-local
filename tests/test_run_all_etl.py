"""Tests for ETL orchestrator (run_all_etl)."""

import sys
from pathlib import Path
from unittest.mock import patch

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.run_all_etl import (
    print_summary,
    run_etl_pipeline,
)


class TestRunETLPipeline:
    """Tests for run_etl_pipeline function."""

    def test_run_etl_pipeline_calls_all_etls(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline calls all ETL modules in order."""
        result = run_etl_pipeline()

        mock_etl_modules["teams"].assert_called_once()
        mock_etl_modules["players"].assert_called_once_with(active_only=True)
        mock_etl_modules["games"].assert_called_once()
        mock_etl_modules["stats"].assert_called_once()

        # Verify order by checking call counts
        assert result["steps"]["teams"]["status"] == "success"
        assert result["steps"]["players"]["status"] == "success"
        assert result["steps"]["games"]["status"] == "success"
        assert result["steps"]["stats"]["status"] == "success"

    def test_run_etl_pipeline_with_season(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline passes season parameter."""
        result = run_etl_pipeline(season="2023-24", season_type="Regular Season")

        # Games and stats should receive season parameter
        mock_etl_modules["games"].assert_called_once_with(
            season="2023-24", season_type="Regular Season"
        )
        mock_etl_modules["stats"].assert_called_once_with(
            season="2023-24", season_type="Regular Season", batch_size=1000
        )

        assert result["season"] == "2023-24"
        assert result["season_type"] == "Regular Season"

    def test_run_etl_pipeline_with_playoffs(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline with playoffs season type."""
        result = run_etl_pipeline(season="2023-24", season_type="Playoffs")

        mock_etl_modules["games"].assert_called_once_with(season="2023-24", season_type="Playoffs")
        mock_etl_modules["stats"].assert_called_once_with(
            season="2023-24", season_type="Playoffs", batch_size=1000
        )

    def test_run_etl_pipeline_with_batch_size(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline with custom batch size."""
        result = run_etl_pipeline(batch_size=500)

        mock_etl_modules["stats"].assert_called_once_with(
            season=None, season_type="Regular Season", batch_size=500
        )

    def test_run_etl_pipeline_skip_teams(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline can skip teams ETL."""
        result = run_etl_pipeline(skip_teams=True)

        mock_etl_modules["teams"].assert_not_called()
        mock_etl_modules["players"].assert_called_once()
        mock_etl_modules["games"].assert_called_once()
        mock_etl_modules["stats"].assert_called_once()

        assert result["steps"]["teams"]["status"] == "skipped"

    def test_run_etl_pipeline_skip_players(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline can skip players ETL."""
        result = run_etl_pipeline(skip_players=True)

        mock_etl_modules["teams"].assert_called_once()
        mock_etl_modules["players"].assert_not_called()
        mock_etl_modules["games"].assert_called_once()
        mock_etl_modules["stats"].assert_called_once()

        assert result["steps"]["players"]["status"] == "skipped"

    def test_run_etl_pipeline_skip_games(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline can skip games ETL."""
        result = run_etl_pipeline(skip_games=True)

        mock_etl_modules["teams"].assert_called_once()
        mock_etl_modules["players"].assert_called_once()
        mock_etl_modules["games"].assert_not_called()
        mock_etl_modules["stats"].assert_called_once()

        assert result["steps"]["games"]["status"] == "skipped"

    def test_run_etl_pipeline_skip_stats(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline can skip stats ETL."""
        result = run_etl_pipeline(skip_stats=True)

        mock_etl_modules["teams"].assert_called_once()
        mock_etl_modules["players"].assert_called_once()
        mock_etl_modules["games"].assert_called_once()
        mock_etl_modules["stats"].assert_not_called()

        assert result["steps"]["stats"]["status"] == "skipped"

    def test_run_etl_pipeline_skip_multiple(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline can skip multiple ETLs."""
        result = run_etl_pipeline(skip_teams=True, skip_players=True)

        mock_etl_modules["teams"].assert_not_called()
        mock_etl_modules["players"].assert_not_called()
        mock_etl_modules["games"].assert_called_once()
        mock_etl_modules["stats"].assert_called_once()

        assert result["steps"]["teams"]["status"] == "skipped"
        assert result["steps"]["players"]["status"] == "skipped"

    def test_run_etl_pipeline_calculates_total_loaded(
        self, mock_etl_modules, mock_set_app_metadata
    ):
        """Test pipeline calculates total records loaded."""
        result = run_etl_pipeline()

        # 30 + 500 + 1230 + 15000 = 16760
        assert result["total_loaded"] == 16760

    def test_run_etl_pipeline_tracks_duration(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline tracks execution duration."""
        result = run_etl_pipeline()

        assert "start_time" in result
        assert "end_time" in result
        assert "duration_seconds" in result
        assert result["duration_seconds"] >= 0

    def test_run_etl_pipeline_updates_metadata(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline updates app metadata."""
        result = run_etl_pipeline(season="2024-25")

        # Should update metadata 3 times
        assert mock_set_app_metadata.call_count == 3
        mock_set_app_metadata.assert_any_call("last_etl_run", result["end_time"])
        mock_set_app_metadata.assert_any_call("last_etl_season", "2024-25")
        mock_set_app_metadata.assert_any_call("last_etl_status", result["status"])

    def test_run_etl_pipeline_handles_team_failure(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline continues when teams ETL fails."""
        mock_etl_modules["teams"].return_value = {
            "status": "failed",
            "extracted": 0,
            "loaded": 0,
            "error": "API Timeout",
        }

        result = run_etl_pipeline()

        # Should continue with other ETLs
        mock_etl_modules["players"].assert_called_once()
        mock_etl_modules["games"].assert_called_once()
        mock_etl_modules["stats"].assert_called_once()

        assert result["steps"]["teams"]["status"] == "failed"
        assert result["status"] == "completed_with_errors"
        assert "Teams ETL failed" in result["errors"][0]

    def test_run_etl_pipeline_handles_player_failure(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline continues when players ETL fails."""
        mock_etl_modules["players"].return_value = {
            "status": "failed",
            "extracted": 0,
            "loaded": 0,
            "error": "API Error",
        }

        result = run_etl_pipeline()

        # Should continue with other ETLs
        assert result["steps"]["teams"]["status"] == "success"
        assert result["steps"]["players"]["status"] == "failed"
        assert result["steps"]["games"]["status"] == "success"
        assert result["steps"]["stats"]["status"] == "success"

    def test_run_etl_pipeline_handles_exception(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline handles exceptions gracefully."""
        mock_etl_modules["teams"].side_effect = Exception("Unexpected Error")

        result = run_etl_pipeline()

        # Should continue with other ETLs
        assert result["steps"]["teams"]["status"] == "failed"
        assert result["steps"]["teams"]["error"] == "Teams ETL error"
        assert result["steps"]["players"]["status"] == "success"

    def test_run_etl_pipeline_all_failures(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline handles all ETLs failing."""
        for mock in mock_etl_modules.values():
            mock.return_value = {
                "status": "failed",
                "extracted": 0,
                "loaded": 0,
                "error": "API Error",
            }

        result = run_etl_pipeline()

        assert result["status"] == "completed_with_errors"
        assert len(result["errors"]) == 4
        assert result["total_loaded"] == 0

    def test_run_etl_pipeline_success_status(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline returns success when all ETLs succeed."""
        result = run_etl_pipeline()

        assert result["status"] == "success"
        assert len(result["errors"]) == 0

    def test_run_etl_pipeline_result_structure(self, mock_etl_modules, mock_set_app_metadata):
        """Test pipeline returns properly structured result."""
        result = run_etl_pipeline()

        assert "start_time" in result
        assert "end_time" in result
        assert "duration_seconds" in result
        assert "season" in result
        assert "season_type" in result
        assert "steps" in result
        assert "total_loaded" in result
        assert "status" in result
        assert "errors" in result

        # Check steps structure
        for step_name in ["teams", "players", "games", "stats"]:
            assert step_name in result["steps"]
            assert "status" in result["steps"][step_name]


class TestPrintSummary:
    """Tests for print_summary function."""

    def test_print_summary_logs_results(self, caplog):
        """Test print_summary logs ETL results."""
        results = {
            "season": "2024-25",
            "season_type": "Regular Season",
            "status": "success",
            "duration_seconds": 45.5,
            "total_loaded": 16760,
            "steps": {
                "teams": {"status": "success", "extracted": 30, "loaded": 30},
                "players": {"status": "success", "extracted": 500, "loaded": 500},
                "games": {"status": "success", "extracted": 2460, "loaded": 1230},
                "stats": {"status": "success", "extracted": 15000, "loaded": 15000},
            },
            "errors": [],
        }

        with caplog.at_level("INFO"):
            print_summary(results)

        # Check that summary information is logged
        assert "ETL PIPELINE SUMMARY" in caplog.text
        assert "2024-25" in caplog.text
        assert "success" in caplog.text
        assert "45.5" in caplog.text or "45" in caplog.text
        assert "16,760" in caplog.text

    def test_print_summary_shows_failed_steps(self, caplog):
        """Test print_summary shows failed steps."""
        results = {
            "season": "2024-25",
            "season_type": "Regular Season",
            "status": "completed_with_errors",
            "duration_seconds": 30.0,
            "total_loaded": 500,
            "steps": {
                "teams": {"status": "failed", "error": "API Timeout"},
                "players": {"status": "success", "extracted": 500, "loaded": 500},
                "games": {"status": "skipped"},
                "stats": {"status": "skipped"},
            },
            "errors": ["Teams ETL failed: API Timeout"],
        }

        with caplog.at_level("INFO"):
            print_summary(results)

        assert "TEAMS" in caplog.text
        assert "failed" in caplog.text
        assert "API Timeout" in caplog.text

    def test_print_summary_shows_skipped_steps(self, caplog):
        """Test print_summary shows skipped steps."""
        results = {
            "season": "2024-25",
            "season_type": "Regular Season",
            "status": "success",
            "duration_seconds": 20.0,
            "total_loaded": 530,
            "steps": {
                "teams": {"status": "success", "extracted": 30, "loaded": 30},
                "players": {"status": "success", "extracted": 500, "loaded": 500},
                "games": {"status": "skipped"},
                "stats": {"status": "skipped"},
            },
            "errors": [],
        }

        with caplog.at_level("INFO"):
            print_summary(results)

        assert "GAMES" in caplog.text
        assert "STATS" in caplog.text
        assert "skipped" in caplog.text

    def test_print_summary_shows_error_list(self, caplog):
        """Test print_summary shows error list."""
        results = {
            "season": "2024-25",
            "season_type": "Regular Season",
            "status": "completed_with_errors",
            "duration_seconds": 25.0,
            "total_loaded": 0,
            "steps": {},
            "errors": [
                "Teams ETL failed: API Error",
                "Players ETL failed: DB Error",
            ],
        }

        with caplog.at_level("INFO"):
            print_summary(results)

        assert "ERRORS" in caplog.text
        assert "Teams ETL failed" in caplog.text
        assert "Players ETL failed" in caplog.text


class TestMainFunction:
    """Tests for main function and CLI argument parsing."""

    @patch("scripts.run_all_etl.run_etl_pipeline")
    @patch("sys.argv", ["run_all_etl.py"])
    def test_main_default_args(self, mock_pipeline):
        """Test main with default arguments."""
        mock_pipeline.return_value = {
            "status": "success",
            "total_loaded": 100,
            "steps": {},
            "errors": [],
        }

        from scripts.run_all_etl import main

        result = main()

        assert result == 0
        mock_pipeline.assert_called_once_with(
            season=None,
            season_type="Regular Season",
            skip_teams=False,
            skip_players=False,
            skip_games=False,
            skip_stats=False,
            batch_size=1000,
        )

    @patch("scripts.run_all_etl.run_etl_pipeline")
    @patch("sys.argv", ["run_all_etl.py", "--season", "2023-24", "--season-type", "Playoffs"])
    def test_main_with_season_args(self, mock_pipeline):
        """Test main with season arguments."""
        mock_pipeline.return_value = {
            "status": "success",
            "total_loaded": 100,
            "steps": {},
            "errors": [],
        }

        from scripts.run_all_etl import main

        result = main()

        assert result == 0
        mock_pipeline.assert_called_once_with(
            season="2023-24",
            season_type="Playoffs",
            skip_teams=False,
            skip_players=False,
            skip_games=False,
            skip_stats=False,
            batch_size=1000,
        )

    @patch("scripts.run_all_etl.run_etl_pipeline")
    @patch("sys.argv", ["run_all_etl.py", "--skip-teams", "--skip-players"])
    def test_main_with_skip_args(self, mock_pipeline):
        """Test main with skip arguments."""
        mock_pipeline.return_value = {
            "status": "success",
            "total_loaded": 100,
            "steps": {},
            "errors": [],
        }

        from scripts.run_all_etl import main

        result = main()

        assert result == 0
        mock_pipeline.assert_called_once_with(
            season=None,
            season_type="Regular Season",
            skip_teams=True,
            skip_players=True,
            skip_games=False,
            skip_stats=False,
            batch_size=1000,
        )

    @patch("scripts.run_all_etl.run_etl_pipeline")
    @patch("sys.argv", ["run_all_etl.py", "--batch-size", "500"])
    def test_main_with_batch_size(self, mock_pipeline):
        """Test main with custom batch size."""
        mock_pipeline.return_value = {
            "status": "success",
            "total_loaded": 100,
            "steps": {},
            "errors": [],
        }

        from scripts.run_all_etl import main

        result = main()

        assert result == 0
        mock_pipeline.assert_called_once_with(
            season=None,
            season_type="Regular Season",
            skip_teams=False,
            skip_players=False,
            skip_games=False,
            skip_stats=False,
            batch_size=500,
        )

    @patch("scripts.run_all_etl.run_etl_pipeline")
    @patch("sys.argv", ["run_all_etl.py"])
    def test_main_returns_success_exit_code(self, mock_pipeline):
        """Test main returns 0 on success."""
        mock_pipeline.return_value = {"status": "success"}

        from scripts.run_all_etl import main

        result = main()

        assert result == 0

    @patch("scripts.run_all_etl.run_etl_pipeline")
    @patch("sys.argv", ["run_all_etl.py"])
    def test_main_returns_error_exit_code(self, mock_pipeline):
        """Test main returns 1 on failure."""
        mock_pipeline.return_value = {"status": "failed"}

        from scripts.run_all_etl import main

        result = main()

        assert result == 1

    @patch("scripts.run_all_etl.run_etl_pipeline")
    @patch("sys.argv", ["run_all_etl.py"])
    def test_main_returns_zero_on_completed_with_errors(self, mock_pipeline):
        """Test main returns 0 when completed with errors (partial success)."""
        mock_pipeline.return_value = {"status": "completed_with_errors"}

        from scripts.run_all_etl import main

        result = main()

        assert result == 0

    @patch(
        "sys.argv",
        ["run_all_etl.py", "--skip-teams", "--skip-players", "--skip-games", "--skip-stats"],
    )
    def test_main_validates_skip_all(self):
        """Test main validates that not all steps can be skipped."""
        from scripts.run_all_etl import main

        result = main()

        assert result == 1

    @patch("scripts.run_all_etl.set_app_metadata")
    @patch("scripts.run_all_etl.run_etl_pipeline")
    @patch("sys.argv", ["run_all_etl.py", "--verbose"])
    def test_main_verbose_mode(self, mock_pipeline, mock_set_metadata, caplog):
        """Test main enables verbose logging."""
        mock_pipeline.return_value = {"status": "success"}

        from scripts.run_all_etl import main

        with caplog.at_level("DEBUG"):
            main()

        # Pipeline should still run
        mock_pipeline.assert_called_once()
