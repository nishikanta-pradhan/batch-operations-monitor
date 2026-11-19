"""CSV import functions with row-level validation context."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .errors import ImportFileError, MonitorError, ValidationError
from .models import (
    Criticality,
    ExecutionRecord,
    ExecutionStatus,
    JobDefinition,
    parse_bool,
    parse_date,
    parse_datetime,
    parse_time,
)
from .repository import MonitorRepository


JOB_COLUMNS = {
    "job_name",
    "owner",
    "schedule_time",
    "sla_time",
    "expected_duration_minutes",
    "criticality",
    "enabled",
}

EXECUTION_COLUMNS = {
    "execution_id",
    "job_name",
    "business_date",
    "started_at",
    "finished_at",
    "status",
    "records_processed",
    "error_message",
}


@dataclass(frozen=True, slots=True)
class ImportSummary:
    read: int
    inserted: int
    skipped: int


def _read_csv(path: str | Path, required_columns: set[str]) -> Iterable[tuple[int, dict[str, str]]]:
    csv_path = Path(path)
    if not csv_path.is_file():
        raise ImportFileError(f"CSV file does not exist: {csv_path}")
    try:
        handle = csv_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise ImportFileError(f"cannot open CSV file: {csv_path}") from exc
    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ImportFileError(f"CSV has no header: {csv_path}")
        actual = {name.strip() for name in reader.fieldnames if name}
        missing = sorted(required_columns - actual)
        if missing:
            raise ImportFileError(
                f"CSV is missing required columns: {', '.join(missing)}"
            )
        for line_number, row in enumerate(reader, start=2):
            normalized = {(key or "").strip(): (value or "").strip() for key, value in row.items()}
            if not any(normalized.values()):
                continue
            yield line_number, normalized


def _positive_int(raw: str, field_name: str) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be an integer") from exc
    if value < 0:
        raise ValidationError(f"{field_name} cannot be negative")
    return value


def import_jobs(path: str | Path, repository: MonitorRepository) -> ImportSummary:
    read = inserted = 0
    for line_number, row in _read_csv(path, JOB_COLUMNS):
        read += 1
        try:
            duration = _positive_int(
                row["expected_duration_minutes"], "expected_duration_minutes"
            )
            job = JobDefinition(
                job_name=row["job_name"],
                owner=row["owner"],
                schedule_time=parse_time(row["schedule_time"], "schedule_time"),
                sla_time=parse_time(row["sla_time"], "sla_time"),
                expected_duration_minutes=duration,
                criticality=Criticality.parse(row["criticality"]),
                enabled=parse_bool(row["enabled"]),
            )
            repository.upsert_job(job)
            inserted += 1
        except MonitorError as exc:
            raise ImportFileError(f"{path}: line {line_number}: {exc}") from exc
    return ImportSummary(read=read, inserted=inserted, skipped=0)


def import_executions(
    path: str | Path, repository: MonitorRepository
) -> ImportSummary:
    read = inserted = skipped = 0
    for line_number, row in _read_csv(path, EXECUTION_COLUMNS):
        read += 1
        try:
            execution = ExecutionRecord(
                execution_id=row["execution_id"],
                job_name=row["job_name"],
                business_date=parse_date(row["business_date"]),
                started_at=parse_datetime(row["started_at"], "started_at"),
                finished_at=parse_datetime(
                    row["finished_at"], "finished_at", optional=True
                ),
                status=ExecutionStatus.parse(row["status"]),
                records_processed=_positive_int(
                    row["records_processed"], "records_processed"
                ),
                error_message=row["error_message"],
            )
            if repository.add_execution(execution):
                inserted += 1
            else:
                skipped += 1
        except MonitorError as exc:
            raise ImportFileError(f"{path}: line {line_number}: {exc}") from exc
    return ImportSummary(read=read, inserted=inserted, skipped=skipped)

