"""Report generation service."""

from __future__ import annotations

import csv
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

from vectortrack.config import APP_NAME, COMPANY_NAME, format_version
from vectortrack.services.report_data import ProjectAggregate, ReportDataSet, ReportRow


class ReportService:
    """Generate PDF and CSV deliverables for tracked projects."""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_master_pdf(
        self,
        data: ReportDataSet,
        aggregates: Sequence[ProjectAggregate],
        output_path: Optional[str] = None,
    ) -> str:
        pdf_path = output_path or str(self.output_dir / "master_report.pdf")
        headers = [
            "Project",
            "Client",
            "Raw Hrs",
            "Billed Hrs",
            "Raw Amt",
            "Billed Amt",
            "Trust",
        ]
        rows = [
            [
                agg.project_label,
                agg.client_name,
                f"{agg.raw_hours:.2f}",
                f"{agg.billed_hours:.2f}",
                self._money(agg.raw_amount),
                self._money(agg.billed_amount),
                f"{agg.trust_score:.2f}",
            ]
            for agg in aggregates
        ]
        totals = self._totals_from_aggregates(aggregates)
        rows.append(
            [
                "TOTAL",
                "",
                f"{totals['raw_hours']:.2f}",
                f"{totals['billed_hours']:.2f}",
                self._money(totals["raw_amount"]),
                self._money(totals["billed_amount"]),
                "",
            ]
        )
        self._write_pdf(
            pdf_path,
            title="Master Summary Report",
            subtitle=data.filter_summary,
            table_headers=headers,
            rows=rows,
            totals_label=f"Amount due: {self._money(totals['billed_amount'])}",
        )
        return pdf_path

    def create_project_pdf(
        self,
        data: ReportDataSet,
        project_name: str,
        client_name: str = "",
        hourly_rate: float = 0.0,
        invoice_number: str = "",
        is_locked: bool = False,
        output_path: Optional[str] = None,
    ) -> str:
        slug = self._slug(project_name)
        pdf_path = output_path or str(self.output_dir / f"{slug}_project.pdf")
        meta_lines = [
            f"Client: {client_name or '—'}",
            f"Hourly rate: {self._money(hourly_rate)}",
        ]
        if is_locked and invoice_number:
            meta_lines.append(f"Invoice #: {invoice_number}")
        if is_locked:
            meta_lines.append("Status: Locked")

        headers = ["Date", "File", "Raw Hrs", "Billed Hrs", "Rate", "Raw Amt", "Billed Amt", "Source"]
        rows = [
            [
                row.date,
                row.file,
                f"{row.raw_hours:.2f}",
                f"{row.billed_hours:.2f}",
                self._money(row.rate),
                self._money(row.raw_amount),
                self._money(row.billed_amount),
                row.source,
            ]
            for row in data.active_rows
        ]
        totals = self._totals_from_rows(data.active_rows)
        rows.append(
            [
                "TOTAL",
                "",
                f"{totals['raw_hours']:.2f}",
                f"{totals['billed_hours']:.2f}",
                "",
                self._money(totals["raw_amount"]),
                self._money(totals["billed_amount"]),
                "",
            ]
        )
        self._write_pdf(
            pdf_path,
            title=f"Project Report: {project_name}",
            subtitle=data.filter_summary,
            meta_lines=meta_lines,
            table_headers=headers,
            rows=rows,
            totals_label=f"Amount due: {self._money(totals['billed_amount'])}",
        )
        return pdf_path

    def create_client_statement(
        self,
        client_name: str,
        aggregates: Sequence[ProjectAggregate],
        data: ReportDataSet,
        output_path: Optional[str] = None,
    ) -> str:
        pdf_path = output_path or str(self.output_dir / f"{self._slug(client_name)}_statement.pdf")
        meta_lines = [f"Bill to: {client_name}"]
        headers = ["Project", "Invoice #", "Raw Hrs", "Billed Hrs", "Raw Amt", "Billed Amt"]
        rows = [
            [
                agg.project_label,
                agg.invoice_number if agg.is_locked else "—",
                f"{agg.raw_hours:.2f}",
                f"{agg.billed_hours:.2f}",
                self._money(agg.raw_amount),
                self._money(agg.billed_amount),
            ]
            for agg in aggregates
        ]
        totals = self._totals_from_aggregates(aggregates)
        rows.append(
            [
                "TOTAL",
                "",
                f"{totals['raw_hours']:.2f}",
                f"{totals['billed_hours']:.2f}",
                self._money(totals["raw_amount"]),
                self._money(totals["billed_amount"]),
            ]
        )
        self._write_pdf(
            pdf_path,
            title=f"Client Statement: {client_name}",
            subtitle=data.filter_summary,
            meta_lines=meta_lines,
            table_headers=headers,
            rows=rows,
            totals_label=f"Amount due: {self._money(totals['billed_amount'])}",
        )
        return pdf_path

    def export_csv(
        self,
        rows: Sequence[ReportRow],
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
                mapped = self._map_row_for_variant(row, variant)
                writer.writerow({header: mapped.get(header, "") for header in headers})
        return csv_path

    def export_unified_csv(
        self,
        rows: Sequence[ReportRow],
        output_path: str,
    ) -> str:
        headers = self._csv_headers_for_variant("standard")
        with open(output_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                mapped = row.to_standard_csv()
                writer.writerow({header: mapped.get(header, "") for header in headers})
        return output_path

    def build_clipboard_summary(self, aggregates: Sequence[ProjectAggregate]) -> str:
        lines: List[str] = ["VectorTrack Summary"]
        if aggregates:
            lines.append("")
        grand_raw_hours = 0.0
        grand_billed_hours = 0.0
        grand_raw_amount = 0.0
        grand_billed_amount = 0.0
        for agg in aggregates:
            grand_raw_hours += agg.raw_hours
            grand_billed_hours += agg.billed_hours
            grand_raw_amount += agg.raw_amount
            grand_billed_amount += agg.billed_amount
            lines.append(
                f"- {agg.project_label}: {agg.raw_hours:.2f}h raw / {agg.billed_hours:.2f}h billed "
                f"(${agg.raw_amount:.2f} raw / ${agg.billed_amount:.2f} billed)"
            )
        lines.append(
            f"TOTAL: {grand_raw_hours:.2f}h raw / {grand_billed_hours:.2f}h billed "
            f"(${grand_raw_amount:.2f} raw / ${grand_billed_amount:.2f} billed)"
        )
        return "\n".join(lines)

    def copy_summary_to_clipboard(self, summary_text: str) -> None:
        try:
            import pyperclip  # type: ignore

            pyperclip.copy(summary_text)
            return
        except Exception:
            pass
        subprocess.run(["clip"], input=summary_text, text=True, check=False)

    def _write_pdf(
        self,
        output_path: str,
        title: str,
        subtitle: str,
        table_headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        meta_lines: Optional[Sequence[str]] = None,
        totals_label: str = "",
    ) -> None:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_RIGHT
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            leftMargin=0.65 * inch,
            rightMargin=0.65 * inch,
            topMargin=0.65 * inch,
            bottomMargin=0.75 * inch,
        )
        styles = getSampleStyleSheet()
        header_style = ParagraphStyle(
            "ReportHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
        )
        muted_style = ParagraphStyle(
            "ReportMuted",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748B"),
        )
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            spaceAfter=6,
        )
        totals_style = ParagraphStyle(
            "ReportTotals",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_RIGHT,
        )

        story: list = []
        story.append(Paragraph(f"{COMPANY_NAME}", header_style))
        story.append(Paragraph(f"{APP_NAME} — {format_version()}", muted_style))
        story.append(Spacer(1, 8))
        story.append(Paragraph(title, title_style))
        if subtitle:
            story.append(Paragraph(subtitle, muted_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", muted_style))
        if meta_lines:
            for line in meta_lines:
                story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 12))

        cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        )
        header_cells = [Paragraph(str(header), header_style) for header in table_headers]
        data: list[list] = [header_cells]
        for row in rows:
            data.append([Paragraph(self._escape_xml(str(cell)), cell_style) for cell in row])

        col_count = len(table_headers)
        available_width = letter[0] - doc.leftMargin - doc.rightMargin
        col_width = available_width / max(col_count, 1)
        table = Table(data, colWidths=[col_width] * col_count, repeatRows=1)
        last_row = len(data) - 1
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F7")),
                    ("BACKGROUND", (0, last_row), (-1, last_row), colors.HexColor("#F3F5F8")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, last_row), (-1, last_row), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(table)
        if totals_label:
            story.append(Spacer(1, 10))
            story.append(Paragraph(totals_label, totals_style))

        def _footer(canvas, doc_obj) -> None:
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#64748B"))
            canvas.drawString(doc.leftMargin, 0.45 * inch, f"{COMPANY_NAME} | {APP_NAME}")
            canvas.drawRightString(
                letter[0] - doc.rightMargin,
                0.45 * inch,
                f"Page {canvas.getPageNumber()}",
            )
            canvas.restoreState()

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)

    @staticmethod
    def _map_row_for_variant(row: ReportRow, variant: str) -> dict[str, object]:
        normalized = variant.lower().strip()
        if normalized in ("qb", "quickbooks"):
            return row.to_qb_csv()
        if normalized == "accountant":
            return row.to_accountant_csv()
        return row.to_standard_csv()

    @staticmethod
    def _csv_headers_for_variant(variant: str) -> List[str]:
        normalized = variant.lower().strip()
        if normalized in ("qb", "quickbooks"):
            return ["date", "project", "description", "hours", "rate", "amount", "customer"]
        if normalized == "accountant":
            return ["date", "client", "project", "hours", "amount", "taxable", "memo"]
        return [
            "date",
            "client_name",
            "project_name",
            "project",
            "file",
            "raw_hours",
            "billed_hours",
            "rate",
            "raw_amount",
            "billed_amount",
            "billable",
        ]

    @staticmethod
    def _totals_from_rows(rows: Sequence[ReportRow]) -> dict[str, float]:
        return {
            "raw_hours": sum(row.raw_hours for row in rows),
            "billed_hours": sum(row.billed_hours for row in rows),
            "raw_amount": sum(row.raw_amount for row in rows),
            "billed_amount": sum(row.billed_amount for row in rows),
        }

    @staticmethod
    def _totals_from_aggregates(aggregates: Sequence[ProjectAggregate]) -> dict[str, float]:
        return {
            "raw_hours": sum(agg.raw_hours for agg in aggregates),
            "billed_hours": sum(agg.billed_hours for agg in aggregates),
            "raw_amount": sum(agg.raw_amount for agg in aggregates),
            "billed_amount": sum(agg.billed_amount for agg in aggregates),
        }

    @staticmethod
    def _money(value: float) -> str:
        return f"${value:,.2f}"

    @staticmethod
    def _escape_xml(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    @staticmethod
    def _slug(value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value.strip())
        return cleaned.strip("_") or "report"
