import unittest
from datetime import date, datetime, time

from batch_monitor.errors import ValidationError
from batch_monitor.models import Criticality, ExecutionRecord, ExecutionStatus, JobDefinition


class ModelTests(unittest.TestCase):
    def test_job_normalizes_name(self):
        job = JobDefinition(" customer_import ", "Operations", time(1), time(2), 30, Criticality.HIGH)
        self.assertEqual("CUSTOMER_IMPORT", job.job_name)

    def test_running_execution_rejects_finish_time(self):
        with self.assertRaisesRegex(ValidationError, "running execution"):
            ExecutionRecord(
                "e1", "JOB", date(2026, 11, 18), datetime(2026, 11, 18, 1),
                datetime(2026, 11, 18, 2), ExecutionStatus.RUNNING,
            )

    def test_failed_execution_requires_message(self):
        with self.assertRaisesRegex(ValidationError, "requires error_message"):
            ExecutionRecord(
                "e1", "JOB", date(2026, 11, 18), datetime(2026, 11, 18, 1),
                datetime(2026, 11, 18, 2), ExecutionStatus.FAILED,
            )


if __name__ == "__main__":
    unittest.main()

