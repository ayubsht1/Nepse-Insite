import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from apps.crawlers.models import CrawlRun, CrawlSource
from apps.crawlers.tasks import run_crawl_source_direct
from apps.market_data import tasks as market_tasks

logger = logging.getLogger(__name__)

COLLECTION_LOCK_ID = 0x4E45505345
MAX_RUN_IDS = 100

MARKET_DATA_TASKS = (
    market_tasks.collect_nepsealpha_market_data,
    market_tasks.collect_sharesansar_market_data,
    market_tasks.collect_merolagani_market_data,
    market_tasks.collect_merolagani_floorsheet_data,
)

OPERATIONS = {
    "market-data": MARKET_DATA_TASKS,
    "company-history": (market_tasks.collect_sharesansar_company_history_data,),
    "index-history": (market_tasks.collect_sharesansar_index_history_data,),
    "company-directory": (market_tasks.sync_sharesansar_company_directory,),
}


class Command(BaseCommand):
    help = "Run a data collection operation synchronously without publishing Celery tasks."

    def add_arguments(self, parser):
        parser.add_argument(
            "operation",
            choices=(*OPERATIONS, "news"),
            help="Collection operation to execute.",
        )
        parser.add_argument(
            "--source-keys",
            default="",
            help="Comma-separated enabled crawler keys; defaults to all enabled sources.",
        )
        parser.add_argument(
            "--run-ids",
            default="",
            help="Comma-separated queued CrawlRun IDs to execute directly.",
        )

    def handle(self, *args, **options):
        operation = options["operation"]
        source_keys = self._parse_csv(options["source_keys"], "source-keys")
        run_ids = self._parse_ids(options["run_ids"])
        if operation != "news" and (source_keys or run_ids):
            raise CommandError("--source-keys and --run-ids are valid only for news.")
        if source_keys and run_ids:
            raise CommandError("Use either --source-keys or --run-ids, not both.")

        if not self._acquire_lock():
            raise CommandError(
                "Another collection job is running; this job did not start."
            )
        try:
            if operation == "news":
                self._run_news(source_keys, run_ids)
            else:
                self._run_tasks(OPERATIONS[operation])
        finally:
            self._release_lock()

    def _parse_csv(self, value, option):
        values = [item.strip() for item in value.split(",") if item.strip()]
        if len(values) > MAX_RUN_IDS:
            raise CommandError(f"--{option} accepts at most {MAX_RUN_IDS} values.")
        if len(values) != len(set(values)):
            raise CommandError(f"--{option} must not contain duplicates.")
        return values

    def _parse_ids(self, value):
        raw_ids = self._parse_csv(value, "run-ids")
        if any(not value.isdecimal() or int(value) < 1 for value in raw_ids):
            raise CommandError("--run-ids must contain positive integer IDs.")
        return [int(value) for value in raw_ids]

    def _acquire_lock(self):
        if connection.vendor != "postgresql":
            return True
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", [COLLECTION_LOCK_ID])
            return cursor.fetchone()[0]

    def _release_lock(self):
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [COLLECTION_LOCK_ID])

    def _run_tasks(self, tasks):
        failures = []
        for task in tasks:
            try:
                result = task.run()
            except Exception as exc:
                logger.exception("Direct collection task %s failed", task.name)
                self.stderr.write(f"{task.name} failed: {exc}")
                failures.append(task.name)
            else:
                summary = (
                    {key: value for key, value in result.items() if key != "results"}
                    if isinstance(result, dict)
                    else result
                )
                self.stdout.write(f"{task.name}: {summary!r}")
                if isinstance(result, dict) and result.get("failed", 0):
                    failures.append(task.name)

        if failures:
            raise CommandError(
                "One or more collection tasks failed: " + ", ".join(failures)
            )

    def _run_news(self, source_keys, run_ids):
        if run_ids:
            runs = list(
                CrawlRun.objects.filter(pk__in=run_ids)
                .select_related("source")
                .order_by("pk")
            )
            if len(runs) != len(run_ids):
                found_ids = {run.pk for run in runs}
                missing_ids = [
                    run_id for run_id in run_ids if run_id not in found_ids
                ]
                raise CommandError(
                    "CrawlRun ID(s) do not exist: "
                    + ", ".join(str(run_id) for run_id in missing_ids)
                )
            if any(run.status != CrawlRun.Status.QUEUED for run in runs):
                raise CommandError("Only queued CrawlRuns can be executed.")
        elif source_keys:
            sources = list(CrawlSource.objects.filter(key__in=source_keys))
            found_keys = {source.key for source in sources}
            missing_keys = set(source_keys) - found_keys
            disabled_keys = {
                source.key for source in sources if not source.enabled
            }
            if missing_keys:
                raise CommandError(
                    "Unknown crawler source key(s): "
                    + ", ".join(sorted(missing_keys))
                )
            if disabled_keys:
                raise CommandError(
                    "Crawler source(s) are disabled: "
                    + ", ".join(sorted(disabled_keys))
                )
            runs = [
                CrawlRun.objects.create(source=source)
                for source in sorted(sources, key=lambda source: source.key)
            ]
        else:
            runs = list(
                CrawlRun.objects.filter(status=CrawlRun.Status.QUEUED)
                .select_related("source")
                .order_by("created_at", "pk")[:MAX_RUN_IDS]
            )
            queued_source_ids = {
                run.source_id for run in runs if run.source_id is not None
            }
            enabled_sources = CrawlSource.objects.filter(enabled=True).exclude(
                pk__in=queued_source_ids
            )
            runs.extend(
                CrawlRun.objects.create(source=source)
                for source in enabled_sources.order_by("key")[:MAX_RUN_IDS]
            )

        if not runs:
            self.stdout.write("No queued runs or enabled crawler sources.")
            return

        failures = []
        for run in runs:
            if run.source is None or not run.source.enabled:
                self._fail_run(run, "Crawler source is missing or disabled.")
                failures.append(str(run.pk))
                continue
            try:
                result = run_crawl_source_direct(run.source_id, run.pk)
            except Exception as exc:
                logger.exception("Direct crawl run %s failed", run.pk)
                failures.append(str(run.pk))
                self.stderr.write(f"CrawlRun {run.pk} failed: {exc}")
            else:
                self.stdout.write(f"CrawlRun {run.pk}: {result!r}")

        if failures:
            raise CommandError("CrawlRun failure(s): " + ", ".join(failures))

    def _fail_run(self, run, message):
        run.status = CrawlRun.Status.FAILED
        run.error_message = message
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "error_message", "finished_at"])
