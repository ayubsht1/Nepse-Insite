from contextlib import ExitStack
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.crawlers.github_actions import (
    WorkflowDispatchError,
    dispatch_crawl_workflow,
)
from apps.crawlers.management.commands.run_collection import (
    HISTORICAL_MARKET_TASKS,
    MARKET_DATA_TASKS,
)
from apps.crawlers.models import CrawlRun, CrawlSource
from apps.market_data.models import MarketSnapshot


class RunCollectionCommandTests(TestCase):
    def _mock_collection_tasks(self, events, status="collected"):
        stack = ExitStack()
        for task in (*MARKET_DATA_TASKS, *HISTORICAL_MARKET_TASKS):
            stack.enter_context(
                patch.object(
                    task,
                    "run",
                    side_effect=lambda task=task: (
                        events.append(task.name),
                        {
                            "status": status,
                            "records_created": 2,
                            "records_updated": 1,
                            "records_processed": 3,
                        },
                    )[1],
                )
            )
        return stack

    def test_live_market_tracks_per_source_results_and_runs_analysis(self):
        events = []
        with self._mock_collection_tasks(events), patch(
            "apps.crawlers.management.commands.run_collection.refresh_market_analysis",
            return_value={
                "status": "collected",
                "records_processed": 4,
            },
        ) as analysis:
            call_command("run_collection", "live_market")

        self.assertEqual(events, [task.name for task in MARKET_DATA_TASKS])
        analysis.assert_called_once_with()
        self.assertEqual(
            CrawlRun.objects.filter(
                collection_type=CrawlRun.CollectionType.LIVE_MARKET,
                status=CrawlRun.Status.SUCCEEDED,
            ).count(),
            len(MARKET_DATA_TASKS),
        )
        first_run = CrawlRun.objects.filter(
            collection_type=CrawlRun.CollectionType.LIVE_MARKET
        ).first()
        self.assertEqual(first_run.records_created, 2)
        self.assertEqual(first_run.records_updated, 1)
        self.assertEqual(first_run.records_processed, 3)

    def test_market_source_selection_runs_only_requested_provider(self):
        events = []
        with self._mock_collection_tasks(events), patch(
            "apps.crawlers.management.commands.run_collection.refresh_market_analysis",
            return_value={"status": "collected", "records_processed": 1},
        ):
            call_command(
                "run_collection",
                "live_market",
                market_source_keys="sharesansar",
            )

        self.assertEqual(events, [MARKET_DATA_TASKS[1].name])
        self.assertEqual(
            CrawlRun.objects.filter(
                collection_type=CrawlRun.CollectionType.LIVE_MARKET
            ).count(),
            1,
        )

    def test_live_market_continues_after_a_provider_failure(self):
        events = []
        with (
            self._mock_collection_tasks(events),
            patch.object(
                MARKET_DATA_TASKS[0],
                "run",
                side_effect=RuntimeError("provider unavailable"),
            ),
            patch(
                "apps.crawlers.management.commands.run_collection.refresh_market_analysis",
                return_value={"status": "collected", "records_processed": 1},
            ) as analysis,
        ):
            with self.assertRaisesRegex(CommandError, "nepsealpha"):
                call_command("run_collection", "live_market")

        self.assertEqual(events, [task.name for task in MARKET_DATA_TASKS[1:]])
        analysis.assert_called_once_with()
        runs = list(
            CrawlRun.objects.filter(
                collection_type=CrawlRun.CollectionType.LIVE_MARKET
            ).order_by("pk")
        )
        self.assertEqual(runs[0].status, CrawlRun.Status.FAILED)
        self.assertTrue(
            all(run.status == CrawlRun.Status.SUCCEEDED for run in runs[1:])
        )

    def test_failed_provider_result_is_recorded_as_failure(self):
        events = []
        with (
            self._mock_collection_tasks(events),
            patch.object(
                MARKET_DATA_TASKS[0],
                "run",
                return_value={
                    "status": "failed",
                    "reason": "provider rejected the request",
                },
            ),
            patch(
                "apps.crawlers.management.commands.run_collection.refresh_market_analysis",
                return_value={"status": "collected", "records_processed": 1},
            ),
        ):
            with self.assertRaisesRegex(CommandError, "provider rejected"):
                call_command("run_collection", "live_market")

        failed_run = CrawlRun.objects.get(
            collection_type=CrawlRun.CollectionType.LIVE_MARKET,
            collection_source="nepsealpha",
        )
        self.assertEqual(failed_run.status, CrawlRun.Status.FAILED)
        self.assertIn("provider rejected", failed_run.error_message)

    def test_market_analysis_is_gated_when_all_live_sources_are_skipped(self):
        with (
            self._mock_collection_tasks([], status="skipped"),
            patch(
                "apps.crawlers.management.commands.run_collection.refresh_market_analysis"
            ) as analysis,
        ):
            call_command("run_collection", "live_market")

        analysis.assert_not_called()
        analysis_run = CrawlRun.objects.get(
            collection_type=CrawlRun.CollectionType.MARKET_ANALYSIS
        )
        self.assertEqual(analysis_run.status, CrawlRun.Status.SKIPPED)
        self.assertIn("No market collection source succeeded", analysis_run.error_message)

    def test_historical_market_runs_directory_before_history_then_analysis(self):
        events = []
        with self._mock_collection_tasks(events), patch(
            "apps.crawlers.management.commands.run_collection.refresh_market_analysis",
            side_effect=lambda: (
                events.append("market_analysis"),
                {"status": "collected", "records_processed": 1},
            )[1],
        ):
            call_command("run_collection", "historical_market")

        self.assertEqual(
            events,
            [task.name for task in HISTORICAL_MARKET_TASKS] + ["market_analysis"],
        )

    def test_market_analysis_is_skipped_when_no_market_data_exists(self):
        call_command("run_collection", "market_analysis")

        run = CrawlRun.objects.get(
            collection_type=CrawlRun.CollectionType.MARKET_ANALYSIS
        )
        self.assertEqual(run.status, CrawlRun.Status.SKIPPED)
        self.assertIn("No stored market", run.error_message)
        self.assertEqual(run.records_processed, 0)

    def test_market_analysis_processes_stored_market_records(self):
        now = timezone.now()
        MarketSnapshot.objects.create(
            source="nepsealpha",
            date=now.date(),
            as_of=now,
            index_value="2700",
        )

        call_command("run_collection", "market_analysis")

        run = CrawlRun.objects.get(
            collection_type=CrawlRun.CollectionType.MARKET_ANALYSIS
        )
        self.assertEqual(run.status, CrawlRun.Status.SUCCEEDED)
        self.assertEqual(run.records_processed, 1)

    def test_all_runs_in_dependency_order_with_empty_run_history(self):
        events = []
        source = CrawlSource.objects.create(
            name="All operation source",
            key="all-operation-source",
            base_url="https://all.example.test",
            listing_url="https://all.example.test/news",
            article_url_pattern=r"/article/",
            enabled=True,
        )
        with (
            self._mock_collection_tasks(events),
            patch(
                "apps.crawlers.management.commands.run_collection.run_crawl_source_direct",
                side_effect=lambda _source_id, _run_id: events.append("news"),
            ),
            patch(
                "apps.crawlers.management.commands.run_collection.refresh_market_analysis",
                side_effect=lambda: (
                    events.append("market_analysis"),
                    {"status": "collected", "records_processed": 2},
                )[1],
            ),
        ):
            call_command("run_collection", "all")

        self.assertEqual(
            events,
            ["news"]
            + [task.name for task in MARKET_DATA_TASKS]
            + [task.name for task in HISTORICAL_MARKET_TASKS]
            + ["market_analysis"],
        )
        self.assertEqual(CrawlRun.objects.filter(source=source).count(), 1)
        self.assertEqual(CrawlRun.objects.count(), 1 + 4 + 3 + 1)
        self.assertEqual(
            set(
                CrawlRun.objects.filter(
                    collection_type=CrawlRun.CollectionType.MARKET_ANALYSIS
                ).values_list("status", flat=True)
            ),
            {CrawlRun.Status.SUCCEEDED},
        )

    def test_all_reuses_queued_news_run_with_existing_history(self):
        events = []
        source = CrawlSource.objects.create(
            name="Existing news source",
            key="existing-news-source",
            base_url="https://existing.example.test",
            listing_url="https://existing.example.test/news",
            article_url_pattern=r"/article/",
            enabled=True,
        )
        queued_run = CrawlRun.objects.create(source=source)
        CrawlRun.objects.create(
            source=source,
            status=CrawlRun.Status.SUCCEEDED,
        )
        with (
            self._mock_collection_tasks(events),
            patch(
                "apps.crawlers.management.commands.run_collection.run_crawl_source_direct",
                side_effect=lambda _source_id, run_id: events.append(
                    f"news:{run_id}"
                ),
            ),
            patch(
                "apps.crawlers.management.commands.run_collection.refresh_market_analysis",
                return_value={"status": "collected", "records_processed": 1},
            ),
        ):
            call_command("run_collection", "all")

        self.assertEqual(events[0], f"news:{queued_run.pk}")
        self.assertEqual(CrawlRun.objects.filter(source=source).count(), 2)
        self.assertEqual(CrawlRun.objects.filter(source=source, status="queued").count(), 1)

    def test_market_data_runs_tasks_without_publishing_to_celery(self):
        with (
            patch.object(MARKET_DATA_TASKS[0], "run", return_value={"status": "ok"}) as first,
            patch.object(MARKET_DATA_TASKS[1], "run", return_value={"status": "ok"}) as second,
            patch.object(MARKET_DATA_TASKS[2], "run", return_value={"status": "ok"}) as third,
            patch.object(MARKET_DATA_TASKS[3], "run", return_value={"status": "ok"}) as fourth,
            patch.object(
                MARKET_DATA_TASKS[0],
                "apply_async",
                side_effect=AssertionError("collection must not be queued"),
            ),
            patch.object(
                MARKET_DATA_TASKS[0],
                "delay",
                side_effect=AssertionError("collection must not be queued"),
            ),
        ):
            call_command("run_collection", "market-data")

        for task_run in (first, second, third, fourth):
            task_run.assert_called_once_with()
        self.assertEqual(
            CrawlRun.objects.get(
                collection_type=CrawlRun.CollectionType.MARKET_ANALYSIS
            ).status,
            CrawlRun.Status.SKIPPED,
        )

    @patch("apps.crawlers.management.commands.run_collection.run_crawl_source_direct")
    def test_news_source_selection_validates_and_runs_enabled_source(self, run_direct):
        source = CrawlSource.objects.create(
            name="Direct source",
            key="direct-source",
            base_url="https://direct.example.test",
            listing_url="https://direct.example.test/news",
            article_url_pattern=r"/article/",
            enabled=True,
        )

        call_command(
            "run_collection",
            "news",
            "--source-keys",
            "direct-source",
        )

        run = CrawlRun.objects.get(source=source)
        run_direct.assert_called_once_with(source.pk, run.pk)

    @patch("apps.crawlers.management.commands.run_collection.run_crawl_source_direct")
    def test_scheduled_news_creates_runs_when_no_runs_exist(self, run_direct):
        source = CrawlSource.objects.create(
            name="Scheduled source",
            key="scheduled-source",
            base_url="https://scheduled.example.test",
            listing_url="https://scheduled.example.test/news",
            article_url_pattern=r"/article/",
            enabled=True,
        )

        call_command("run_collection", "news")

        run = CrawlRun.objects.get(source=source)
        self.assertEqual(run.status, CrawlRun.Status.QUEUED)
        run_direct.assert_called_once_with(source.pk, run.pk)

    @patch("apps.crawlers.management.commands.run_collection.run_crawl_source_direct")
    def test_scheduled_news_reuses_queued_runs_and_creates_runs_for_other_sources(
        self, run_direct
    ):
        queued_source = CrawlSource.objects.create(
            name="Queued source",
            key="queued-source",
            base_url="https://queued.example.test",
            listing_url="https://queued.example.test/news",
            article_url_pattern=r"/article/",
            enabled=True,
        )
        completed_source = CrawlSource.objects.create(
            name="Completed source",
            key="completed-source",
            base_url="https://completed.example.test",
            listing_url="https://completed.example.test/news",
            article_url_pattern=r"/article/",
            enabled=True,
        )
        queued_run = CrawlRun.objects.create(source=queued_source)
        CrawlRun.objects.create(
            source=completed_source,
            status=CrawlRun.Status.SUCCEEDED,
        )

        call_command("run_collection", "news")

        runs = list(CrawlRun.objects.order_by("pk"))
        self.assertEqual(len(runs), 3)
        created_run = CrawlRun.objects.get(source=completed_source, status="queued")
        self.assertEqual(
            {call.args for call in run_direct.call_args_list},
            {
                (queued_source.pk, queued_run.pk),
                (completed_source.pk, created_run.pk),
            },
        )

    def test_explicit_run_ids_report_missing_ids_clearly(self):
        with self.assertRaisesRegex(CommandError, r"CrawlRun ID\(s\) do not exist: 9, 10"):
            call_command("run_collection", "news", run_ids="9,10")

    def test_news_rejects_disabled_or_unknown_sources_without_creating_runs(self):
        disabled = CrawlSource.objects.create(
            name="Disabled direct source",
            key="disabled-direct-source",
            base_url="https://disabled.example.test",
            enabled=False,
        )

        with self.assertRaises(CommandError):
            call_command(
                "run_collection",
                "news",
                "--source-keys",
                disabled.key,
            )
        with self.assertRaises(CommandError):
            call_command(
                "run_collection",
                "news",
                "--source-keys",
                "unknown-source",
            )

        self.assertEqual(CrawlRun.objects.count(), 0)

    @override_settings(
        GITHUB_ACTIONS_TOKEN="test-token",
        GITHUB_REPOSITORY="owner/repository",
        GITHUB_WORKFLOW_FILE="data-jobs.yml",
        GITHUB_ACTIONS_REF="main",
    )
    @patch("apps.crawlers.github_actions.httpx.post")
    def test_workflow_dispatch_sends_only_run_ids(self, post):
        post.return_value.status_code = 204

        dispatch_crawl_workflow([12, 13])

        post.assert_called_once()
        request = post.call_args
        self.assertEqual(
            request.args[0],
            "https://api.github.com/repos/owner/repository/actions/"
            "workflows/data-jobs.yml/dispatches",
        )
        self.assertEqual(
            request.kwargs["json"]["inputs"],
            {
                "operation": "news",
                "crawl_run_ids": "12,13",
                "source_keys": "",
                "run_legacy_queue_worker": "false",
            },
        )

    @override_settings(GITHUB_ACTIONS_TOKEN="")
    def test_workflow_dispatch_fails_explicitly_when_not_configured(self):
        with self.assertRaises(WorkflowDispatchError):
            dispatch_crawl_workflow([1])
