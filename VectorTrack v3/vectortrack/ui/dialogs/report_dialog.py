"""Report generation dialog."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vectortrack.db.repository import Repository
from vectortrack.services.report_service import ReportService


class ReportDialog(QDialog):
    def __init__(
        self,
        repository: Repository,
        report_service: ReportService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self.report_service = report_service

        self.setWindowTitle("Generate Report")
        self.setMinimumWidth(520)
        root = QVBoxLayout(self)
        form = QFormLayout()

        now = datetime.now()
        self.from_edit = QDateTimeEdit(self)
        self.from_edit.setCalendarPopup(True)
        self.from_edit.setDateTime(now.replace(hour=0, minute=0, second=0, microsecond=0))
        self.to_edit = QDateTimeEdit(self)
        self.to_edit.setCalendarPopup(True)
        self.to_edit.setDateTime(now)

        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["PDF", "CSV", "QB", "Accountant"])

        self.project_combo = QComboBox(self)
        self.project_combo.addItem("All Projects", "")
        for project in self.repository.list_projects(active_only=False):
            self.project_combo.addItem(project.project_code, project.project_code)

        self.client_combo = QComboBox(self)
        self.client_combo.addItem("All Clients", 0)
        for client in self.repository.list_clients(active_only=False):
            self.client_combo.addItem(client.name, int(client.id or 0))

        form.addRow("From", self.from_edit)
        form.addRow("To", self.to_edit)
        form.addRow("Format", self.format_combo)
        form.addRow("Project filter", self.project_combo)
        form.addRow("Client filter", self.client_combo)
        root.addLayout(form)

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        root.addWidget(self.result_label)

        buttons = QHBoxLayout()
        generate_btn = QPushButton("Generate")
        generate_btn.clicked.connect(self._generate)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(generate_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

    def _filtered_rows(self) -> list[dict[str, object]]:
        selected_project = str(self.project_combo.currentData() or "")
        selected_client_id = int(self.client_combo.currentData() or 0)
        by_project = {project.project_code: project for project in self.repository.list_projects(active_only=False)}

        from_dt = self.from_edit.dateTime().toPyDateTime()
        to_dt = self.to_edit.dateTime().toPyDateTime()

        rows: list[dict[str, object]] = []
        sessions = self.repository.list_sessions(include_open=True, limit=10000)
        for session in sessions:
            if session.start_time < from_dt or session.start_time > to_dt:
                continue
            if selected_project and session.project_id != selected_project:
                continue
            project = by_project.get(session.project_id)
            if selected_client_id and (project is None or int(project.client_id) != selected_client_id):
                continue
            rows.append(
                {
                    "date": session.start_time.strftime("%Y-%m-%d"),
                    "project": session.project_id,
                    "client": str(project.client_id) if project else "",
                    "customer": str(project.client_id) if project else "",
                    "description": session.file_alias or session.file_path,
                    "file": session.file_alias or session.file_path,
                    "hours": session.active_duration.total_seconds() / 3600.0,
                    "rate": session.hourly_rate,
                    "amount": session.billable_amount,
                    "billable": "yes",
                    "taxable": "yes",
                    "memo": "VectorTrack export",
                }
            )
        return rows

    def _generate(self) -> None:
        rows = self._filtered_rows()
        if not rows:
            QMessageBox.information(self, "No data", "No rows match the selected filters.")
            return

        output_path = ""
        fmt = self.format_combo.currentText().lower()
        if fmt == "pdf":
            grouped: dict[str, dict[str, float]] = {}
            for row in rows:
                key = str(row["project"])
                agg = grouped.setdefault(key, {"hours": 0.0, "amount": 0.0})
                agg["hours"] += float(row["hours"])
                agg["amount"] += float(row["amount"])
            totals = [
                {"project": project, "hours": values["hours"], "amount": values["amount"], "trust": 1.0}
                for project, values in sorted(grouped.items())
            ]
            output_path = self.report_service.create_master_pdf(totals)
        elif fmt == "csv":
            output_path = self.report_service.export_csv(rows, variant="standard")
        elif fmt == "qb":
            output_path = self.report_service.export_csv(rows, variant="qb")
        else:
            output_path = self.report_service.export_csv(rows, variant="accountant")

        self.result_label.setText(f"Created: {output_path}")
        QMessageBox.information(self, "Report generated", f"Saved:\n{output_path}")
