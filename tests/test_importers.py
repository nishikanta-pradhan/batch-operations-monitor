import tempfile
import unittest
from pathlib import Path

from batch_monitor.database import Database
from batch_monitor.errors import ImportFileError
from batch_monitor.importers import import_executions, import_jobs
from batch_monitor.repository import MonitorRepository


class ImporterTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        database = Database(root / "test.db")
        database.initialize()
        self.repository = MonitorRepository(database)
        self.root = root

    def tearDown(self):
        self.tempdir.cleanup()

    def write(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_import_jobs_and_idempotent_executions(self):
        jobs = self.write(
            "jobs.csv",
            "job_name,owner,schedule_time,sla_time,expected_duration_minutes,criticality,enabled\n"
            "JOB_A,Ops,01:00,02:00,30,high,true\n",
        )
        executions = self.write(
            "executions.csv",
            "execution_id,job_name,business_date,started_at,finished_at,status,records_processed,error_message\n"
            "e1,JOB_A,2026-11-18,2026-11-18T01:00:00,2026-11-18T01:20:00,succeeded,10,\n",
        )
        self.assertEqual(1, import_jobs(jobs, self.repository).inserted)
        self.assertEqual(1, import_executions(executions, self.repository).inserted)
        second = import_executions(executions, self.repository)
        self.assertEqual(0, second.inserted)
        self.assertEqual(1, second.skipped)

    def test_missing_columns_are_reported(self):
        bad = self.write("bad.csv", "job_name,owner\nJOB_A,Ops\n")
        with self.assertRaisesRegex(ImportFileError, "missing required columns"):
            import_jobs(bad, self.repository)


if __name__ == "__main__":
    unittest.main()

