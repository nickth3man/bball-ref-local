"""Generate validation reports in multiple formats."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ReportSection:
    """A section of a validation report."""

    def __init__(self, title: str, status: str = "pending"):
        self.title = title
        self.status = status
        self.items: list[dict[str, Any]] = []
        self.summary: dict[str, Any] = {}

    def add_item(self, item: dict[str, Any]):
        """Add an item to the section."""
        self.items.append(item)

    def set_summary(self, summary: dict[str, Any]):
        """Set the section summary."""
        self.summary = summary

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "status": self.status,
            "summary": self.summary,
            "items": self.items,
            "item_count": len(self.items),
        }


class ValidationReport:
    """Generates validation reports."""

    def __init__(self, title: str = "Data Validation Report"):
        self.title = title
        self.generated_at = datetime.now()
        self.sections: list[ReportSection] = []
        self.metadata: dict[str, Any] = {}

    def add_section(
        self, title: str, results: list[dict[str, Any]], status: str = "pending"
    ) -> ReportSection:
        """Add a validation section."""
        section = ReportSection(title, status)
        for result in results:
            section.add_item(result)
        self.sections.append(section)
        return section

    def add_metadata(self, key: str, value: Any):
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

    def generate_html_report(self, output_path: str | Path) -> str:
        """Generate HTML report with tables."""
        summary = self.generate_summary()

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{self.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .status-passed {{ color: green; }}
        .status-failed {{ color: red; }}
        .status-pending {{ color: orange; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .section {{ margin: 30px 0; }}
        .no-issues {{ color: green; font-style: italic; }}
    </style>
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
            html += f"""
    <div class="section">
        <h2>{section.title} <span class="status-{section.status}">({section.status})</span></h2>
"""
            if section.summary:
                html += f"""
        <div class="summary">
            <pre>{json.dumps(section.summary, indent=2)}</pre>
        </div>
"""

            if section.items:
                html += """
        <table>
            <tr>
                <th>#</th>
                <th>Details</th>
            </tr>
"""
                for i, item in enumerate(section.items[:100], 1):  # Limit to 100
                    html += f"""
            <tr>
                <td>{i}</td>
                <td><pre>{json.dumps(item, indent=2)}</pre></td>
            </tr>
"""
                if len(section.items) > 100:
                    html += f"""
            <tr>
                <td colspan="2"><em>... and {len(section.items) - 100} more issues</em></td>
            </tr>
"""
                html += "</table>"
            else:
                html += '<p class="no-issues">No issues found</p>'

            html += "</div>"

        html += """
</body>
</html>
"""

        output = Path(output_path)
        output.write_text(html, encoding="utf-8")
        logger.info(f"HTML report written to {output_path}")
        return html

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
            md += f"""## {section.title}

**Status**: {section.status}

"""
            if section.summary:
                md += f"""### Summary

```json
{json.dumps(section.summary, indent=2)}
```

"""

            if section.items:
                md += f"""### Issues ({len(section.items)} total)

| # | Issue |
|---|-------|
"""
                for i, item in enumerate(section.items[:50], 1):  # Limit to 50
                    md += f"| {i} | `{json.dumps(item)}` |\n"

                if len(section.items) > 50:
                    md += f"\n*... and {len(section.items) - 50} more issues*\n"
            else:
                md += "*No issues found*\n"

            md += "\n"

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

            for i, item in enumerate(section.items[:20], 1):
                lines.append(f"  {i}. {json.dumps(item)}")

            if len(section.items) > 20:
                lines.append(f"  ... and {len(section.items) - 20} more")

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

    def save_json(self, output_path: str | Path):
        """Save report as JSON."""
        data = self.to_dict()
        output = Path(output_path)
        output.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"JSON report written to {output_path}")

    def print_summary(self):
        """Print summary to console."""
        print(self.generate_text_report())
