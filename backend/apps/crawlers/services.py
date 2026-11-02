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


def _canonical_article_url(base_url, href):
    resolved = urljoin(base_url, href)
    parsed = urlparse(resolved)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    source_host = urlparse(base_url).hostname
    if parsed.hostname.lower() != source_host.lower():
        return None
    return urlunparse(parsed._replace(fragment=""))


def _validate_response_host(response, source):
    final_url = urlparse(str(response.url))
    expected_url = urlparse(source.base_url)
    final_host = final_url.hostname
    expected_host = expected_url.hostname
    if not final_host or final_host.lower() != expected_host.lower():
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
    owns_client = client is None
    if client is None:
        client = httpx.Client(
            timeout=httpx.Timeout(20.0),
            follow_redirects=True,
            headers={"User-Agent": "NEPSEInsightBot/1.0"},
        )
    user_agent = client.headers.get("User-Agent", "NEPSEInsightBot/1.0")

    def get(url):
        nonlocal requests_made
        requests_made += 1
        if on_request:
            on_request()
        return client.get(url)

    try:
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
        if not robots.can_fetch(user_agent, source.listing_url):
            raise RobotsDenied(
                f"robots.txt disallows listing URL {source.listing_url}"
            )
        listing_response = get(source.listing_url)
        _validate_response_host(listing_response, source)
        listing_response.raise_for_status()

        soup = BeautifulSoup(listing_response.text, "html.parser")
        base_host = urlparse(source.base_url).hostname.lower()
        pattern = re.compile(source.article_url_pattern)
        article_urls = []

        def append_candidate(href):
            candidate = _canonical_article_url(source.listing_url, href)
            if (
                candidate
                and urlparse(candidate).hostname.lower() == base_host
                and pattern.search(candidate)
                and candidate not in article_urls
            ):
                article_urls.append(candidate)

        for link in soup.select("a[href]"):
            append_candidate(link.get("href", ""))
            if len(article_urls) >= source.max_articles_per_run:
                break
        if len(article_urls) < source.max_articles_per_run:
            for entry in soup.find_all(["item", "entry"]):
                link = entry.find("link")
                if link:
                    append_candidate(link.get("href") or link.get_text(strip=True))
                if len(article_urls) >= source.max_articles_per_run:
                    break

        delay = max(1, source.request_interval_seconds)
        robots_delay = robots.crawl_delay(user_agent)
        if robots_delay is not None:
            delay = max(delay, int(robots_delay))
        fetched = 0
        for article_url in article_urls:
            if not robots.can_fetch(user_agent, article_url):
                logger.info("Skipping robots-disallowed article URL: %s", article_url)
                continue
            if fetched:
                sleep(delay)
            response = get(article_url)
            _validate_response_host(response, source)
            response.raise_for_status()
            fetched += 1
            data = _article_data(response.text, article_url)
            if not data["headline"]:
                logger.info(
                    "Skipping article with no extractable headline: %s", article_url
                )
                continue
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
        return {
            "requests_made": requests_made,
        }
    finally:
        if owns_client:
            client.close()
