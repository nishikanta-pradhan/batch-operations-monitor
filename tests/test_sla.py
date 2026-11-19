import unittest
from datetime import date, datetime, time

from batch_monitor.models import (
    Criticality, ExecutionRecord, ExecutionStatus, HealthState, JobDefinition,
)
from batch_monitor.sla import classify_job


class SlaTests(unittest.TestCase):
    def setUp(self):
        self.day = date(2026, 11, 18)
        self.job = JobDefinition("INVOICE_BUILD", "Billing", time(1), time(2), 30, Criticality.CRITICAL)

    def record(self, status, started, finished=None, error=""):
        return ExecutionRecord("e1", self.job.job_name, self.day, started, finished, status, 10, error)

    def test_missing_after_sla(self):
        result = classify_job(self.job, self.day, None, datetime(2026, 11, 18, 3))
        self.assertEqual(HealthState.MISSING, result.state)

    def test_not_due_before_sla(self):
        result = classify_job(self.job, self.day, None, datetime(2026, 11, 18, 1, 30))
        self.assertEqual(HealthState.NOT_DUE, result.state)

    def test_failed_takes_priority(self):
        record = self.record(
            ExecutionStatus.FAILED, datetime(2026, 11, 18, 1),
            datetime(2026, 11, 18, 1, 10), "database unavailable",
        )
        result = classify_job(self.job, self.day, record, datetime(2026, 11, 18, 1, 20))
        self.assertEqual(HealthState.FAILED, result.state)

    def test_running_overdue(self):
        record = self.record(ExecutionStatus.RUNNING, datetime(2026, 11, 18, 1))
        result = classify_job(self.job, self.day, record, datetime(2026, 11, 18, 1, 45))
        self.assertEqual(HealthState.RUNNING_OVERDUE, result.state)

    def test_success_after_sla_is_late(self):
        record = self.record(
            ExecutionStatus.SUCCEEDED, datetime(2026, 11, 18, 1, 30),
            datetime(2026, 11, 18, 2, 15),
        )
        result = classify_job(self.job, self.day, record, datetime(2026, 11, 18, 3))
        self.assertEqual(HealthState.LATE, result.state)


if __name__ == "__main__":
    unittest.main()

