"""Report generation dialog."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vectortrack import config
from vectortrack.db.repository import Repository
from vectortrack.services.billing_service import BillingService
from vectortrack.services.log_service import LogService
from vectortrack.services.report_data import ReportDataBuilder, ReportFilter
from vectortrack.services.report_service import ReportService
from vectortrack.services.session_aggregator import SessionAggregator
from vectortrack.ui.formatting import project_display_name


class ReportDialog(QDialog):
    REPORT_TYPES = [
        ("Master Summary", "master"),
        ("Project Detail", "project"),
        ("Client Statement", "client"),
    ]

    def __init__(
        self,
        repository: Repository,
        report_service: ReportService,
        billing_service: BillingService,
        session_aggregator: SessionAggregator,
        log_service: LogService,
        log_paths: list[str],
        assigned_files: dict[str, str] | None = None,
        initial_report_type: str = "master",
        initial_project_code: str = "",
        initial_client_id: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self.report_service = report_service
        self.data_builder = ReportDataBuilder(
            repository=repository,
            session_aggregator=session_aggregator,
            billing_service=billing_service,
            log_service=log_service,
            log_paths=log_paths,
            assigned_files=assigned_files,
        )

        self.setWindowTitle("Generate Report")
        self.setMinimumWidth(540)
        root = QVBoxLayout(self)
        form = QFormLayout()

        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        self.type_combo = QComboBox(self)
        for label, value in self.REPORT_TYPES:
            self.type_combo.addItem(label, value)

        self.from_edit = QDateTimeEdit(self)
        self.from_edit.setCalendarPopup(True)
        self.from_edit.setDateTime(month_start)

        self.to_edit = QDateTimeEdit(self)
        self.to_edit.setCalendarPopup(True)
        self.to_edit.setDateTime(now)

        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["PDF", "CSV", "QB", "Accountant"])

        self.project_combo = QComboBox(self)
        self.project_combo.addItem("All Projects", "")
        for project in self.repository.list_projects(active_only=False):
            label = project_display_name(project.name, project.project_code)
            self.project_combo.addItem(label, project.project_code)

        self.client_combo = QComboBox(self)
        self.client_combo.addItem("All Clients", 0)
        for client in self.repository.list_clients(active_only=False):
            self.client_combo.addItem(client.name, int(client.id or 0))

        self.open_after_check = QCheckBox("Open PDF after generating")
        self.open_after_check.setChecked(True)

        form.addRow("Report type", self.type_combo)
        form.addRow("From", self.from_edit)
        form.addRow("To", self.to_edit)
        form.addRow("Format", self.format_combo)
        form.addRow("Project filter", self.project_combo)
        form.addRow("Client filter", self.client_combo)
        form.addRow("", self.open_after_check)
        root.addLayout(form)

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        root.addWidget(self.result_label)

        buttons = QHBoxLayout()
        generate_btn = QPushButton("Generate")
        generate_btn.clicked.connect(self._generate)
        clipboard_btn = QPushButton("Copy Summary")
        clipboard_btn.clicked.connect(self._copy_summary)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(generate_btn)
        buttons.addWidget(clipboard_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

        self._apply_initial_state(initial_report_type, initial_project_code, initial_client_id)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self._on_type_changed()

    def _apply_initial_state(
        self,
        report_type: str,
        project_code: str,
        client_id: int,
    ) -> None:
        for index in range(self.type_combo.count()):
            if self.type_combo.itemData(index) == report_type:
                self.type_combo.setCurrentIndex(index)
                break
        if project_code:
            for index in range(self.project_combo.count()):
                if str(self.project_combo.itemData(index) or "") == project_code:
                    self.project_combo.setCurrentIndex(index)
                    break
        if client_id:
            for index in range(self.client_combo.count()):
                if int(self.client_combo.itemData(index) or 0) == client_id:
                    self.client_combo.setCurrentIndex(index)
                    break

    def _on_type_changed(self) -> None:
        report_type = str(self.type_combo.currentData() or "master")
        self.project_combo.setEnabled(report_type != "client")
        self.client_combo.setEnabled(report_type != "project")
        if report_type == "client":
            self.format_combo.setCurrentText("PDF")
            self.format_combo.setEnabled(False)
        elif report_type == "project":
            self.format_combo.setEnabled(True)
        else:
            self.format_combo.setEnabled(True)

    def _filters(self) -> ReportFilter:
        selected_project = str(self.project_combo.currentData() or "")
        selected_client_id = int(self.client_combo.currentData() or 0)
        report_type = str(self.type_combo.currentData() or "master")
        if report_type == "project" and not selected_project:
            project_data = self.project_combo.currentData()
            selected_project = str(project_data or "")
        if report_type == "client":
            selected_project = ""
        elif report_type == "project":
            selected_client_id = 0
        return ReportFilter(
            from_dt=self.from_edit.dateTime().toPyDateTime(),
            to_dt=self.to_edit.dateTime().toPyDateTime(),
            project_code=selected_project,
            client_id=selected_client_id if report_type == "client" else (
                selected_client_id if selected_client_id else 0
            ),
        )

    def _build_data(self) -> tuple[object, list]:
        filters = self._filters()
        report_type = str(self.type_combo.currentData() or "master")
        if report_type == "client":
            client_id = int(self.client_combo.currentData() or 0)
            if not client_id:
                raise ValueError("Select a client for client statements.")
            data = self.data_builder.build_for_client(
                client_id=client_id,
                from_dt=filters.from_dt,
                to_dt=filters.to_dt,
            )
        elif report_type == "project":
            project_code = str(self.project_combo.currentData() or "")
            if not project_code:
                raise ValueError("Select a project for project detail reports.")
            data = self.data_builder.build_for_project(
                project_code=project_code,
                from_dt=filters.from_dt,
                to_dt=filters.to_dt,
            )
        else:
            data = self.data_builder.build(filters)
        aggregates = data.aggregate_by_project()
        return data, aggregates

    def _default_output_path(self, extension: str) -> str:
        report_type = str(self.type_combo.currentData() or "master")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if report_type == "client":
            client_name = self.client_combo.currentText()
            slug = ReportService._slug(client_name)
            return str(config.reports_dir() / f"{slug}_statement_{stamp}.{extension}")
        if report_type == "project":
            project_code = str(self.project_combo.currentData() or "project")
            slug = ReportService._slug(project_code)
            return str(config.reports_dir() / f"{slug}_project_{stamp}.{extension}")
        return str(config.reports_dir() / f"master_report_{stamp}.{extension}")

    def _generate(self) -> None:
        try:
            data, aggregates = self._build_data()
        except ValueError as exc:
            QMessageBox.warning(self, "Missing selection", str(exc))
            return

        if not data.active_rows:
            QMessageBox.information(self, "No data", "No billable rows match the selected filters.")
            return

        fmt = self.format_combo.currentText().lower()
        report_type = str(self.type_combo.currentData() or "master")
        default_ext = "pdf" if fmt == "pdf" else "csv"
        default_path = self._default_output_path(default_ext)

        if fmt == "pdf":
            suggested = QFileDialog.getSaveFileName(
                self,
                "Save Report PDF",
                default_path,
                "PDF Files (*.pdf)",
            )[0]
            if not suggested:
                return
            output_path = self._write_pdf(report_type, data, aggregates, suggested)
            self._show_result(output_path, open_pdf=self.open_after_check.isChecked())
            return

        variant = "standard"
        if fmt == "qb":
            variant = "qb"
        elif fmt == "accountant":
            variant = "accountant"
        suggested = QFileDialog.getSaveFileName(
            self,
            "Save Report CSV",
            default_path,
            "CSV Files (*.csv)",
        )[0]
        if not suggested:
            return
        output_path = self.report_service.export_csv(data.active_rows, variant=variant, output_path=suggested)
        self._show_result(output_path, open_pdf=False)

    def _write_pdf(
        self,
        report_type: str,
        data: object,
        aggregates: list,
        output_path: str,
    ) -> str:
        if report_type == "client":
            client_name = self.client_combo.currentText()
            return self.report_service.create_client_statement(
                client_name=client_name,
                aggregates=aggregates,
                data=data,
                output_path=output_path,
            )
        if report_type == "project":
            project_code = str(self.project_combo.currentData() or "")
            project = self.repository.get_project_by_code(project_code)
            project_name = project_code
            client_name = ""
            hourly_rate = 0.0
            invoice_number = ""
            is_locked = False
            if project:
                project_name = project_display_name(project.name, project.project_code)
                client = self.repository.get_client(project.client_id)
                client_name = client.name if client else ""
                hourly_rate = float(project.hourly_rate)
                invoice_number = project.invoice_number or ""
                is_locked = bool(project.is_locked)
            return self.report_service.create_project_pdf(
                data=data,
                project_name=project_name,
                client_name=client_name,
                hourly_rate=hourly_rate,
                invoice_number=invoice_number,
                is_locked=is_locked,
                output_path=output_path,
            )
        return self.report_service.create_master_pdf(
            data=data,
            aggregates=aggregates,
            output_path=output_path,
        )

    def _copy_summary(self) -> None:
        try:
            data, aggregates = self._build_data()
        except ValueError as exc:
            QMessageBox.warning(self, "Missing selection", str(exc))
            return
        if not aggregates:
            QMessageBox.information(self, "No data", "No rows match the selected filters.")
            return
        summary = self.report_service.build_clipboard_summary(aggregates)
        self.report_service.copy_summary_to_clipboard(summary)
        self.result_label.setText("Summary copied to clipboard.")
        QMessageBox.information(self, "Copied", "Summary copied to clipboard.")

    def _show_result(self, output_path: str, open_pdf: bool) -> None:
        self.result_label.setText(f"Created: {output_path}")
        QMessageBox.information(self, "Report generated", f"Saved:\n{output_path}")
        if open_pdf and output_path.lower().endswith(".pdf"):
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_path))
