from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Signal, Qt
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.models import DuplicateResult


class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, numeric_value: int) -> None:
        super().__init__(str(numeric_value))
        self.numeric_value = numeric_value

    def __lt__(self, other: object) -> bool:
        if isinstance(other, NumericTableWidgetItem):
            return self.numeric_value < other.numeric_value
        if isinstance(other, QTableWidgetItem):
            return super().__lt__(other)
        return False


class FileSelector(QWidget):
    filesChanged = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.file_paths: list[str] = []
        self._path_by_item_id: dict[int, str] = {}

        self.label = QLabel("Aucun fichier selectionne")
        self.button = QPushButton("Selectionner des fichiers")
        self.button.clicked.connect(self._select_files)
        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(140)
        self.list_widget.itemChanged.connect(self._on_item_changed)

        layout = QVBoxLayout(self)
        layout.addWidget(self.button)
        layout.addWidget(self.label)
        layout.addWidget(self.list_widget)

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
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        self._path_by_item_id = {}

        for index, path in enumerate(paths, start=1):
            item = QListWidgetItem(f"{index} - {Path(path).name}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.list_widget.addItem(item)
            self._path_by_item_id[id(item)] = path

        self.list_widget.blockSignals(False)
        self._refresh_label()
        self.filesChanged.emit(self.get_files())

    def _on_item_changed(self, _: QListWidgetItem) -> None:
        self._refresh_label()
        self.filesChanged.emit(self.get_files())

    def _refresh_label(self) -> None:
        selected_count = len(self.get_files())
        total_count = len(self.file_paths)
        if total_count == 0:
            self.label.setText("Aucun fichier selectionne")
            return
        self.label.setText(f"{selected_count} fichier(s) selectionne(s) sur {total_count}")

    def get_files(self) -> list[str]:
        selected_paths: list[str] = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                path = self._path_by_item_id.get(id(item))
                if path:
                    selected_paths.append(path)
        return selected_paths


class ColumnSelector(QWidget):
    _COLS_PER_ROW = 4

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.columns: list[str] = []
        self._checkboxes: list[tuple[str, QCheckBox]] = []

        self.label = QLabel("Colonnes detectees: 0")

        btn_all = QPushButton("Tout")
        btn_none = QPushButton("Aucun")
        btn_invert = QPushButton("Inverser")
        btn_all.clicked.connect(self._select_all)
        btn_none.clicked.connect(self._select_none)
        btn_invert.clicked.connect(self._invert)

        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        btn_row.addWidget(btn_invert)
        btn_row.addStretch(1)

        self._inner_widget = QWidget()
        self._grid_layout = QGridLayout(self._inner_widget)
        self._grid_layout.setContentsMargins(4, 4, 4, 4)
        self._grid_layout.setSpacing(6)

        self._scroll = QScrollArea()
        self._scroll.setWidget(self._inner_widget)
        self._scroll.setWidgetResizable(True)
        self._scroll.setMaximumHeight(160)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addLayout(btn_row)
        layout.addWidget(self._scroll)

    def set_columns(self, columns: list[str]) -> None:
        self.columns = columns
        self._checkboxes.clear()
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        for idx, column_name in enumerate(columns):
            code = _column_code(idx + 1)
            cb = QCheckBox(f"{code} - {column_name}")
            cb.setChecked(True)
            grid_row, grid_col = divmod(idx, self._COLS_PER_ROW)
            self._grid_layout.addWidget(cb, grid_row, grid_col)
            self._checkboxes.append((column_name, cb))

        self.label.setText(f"Colonnes detectees: {len(columns)}")

    def clear(self) -> None:
        self.columns = []
        self._checkboxes.clear()
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        self.label.setText("Colonnes detectees: 0")

    def get_selected_columns(self) -> list[str]:
        return [col_name for col_name, cb in self._checkboxes if cb.isChecked()]

    def _select_all(self) -> None:
        for _, cb in self._checkboxes:
            cb.setChecked(True)

    def _select_none(self) -> None:
        for _, cb in self._checkboxes:
            cb.setChecked(False)

    def _invert(self) -> None:
        for _, cb in self._checkboxes:
            cb.setChecked(not cb.isChecked())


def _column_code(index: int) -> str:
    code = ""
    value = index
    while value > 0:
        value, remainder = divmod(value - 1, 26)
        code = chr(ord("A") + remainder) + code
    return code


class ResultTable(QTableWidget):
    HEADERS = ["Colonne", "Ligne", "Valeur", "Type", "Fichier", "Ouvrir"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setVisible(False)

    def populate(self, results: list[DuplicateResult], file_paths: list[str] | None = None) -> None:
        self.setSortingEnabled(False)
        self.setRowCount(0)

        file_number_map: dict[str, int] = {}
        if file_paths:
            for idx, fp in enumerate(file_paths, start=1):
                file_number_map[fp] = idx

        row_index = 0
        for group_index, result in enumerate(results):
            group_color = QColor("#f5f7fa" if group_index % 2 == 0 else "#ebf4ff")
            col_letter = _column_code(result.column_index + 1)
            for occurrence in result.occurrences:
                self.insertRow(row_index)

                col_item = QTableWidgetItem(col_letter)
                col_item.setBackground(group_color)
                col_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row_index, 0, col_item)

                line_item = NumericTableWidgetItem(occurrence.row_index)
                line_item.setBackground(group_color)
                line_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row_index, 1, line_item)

                val_item = QTableWidgetItem(result.value)
                val_item.setBackground(group_color)
                self.setItem(row_index, 2, val_item)

                type_item = QTableWidgetItem(result.type.value)
                type_item.setBackground(group_color)
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row_index, 3, type_item)

                file_num = file_number_map.get(occurrence.file, 0)
                file_item = NumericTableWidgetItem(file_num)
                file_item.setBackground(group_color)
                file_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row_index, 4, file_item)

                open_btn = QPushButton("Ouvrir")
                file_path = occurrence.file
                open_btn.clicked.connect(
                    lambda checked=False, p=file_path: QDesktopServices.openUrl(QUrl.fromLocalFile(p))
                )
                self.setCellWidget(row_index, 5, open_btn)

                row_index += 1

        self.resizeColumnsToContents()
        self.setSortingEnabled(True)


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
