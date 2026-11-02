import logging
import re
import time
from datetime import datetime, timezone as datetime_timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from django.utils.dateparse import parse_date, parse_datetime

from apps.news.models import NewsArticle
from apps.news.services.categorization import categorize_article
from common.events import broadcast_on_commit

logger = logging.getLogger(__name__)


class RobotsDenied(Exception):
    pass


class NoArticlesDiscovered(Exception):
    pass


def _same_site_host(first_host, second_host):
    return first_host.lower().removeprefix("www.") == second_host.lower().removeprefix(
        "www."
    )


def _canonical_article_url(base_url, href, canonical_host=None):
    resolved = urljoin(base_url, href)
    parsed = urlparse(resolved)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    source_host = urlparse(base_url).hostname
    if not _same_site_host(parsed.hostname, source_host):
        return None
    if canonical_host:
        parsed = parsed._replace(netloc=canonical_host)
    return urlunparse(parsed._replace(fragment=""))


def _validate_response_host(response, source):
    final_url = urlparse(str(response.url))
    expected_url = urlparse(source.base_url)
    final_host = final_url.hostname
    expected_host = expected_url.hostname
    if not final_host or not _same_site_host(final_host, expected_host):
        raise ValueError("Source redirected to a different host; response rejected.")
    if expected_url.scheme == "https" and final_url.scheme != "https":
        raise ValueError("Source redirected to an insecure HTTP URL; response rejected.")


def _date_from_value(value):
    if not value:
        return None
    value = value.strip()
    parsed = parse_datetime(value)
    if parsed is None:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            parsed = None
    if parsed is None:
        day = parse_date(value[:10])
        if day:
            parsed = datetime.combine(day, datetime.min.time())
    if parsed and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime_timezone.utc)
    return parsed


def _article_data(html, url):
    soup = BeautifulSoup(html, "html.parser")
    headline = ""
    for selector, attribute in (
        ('meta[property="og:title"]', "content"),
        ('meta[name="twitter:title"]', "content"),
        ("article h1", None),
        ("h1", None),
        ("title", None),
    ):
        element = soup.select_one(selector)
        if element:
            headline = (
                element.get(attribute, "").strip()
                if attribute
                else element.get_text(" ", strip=True)
            )
            if headline:
                break

    body = ""
    article = soup.select_one("article")
    if article:
        body = article.get_text(" ", strip=True)
    if not body:
        for selector in (
            'meta[property="og:description"]',
            'meta[name="description"]',
        ):
            element = soup.select_one(selector)
            if element and element.get("content"):
                body = element["content"].strip()
                break

    published_at = None
    for selector, attribute in (
        ('meta[property="article:published_time"]', "content"),
        ('meta[name="date"]', "content"),
        ("time[datetime]", "datetime"),
    ):
        element = soup.select_one(selector)
        if element and element.get(attribute):
            published_at = _date_from_value(element[attribute])
            if published_at:
                break
    return {
        "url": url,
        "headline": headline[:512],
        "body": body,
        "published_at": published_at,
    }


