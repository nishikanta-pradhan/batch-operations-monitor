"""Domain models and parsing helpers for batch operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum

from .errors import ValidationError


class Criticality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return {
            Criticality.LOW: 1,
            Criticality.MEDIUM: 2,
            Criticality.HIGH: 3,
            Criticality.CRITICAL: 4,
        }[self]

    @classmethod
    def parse(cls, raw: str) -> "Criticality":
        try:
            return cls(raw.strip().lower())
        except (AttributeError, ValueError) as exc:
            allowed = ", ".join(item.value for item in cls)
            raise ValidationError(f"criticality must be one of: {allowed}") from exc


class ExecutionStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

    @classmethod
    def parse(cls, raw: str) -> "ExecutionStatus":
        try:
            return cls(raw.strip().lower())
        except (AttributeError, ValueError) as exc:
            allowed = ", ".join(item.value for item in cls)
            raise ValidationError(f"status must be one of: {allowed}") from exc


class HealthState(str, Enum):
    FAILED = "FAILED"
    RUNNING_OVERDUE = "RUNNING_OVERDUE"
    MISSING = "MISSING"
    LATE = "LATE"
    RUNNING = "RUNNING"
    HEALTHY = "HEALTHY"
    NOT_DUE = "NOT_DUE"

    @property
    def severity(self) -> int:
        return {
            HealthState.FAILED: 70,
            HealthState.RUNNING_OVERDUE: 60,
            HealthState.MISSING: 50,
            HealthState.LATE: 40,
            HealthState.RUNNING: 30,
            HealthState.HEALTHY: 20,
            HealthState.NOT_DUE: 10,
        }[self]


def parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in {"true", "1", "yes", "y"}:
        return True
    if value in {"false", "0", "no", "n"}:
        return False
    raise ValidationError("enabled must be true/false, yes/no, or 1/0")


def parse_time(raw: str, field_name: str) -> time:
    try:
        return time.fromisoformat(raw.strip())
    except (AttributeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must use HH:MM format") from exc


def parse_date(raw: str, field_name: str = "business_date") -> date:
    try:
        return date.fromisoformat(raw.strip())
    except (AttributeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must use YYYY-MM-DD format") from exc


def parse_datetime(raw: str, field_name: str, *, optional: bool = False) -> datetime | None:
    value = raw.strip()
    if optional and not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (AttributeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is not None:
        raise ValidationError(f"{field_name} must be a local timestamp without timezone")
    return parsed


@dataclass(frozen=True, slots=True)
class JobDefinition:
    job_name: str
    owner: str
    schedule_time: time
    sla_time: time
    expected_duration_minutes: int
    criticality: Criticality
    enabled: bool = True

    def __post_init__(self) -> None:
        normalized_name = self.job_name.strip().upper()
        normalized_owner = self.owner.strip()
        if not normalized_name:
            raise ValidationError("job_name is required")
        if not normalized_owner:
            raise ValidationError("owner is required")
        if self.expected_duration_minutes <= 0:
            raise ValidationError("expected_duration_minutes must be greater than zero")
        object.__setattr__(self, "job_name", normalized_name)
        object.__setattr__(self, "owner", normalized_owner)


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    execution_id: str
    job_name: str
    business_date: date
    started_at: datetime
    finished_at: datetime | None
    status: ExecutionStatus
    records_processed: int = 0
    error_message: str = ""

    def __post_init__(self) -> None:
        execution_id = self.execution_id.strip()
        job_name = self.job_name.strip().upper()
        error_message = self.error_message.strip()
        if not execution_id:
            raise ValidationError("execution_id is required")
        if not job_name:
            raise ValidationError("job_name is required")
        if self.records_processed < 0:
            raise ValidationError("records_processed cannot be negative")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValidationError("finished_at cannot be earlier than started_at")
        if self.status == ExecutionStatus.RUNNING and self.finished_at is not None:
            raise ValidationError("a running execution cannot have finished_at")
        if self.status != ExecutionStatus.RUNNING and self.finished_at is None:
            raise ValidationError("a completed execution requires finished_at")
        if self.status == ExecutionStatus.FAILED and not error_message:
            raise ValidationError("a failed execution requires error_message")
        object.__setattr__(self, "execution_id", execution_id)
        object.__setattr__(self, "job_name", job_name)
        object.__setattr__(self, "error_message", error_message)


@dataclass(frozen=True, slots=True)
class JobHealth:
    job: JobDefinition
    business_date: date
    state: HealthState
    reason: str
    execution: ExecutionRecord | None = None

    def to_dict(self) -> dict[str, object]:
        execution = self.execution
        return {
            "job_name": self.job.job_name,
            "owner": self.job.owner,
            "criticality": self.job.criticality.value,
            "business_date": self.business_date.isoformat(),
            "state": self.state.value,
            "reason": self.reason,
            "execution_id": execution.execution_id if execution else None,
            "started_at": execution.started_at.isoformat() if execution else None,
            "finished_at": (
                execution.finished_at.isoformat()
                if execution and execution.finished_at
                else None
            ),
            "records_processed": execution.records_processed if execution else None,
        }

