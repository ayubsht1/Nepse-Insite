from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.crawlers.github_actions import (
    WorkflowDispatchError,
    dispatch_crawl_workflow,
)
from apps.crawlers.management.commands.run_collection import MARKET_DATA_TASKS
from apps.crawlers.models import CrawlRun, CrawlSource


class RunCollectionCommandTests(TestCase):
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
