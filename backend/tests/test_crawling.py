import httpx
from django.test import TestCase

from apps.crawlers.models import CrawlSource
from apps.crawlers.services import NoArticlesDiscovered, RobotsDenied, crawl_source
from apps.news.models import NewsArticle, NewsCompanyTag
from .factories import create_company


class CrawlerServiceTests(TestCase):
    def setUp(self):
        self.company = create_company()
        self.source = CrawlSource.objects.create(
            name="Fixture News",
            key="fixture",
            base_url="https://news.example.test",
            listing_url="https://news.example.test/news",
            article_url_pattern=r"/article/",
            enabled=True,
            request_interval_seconds=1,
        )

    def client_for(self, robots_text="User-agent: *\nAllow: /\n"):
        def handler(request):
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots_text, request=request)
            if request.url.path == "/news":
                return httpx.Response(
                    200,
                    text=(
                        '<a href="/article/1#section">NABIL story</a>'
                        '<a href="https://external.test/article/2">external</a>'
                    ),
                    request=request,
                )
            if request.url.path == "/article/1":
                return httpx.Response(
                    200,
                    text=(
                        '<meta property="og:title" content="NABIL Bank news">'
                        '<meta property="article:published_time" '
                        'content="2026-10-30T12:00:00+05:45">'
                        "<article>News body for Nabil Bank Limited.</article>"
                    ),
                    request=request,
                )
            return httpx.Response(404, request=request)

        return httpx.Client(
            transport=httpx.MockTransport(handler),
            headers={"User-Agent": "NEPSEInsightTest/1.0"},
        )

    def test_crawl_respects_host_filters_and_deduplicates_article_urls(self):
        client = self.client_for()
        first_seen = []
        first = crawl_source(
            self.source,
            client=client,
            sleep=lambda _: None,
            on_article=first_seen.append,
        )
        second_seen = []
        second = crawl_source(
            self.source,
            client=client,
            sleep=lambda _: None,
            on_article=second_seen.append,
        )
        client.close()

        article = NewsArticle.objects.get()
        self.assertEqual(article.url, "https://news.example.test/article/1")
        self.assertEqual(article.source, self.source.name)
        self.assertEqual(first["requests_made"], 3)
        self.assertEqual(second["requests_made"], 3)
        self.assertEqual(first_seen, [True])
        self.assertEqual(second_seen, [False])
        self.assertEqual(NewsCompanyTag.objects.filter(article=article).count(), 1)

    def test_crawl_fails_closed_when_robots_disallows_listing(self):
        client = self.client_for("User-agent: *\nDisallow: /\n")
        with self.assertRaises(RobotsDenied):
            crawl_source(self.source, client=client, sleep=lambda _: None)
        client.close()
        self.assertFalse(NewsArticle.objects.exists())

    def test_crawl_reports_robots_disallowed_article_pages_as_partial(self):
        client = self.client_for(
            "User-agent: *\nAllow: /news\nDisallow: /article/\n"
        )
        with self.assertRaisesRegex(
            RobotsDenied, "disallows every matching article URL"
        ):
            crawl_source(self.source, client=client, sleep=lambda _: None)
        client.close()
        self.assertFalse(NewsArticle.objects.exists())

    def test_crawl_waits_between_robots_listing_and_article_requests(self):
        self.source.request_interval_seconds = 500
        self.source.save(update_fields=["request_interval_seconds"])
        client = self.client_for()
        delays = []

        crawl_source(
            self.source,
            client=client,
            sleep=delays.append,
        )

        client.close()
        self.assertEqual(len(delays), 2)
        self.assertTrue(all(delay >= 499 for delay in delays))

    def test_crawl_reports_empty_listing_instead_of_success(self):
        client = httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    text="User-agent: *\nAllow: /\n"
                    if request.url.path == "/robots.txt"
                    else "<html><body>No stories listed</body></html>",
                    request=request,
                )
            ),
            headers={"User-Agent": "NEPSEInsightTest/1.0"},
        )
        with self.assertRaisesRegex(NoArticlesDiscovered, "No article URLs matched"):
            crawl_source(self.source, client=client, sleep=lambda _: None)
        client.close()
        self.assertFalse(NewsArticle.objects.exists())

    def test_crawl_reports_candidate_pages_without_headlines(self):
        client = httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    text=(
                        "User-agent: *\nAllow: /\n"
                        if request.url.path == "/robots.txt"
                        else '<a href="/article/1">story</a>'
                        if request.url.path == "/news"
                        else "<html><body>Changed article layout</body></html>"
                    ),
                    request=request,
                )
            ),
            headers={"User-Agent": "NEPSEInsightTest/1.0"},
        )
        with self.assertRaisesRegex(
            NoArticlesDiscovered, "none had an extractable headline"
        ):
            crawl_source(self.source, client=client, sleep=lambda _: None)
        client.close()
        self.assertFalse(NewsArticle.objects.exists())
