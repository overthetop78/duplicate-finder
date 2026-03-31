from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.analyzer import analyze_duplicates
from core.loader import FileLoadError, load_file
from core.models import AnalysisSummary, DuplicateResult, ServiceResult
from utils.file_utils import safe_output_name


class DuplicateFinderService:
    def load_and_analyze(
        self,
        file_paths: list[str],
        selected_columns: list[str] | None = None,
        *,
        trim_values: bool = True,
        lowercase_values: bool = True,
        ignore_zero_values: bool = True,
        ignore_unnamed_columns: bool = True,
    ) -> ServiceResult:
        if not file_paths:
            raise ValueError("Aucun fichier selectionne.")

        selected_columns_set = set(selected_columns) if selected_columns else None

        dataframes: list[pd.DataFrame] = []
        errors: list[str] = []

        for path in file_paths:
            try:
                dataframe = load_file(path)
                cleaned = self._clean_dataframe(
                    dataframe,
                    selected_columns_set,
                    trim_values,
                    lowercase_values,
                    ignore_zero_values,
                    ignore_unnamed_columns,
                )
                dataframes.append(cleaned)
            except (FileLoadError, ValueError) as exc:
                errors.append(str(exc))

        if not dataframes:
            raise ValueError("Aucun fichier exploitable n'a pu etre charge.")

        results, scanned_value_count, ignored_value_count = analyze_duplicates(
            dataframes,
            selected_columns=selected_columns_set,
            ignore_unnamed_columns=ignore_unnamed_columns,
        )
        summary = self._build_summary(results, len(dataframes), scanned_value_count, ignored_value_count)
        return ServiceResult(results=results, summary=summary, errors=errors)

    def get_available_columns(
        self,
        file_paths: list[str],
        *,
        ignore_unnamed_columns: bool = True,
    ) -> tuple[list[str], list[str]]:
        ordered_columns: list[str] = []
        known_columns: set[str] = set()
        errors: list[str] = []

        for path in file_paths:
            try:
                dataframe = load_file(path)
                for column in dataframe.columns:
                    column_name = str(column)
                    if column_name in {"__file__", "__row_index__"}:
                        continue
                    if ignore_unnamed_columns and column_name.lower().startswith("unnamed"):
                        continue
                    if column_name not in known_columns:
                        known_columns.add(column_name)
                        ordered_columns.append(column_name)
            except (FileLoadError, ValueError) as exc:
                errors.append(str(exc))

        return ordered_columns, errors

    def export_results_csv(self, results: list[DuplicateResult], output_dir: str | Path) -> Path:
        export_path = Path(output_dir) / self._build_export_name("duplicates", "csv")
        self._flatten_results(results).to_csv(export_path, index=False)
        return export_path

    def export_results_excel(self, results: list[DuplicateResult], output_dir: str | Path) -> Path:
        export_path = Path(output_dir) / self._build_export_name("duplicates", "xlsx")
        self._flatten_results(results).to_excel(export_path, index=False)  # pyright: ignore[reportUnknownMemberType]
        return export_path

    def _clean_dataframe(
        self,
        dataframe: pd.DataFrame,
        selected_columns: set[str] | None,
        trim_values: bool,
        lowercase_values: bool,
        ignore_zero_values: bool,
        ignore_unnamed_columns: bool,
    ) -> pd.DataFrame:
        cleaned = pd.DataFrame(dataframe)

        data_columns = [
            column
            for column in cleaned.columns
            if str(column) not in {"__file__", "__row_index__"}
            and (not ignore_unnamed_columns or not str(column).lower().startswith("unnamed"))
            and (selected_columns is None or str(column) in selected_columns)
        ]

        if not data_columns:
            source = str(cleaned["__file__"].iloc[0]) if "__file__" in cleaned.columns and not cleaned.empty else "fichier inconnu"
            raise ValueError(f"Aucune colonne exploitable dans {source}")

        def normalize(value: object) -> str | None:
            if value is None or value is pd.NaT or value is pd.NA:
                return None
            if isinstance(value, float) and value != value:
                return None
            text = value if isinstance(value, str) else str(value)
            if trim_values:
                text = text.strip()
            if lowercase_values:
                text = text.lower()
            if text == "":
                return None
            if ignore_zero_values and text in {"0", "0.0", "0,0", "0,00"}:
                return None
            return text

        for column_label in data_columns:
            cleaned[column_label] = cleaned[column_label].map(normalize)
        return cleaned

    def _build_summary(
        self,
        results: list[DuplicateResult],
        file_count: int,
        scanned_value_count: int,
        ignored_value_count: int,
    ) -> AnalysisSummary:
        internal_count = sum(1 for result in results if result.type.value == "INTERNE")
        external_count = sum(1 for result in results if result.type.value == "EXTERNE")
        occurrence_count = sum(len(result.occurrences) for result in results)
        analyzed_value_count = scanned_value_count - ignored_value_count
        return AnalysisSummary(
            file_count=file_count,
            duplicate_group_count=len(results),
            internal_count=internal_count,
            external_count=external_count,
            occurrence_count=occurrence_count,
            scanned_value_count=scanned_value_count,
            ignored_value_count=ignored_value_count,
            analyzed_value_count=analyzed_value_count,
        )

    def _flatten_results(self, results: list[DuplicateResult]) -> pd.DataFrame:
        rows: list[dict[str, object]] = []
        for result in results:
            for record in result.occurrences:
                rows.append(
                    {
                        "Colonne": result.column_name,
                        "Valeur": result.value,
                        "Type": result.type.value,
                        "Fichier": record.file,
                        "Ligne complete": self._format_row(record.row_data),
                        "Index ligne": record.row_index,
                    }
                )
        return pd.DataFrame(rows)

    def _format_row(self, row_data: dict[str, object]) -> str:
        visible_items = {
            key: value
            for key, value in row_data.items()
            if key not in {"__file__", "__row_index__"}
        }
        return " | ".join(f"{key}={value}" for key, value in visible_items.items())

    def _build_export_name(self, prefix: str, extension: str) -> str:
        return safe_output_name(prefix, extension)
