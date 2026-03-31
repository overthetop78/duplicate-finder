from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils.file_utils import is_supported_file


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

    dataframe = dataframe.copy()
    dataframe["__file__"] = str(path)
    dataframe["__row_index__"] = dataframe.index.astype(int)
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
        return pd.read_excel(path, engine="openpyxl")

    if suffix == ".ods":
        return pd.read_excel(path, engine="odf")

    raise FileLoadError(f"Format non pris en charge: {suffix}")
