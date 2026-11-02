import httpx
from django.test import TestCase

from apps.crawlers.models import CrawlSource
from apps.crawlers.serializers import CrawlSourceSerializer
from apps.crawlers.services import (
    NoArticlesDiscovered,
    RobotsDenied,
    build_listing_url,
    crawl_source,
)
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

    def test_paginated_source_crawls_multiple_pages_and_accepts_www_alias(self):
        self.source.base_url = "https://news.example.test"
        self.source.listing_url = (
            "https://news.example.test/all-news?cid=1&page=1"
        )
        self.source.listing_pagination = (
            "https://news.example.test/all-news?cid=1&page={page}"
        )
        self.source.max_listing_pages = 5
        self.source.article_url_pattern = (
            r"https://(www\.)?news\.example\.test/article/\d+"
        )
        self.source.save()

        def handler(request):
            path = request.url.path
            page_number = request.url.params.get("page")
            if path == "/robots.txt":
                return httpx.Response(
                    200,
                    text="User-agent: *\nAllow: /\n",
                    request=request,
                )
            if path == "/all-news" and page_number == "1":
                body = '<a href="https://www.news.example.test/article/1">one</a>'
            elif path == "/all-news" and page_number == "2":
                body = (
                    '<a href="https://www.news.example.test/article/1">one</a>'
                    '<a href="/article/2">two</a>'
                )
            elif path == "/all-news" and page_number == "3":
                body = (
                    '<a href="/article/2">two</a>'
                    '<a href="/article/1">one</a>'
                )
            elif path == "/all-news" and page_number == "4":
                body = "<html><body>No more news</body></html>"
            elif path in {"/article/1", "/article/2"}:
                body = (
                    f'<meta property="og:title" content="Story {path[-1]}">'
                )
            else:
                return httpx.Response(404, request=request)
            return httpx.Response(200, text=body, request=request)

        client = httpx.Client(
            transport=httpx.MockTransport(handler),
            headers={"User-Agent": "NEPSEInsightTest/1.0"},
        )
        result = crawl_source(self.source, client=client, sleep=lambda _: None)
        client.close()

        self.assertEqual(result["article_urls_found"], 2)
        self.assertEqual(result["articles_extracted"], 2)
        self.assertEqual(result["requests_made"], 7)
        self.assertEqual(NewsArticle.objects.count(), 2)

    def test_listing_url_builder_supports_parameter_names_and_templates(self):
        listing_url = "https://news.example.test/all-news?cid=1&page=1"
        cases = (
            ("page", "https://news.example.test/all-news?cid=1&page=2"),
            ("page={page}", "https://news.example.test/all-news?cid=1&page=2"),
            ("?page={page}", "https://news.example.test/all-news?cid=1&page=2"),
            (
                "https://news.example.test/all-news?cid=1&page={page}",
                "https://news.example.test/all-news?cid=1&page=2",
            ),
        )

        for pagination, expected in cases:
            with self.subTest(pagination=pagination):
                self.assertEqual(
                    build_listing_url(listing_url, pagination, 2), expected
                )

    def test_crawl_paginates_when_pagination_is_a_query_parameter_name(self):
        self.source.listing_url = (
            "https://news.example.test/news?category=markets&page=1"
        )
        self.source.listing_pagination = "page"
        self.source.max_listing_pages = 3
        self.source.save()
        listing_pages = []

        def handler(request):
            if request.url.path == "/robots.txt":
                return httpx.Response(
                    200,
                    text="User-agent: *\nAllow: /\n",
                    request=request,
                )
            if request.url.path == "/news":
                listing_pages.append(request.url.params.get("page"))
                body = (
                    '<a href="/article/1">story</a>'
                    if request.url.params.get("page") == "1"
                    else "<html><body>No more news</body></html>"
                )
                return httpx.Response(200, text=body, request=request)
            if request.url.path == "/article/1":
                return httpx.Response(
                    200,
                    text='<meta property="og:title" content="Market story">',
                    request=request,
                )
            return httpx.Response(404, request=request)

        client = httpx.Client(
            transport=httpx.MockTransport(handler),
            headers={"User-Agent": "NEPSEInsightTest/1.0"},
        )
        result = crawl_source(self.source, client=client, sleep=lambda _: None)
        client.close()

        self.assertEqual(listing_pages, ["1", "2"])
        self.assertEqual(result["article_urls_found"], 1)
        self.assertEqual(NewsArticle.objects.get().url, "https://news.example.test/article/1")

    def test_crawl_resolves_relative_article_links_against_listing_url(self):
        self.source.listing_url = "https://news.example.test/news/archive/"
        self.source.article_url_pattern = r"/news/archive/article/1$"
        self.source.save()

        def handler(request):
            if request.url.path == "/robots.txt":
                return httpx.Response(
                    200,
                    text="User-agent: *\nAllow: /\n",
                    request=request,
                )
            if request.url.path == "/news/archive/":
                return httpx.Response(
                    200,
                    text='<a href="article/1">relative story</a>',
                    request=request,
                )
            if request.url.path == "/news/archive/article/1":
                return httpx.Response(
                    200,
                    text='<meta property="og:title" content="Relative story">',
                    request=request,
                )
            return httpx.Response(404, request=request)

        client = httpx.Client(
            transport=httpx.MockTransport(handler),
            headers={"User-Agent": "NEPSEInsightTest/1.0"},
        )
        crawl_source(self.source, client=client, sleep=lambda _: None)
        client.close()

        self.assertEqual(
            NewsArticle.objects.get().url,
            "https://news.example.test/news/archive/article/1",
        )

    def test_invalid_paginated_url_is_rejected_before_any_request(self):
        self.source.listing_pagination = (
            "https://external.test/news?page={page}"
        )
        self.source.save()
        requests = []
        client = httpx.Client(
            transport=httpx.MockTransport(
                lambda request: requests.append(request.url)
                or httpx.Response(200, request=request)
            ),
            headers={"User-Agent": "NEPSEInsightTest/1.0"},
        )

        with self.assertRaisesRegex(ValueError, "Invalid listing URL"):
            crawl_source(self.source, client=client, sleep=lambda _: None)

        client.close()
        self.assertEqual(requests, [])

    def test_source_serializer_accepts_pagination_parameter_name(self):
        serializer = CrawlSourceSerializer(
            instance=self.source,
            data={"listing_pagination": "page"},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

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