def crawl_source(
    source, client=None, sleep=time.sleep, on_request=None, on_article=None
):
    requests_made = 0
    last_request_at = None
    owns_client = client is None
    if client is None:
        client = httpx.Client(
            timeout=httpx.Timeout(20.0),
            follow_redirects=True,
            headers={"User-Agent": "NEPSEInsightBot/1.0"},
        )
    user_agent = client.headers.get("User-Agent", "NEPSEInsightBot/1.0")

    def get(url, minimum_interval=1):
        nonlocal requests_made, last_request_at
        if last_request_at is not None:
            elapsed = time.monotonic() - last_request_at
            if elapsed < minimum_interval:
                sleep(minimum_interval - elapsed)
        requests_made += 1
        if on_request:
            on_request()
        response = client.get(url)
        last_request_at = time.monotonic()
        return response

    try:
        if (
            not source.listing_url
            or not source.article_url_pattern
            or (
                source.listing_pagination
                and "{page}" not in source.listing_pagination
            )
        ):
            raise ValueError(
                f"Source {source.key} is missing a listing URL, pagination "
                "placeholder, or article URL pattern."
            )
        robots_url = urljoin(source.base_url, "/robots.txt")
        robots_response = get(robots_url)
        _validate_response_host(robots_response, source)
        if robots_response.status_code not in {200, 404}:
            robots_response.raise_for_status()
        robots = RobotFileParser(robots_url)
        robots.parse(
            robots_response.text.splitlines()
            if robots_response.status_code == 200
            else []
        )
        delay = max(1, source.request_interval_seconds)
        robots_delay = robots.crawl_delay(user_agent)
        if robots_delay is not None:
            delay = max(delay, int(robots_delay))
        base_host = urlparse(source.base_url).hostname
        pattern = re.compile(source.article_url_pattern)
        article_urls = []

        def append_candidate(href, listing_url):
            candidate = _canonical_article_url(
                listing_url,
                href,
                canonical_host=base_host,
            )
            if (
                not candidate
                or not _same_site_host(urlparse(candidate).hostname, base_host)
                or not pattern.search(candidate)
            ):
                return False
            if candidate not in article_urls:
                article_urls.append(candidate)
            return True

        listing_pages = (
            source.max_listing_pages if source.listing_pagination else 1
        )
        for page_number in range(1, listing_pages + 1):
            listing_url = (
                source.listing_pagination.format(page=page_number)
                if source.listing_pagination
                else source.listing_url
            )
            if not robots.can_fetch(user_agent, listing_url):
                raise RobotsDenied(
                    f"robots.txt disallows listing URL {listing_url}"
                )
            listing_response = get(listing_url, minimum_interval=delay)
            _validate_response_host(listing_response, source)
            listing_response.raise_for_status()

            soup = BeautifulSoup(listing_response.text, "html.parser")
            page_has_matching_candidates = False
            for link in soup.select("a[href]"):
                page_has_matching_candidates = (
                    append_candidate(link.get("href", ""), listing_url)
                    or page_has_matching_candidates
                )
                if len(article_urls) >= source.max_articles_per_run:
                    break
            if len(article_urls) < source.max_articles_per_run:
                for entry in soup.find_all(["item", "entry"]):
                    link = entry.find("link")
                    if link:
                        page_has_matching_candidates = (
                            append_candidate(
                                link.get("href") or link.get_text(strip=True),
                                listing_url,
                            )
                            or page_has_matching_candidates
                        )
                    if len(article_urls) >= source.max_articles_per_run:
                        break
            if not article_urls:
                if not source.listing_pagination:
                    break
                continue
            if len(article_urls) >= source.max_articles_per_run:
                break
            if (
                source.listing_pagination
                and page_number > 1
                and not page_has_matching_candidates
            ):
                break

        if not article_urls:
            raise NoArticlesDiscovered(
                f"No article URLs matched the configured pattern for {source.key}."
            )

        articles_extracted = 0
        article_urls_disallowed = 0
        for article_url in article_urls:
            if not robots.can_fetch(user_agent, article_url):
                logger.info("Skipping robots-disallowed article URL: %s", article_url)
                article_urls_disallowed += 1
                continue
            response = get(article_url, minimum_interval=delay)
            _validate_response_host(response, source)
            response.raise_for_status()
            data = _article_data(response.text, article_url)
            if not data["headline"]:
                logger.info(
                    "Skipping article with no extractable headline: %s", article_url
                )
                continue
            articles_extracted += 1
            article, was_created = NewsArticle.objects.get_or_create(
                url=data["url"],
                defaults={
                    "source": source.name,
                    "headline": data["headline"],
                    "body": data["body"],
                    "published_at": data["published_at"],
                },
            )
            if on_article:
                on_article(was_created)
            if was_created:
                categorize_article(article)
                broadcast_on_commit(
                    "news.article.created",
                    {"article_id": article.pk, "headline": article.headline},
                )
        if articles_extracted == 0 and article_urls_disallowed == len(article_urls):
            raise RobotsDenied(
                f"robots.txt disallows every matching article URL for {source.key}."
            )
        if articles_extracted == 0:
            raise NoArticlesDiscovered(
                f"Found {len(article_urls)} candidate article URL(s) for "
                f"{source.key}, but none had an extractable headline."
            )
        return {
            "requests_made": requests_made,
            "article_urls_found": len(article_urls),
            "articles_extracted": articles_extracted,
        }
    finally:
        if owns_client:
            client.close()
