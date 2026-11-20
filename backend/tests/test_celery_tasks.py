import re
from unittest.mock import patch

import httpx
from django.conf import settings
from django.test import TestCase

from config.celery import app as celery_app
from apps.crawlers.models import CrawlRun, CrawlSource
from apps.crawlers.services import NoArticlesDiscovered
from apps.crawlers.tasks import (
    crawl_enabled_sources,
    crawl_source,
    run_crawl_source_direct,
)


class CrawlerTaskTests(TestCase):
    def test_beat_schedule_references_registered_tasks(self):
        celery_app.loader.import_default_modules()
        scheduled_tasks = {
            entry["task"]
            for entry in settings.CELERY_BEAT_SCHEDULE.values()
        }
        registered_tasks = set(celery_app.tasks)

        self.assertIn("apps.crawlers.tasks.crawl_enabled_sources", scheduled_tasks)
        self.assertIn(crawl_source.name, registered_tasks)
        self.assertFalse(scheduled_tasks - registered_tasks)

    def test_observed_news_source_patterns_are_configured_but_disabled(self):
        examples = {
            "merolagani": (
                "https://merolagani.com/NewsDetail.aspx?newsID=12345"
            ),
            "sharesansar": (
                "https://www.sharesansar.com/index.php/newsdetail/company-news-example"
            ),
            "bizmandu": "https://bizmandu.com/content/12345.html",
            "nepsealpha": "https://nepsealpha.com/news-article/company-news",
        }
        expected_listings = {
            "merolagani": "https://merolagani.com/NewsList.aspx",
            "sharesansar": "https://www.sharesansar.com/news-page",
            "bizmandu": "https://bizmandu.com/content/category/news.html",
            "nepsealpha": (
                "https://www.nepsealpha.com/all-news?cid=1&page=1"
            ),
        }
        for key, example_url in examples.items():
            source = CrawlSource.objects.get(key=key)
            self.assertFalse(source.enabled)
            self.assertEqual(source.listing_url, expected_listings[key])
            self.assertRegex(example_url, re.compile(source.article_url_pattern))

        nepse_alpha = CrawlSource.objects.get(key="nepsealpha")
        self.assertEqual(
            nepse_alpha.listing_pagination,
            "https://www.nepsealpha.com/all-news?cid=1&page={page}",
        )
        self.assertEqual(nepse_alpha.max_listing_pages, 10)

    def test_disabled_seed_sources_are_not_scheduled(self):
        source = CrawlSource.objects.create(
            name="Disabled",
            key="disabled",
            base_url="https://disabled.example.test",
            enabled=False,
        )
        result = crawl_enabled_sources.apply(throw=True)
        self.assertEqual(result.get(), [])
        self.assertEqual(CrawlRun.objects.filter(source=source).count(), 0)

    @patch("apps.crawlers.tasks.execute_crawl")
    def test_task_records_success_counts_and_requests(self, execute_crawl):
        source = CrawlSource.objects.create(
            name="Enabled",
            key="enabled",
            base_url="https://enabled.example.test",
            listing_url="https://enabled.example.test/news",
            article_url_pattern=r"/article/",
            enabled=True,
        )
        run = CrawlRun.objects.create(source=source)
        execute_crawl.side_effect = lambda _source, on_request, on_article, **kwargs: (
            on_request(),
            on_article(True),
            on_article(False),
            {"requests_made": 1},
        )[-1]

        result = crawl_source.apply(
            args=(source.pk, run.pk),
            throw=True,
        ).get()
        run.refresh_from_db()

        self.assertEqual(run.status, CrawlRun.Status.SUCCEEDED)
        self.assertEqual(run.requests_made, 1)
        self.assertEqual(run.articles_created, 1)
        self.assertEqual(run.articles_duplicates, 1)
        self.assertEqual(run.records_created, 1)
        self.assertEqual(run.records_updated, 0)
        self.assertEqual(run.records_processed, 2)
        self.assertEqual(result["status"], CrawlRun.Status.SUCCEEDED)

    @patch("apps.crawlers.tasks.execute_crawl")
    def test_direct_crawl_retries_without_publishing_to_the_broker(self, execute_crawl):
        source = CrawlSource.objects.create(
            name="Direct retry",
            key="direct-retry",
            base_url="https://direct-retry.example.test",
            listing_url="https://direct-retry.example.test/news",
            article_url_pattern=r"/article/",
            enabled=True,
        )
        run = CrawlRun.objects.create(source=source)
        execute_crawl.side_effect = [
            httpx.TimeoutException("temporary timeout"),
            {"requests_made": 1},
        ]
        with patch("apps.crawlers.tasks.time.sleep") as sleep:
            with (
                patch.object(
                    crawl_source,
                    "apply_async",
                    side_effect=AssertionError("direct crawl must not be queued"),
                ),
                patch.object(
                    crawl_source,
                    "delay",
                    side_effect=AssertionError("direct crawl must not be queued"),
                ),
            ):
                result = run_crawl_source_direct(
                    source.pk,
                    run.pk,
                    sleep=sleep,
                )

        run.refresh_from_db()
        self.assertEqual(run.status, CrawlRun.Status.SUCCEEDED)
        self.assertEqual(result["status"], CrawlRun.Status.SUCCEEDED)
        sleep.assert_called_once_with(crawl_source.default_retry_delay)

    @patch("apps.crawlers.tasks.execute_crawl", side_effect=NoArticlesDiscovered(
        "No article URLs matched the configured pattern."
    ))
    def test_task_records_failed_run_when_no_articles_are_extracted(self, _execute):
        source = CrawlSource.objects.create(
            name="Empty listing",
            key="empty-listing",
            base_url="https://empty.example.test",
            listing_url="https://empty.example.test/news",
            article_url_pattern=r"/article/",
            enabled=True,
        )
        run = CrawlRun.objects.create(source=source)

        with self.assertRaises(NoArticlesDiscovered):
            crawl_source.apply(args=(source.pk, run.pk), throw=True).get()

        run.refresh_from_db()
        self.assertEqual(run.status, CrawlRun.Status.FAILED)
        self.assertEqual(run.records_created, 0)
        self.assertEqual(run.records_processed, 0)
        self.assertIn("No article URLs matched", run.error_message)
        self.assertIsNotNone(run.finished_at)

    @patch("apps.crawlers.tasks.execute_crawl")
    def test_task_does_not_retry_permanent_http_client_errors(self, execute_crawl):
        source = CrawlSource.objects.create(
            name="Forbidden listing",
            key="forbidden-listing",
            base_url="https://forbidden.example.test",
            listing_url="https://forbidden.example.test/news",
            article_url_pattern=r"/article/",
            enabled=True,
        )
        run = CrawlRun.objects.create(source=source)
        request = httpx.Request("GET", "https://forbidden.example.test/news")
        response = httpx.Response(403, request=request)
        execute_crawl.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=request, response=response
        )

        with self.assertRaises(httpx.HTTPStatusError):
            crawl_source.apply(args=(source.pk, run.pk), throw=True).get()

        run.refresh_from_db()
        self.assertEqual(run.status, CrawlRun.Status.FAILED)
        self.assertIn("403 Forbidden", run.error_message)
