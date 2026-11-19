"""Application service coordinating persistence, filtering and SLA rules."""

from __future__ import annotations

from datetime import date, datetime

from .models import Criticality, JobHealth
from .repository import MonitorRepository
from .sla import classify_job


class MonitorService:
    def __init__(self, repository: MonitorRepository) -> None:
        self.repository = repository

    def build_report(
        self,
        business_date: date,
        observed_at: datetime,
        *,
        owner: str | None = None,
        minimum_criticality: Criticality | None = None,
    ) -> list[JobHealth]:
        jobs = self.repository.list_jobs(enabled_only=True)
        if owner:
            expected_owner = owner.strip().casefold()
            jobs = [job for job in jobs if job.owner.casefold() == expected_owner]
        if minimum_criticality:
            jobs = [
                job
                for job in jobs
                if job.criticality.rank >= minimum_criticality.rank
            ]

        health = [
            classify_job(
                job,
                business_date,
                self.repository.latest_execution(job.job_name, business_date),
                observed_at,
            )
            for job in jobs
        ]
        return sorted(
            health,
            key=lambda item: (-item.state.severity, -item.job.criticality.rank, item.job.job_name),
        )

