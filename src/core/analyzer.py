from __future__ import annotations

from collections import defaultdict

import pandas as pd

from core.models import DuplicateResult, DuplicateType, Record


INTERNAL_COLUMNS = {"__file__", "__row_index__"}


def analyze_duplicates(
    dataframes: list[pd.DataFrame],
    *,
    selected_columns: set[str] | None = None,
    ignore_unnamed_columns: bool = True,
) -> tuple[list[DuplicateResult], int, int]:
    grouped_records: dict[tuple[str, str], list[Record]] = defaultdict(list)
    column_index_by_name: dict[str, int] = {}
    scanned_value_count = 0
    ignored_value_count = 0

    for dataframe in dataframes:
        all_data_col_names = [
            str(column)
            for column in dataframe.columns
            if str(column) not in INTERNAL_COLUMNS
        ]
        for position, name in enumerate(all_data_col_names):
            if name not in column_index_by_name:
                column_index_by_name[name] = position
        data_columns = [
            name
            for name in all_data_col_names
            if (selected_columns is None or name in selected_columns)
            and (not ignore_unnamed_columns or not name.lower().startswith("unnamed"))
        ]
        for _, row in dataframe.iterrows():
            row_data = {str(k): v for k, v in row.to_dict().items()}
            record_file = str(row_data.get("__file__", ""))
            record_row_index = int(row_data.get("__row_index__", -1))

            for column_name in data_columns:
                scanned_value_count += 1
                value = row_data.get(column_name)
                if _is_missing(value):
                    ignored_value_count += 1
                    continue

                normalized = str(value)
                record = Record(
                    target_value=normalized,
                    row_data=row_data,
                    file=record_file,
                    row_index=record_row_index,
                )
                grouped_records[(column_name, normalized)].append(record)

    results: list[DuplicateResult] = []
    for (column_name, value), occurrences in grouped_records.items():
        if len(occurrences) < 2:
            continue

        files = {record.file for record in occurrences}
        duplicate_type = DuplicateType.EXTERNE if len(files) > 1 else DuplicateType.INTERNE
        results.append(
            DuplicateResult(
                column_name=column_name,
                column_index=column_index_by_name.get(column_name, 0),
                value=value,
                type=duplicate_type,
                occurrences=sorted(occurrences, key=lambda record: (record.file, record.row_index)),
            )
        )

    sorted_results = sorted(results, key=lambda result: (result.column_name.lower(), result.value.lower(), result.type.value))
    return sorted_results, scanned_value_count, ignored_value_count


def _is_missing(value: object) -> bool:
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    if isinstance(value, float) and value != value:
        return True
    return False
