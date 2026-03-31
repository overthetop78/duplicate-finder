from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.models import DuplicateResult


class FileSelector(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.file_paths: list[str] = []

        self.label = QLabel("Aucun fichier selectionne")
        self.button = QPushButton("Selectionner des fichiers")
        self.button.clicked.connect(self._select_files)

        layout = QVBoxLayout(self)
        layout.addWidget(self.button)
        layout.addWidget(self.label)

    def _select_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Selectionner des fichiers",
            "",
            "Fichiers tabulaires (*.csv *.xlsx *.ods)",
        )
        if not paths:
            return

        self.file_paths = paths
        names = ", ".join(Path(path).name for path in paths)
        self.label.setText(names)

    def get_files(self) -> list[str]:
        return self.file_paths


class ColumnInput(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Exemple: email")

        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Colonne cible"))
        layout.addWidget(self.input)

    def text(self) -> str:
        return self.input.text().strip()


class ResultTable(QTableWidget):
    HEADERS = ["Valeur", "Type", "Fichier", "Ligne complete", "Index ligne"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)

    def populate(self, results: list[DuplicateResult]) -> None:
        self.setSortingEnabled(False)
        self.setRowCount(0)

        row_index = 0
        for group_index, result in enumerate(results):
            group_color = "#f5f7fa" if group_index % 2 == 0 else "#ebf4ff"
            for occurrence in result.occurrences:
                self.insertRow(row_index)
                values = [
                    result.value,
                    result.type.value,
                    occurrence.file,
                    self._format_row(occurrence.row_data),
                    str(occurrence.row_index),
                ]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setBackground(group_color)
                    if column == 4:
                        item.setTextAlignment(Qt.AlignCenter)
                    self.setItem(row_index, column, item)
                row_index += 1

        self.resizeColumnsToContents()
        self.setSortingEnabled(True)

    def _format_row(self, row_data: dict[str, object]) -> str:
        visible_items = {
            key: value
            for key, value in row_data.items()
            if key not in {"__file__", "__row_index__"}
        }
        return " | ".join(f"{key}={value}" for key, value in visible_items.items())


class StatusBar(QStatusBar):
    def show_info(self, message: str) -> None:
        self.showMessage(message, 5000)


class ProgressIndicator(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(110)

        layout = QVBoxLayout(self)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log)

    def start(self, message: str) -> None:
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self.append_log(message)

    def finish(self, message: str) -> None:
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.append_log(message)

    def append_log(self, message: str) -> None:
        self.log.append(message)
