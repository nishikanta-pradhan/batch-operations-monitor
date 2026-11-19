"""SLA classification rules for individual batch jobs."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from .models import ExecutionRecord, ExecutionStatus, HealthState, JobDefinition, JobHealth


def _at_time(business_date: date, value: object) -> datetime:
    return datetime.combine(business_date, value)


def classify_job(
    job: JobDefinition,
    business_date: date,
    execution: ExecutionRecord | None,
    observed_at: datetime,
) -> JobHealth:
    """Return the operational state of one job at a point in time."""
    sla_deadline = _at_time(business_date, job.sla_time)

    if execution is None:
        if observed_at > sla_deadline:
            return JobHealth(
                job,
                business_date,
                HealthState.MISSING,
                f"no execution recorded by SLA {job.sla_time.isoformat(timespec='minutes')}",
            )
        return JobHealth(
            job,
            business_date,
            HealthState.NOT_DUE,
            f"no execution yet; SLA is {job.sla_time.isoformat(timespec='minutes')}",
        )

    if execution.status == ExecutionStatus.FAILED:
        return JobHealth(
            job,
            business_date,
            HealthState.FAILED,
            execution.error_message,
            execution,
        )

    if execution.status == ExecutionStatus.RUNNING:
        expected_finish = execution.started_at + timedelta(
            minutes=job.expected_duration_minutes
        )
        if observed_at > expected_finish:
            overdue_minutes = int((observed_at - expected_finish).total_seconds() // 60)
            return JobHealth(
                job,
                business_date,
                HealthState.RUNNING_OVERDUE,
                f"running {overdue_minutes} minutes beyond expected finish",
                execution,
            )
        return JobHealth(
            job,
            business_date,
            HealthState.RUNNING,
            f"running; expected finish {expected_finish.isoformat(timespec='minutes')}",
            execution,
        )

    if execution.finished_at and execution.finished_at > sla_deadline:
        late_minutes = int((execution.finished_at - sla_deadline).total_seconds() // 60)
        return JobHealth(
            job,
            business_date,
            HealthState.LATE,
            f"completed {late_minutes} minutes after SLA",
            execution,
        )

    return JobHealth(
        job,
        business_date,
        HealthState.HEALTHY,
        "completed within SLA",
        execution,
    )

