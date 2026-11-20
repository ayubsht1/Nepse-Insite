import logging
import time

import httpx
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from common.events import broadcast_on_commit
from apps.crawlers.models import CrawlRun, CrawlSource
from apps.crawlers.tasks import run_crawl_source_direct
from apps.market_data import tasks as market_tasks
from apps.market_data.analysis import refresh_market_analysis

logger = logging.getLogger(__name__)

COLLECTION_LOCK_ID = 0x4E45505345
MAX_RUN_IDS = 100

MARKET_DATA_TASKS = (
    market_tasks.collect_nepsealpha_market_data,
    market_tasks.collect_sharesansar_market_data,
    market_tasks.collect_merolagani_market_data,
    market_tasks.collect_merolagani_floorsheet_data,
)

HISTORICAL_MARKET_TASKS = (
    market_tasks.sync_sharesansar_company_directory,
    market_tasks.collect_sharesansar_index_history_data,
    market_tasks.collect_sharesansar_company_history_data,
)

OPERATIONS = {
    "market-data": MARKET_DATA_TASKS,
    "live_market": MARKET_DATA_TASKS,
    "historical_market": HISTORICAL_MARKET_TASKS,
    "company-history": (market_tasks.collect_sharesansar_company_history_data,),
    "index-history": (market_tasks.collect_sharesansar_index_history_data,),
    "company-directory": (market_tasks.sync_sharesansar_company_directory,),
}

TASK_SOURCES = {
    market_tasks.collect_nepsealpha_market_data.name: "nepsealpha",
    market_tasks.collect_sharesansar_market_data.name: "sharesansar",
    market_tasks.collect_merolagani_market_data.name: "merolagani",
    market_tasks.collect_merolagani_floorsheet_data.name: "merolagani-floorsheet",
    market_tasks.sync_sharesansar_company_directory.name: "sharesansar-company-directory",
    market_tasks.collect_sharesansar_index_history_data.name: "sharesansar-index-history",
    market_tasks.collect_sharesansar_company_history_data.name: "sharesansar-company-history",
}

MARKET_SOURCE_TASKS = {
    "nepsealpha": (market_tasks.collect_nepsealpha_market_data,),
    "sharesansar": (
        market_tasks.collect_sharesansar_market_data,
        market_tasks.sync_sharesansar_company_directory,
        market_tasks.collect_sharesansar_index_history_data,
        market_tasks.collect_sharesansar_company_history_data,
    ),
    "merolagani": (
        market_tasks.collect_merolagani_market_data,
        market_tasks.collect_merolagani_floorsheet_data,
    ),
    "merolagani-floorsheet": (
        market_tasks.collect_merolagani_floorsheet_data,
    ),
    "sharesansar-company-directory": (
        market_tasks.sync_sharesansar_company_directory,
    ),
    "sharesansar-index-history": (
        market_tasks.collect_sharesansar_index_history_data,
    ),
    "sharesansar-company-history": (
        market_tasks.collect_sharesansar_company_history_data,
    ),
}

MAX_PROVIDER_RETRIES = 2


