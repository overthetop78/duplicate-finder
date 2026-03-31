from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DuplicateType(str, Enum):
    INTERNE = "INTERNE"
    EXTERNE = "EXTERNE"


@dataclass(slots=True)
class Record:
    target_value: str
    row_data: dict[str, Any]
    file: str
    row_index: int


@dataclass(slots=True)
class DuplicateResult:
    column_name: str
    value: str
    type: DuplicateType
    column_index: int = 0
    occurrences: list[Record] = field(default_factory=lambda: [])


@dataclass(slots=True)
class AnalysisSummary:
    file_count: int
    duplicate_group_count: int
    internal_count: int
    external_count: int
    occurrence_count: int
    scanned_value_count: int
    ignored_value_count: int
    analyzed_value_count: int


@dataclass(slots=True)
class ServiceResult:
    results: list[DuplicateResult]
    summary: AnalysisSummary
    errors: list[str] = field(default_factory=lambda: [])
