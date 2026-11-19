import tempfile
import unittest
from datetime import date, datetime, time
from pathlib import Path

from batch_monitor.database import Database
from batch_monitor.errors import UnknownJobError
from batch_monitor.models import Criticality, ExecutionRecord, ExecutionStatus, JobDefinition
from batch_monitor.repository import MonitorRepository


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(self.tempdir.name) / "test.db")
        database.initialize()
        self.repository = MonitorRepository(database)
        self.job = JobDefinition("DAILY_REPORT", "Reporting", time(3), time(4), 30, Criticality.MEDIUM)
        self.repository.upsert_job(self.job)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_upsert_updates_existing_job(self):
        changed = JobDefinition("DAILY_REPORT", "DataOps", time(3), time(5), 45, Criticality.HIGH)
        self.repository.upsert_job(changed)
        loaded = self.repository.get_job("daily_report")
        self.assertEqual("DataOps", loaded.owner)
        self.assertEqual(time(5), loaded.sla_time)

    def test_duplicate_execution_is_skipped(self):
        record = ExecutionRecord(
            "exec-1", "DAILY_REPORT", date(2026, 11, 18), datetime(2026, 11, 18, 3),
            datetime(2026, 11, 18, 3, 20), ExecutionStatus.SUCCEEDED, 20,
        )
        self.assertTrue(self.repository.add_execution(record))
        self.assertFalse(self.repository.add_execution(record))

    def test_unknown_job_is_rejected(self):
        record = ExecutionRecord(
            "exec-2", "UNKNOWN", date(2026, 11, 18), datetime(2026, 11, 18, 3),
            datetime(2026, 11, 18, 3, 20), ExecutionStatus.SUCCEEDED,
        )
        with self.assertRaises(UnknownJobError):
            self.repository.add_execution(record)


if __name__ == "__main__":
    unittest.main()

