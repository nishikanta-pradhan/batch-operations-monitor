"""Console and JSON formatting for operational reports."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime
from typing import Iterable

from .models import ExecutionRecord, JobHealth


def report_as_json(
    health: Iterable[JobHealth], business_date: date, observed_at: datetime
) -> str:
    items = list(health)
    counts = Counter(item.state.value for item in items)
    payload = {
        "business_date": business_date.isoformat(),
        "observed_at": observed_at.isoformat(timespec="seconds"),
        "summary": dict(sorted(counts.items())),
        "jobs": [item.to_dict() for item in items],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def report_as_text(
    health: Iterable[JobHealth], business_date: date, observed_at: datetime
) -> str:
    items = list(health)
    counts = Counter(item.state.value for item in items)
    lines = [
        f"Batch Operations Report - {business_date.isoformat()}",
        f"Observed at: {observed_at.isoformat(timespec='minutes')}",
        "",
    ]
    if counts:
        lines.append(
            "Summary: " + ", ".join(f"{state}={count}" for state, count in sorted(counts.items()))
        )
    else:
        lines.append("Summary: no matching jobs")
    lines.extend(["", "STATE            CRITICALITY JOB                  OWNER           REASON"])
    lines.append("-" * 100)
    for item in items:
        lines.append(
            f"{item.state.value:<16} "
            f"{item.job.criticality.value:<11} "
            f"{item.job.job_name:<20} "
            f"{item.job.owner:<15} "
            f"{item.reason}"
        )
    return "\n".join(lines)


def history_as_text(records: Iterable[ExecutionRecord]) -> str:
    items = list(records)
    if not items:
        return "No execution history found."
    lines = [
        "BUSINESS DATE STATUS     STARTED             FINISHED            RECORDS EXECUTION ID",
        "-" * 100,
    ]
    for record in items:
        finished = record.finished_at.isoformat(timespec="minutes") if record.finished_at else "-"
        lines.append(
            f"{record.business_date.isoformat():<13} "
            f"{record.status.value:<10} "
            f"{record.started_at.isoformat(timespec='minutes'):<19} "
            f"{finished:<19} "
            f"{record.records_processed:<7} "
            f"{record.execution_id}"
        )
    return "\n".join(lines)

