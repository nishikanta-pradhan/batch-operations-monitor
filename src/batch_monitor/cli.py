"""Command-line interface for Batch Operations Monitor."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from .database import Database
from .errors import MonitorError, ValidationError
from .importers import import_executions, import_jobs
from .models import Criticality, parse_date, parse_datetime
from .reporting import history_as_text, report_as_json, report_as_text
from .repository import MonitorRepository
from .service import MonitorService


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="batch-monitor",
        description="Track batch executions and report SLA health.",
    )
    parser.add_argument(
        "--database",
        default="batch-monitor.db",
        help="SQLite database path (default: batch-monitor.db)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="create or upgrade the local database")

    jobs_parser = subparsers.add_parser("import-jobs", help="import job definitions from CSV")
    jobs_parser.add_argument("csv_file", type=Path)

    executions_parser = subparsers.add_parser(
        "import-executions", help="import execution records from CSV"
    )
    executions_parser.add_argument("csv_file", type=Path)

    report_parser = subparsers.add_parser("report", help="show SLA health for a business date")
    report_parser.add_argument("--date", dest="business_date", required=True)
    report_parser.add_argument(
        "--observed-at",
        help="ISO local timestamp used for evaluation (default: current time)",
    )
    report_parser.add_argument("--owner", help="include jobs owned by this team only")
    report_parser.add_argument(
        "--minimum-criticality",
        choices=[item.value for item in Criticality],
    )
    report_parser.add_argument("--format", choices=["text", "json"], default="text")

    history_parser = subparsers.add_parser("history", help="show recent executions for one job")
    history_parser.add_argument("job_name")
    history_parser.add_argument("--limit", type=int, default=20)
    return parser


def _initialize_components(database_path: str) -> tuple[Database, MonitorRepository]:
    database = Database(database_path)
    database.initialize()
    return database, MonitorRepository(database)


def run(arguments: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(arguments)
    database, repository = _initialize_components(args.database)

    if args.command == "init":
        print(f"Initialized database: {database.path}")
        return 0

    if args.command == "import-jobs":
        summary = import_jobs(args.csv_file, repository)
        print(f"Jobs: read={summary.read}, upserted={summary.inserted}")
        return 0

    if args.command == "import-executions":
        summary = import_executions(args.csv_file, repository)
        print(
            f"Executions: read={summary.read}, inserted={summary.inserted}, "
            f"duplicates_skipped={summary.skipped}"
        )
        return 0

    if args.command == "report":
        business_date = parse_date(args.business_date, "date")
        observed_at = (
            parse_datetime(args.observed_at, "observed_at")
            if args.observed_at
            else datetime.now()
        )
        minimum = (
            Criticality.parse(args.minimum_criticality)
            if args.minimum_criticality
            else None
        )
        health = MonitorService(repository).build_report(
            business_date,
            observed_at,
            owner=args.owner,
            minimum_criticality=minimum,
        )
        output = (
            report_as_json(health, business_date, observed_at)
            if args.format == "json"
            else report_as_text(health, business_date, observed_at)
        )
        print(output)
        return 0

    if args.command == "history":
        if args.limit <= 0:
            raise ValidationError("limit must be greater than zero")
        print(history_as_text(repository.history(args.job_name, args.limit)))
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


def main() -> None:
    try:
        raise SystemExit(run())
    except MonitorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()

