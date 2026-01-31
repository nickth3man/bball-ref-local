"""Main orchestration for the data ingestion pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from scripts.ingestion.config import INGESTION_PHASES
from scripts.ingestion.exceptions import IngestionError
from scripts.ingestion.logger import configure_root_logger, get_logger

logger = get_logger(__name__)


@dataclass
class IngestionReport:
    """Report of ingestion pipeline execution."""

    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    phases: dict = field(default_factory=dict)
    total_rows: int = 0
    errors: list = field(default_factory=list)
    status: str = "pending"

    def add_phase_result(self, phase, rows, duration, status, details=None):
        """Add a phase result to the report."""
        self.phases[phase] = {
            "rows": rows,
            "duration_seconds": round(duration, 2),
            "status": status,
            "details": details or {},
        }
        self.total_rows += rows

    def add_error(self, phase, error):
        """Add an error to the report."""
        self.errors.append(
            {
                "phase": phase,
                "type": type(error).__name__,
                "message": str(error),
                "timestamp": datetime.now().isoformat(),
            }
        )

    def finalize(self, status):
        """Finalize the report with end time and status."""
        self.end_time = datetime.now()
        self.status = status

    def to_dict(self):
        """Convert report to dictionary."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration,
            "status": self.status,
            "total_rows": self.total_rows,
            "phases": self.phases,
            "errors": self.errors,
        }

    @property
    def duration(self):
        """Calculate total duration in seconds."""
        if self.end_time:
            return round((self.end_time - self.start_time).total_seconds(), 2)
        return None

    def __str__(self):
        """Return formatted report string."""
        lines = ["=" * 60, "INGESTION REPORT", "=" * 60]
        lines.append(f"Status: {self.status.upper()}")
        if self.duration:
            lines.append(f"Duration: {self.duration}s")
        else:
            lines.append("Duration: N/A")
        lines.append(f"Total Rows: {self.total_rows}")
        lines.append("-" * 60)
        for phase, result in self.phases.items():
            lines.append(f"Phase: {phase}")
            status_val = result.get("status", "unknown")
            rows_val = result.get("rows", 0)
            dur_val = result.get("duration_seconds", 0)
            lines.append(f"  Status: {status_val}")
            lines.append(f"  Rows: {rows_val}")
            lines.append(f"  Duration: {dur_val}s")
        if self.errors:
            lines.append("-" * 60)
            lines.append(f"ERRORS ({len(self.errors)}):")
            for error in self.errors:
                phase_val = error.get("phase", "unknown")
                type_val = error.get("type", "Error")
                msg_val = error.get("message", "")
                lines.append(f"  [{phase_val}] {type_val}: {msg_val}")
        lines.append("=" * 60)
        return chr(10).join(lines)


class IngestionOrchestrator:
    """Orchestrates the entire ingestion pipeline."""

    def __init__(self):
        """Initialize the orchestrator."""
        self.loaders = []
        self.validators = []
        self.report = None
        self._phase_loaders = {phase: [] for phase in INGESTION_PHASES}
        configure_root_logger()
        logger.info("IngestionOrchestrator initialized")

    def register_loader(self, loader, phase=None):
        """Register a data loader."""
        self.loaders.append(loader)
        if phase:
            if phase not in INGESTION_PHASES:
                raise ValueError(f"Unknown phase: {phase}")
            self._phase_loaders[phase].append(loader)
            logger.debug(f"Registered {loader.__class__.__name__} for phase {phase}")
        else:
            for phase_loaders in self._phase_loaders.values():
                phase_loaders.append(loader)
            logger.debug(f"Registered {loader.__class__.__name__} for all phases")

    def register_validator(self, validator):
        """Register a data validator."""
        self.validators.append(validator)
        logger.debug(f"Registered validator: {validator.__class__.__name__}")

    def run_ingestion(self, phases=None, dry_run=False):
        """Run the ingestion pipeline."""
        phases_to_run = phases or INGESTION_PHASES
        invalid_phases = set(phases_to_run) - set(INGESTION_PHASES)
        if invalid_phases:
            raise ValueError(f"Invalid phases: {invalid_phases}")
        self.report = IngestionReport()
        logger.info(f"Starting ingestion pipeline for phases: {phases_to_run}")
        if dry_run:
            logger.info("DRY RUN MODE: No data will be loaded")
        try:
            for phase in phases_to_run:
                self._run_phase(phase, dry_run)
            if self.report.errors:
                status = "partial" if self.report.total_rows > 0 else "failed"
            else:
                status = "success"
            self.report.finalize(status)
            logger.info(f"Ingestion pipeline completed with status: {status}")
        except Exception as e:
            self.report.add_error("orchestrator", e)
            self.report.finalize("failed")
            logger.error(f"Ingestion pipeline failed: {e}")
            raise IngestionError(f"Pipeline execution failed: {e}") from e
        return self.report

    def _run_phase(self, phase, dry_run):
        """Run a single ingestion phase."""
        logger.info(f"Starting phase: {phase}")
        phase_start = datetime.now()
        phase_rows = 0
        phase_status = "success"
        loaders = self._phase_loaders.get(phase, [])
        if not loaders:
            logger.warning(f"No loaders registered for phase: {phase}")
            self.report.add_phase_result(
                phase=phase,
                rows=0,
                duration=0,
                status="skipped",
                details={"reason": "No loaders registered"},
            )
            return
        for loader in loaders:
            try:
                if dry_run:
                    row_count = loader.get_row_count()
                    logger.info(f"[DRY RUN] {loader.__class__.__name__}: {row_count} rows")
                    phase_rows += row_count
                else:
                    rows = loader.load()
                    phase_rows += rows
                    logger.info(f"{loader.__class__.__name__} loaded {rows} rows")
            except Exception as e:
                logger.error(f"Loader {loader.__class__.__name__} failed: {e}")
                self.report.add_error(phase, e)
                phase_status = "partial"
        phase_duration = (datetime.now() - phase_start).total_seconds()
        self.report.add_phase_result(
            phase=phase,
            rows=phase_rows,
            duration=phase_duration,
            status=phase_status,
            details={"loaders": len(loaders)},
        )
        logger.info(f"Phase {phase} completed: {phase_rows} rows in {phase_duration:.2f}s")

    def validate_data(self):
        """Run validation checks on loaded data."""
        logger.info("Running data validation checks")
        results = {}
        for validator in self.validators:
            try:
                validator_name = validator.__class__.__name__
                logger.debug(f"Running validator: {validator_name}")
                result = validator.validate()
                results[validator_name] = {"passed": result, "errors": []}
            except Exception as e:
                logger.error(f"Validator {validator.__class__.__name__} failed: {e}")
                results[validator.__class__.__name__] = {"passed": False, "errors": [str(e)]}
        return results

    def generate_report(self):
        """Generate or retrieve the ingestion report."""
        return self.report

    def save_report(self, output_path):
        """Save the ingestion report to a file."""
        if not self.report:
            raise ValueError("No report available. Run ingestion first.")
        import json

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(self.report.to_dict(), f, indent=2)
        logger.info(f"Report saved to {output_path}")

    def reset(self):
        """Reset the orchestrator state."""
        self.loaders = []
        self.validators = []
        self.report = None
        self._phase_loaders = {phase: [] for phase in INGESTION_PHASES}
        logger.info("Orchestrator state reset")

    def __repr__(self):
        """Return string representation."""
        return f"IngestionOrchestrator(loaders={len(self.loaders)}, validators={len(self.validators)}, phases={len(INGESTION_PHASES)})"
