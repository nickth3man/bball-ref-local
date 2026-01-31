"""Generate validation reports in multiple formats."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ReportSection:
    """A section of a validation report."""

    title: str
    status: str = "pending"
    items: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def add_item(self, item: dict[str, Any]) -> None:
        """Add an item to the section."""
        self.items.append(item)

    def set_summary(self, summary: dict[str, Any]) -> None:
        """Set the section summary."""
        self.summary = summary

    def to_dict(self) -> dict[str, Any]:
        """Convert section to dictionary."""
        return {
            "title": self.title,
            "status": self.status,
            "summary": self.summary,
            "items": self.items,
            "item_count": len(self.items),
        }


class ReportFormatter:
    """Handles formatting of report data for different output formats."""

    @staticmethod
    def format_json_item(item: dict[str, Any]) -> str:
        """Format an item as indented JSON."""
        return json.dumps(item, indent=2)

    @staticmethod
    def truncate_items(items: list[Any], limit: int) -> tuple[list[Any], int]:
        """Truncate items to limit and return remaining count.

        Args:
            items: List of items to potentially truncate
            limit: Maximum number of items to return

        Returns:
            Tuple of (truncated_items, remaining_count)
        """
        if len(items) <= limit:
            return items, 0
        return items[:limit], len(items) - limit


class ValidationReport:
    """Generates validation reports in multiple formats."""

    # Format-specific limits
    HTML_ITEM_LIMIT = 100
    MARKDOWN_ITEM_LIMIT = 50
    TEXT_ITEM_LIMIT = 20

    # HTML template constants
    HTML_STYLE = """
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
        .summary { background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .status-passed { color: green; }
        .status-failed { color: red; }
        .status-pending { color: orange; }
        table { border-collapse: collapse; width: 100%; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .section { margin: 30px 0; }
        .no-issues { color: green; font-style: italic; }
    </style>
    """

    def __init__(self, title: str = "Data Validation Report"):
        self.title = title
        self.generated_at = datetime.now()
        self.sections: list[ReportSection] = []
        self.metadata: dict[str, Any] = {}
        self.formatter = ReportFormatter()

    def add_section(
        self, title: str, results: list[dict[str, Any]], status: str = "pending"
    ) -> ReportSection:
        """Add a validation section."""
        section = ReportSection(title, status)
        for result in results:
            section.add_item(result)
        self.sections.append(section)
        return section

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the report."""
        self.metadata[key] = value

    def generate_summary(self) -> dict[str, Any]:
        """Generate executive summary."""
        total_issues = sum(len(s.items) for s in self.sections)
        sections_with_issues = sum(1 for s in self.sections if s.items)

        return {
            "title": self.title,
            "generated_at": self.generated_at.isoformat(),
            "total_sections": len(self.sections),
            "sections_with_issues": sections_with_issues,
            "total_issues": total_issues,
            "status": "failed" if total_issues > 0 else "passed",
        }

    def _build_html_section(self, section: ReportSection) -> str:
        """Build HTML for a single section."""
        html = f"""
    <div class="section">
        <h2>{section.title} <span class="status-{section.status}">({section.status})</span></h2>
"""
        if section.summary:
            html += f"""
        <div class="summary">
            <pre>{self.formatter.format_json_item(section.summary)}</pre>
        </div>
"""

        if section.items:
            items, remaining = self.formatter.truncate_items(
                section.items, self.HTML_ITEM_LIMIT
            )
            html += """
        <table>
            <tr>
                <th>#</th>
                <th>Details</th>
            </tr>
"""
            for i, item in enumerate(items, 1):
                html += f"""
            <tr>
                <td>{i}</td>
                <td><pre>{self.formatter.format_json_item(item)}</pre></td>
            </tr>
"""
            if remaining:
                html += f"""
            <tr>
                <td colspan="2"><em>... and {remaining} more issues</em></td>
            </tr>
"""
            html += "</table>"
        else:
            html += '<p class="no-issues">No issues found</p>'

        html += "</div>"
        return html

    def generate_html_report(self, output_path: str | Path) -> str:
        """Generate HTML report with tables."""
        summary = self.generate_summary()

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{self.title}</title>
    {self.HTML_STYLE}
</head>
<body>
    <h1>{self.title}</h1>
    <p>Generated: {self.generated_at.strftime("%Y-%m-%d %H:%M:%S")}</p>
    
    <div class="summary">
        <h2>Executive Summary</h2>
        <p>Status: <span class="status-{summary["status"]}">{summary["status"].upper()}</span></p>
        <p>Total Sections: {summary["total_sections"]}</p>
        <p>Sections with Issues: {summary["sections_with_issues"]}</p>
        <p>Total Issues: {summary["total_issues"]}</p>
    </div>
"""

        for section in self.sections:
            html += self._build_html_section(section)

        html += """
</body>
</html>
"""

        output = Path(output_path)
        output.write_text(html, encoding="utf-8")
        logger.info(f"HTML report written to {output_path}")
        return html

    def _build_markdown_section(self, section: ReportSection) -> str:
        """Build Markdown for a single section."""
        md = f"""## {section.title}

**Status**: {section.status}

"""
        if section.summary:
            md += f"""### Summary

```json
{self.formatter.format_json_item(section.summary)}
```

"""

        if section.items:
            items, remaining = self.formatter.truncate_items(
                section.items, self.MARKDOWN_ITEM_LIMIT
            )
            md += f"""### Issues ({len(section.items)} total)

| # | Issue |
|---|-------|
"""
            for i, item in enumerate(items, 1):
                md += f"| {i} | `{self.formatter.format_json_item(item)}` |\n"

            if remaining:
                md += f"\n*... and {remaining} more issues*\n"
        else:
            md += "*No issues found*\n"

        md += "\n"
        return md

    def generate_markdown_report(self, output_path: str | Path) -> str:
        """Generate markdown report."""
        summary = self.generate_summary()

        md = f"""# {self.title}

Generated: {self.generated_at.strftime("%Y-%m-%d %H:%M:%S")}

## Executive Summary

- **Status**: {summary["status"].upper()}
- **Total Sections**: {summary["total_sections"]}
- **Sections with Issues**: {summary["sections_with_issues"]}
- **Total Issues**: {summary["total_issues"]}

"""

        for section in self.sections:
            md += self._build_markdown_section(section)

        output = Path(output_path)
        output.write_text(md, encoding="utf-8")
        logger.info(f"Markdown report written to {output_path}")
        return md

    def generate_text_report(self) -> str:
        """Generate plain text report."""
        summary = self.generate_summary()

        lines = [
            "=" * 60,
            self.title,
            "=" * 60,
            f"Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "EXECUTIVE SUMMARY",
            "-" * 40,
            f"Status: {summary['status'].upper()}",
            f"Total Sections: {summary['total_sections']}",
            f"Sections with Issues: {summary['sections_with_issues']}",
            f"Total Issues: {summary['total_issues']}",
            "",
        ]

        for section in self.sections:
            lines.extend(
                [
                    f"\n{section.title}",
                    "-" * 40,
                    f"Status: {section.status}",
                    f"Items: {len(section.items)}",
                    "",
                ]
            )

            items, remaining = self.formatter.truncate_items(
                section.items, self.TEXT_ITEM_LIMIT
            )
            for i, item in enumerate(items, 1):
                lines.append(f"  {i}. {json.dumps(item)}")

            if remaining:
                lines.append(f"  ... and {remaining} more")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Export as dictionary for JSON serialization."""
        return {
            "title": self.title,
            "generated_at": self.generated_at.isoformat(),
            "metadata": self.metadata,
            "summary": self.generate_summary(),
            "sections": [s.to_dict() for s in self.sections],
        }

    def save_json(self, output_path: str | Path) -> None:
        """Save report as JSON."""
        data = self.to_dict()
        output = Path(output_path)
        output.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"JSON report written to {output_path}")

    def print_summary(self) -> None:
        """Print summary to console."""
        print(self.generate_text_report())
