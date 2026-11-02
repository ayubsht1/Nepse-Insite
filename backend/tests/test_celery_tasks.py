from unittest.mock import patch

from django.test import TestCase

from apps.crawlers.models import CrawlRun, CrawlSource
from apps.crawlers.tasks import crawl_enabled_sources, crawl_source


class CrawlerTaskTests(TestCase):
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
        self.assertEqual(result["status"], CrawlRun.Status.SUCCEEDED)
