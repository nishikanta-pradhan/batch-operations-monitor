import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from batch_monitor.cli import run


class CliTests(unittest.TestCase):
    def test_complete_example_workflow(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            database = str(Path(temporary) / "monitor.db")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(0, run(["--database", database, "init"]))
                self.assertEqual(
                    0,
                    run(["--database", database, "import-jobs", str(project / "examples/jobs.csv")]),
                )
                self.assertEqual(
                    0,
                    run([
                        "--database", database, "import-executions",
                        str(project / "examples/executions.csv"),
                    ]),
                )
                self.assertEqual(
                    0,
                    run([
                        "--database", database, "report", "--date", "2026-11-18",
                        "--observed-at", "2026-11-18T06:00:00",
                    ]),
                )
            rendered = output.getvalue()
            self.assertIn("Batch Operations Report", rendered)
            self.assertIn("INVOICE_BUILD", rendered)


if __name__ == "__main__":
    unittest.main()

