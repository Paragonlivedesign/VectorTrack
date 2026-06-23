"""Report generation service."""

from __future__ import annotations

import csv
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


class ReportService:
    """Generate PDF and CSV deliverables for tracked projects."""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_project_pdf(
        self,
        project_name: str,
        rows: Sequence[Dict[str, object]],
        output_path: Optional[str] = None,
    ) -> str:
        pdf_path = output_path or str(self.output_dir / f"{self._slug(project_name)}_project.pdf")
        title = f"Project Report: {project_name}"
        self._write_simple_pdf(
            pdf_path,
            title=title,
            table_headers=["Date", "File", "Hours", "Rate", "Amount"],
            rows=[
                [
                    str(row.get("date", "")),
                    str(row.get("file", "")),
                    f"{float(row.get('hours', 0.0)):.2f}",
                    f"{float(row.get('rate', 0.0)):.2f}",
                    f"{float(row.get('amount', 0.0)):.2f}",
                ]
                for row in rows
            ],
        )
        return pdf_path

    def create_master_pdf(
        self,
        project_totals: Sequence[Dict[str, object]],
        output_path: Optional[str] = None,
    ) -> str:
        pdf_path = output_path or str(self.output_dir / "master_report.pdf")
        self._write_simple_pdf(
            pdf_path,
            title="VectorTrack Master Report",
            table_headers=["Project", "Hours", "Billable", "Trust"],
            rows=[
                [
                    str(row.get("project", "")),
                    f"{float(row.get('hours', 0.0)):.2f}",
                    f"{float(row.get('amount', 0.0)):.2f}",
                    f"{float(row.get('trust', 0.0)):.2f}",
                ]
                for row in project_totals
            ],
        )
        return pdf_path

    def create_client_statement(
        self,
        client_name: str,
        line_items: Sequence[Dict[str, object]],
        output_path: Optional[str] = None,
    ) -> str:
        pdf_path = output_path or str(self.output_dir / f"{self._slug(client_name)}_statement.pdf")
        self._write_simple_pdf(
            pdf_path,
            title=f"Client Statement: {client_name}",
            table_headers=["Description", "Hours", "Rate", "Amount"],
            rows=[
                [
                    str(item.get("description", "")),
                    f"{float(item.get('hours', 0.0)):.2f}",
                    f"{float(item.get('rate', 0.0)):.2f}",
                    f"{float(item.get('amount', 0.0)):.2f}",
                ]
                for item in line_items
            ],
        )
        return pdf_path

    def export_csv(
        self,
        rows: Sequence[Dict[str, object]],
        variant: str = "standard",
        output_path: Optional[str] = None,
    ) -> str:
        filename = f"export_{variant}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_path = output_path or str(self.output_dir / filename)
        headers = self._csv_headers_for_variant(variant)
        with open(csv_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow({header: row.get(header, "") for header in headers})
        return csv_path

    def build_clipboard_summary(self, project_totals: Sequence[Dict[str, object]]) -> str:
        lines: List[str] = ["VectorTrack Summary"]
        grand_hours = 0.0
        grand_amount = 0.0
        for row in project_totals:
            project = str(row.get("project", "Unnamed"))
            hours = float(row.get("hours", 0.0))
            amount = float(row.get("amount", 0.0))
            grand_hours += hours
            grand_amount += amount
            lines.append(f"- {project}: {hours:.2f}h / ${amount:.2f}")
        lines.append(f"TOTAL: {grand_hours:.2f}h / ${grand_amount:.2f}")
        return "\n".join(lines)

    def copy_summary_to_clipboard(self, summary_text: str) -> None:
        # Prefer pyperclip when present, otherwise use Windows clip command.
        try:
            import pyperclip  # type: ignore

            pyperclip.copy(summary_text)
            return
        except Exception:
            pass
        subprocess.run(["clip"], input=summary_text, text=True, check=False)

    def _write_simple_pdf(
        self,
        output_path: str,
        title: str,
        table_headers: Sequence[str],
        rows: Sequence[Sequence[str]],
    ) -> None:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = [Paragraph(title, styles["Heading1"]), Spacer(1, 12)]

        data = [list(table_headers), *[list(row) for row in rows]]
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(table)
        doc.build(story)

    @staticmethod
    def _csv_headers_for_variant(variant: str) -> List[str]:
        normalized = variant.lower().strip()
        if normalized in ("qb", "quickbooks"):
            return ["date", "project", "description", "hours", "rate", "amount", "customer"]
        if normalized == "accountant":
            return ["date", "client", "project", "hours", "amount", "taxable", "memo"]
        return ["date", "project", "file", "hours", "rate", "amount", "billable"]

    @staticmethod
    def _slug(value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value.strip())
        return cleaned.strip("_") or "report"
