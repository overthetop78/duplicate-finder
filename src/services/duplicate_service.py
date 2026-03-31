from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.analyzer import analyze_duplicates
from core.loader import FileLoadError, load_file
from core.models import AnalysisSummary, DuplicateResult, ServiceResult


class DuplicateFinderService:
    def load_and_analyze(
        self,
        file_paths: list[str],
        target_column: str,
        *,
        trim_values: bool = True,
        lowercase_values: bool = True,
    ) -> ServiceResult:
        if not file_paths:
            raise ValueError("Aucun fichier selectionne.")

        if not target_column.strip():
            raise ValueError("Le nom de colonne est obligatoire.")

        dataframes: list[pd.DataFrame] = []
        errors: list[str] = []

        for path in file_paths:
            try:
                dataframe = load_file(path)
                cleaned = self._clean_dataframe(dataframe, target_column, trim_values, lowercase_values)
                dataframes.append(cleaned)
            except (FileLoadError, ValueError) as exc:
                errors.append(str(exc))

        if not dataframes:
            raise ValueError("Aucun fichier exploitable n'a pu etre charge.")

        results = analyze_duplicates(dataframes, target_column)
        summary = self._build_summary(results, len(dataframes))
        return ServiceResult(results=results, summary=summary, errors=errors)

    def export_results_csv(self, results: list[DuplicateResult], output_dir: str | Path) -> Path:
        export_path = Path(output_dir) / self._build_export_name("duplicates", "csv")
        self._flatten_results(results).to_csv(export_path, index=False)
        return export_path

    def export_results_excel(self, results: list[DuplicateResult], output_dir: str | Path) -> Path:
        export_path = Path(output_dir) / self._build_export_name("duplicates", "xlsx")
        self._flatten_results(results).to_excel(export_path, index=False)
        return export_path

    def _clean_dataframe(
        self,
        dataframe: pd.DataFrame,
        target_column: str,
        trim_values: bool,
        lowercase_values: bool,
    ) -> pd.DataFrame:
        if target_column not in dataframe.columns:
            source = dataframe["__file__"].iloc[0] if not dataframe.empty else "fichier inconnu"
            raise ValueError(f"Colonne '{target_column}' absente dans {source}")

        cleaned = dataframe.copy()
        series = cleaned[target_column]

        def normalize(value: object) -> object:
            if pd.isna(value):
                return value
            if not isinstance(value, str):
                value = str(value)
            if trim_values:
                value = value.strip()
            if lowercase_values:
                value = value.lower()
            return value

        cleaned[target_column] = series.apply(normalize)
        return cleaned

    def _build_summary(self, results: list[DuplicateResult], file_count: int) -> AnalysisSummary:
        internal_count = sum(1 for result in results if result.type.value == "INTERNE")
        external_count = sum(1 for result in results if result.type.value == "EXTERNE")
        occurrence_count = sum(len(result.occurrences) for result in results)
        return AnalysisSummary(
            file_count=file_count,
            duplicate_group_count=len(results),
            internal_count=internal_count,
            external_count=external_count,
            occurrence_count=occurrence_count,
        )

    def _flatten_results(self, results: list[DuplicateResult]) -> pd.DataFrame:
        rows: list[dict[str, object]] = []
        for result in results:
            for record in result.occurrences:
                rows.append(
                    {
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
        from utils.file_utils import safe_output_name

        return safe_output_name(prefix, extension)
