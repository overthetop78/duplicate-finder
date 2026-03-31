from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.models import ServiceResult
from services.duplicate_service import DuplicateFinderService
from ui.components import ColumnInput, FileSelector, ProgressIndicator, ResultTable, StatusBar
from utils.file_utils import ensure_directory


class AnalysisWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, service: DuplicateFinderService, file_paths: list[str], column_name: str, trim_values: bool, lowercase_values: bool) -> None:
        super().__init__()
        self.service = service
        self.file_paths = file_paths
        self.column_name = column_name
        self.trim_values = trim_values
        self.lowercase_values = lowercase_values

    def run(self) -> None:
        try:
            result = self.service.load_and_analyze(
                self.file_paths,
                self.column_name,
                trim_values=self.trim_values,
                lowercase_values=self.lowercase_values,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class SummaryDialog(QDialog):
    def __init__(self, result: ServiceResult, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Resume de l'analyse")

        summary = result.summary
        content = QVBoxLayout(self)
        content.addWidget(QLabel(f"Nombre de fichiers : {summary.file_count}"))
        content.addWidget(QLabel(f"Groupes de doublons : {summary.duplicate_group_count}"))
        content.addWidget(QLabel(f"Doublons internes : {summary.internal_count}"))
        content.addWidget(QLabel(f"Doublons externes : {summary.external_count}"))
        content.addWidget(QLabel(f"Occurrences totales : {summary.occurrence_count}"))

        if result.errors:
            content.addWidget(QLabel("Erreurs chargees pendant l'analyse :"))
            for error in result.errors:
                label = QLabel(f"- {error}")
                label.setWordWrap(True)
                content.addWidget(label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        content.addWidget(buttons)


class DuplicateFinderWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.service = DuplicateFinderService()
        self.last_result: ServiceResult | None = None
        self.worker_thread: QThread | None = None

        self.setWindowTitle("Duplicate Finder")
        self.setMinimumSize(1200, 800)

        self.file_selector = FileSelector()
        self.column_input = ColumnInput()
        self.trim_checkbox = QCheckBox("Nettoyer les espaces")
        self.trim_checkbox.setChecked(True)
        self.lower_checkbox = QCheckBox("Ignorer la casse")
        self.lower_checkbox.setChecked(True)

        self.analyze_button = QPushButton("Analyser")
        self.analyze_button.clicked.connect(self.run_analysis)
        self.export_csv_button = QPushButton("Export CSV")
        self.export_csv_button.clicked.connect(self.export_csv)
        self.export_csv_button.setEnabled(False)
        self.export_excel_button = QPushButton("Export Excel")
        self.export_excel_button.clicked.connect(self.export_excel)
        self.export_excel_button.setEnabled(False)
        self.summary_button = QPushButton("Resume")
        self.summary_button.clicked.connect(self.show_summary)
        self.summary_button.setEnabled(False)

        self.progress = ProgressIndicator()
        self.result_table = ResultTable()
        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar)

        controls = QHBoxLayout()
        controls.addWidget(self.trim_checkbox)
        controls.addWidget(self.lower_checkbox)
        controls.addStretch(1)
        controls.addWidget(self.analyze_button)
        controls.addWidget(self.summary_button)
        controls.addWidget(self.export_csv_button)
        controls.addWidget(self.export_excel_button)

        layout = QVBoxLayout()
        layout.addWidget(self.file_selector)
        layout.addWidget(self.column_input)
        layout.addLayout(controls)
        layout.addWidget(self.progress)
        layout.addWidget(self.result_table, stretch=1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def run_analysis(self) -> None:
        files = self.file_selector.get_files()
        column_name = self.column_input.text()

        if not files:
            self._show_error("Selectionnez au moins un fichier.")
            return

        if not column_name:
            self._show_error("Saisissez une colonne cible.")
            return

        self.analyze_button.setEnabled(False)
        self.progress.start("Analyse en cours...")
        self.status_bar.show_info("Chargement des fichiers et detection des doublons...")

        self.worker_thread = QThread(self)
        self.worker = AnalysisWorker(
            self.service,
            files,
            column_name,
            self.trim_checkbox.isChecked(),
            self.lower_checkbox.isChecked(),
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_analysis_success)
        self.worker.failed.connect(self._on_analysis_failure)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def _on_analysis_success(self, result: ServiceResult) -> None:
        self.last_result = result
        self.result_table.populate(result.results)
        self.analyze_button.setEnabled(True)
        self.export_csv_button.setEnabled(bool(result.results))
        self.export_excel_button.setEnabled(bool(result.results))
        self.summary_button.setEnabled(True)
        self.progress.finish(f"Analyse terminee: {result.summary.duplicate_group_count} groupes trouves.")
        if result.errors:
            self.progress.append_log("Certaines erreurs ont ete ignorees pendant le chargement.")
        self.status_bar.show_info("Analyse terminee.")

    def _on_analysis_failure(self, message: str) -> None:
        self.analyze_button.setEnabled(True)
        self.progress.finish("Echec de l'analyse.")
        self._show_error(message)

    def export_csv(self) -> None:
        self._export("csv")

    def export_excel(self) -> None:
        self._export("xlsx")

    def _export(self, export_type: str) -> None:
        if not self.last_result:
            self._show_error("Aucun resultat a exporter.")
            return

        output_dir = ensure_directory(Path(__file__).resolve().parents[2] / "output")
        if export_type == "csv":
            export_path = self.service.export_results_csv(self.last_result.results, output_dir)
        else:
            export_path = self.service.export_results_excel(self.last_result.results, output_dir)

        self.progress.append_log(f"Export cree: {export_path.name}")
        self.status_bar.show_info(f"Export enregistre dans {export_path}")

    def show_summary(self) -> None:
        if not self.last_result:
            self._show_error("Aucun resultat a resumer.")
            return
        dialog = SummaryDialog(self.last_result, self)
        dialog.exec()

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Erreur", message)
        self.status_bar.show_info(message)


def create_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    app.setApplicationName("Duplicate Finder")
    return app


def launch() -> int:
    app = create_app()
    window = DuplicateFinderWindow()
    window.show()
    return app.exec()
