from __future__ import annotations

from collections import defaultdict

import pandas as pd

from core.models import DuplicateResult, DuplicateType, Record


def analyze_duplicates(dataframes: list[pd.DataFrame], target_column: str) -> list[DuplicateResult]:
    grouped_records: dict[str, list[Record]] = defaultdict(list)

    for dataframe in dataframes:
        if target_column not in dataframe.columns:
            source = dataframe["__file__"].iloc[0] if "__file__" in dataframe.columns and not dataframe.empty else "fichier inconnu"
            raise ValueError(f"Colonne '{target_column}' absente dans {source}")

        for _, row in dataframe.iterrows():
            value = row.get(target_column)
            if pd.isna(value):
                continue

            normalized = str(value)
            record = Record(
                target_value=normalized,
                row_data=row.to_dict(),
                file=str(row.get("__file__", "")),
                row_index=int(row.get("__row_index__", -1)),
            )
            grouped_records[normalized].append(record)

    results: list[DuplicateResult] = []
    for value, occurrences in grouped_records.items():
        if len(occurrences) < 2:
            continue

        files = {record.file for record in occurrences}
        duplicate_type = DuplicateType.EXTERNE if len(files) > 1 else DuplicateType.INTERNE
        results.append(
            DuplicateResult(
                value=value,
                type=duplicate_type,
                occurrences=sorted(occurrences, key=lambda record: (record.file, record.row_index)),
            )
        )

    return sorted(results, key=lambda result: (result.value.lower(), result.type.value))
