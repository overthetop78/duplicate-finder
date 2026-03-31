from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

from utils.file_utils import is_supported_file


ExcelEngine = Literal["openpyxl", "odf", "xlrd"]


class FileLoadError(Exception):
    pass


def load_files(file_paths: list[str | Path]) -> list[pd.DataFrame]:
    dataframes: list[pd.DataFrame] = []
    for file_path in file_paths:
        dataframes.append(load_file(file_path))
    return dataframes


def load_file(file_path: str | Path) -> pd.DataFrame:
    path = Path(file_path)

    if not path.exists():
        raise FileLoadError(f"Fichier introuvable: {path}")

    if not is_supported_file(path):
        raise FileLoadError(f"Format non supporte: {path.suffix}")

    try:
        dataframe = _read_dataframe(path)
    except Exception as exc:
        raise FileLoadError(f"Impossible de lire {path.name}: {exc}") from exc

    dataframe = pd.DataFrame(dataframe)
    dataframe["__file__"] = str(path)
    dataframe["__row_index__"] = list(range(len(dataframe)))
    return dataframe


def _read_dataframe(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        encodings = ("utf-8", "utf-8-sig", "latin-1", "cp1252")
        last_error: Exception | None = None
        for encoding in encodings:
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
        raise FileLoadError(f"Encodage CSV non reconnu pour {path.name}: {last_error}")

    if suffix == ".xlsx":
        return _read_excel_best_dataframe(path, engine="openpyxl")

    if suffix == ".ods":
        return _read_excel_best_dataframe(path, engine="odf")

    if suffix == ".xls":
        return _read_excel_best_dataframe(path, engine="xlrd")

    raise FileLoadError(f"Format non pris en charge: {suffix}")


def _read_excel_best_dataframe(path: Path, engine: ExcelEngine) -> pd.DataFrame:
    workbook = pd.ExcelFile(path, engine=engine)  # pyright: ignore[reportUnknownMemberType]
    sheet_names = list(workbook.sheet_names)
    if not sheet_names:
        return pd.DataFrame()

    best_dataframe: pd.DataFrame | None = None
    best_score = -1

    for sheet_name in sheet_names:
        raw_sheet = pd.DataFrame(workbook.parse(sheet_name=sheet_name, header=None))  # pyright: ignore[reportUnknownMemberType]
        candidate = _extract_candidate_dataframe(raw_sheet)
        score = _score_dataframe(candidate)
        if score > best_score:
            best_score = score
            best_dataframe = candidate

    if best_dataframe is None:
        first_sheet = sheet_names[0]
        return pd.DataFrame(workbook.parse(sheet_name=first_sheet))  # pyright: ignore[reportUnknownMemberType]

    return best_dataframe


def _extract_candidate_dataframe(raw_sheet: pd.DataFrame) -> pd.DataFrame:
    rows = [list(row) for row in raw_sheet.itertuples(index=False, name=None)]
    if not rows:
        return raw_sheet

    header_row_index = _detect_header_row(rows)
    columns = _build_unique_headers(rows[header_row_index])
    data_rows = rows[header_row_index + 1 :]

    dataframe = pd.DataFrame(data_rows, columns=columns)
    dataframe.dropna(axis=1, how="all", inplace=True)  # pyright: ignore[reportUnknownMemberType]
    dataframe.reset_index(drop=True, inplace=True)  # pyright: ignore[reportUnknownMemberType]
    return dataframe


def _detect_header_row(rows: list[list[object]]) -> int:
    max_rows_to_scan = min(15, len(rows))
    best_row_index = 0
    best_score = -1

    for row_index in range(max_rows_to_scan):
        score = _score_header_row(rows[row_index])
        if score > best_score:
            best_score = score
            best_row_index = row_index

    return best_row_index


def _score_header_row(values: list[object]) -> int:
    score = 0
    for value in values:
        if _is_missing_cell(value):
            continue
        text = str(value).strip()
        if not text:
            continue
        if any(character.isalpha() for character in text):
            score += 3
        else:
            score += 1
    return score


def _build_unique_headers(values: list[object]) -> list[str]:
    headers: list[str] = []
    seen: dict[str, int] = {}

    for index, value in enumerate(values, start=1):
        base_name = _normalize_header_value(value, index)
        count = seen.get(base_name, 0) + 1
        seen[base_name] = count
        if count == 1:
            headers.append(base_name)
        else:
            headers.append(f"{base_name}_{count}")

    return headers


def _normalize_header_value(value: object, index: int) -> str:
    if _is_missing_cell(value):
        return f"Column_{index}"

    text = str(value).strip()
    if not text:
        return f"Column_{index}"
    return text


def _score_dataframe(dataframe: pd.DataFrame) -> int:
    useful_columns = sum(
        1
        for column in dataframe.columns
        if str(column).strip() and not str(column).lower().startswith("unnamed")
    )
    return useful_columns * 1000 + len(dataframe)


def _is_missing_cell(value: object) -> bool:
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    if isinstance(value, float) and value != value:
        return True
    return False
