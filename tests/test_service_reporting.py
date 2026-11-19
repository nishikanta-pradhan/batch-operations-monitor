import json
import tempfile
import unittest
from datetime import date, datetime, time
from pathlib import Path

from batch_monitor.database import Database
from batch_monitor.models import Criticality, JobDefinition
from batch_monitor.reporting import report_as_json, report_as_text
from batch_monitor.repository import MonitorRepository
from batch_monitor.service import MonitorService


class ServiceReportingTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(self.tempdir.name) / "test.db")
        database.initialize()
        self.repository = MonitorRepository(database)
        self.repository.upsert_job(
            JobDefinition("LOW_JOB", "Team A", time(1), time(2), 30, Criticality.LOW)
        )
        self.repository.upsert_job(
            JobDefinition("HIGH_JOB", "Team B", time(1), time(2), 30, Criticality.HIGH)
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_minimum_criticality_filter(self):
        day = date(2026, 11, 18)
        observed = datetime(2026, 11, 18, 3)
        report = MonitorService(self.repository).build_report(
            day, observed, minimum_criticality=Criticality.HIGH
        )
        self.assertEqual(["HIGH_JOB"], [item.job.job_name for item in report])

    def test_text_and_json_contain_summary(self):
        day = date(2026, 11, 18)
        observed = datetime(2026, 11, 18, 3)
        report = MonitorService(self.repository).build_report(day, observed)
        text = report_as_text(report, day, observed)
        payload = json.loads(report_as_json(report, day, observed))
        self.assertIn("MISSING=2", text)
        self.assertEqual(2, payload["summary"]["MISSING"])


if __name__ == "__main__":
    unittest.main()

