"""Persistence operations that map SQLite rows to domain models."""

from __future__ import annotations

from datetime import date, datetime, time

from .database import Database
from .errors import UnknownJobError
from .models import Criticality, ExecutionRecord, ExecutionStatus, JobDefinition


class MonitorRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def upsert_job(self, job: JobDefinition) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    job_name, owner, schedule_time, sla_time,
                    expected_duration_minutes, criticality, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_name) DO UPDATE SET
                    owner = excluded.owner,
                    schedule_time = excluded.schedule_time,
                    sla_time = excluded.sla_time,
                    expected_duration_minutes = excluded.expected_duration_minutes,
                    criticality = excluded.criticality,
                    enabled = excluded.enabled,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    job.job_name,
                    job.owner,
                    job.schedule_time.isoformat(timespec="minutes"),
                    job.sla_time.isoformat(timespec="minutes"),
                    job.expected_duration_minutes,
                    job.criticality.value,
                    int(job.enabled),
                ),
            )

    def get_job(self, job_name: str) -> JobDefinition | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_name = ?",
                (job_name.strip().upper(),),
            ).fetchone()
        return self._job_from_row(row) if row else None

    def list_jobs(self, *, enabled_only: bool = False) -> list[JobDefinition]:
        query = "SELECT * FROM jobs"
        parameters: tuple[object, ...] = ()
        if enabled_only:
            query += " WHERE enabled = ?"
            parameters = (1,)
        query += " ORDER BY job_name"
        with self.database.connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._job_from_row(row) for row in rows]

    def add_execution(self, execution: ExecutionRecord) -> bool:
        if self.get_job(execution.job_name) is None:
            raise UnknownJobError(
                f"execution {execution.execution_id} references unknown job "
                f"{execution.job_name}"
            )
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO executions (
                    execution_id, job_name, business_date, started_at, finished_at,
                    status, records_processed, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution.execution_id,
                    execution.job_name,
                    execution.business_date.isoformat(),
                    execution.started_at.isoformat(timespec="seconds"),
                    (
                        execution.finished_at.isoformat(timespec="seconds")
                        if execution.finished_at
                        else None
                    ),
                    execution.status.value,
                    execution.records_processed,
                    execution.error_message,
                ),
            )
            return cursor.rowcount == 1

    def latest_execution(
        self, job_name: str, business_date: date
    ) -> ExecutionRecord | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM executions
                WHERE job_name = ? AND business_date = ?
                ORDER BY started_at DESC, imported_at DESC
                LIMIT 1
                """,
                (job_name.strip().upper(), business_date.isoformat()),
            ).fetchone()
        return self._execution_from_row(row) if row else None

    def history(self, job_name: str, limit: int = 20) -> list[ExecutionRecord]:
        if limit <= 0:
            return []
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM executions
                WHERE job_name = ?
                ORDER BY business_date DESC, started_at DESC
                LIMIT ?
                """,
                (job_name.strip().upper(), limit),
            ).fetchall()
        return [self._execution_from_row(row) for row in rows]

    @staticmethod
    def _job_from_row(row: object) -> JobDefinition:
        return JobDefinition(
            job_name=row["job_name"],
            owner=row["owner"],
            schedule_time=time.fromisoformat(row["schedule_time"]),
            sla_time=time.fromisoformat(row["sla_time"]),
            expected_duration_minutes=row["expected_duration_minutes"],
            criticality=Criticality(row["criticality"]),
            enabled=bool(row["enabled"]),
        )

    @staticmethod
    def _execution_from_row(row: object) -> ExecutionRecord:
        return ExecutionRecord(
            execution_id=row["execution_id"],
            job_name=row["job_name"],
            business_date=date.fromisoformat(row["business_date"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=(
                datetime.fromisoformat(row["finished_at"])
                if row["finished_at"]
                else None
            ),
            status=ExecutionStatus(row["status"]),
            records_processed=row["records_processed"],
            error_message=row["error_message"],
        )

