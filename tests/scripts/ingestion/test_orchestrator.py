"""Tests for ingestion orchestrator."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from scripts.ingestion.exceptions import IngestionError
from scripts.ingestion.orchestrator import IngestionOrchestrator, IngestionReport


class TestIngestionReport:
    """Tests for IngestionReport class."""

    def test_report_initialization(self):
        """Test basic report initialization."""
        report = IngestionReport()
        assert report.status == "pending"
        assert report.total_rows == 0
        assert report.phases == {}
        assert report.errors == []
        assert isinstance(report.start_time, datetime)
        assert report.end_time is None

    def test_add_phase_result(self):
        """Test adding phase result."""
        report = IngestionReport()
        report.add_phase_result(
            phase="test_phase", rows=100, duration=1.5, status="success", details={"test": "data"}
        )

        assert report.total_rows == 100
        assert "test_phase" in report.phases
        assert report.phases["test_phase"]["status"] == "success"
        assert report.phases["test_phase"]["rows"] == 100

    def test_add_error(self):
        """Test adding error."""
        report = IngestionReport()
        error = ValueError("test error")
        report.add_error("test_phase", error)

        assert len(report.errors) == 1
        assert report.errors[0]["phase"] == "test_phase"
        assert report.errors[0]["message"] == "test error"

    def test_finalize(self):
        """Test report finalization."""
        report = IngestionReport()
        report.finalize("success")

        assert report.status == "success"
        assert report.end_time is not None
        assert report.duration is not None


class TestIngestionOrchestrator:
    """Tests for IngestionOrchestrator class."""

    @pytest.fixture
    def orchestrator(self):
        """Fixture for orchestrator."""
        return IngestionOrchestrator()

    @pytest.fixture
    def mock_loader(self):
        """Fixture for mock loader."""
        loader = MagicMock()
        loader.load.return_value = 100
        loader.get_row_count.return_value = 100
        return loader

    def test_register_loader(self, orchestrator, mock_loader):
        """Test registering a loader."""
        orchestrator.register_loader(mock_loader, phase="reference")
        assert len(orchestrator.loaders) == 1
        assert len(orchestrator._phase_loaders["reference"]) == 1

    def test_register_loader_invalid_phase(self, orchestrator, mock_loader):
        """Test registering with invalid phase."""
        with pytest.raises(ValueError, match="Unknown phase"):
            orchestrator.register_loader(mock_loader, phase="invalid_phase")

    def test_run_ingestion_success(self, orchestrator, mock_loader):
        """Test successful ingestion run."""
        orchestrator.register_loader(mock_loader, phase="reference")

        report = orchestrator.run_ingestion(phases=["reference"])

        assert report.status == "success"
        assert report.total_rows == 100
        assert mock_loader.load.called

    def test_run_ingestion_dry_run(self, orchestrator, mock_loader):
        """Test dry run ingestion."""
        orchestrator.register_loader(mock_loader, phase="reference")

        report = orchestrator.run_ingestion(phases=["reference"], dry_run=True)

        assert report.status == "success"
        assert report.total_rows == 100
        assert not mock_loader.load.called
        assert mock_loader.get_row_count.called

    def test_run_ingestion_partial_failure(self, orchestrator):
        """Test ingestion with some failures."""
        loader1 = MagicMock()
        loader1.load.return_value = 50
        loader2 = MagicMock()
        loader2.load.side_effect = Exception("Load failed")

        orchestrator.register_loader(loader1, phase="reference")
        orchestrator.register_loader(loader2, phase="reference")

        report = orchestrator.run_ingestion(phases=["reference"])

        assert report.status == "partial"
        assert report.total_rows == 50
        assert len(report.errors) == 1

    def test_run_ingestion_pipeline_failure(self, orchestrator):
        """Test catastrophic pipeline failure."""
        with (
            patch.object(orchestrator, "_run_phase", side_effect=Exception("Pipeline crash")),
            pytest.raises(IngestionError),
        ):
            orchestrator.run_ingestion(phases=["reference"])

    def test_validate_data(self, orchestrator):
        """Test data validation."""
        validator = MagicMock()
        validator.validate.return_value = True
        orchestrator.register_validator(validator)

        results = orchestrator.validate_data()

        assert len(results) == 1
        assert list(results.values())[0]["passed"] is True

    def test_reset(self, orchestrator, mock_loader):
        """Test resetting orchestrator state."""
        orchestrator.register_loader(mock_loader, phase="reference")
        orchestrator.run_ingestion(phases=["reference"])

        assert len(orchestrator.loaders) == 1
        assert orchestrator.report is not None

        orchestrator.reset()

        assert len(orchestrator.loaders) == 0
        assert orchestrator.report is None
        assert len(orchestrator._phase_loaders["reference"]) == 0