class Command(BaseCommand):
    help = "Run news and market collection operations synchronously without Celery workers."

    def add_arguments(self, parser):
        parser.add_argument(
            "operation",
            choices=(*OPERATIONS, "news", "market_analysis", "all"),
            help="Collection operation to execute.",
        )
        parser.add_argument(
            "--source-keys",
            default="",
            help="Enabled news-source keys; for all, applies to its news collection.",
        )
        parser.add_argument(
            "--run-ids",
            default="",
            help="Optional queued CrawlRun IDs for news collection.",
        )
        parser.add_argument(
            "--market-source-keys",
            default="",
            help=(
                "Optional market provider keys: nepsealpha, sharesansar, "
                "merolagani, or a specific history source."
            ),
        )

    def handle(self, *args, **options):
        operation = options["operation"]
        source_keys = self._parse_csv(options["source_keys"], "source-keys")
        run_ids = self._parse_ids(options["run_ids"])
        market_source_keys = self._parse_csv(
            options["market_source_keys"], "market-source-keys"
        )
        if operation not in {"news", "all"} and (source_keys or run_ids):
            raise CommandError(
                "--source-keys and --run-ids are valid only for news or all."
            )
        if source_keys and run_ids:
            raise CommandError("Use either --source-keys or --run-ids, not both.")
        if market_source_keys and operation not in {*OPERATIONS, "all"}:
            raise CommandError(
                "--market-source-keys is valid only for market operations or all."
            )
        unknown_market_keys = sorted(
            set(market_source_keys) - set(MARKET_SOURCE_TASKS)
        )
        if unknown_market_keys:
            raise CommandError(
                "Unknown market source key(s): " + ", ".join(unknown_market_keys)
            )

        if operation == "all":
            live_tasks = self._select_market_tasks(
                OPERATIONS["live_market"], market_source_keys
            )
            historical_tasks = self._select_market_tasks(
                OPERATIONS["historical_market"], market_source_keys
            )
            if market_source_keys and not (live_tasks or historical_tasks):
                raise CommandError(
                    "Selected market sources are not available in a market operation."
                )
        elif operation in OPERATIONS:
            selected_tasks = self._select_market_tasks(
                OPERATIONS[operation], market_source_keys
            )
            if market_source_keys and not selected_tasks:
                raise CommandError(
                    f"Selected market sources are not available for {operation}."
                )
        else:
            selected_tasks = ()

        self._market_collection_successful = False
        if not self._acquire_lock():
            raise CommandError(
                "Another collection job is running; this job did not start."
            )
        try:
            if operation == "news":
                self._run_news(source_keys, run_ids)
            elif operation == "all":
                self._run_all(
                    source_keys,
                    run_ids,
                    live_tasks,
                    historical_tasks,
                )
            elif operation == "market_analysis":
                self._run_market_analysis()
            else:
                collection_type = (
                    CrawlRun.CollectionType.HISTORICAL_MARKET
                    if operation in {
                        "historical_market",
                        "company-history",
                        "index-history",
                        "company-directory",
                    }
                    else CrawlRun.CollectionType.LIVE_MARKET
                )
                failures = []
                try:
                    self._run_tasks(selected_tasks, collection_type)
                except CommandError as exc:
                    failures.append(str(exc))
                try:
                    self._run_market_analysis(require_collection_success=True)
                except CommandError as exc:
                    failures.append(str(exc))
                if failures:
                    raise CommandError("; ".join(failures))
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

    def _select_market_tasks(self, tasks, source_keys):
        if not source_keys:
            return tasks
        selected_names = {
            task.name
            for key in source_keys
            for task in MARKET_SOURCE_TASKS[key]
        }
        return tuple(task for task in tasks if task.name in selected_names)

    def _run_all(self, source_keys, run_ids, live_tasks, historical_tasks):
        failures = []
        for operation, callback in (
            ("news", lambda: self._run_news(source_keys, run_ids)),
            (
                "live_market",
                lambda: self._run_tasks(
                    live_tasks,
                    CrawlRun.CollectionType.LIVE_MARKET,
                ),
            ),
            (
                "historical_market",
                lambda: self._run_tasks(
                    historical_tasks,
                    CrawlRun.CollectionType.HISTORICAL_MARKET,
                ),
            ),
            (
                "market_analysis",
                lambda: self._run_market_analysis(
                    require_collection_success=True
                ),
            ),
        ):
            try:
                callback()
            except CommandError as exc:
                logger.error("Collection operation %s had failures: %s", operation, exc)
                failures.append(f"{operation}: {exc}")

        if failures:
            raise CommandError("Collection 'all' completed with failures: " + "; ".join(failures))

    def _run_tasks(self, tasks, collection_type):
        failures = []
        for task in tasks:
            source = TASK_SOURCES[task.name]
            run = CrawlRun.objects.create(
                collection_type=collection_type,
                collection_source=source,
                status=CrawlRun.Status.RUNNING,
                started_at=timezone.now(),
            )
            self._publish_collection_run(run)
            try:
                result = self._run_task_with_retries(task)
            except Exception as exc:
                logger.exception("Direct collection task %s failed", task.name)
                run.status = CrawlRun.Status.FAILED
                run.error_message = str(exc)[:4000]
                failures.append(f"{source}: {exc}")
                self.stderr.write(f"{source} failed: {exc}")
            else:
                if not isinstance(result, dict):
                    run.status = CrawlRun.Status.FAILED
                    run.error_message = "Collection service returned an invalid result."
                    failures.append(f"{source}: invalid collection result")
                    self.stderr.write(f"{source} returned an invalid result.")
                else:
                    run.records_created = self._count_result(
                        result, "records_created", "created"
                    )
                    run.records_updated = self._count_result(
                        result, "records_updated", "updated"
                    )
                    run.records_processed = self._count_result(
                        result,
                        "records_processed",
                        "records",
                        "stocks",
                        "companies",
                        "submitted",
                    )
                    status = result.get("status")
                    error_messages = result.get("errors", [])
                    if status == "skipped":
                        run.status = CrawlRun.Status.SKIPPED
                        run.error_message = str(result.get("reason", ""))[:4000]
                    elif status == "partial" or result.get("failed", 0):
                        run.status = CrawlRun.Status.PARTIAL
                        run.error_message = (
                            "; ".join(map(str, error_messages))
                            or str(result.get("reason", "partial collection"))
                        )[:4000]
                        failures.append(f"{source}: partial collection")
                    elif status in (None, "collected", "ok", "success"):
                        run.status = CrawlRun.Status.SUCCEEDED
                        if collection_type in {
                            CrawlRun.CollectionType.LIVE_MARKET,
                            CrawlRun.CollectionType.HISTORICAL_MARKET,
                        }:
                            self._market_collection_successful = True
                    else:
                        run.status = CrawlRun.Status.FAILED
                        run.error_message = str(
                            result.get("reason", f"Unexpected status: {status}")
                        )[:4000]
                        failures.append(f"{source}: {run.error_message}")
                        self.stderr.write(f"{source} failed: {run.error_message}")
                    summary = {
                        key: value
                        for key, value in result.items()
                        if key not in {"results", "errors"}
                    }
                    self.stdout.write(f"{source}: {summary!r}")
            run.finished_at = timezone.now()
            run.save(
                update_fields=[
                    "status",
                    "records_created",
                    "records_updated",
                    "records_processed",
                    "error_message",
                    "finished_at",
                ]
            )
            self._publish_collection_run(run)

        if failures:
            raise CommandError(
                "One or more collection sources failed: " + "; ".join(failures)
            )

    def _run_task_with_retries(self, task):
        for attempt in range(MAX_PROVIDER_RETRIES + 1):
            try:
                return task.run()
            except httpx.HTTPError as exc:
                retryable = not isinstance(exc, httpx.HTTPStatusError) or (
                    exc.response.status_code == 429 or exc.response.status_code >= 500
                )
                if not retryable or attempt == MAX_PROVIDER_RETRIES:
                    raise
                delay = 2**attempt
                logger.warning(
                    "Retrying collection source %s in %s seconds (attempt %s/%s)",
                    task.name,
                    delay,
                    attempt + 1,
                    MAX_PROVIDER_RETRIES,
                )
                time.sleep(delay)

    def _run_market_analysis(self, require_collection_success=False):
        run = CrawlRun.objects.create(
            collection_type=CrawlRun.CollectionType.MARKET_ANALYSIS,
            collection_source="stored_market_data",
            status=CrawlRun.Status.RUNNING,
            started_at=timezone.now(),
        )
        self._publish_collection_run(run)
        try:
            if require_collection_success and not self._market_collection_successful:
                result = {
                    "status": "skipped",
                    "reason": "No market collection source succeeded in this operation.",
                    "records_processed": 0,
                }
            else:
                result = refresh_market_analysis()
        except Exception as exc:
            logger.exception("Market analysis failed")
            run.status = CrawlRun.Status.FAILED
            run.error_message = str(exc)[:4000]
            self.stderr.write(f"market_analysis failed: {exc}")
        else:
            run.status = (
                CrawlRun.Status.SKIPPED
                if result["status"] == "skipped"
                else CrawlRun.Status.SUCCEEDED
            )
            run.error_message = str(result.get("reason", ""))[:4000]
            run.records_processed = result.get("records_processed", 0)
            self.stdout.write(f"market_analysis: {result!r}")
        run.finished_at = timezone.now()
        run.save(
            update_fields=[
                "status",
                "records_processed",
                "error_message",
                "finished_at",
            ]
        )
        self._publish_collection_run(run)
        if run.status == CrawlRun.Status.FAILED:
            raise CommandError(run.error_message)

    def _publish_collection_run(self, run):
        broadcast_on_commit(
            "crawl.run.updated",
            {
                "run_id": run.pk,
                "source": run.collection_source,
                "collection_type": run.collection_type,
                "status": run.status,
            },
        )

    def _count_result(self, result, *keys):
        for key in keys:
            value = result.get(key)
            if isinstance(value, int) and value >= 0:
                return value
        return 0

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
