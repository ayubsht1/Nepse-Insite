import logging
import re
import time
from datetime import datetime, timezone as datetime_timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
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


def build_listing_url(listing_url, pagination, page_number):
    if not pagination:
        return listing_url

    placeholder_count = pagination.count("{page}")
    if placeholder_count > 1 or (
        ("{" in pagination or "}" in pagination) and not placeholder_count
    ):
        raise ValueError("Pagination must contain at most one {page} placeholder.")

    if not placeholder_count:
        if (
            any(character in pagination for character in "?#/=&")
            or not pagination.strip()
            or pagination != pagination.strip()
        ):
            raise ValueError(
                "Pagination without a {page} placeholder must be a query "
                "parameter name."
            )
        updates = [(pagination, str(page_number))]
        return _merge_listing_query(listing_url, updates)

    try:
        template_url = pagination.format(page=page_number)
    except (IndexError, KeyError, ValueError) as exc:
        raise ValueError("Pagination URL template must use only {page}.") from exc

    parsed_template = urlparse(template_url)
    if parsed_template.scheme:
        return template_url
    if template_url.startswith("?") or (
        "=" in parsed_template.path and "/" not in parsed_template.path
    ):
        query = parsed_template.query if template_url.startswith("?") else template_url
        updates = parse_qsl(query, keep_blank_values=True)
        if not updates:
            raise ValueError("Pagination query template must include a query parameter.")
        return _merge_listing_query(listing_url, updates)
    return urljoin(listing_url, template_url)


def _merge_listing_query(listing_url, updates):
    parsed_listing = urlparse(listing_url)
    replaced_keys = {key for key, _ in updates}
    existing = [
        (key, value)
        for key, value in parse_qsl(parsed_listing.query, keep_blank_values=True)
        if key not in replaced_keys
    ]
    return urlunparse(
        parsed_listing._replace(query=urlencode([*existing, *updates], doseq=True))
    )


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


def _validate_request_url(url, source, purpose):
    error_message = f"Invalid {purpose} URL for crawl source {source.key}: {url!r}"
    try:
        parsed_url = urlparse(url)
        source_url = urlparse(source.base_url)
        parsed_url.port
        source_url.port
    except ValueError as exc:
        logger.error(
            "Rejecting invalid %s URL for crawl source %s: %r",
            purpose,
            source.key,
            url,
        )
        raise ValueError(error_message) from exc

    valid = (
        parsed_url.scheme in {"http", "https"}
        and parsed_url.hostname is not None
        and source_url.scheme in {"http", "https"}
        and source_url.hostname is not None
        and _same_site_host(parsed_url.hostname, source_url.hostname)
        and not (source_url.scheme == "https" and parsed_url.scheme != "https")
    )
    if not valid:
        logger.error(
            "Rejecting invalid %s URL for crawl source %s: %r",
            purpose,
            source.key,
            url,
        )
        raise ValueError(error_message)


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

    def get(url, purpose, minimum_interval=1):
        nonlocal requests_made, last_request_at
        _validate_request_url(url, source, purpose)
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
        if not source.listing_url or not source.article_url_pattern:
            raise ValueError(
                f"Source {source.key} is missing a listing URL or article URL pattern."
            )
        _validate_request_url(source.base_url, source, "base")
        _validate_request_url(source.listing_url, source, "listing")
        pattern = re.compile(source.article_url_pattern)
        listing_pages = source.max_listing_pages if source.listing_pagination else 1
        try:
            listing_urls = [
                build_listing_url(
                    source.listing_url, source.listing_pagination, page_number
                )
                for page_number in range(1, listing_pages + 1)
            ]
        except ValueError as exc:
            logger.error(
                "Invalid pagination configuration for crawl source %s: %s",
                source.key,
                exc,
            )
            raise ValueError(
                f"Invalid pagination configuration for crawl source "
                f"{source.key}: {exc}"
            ) from exc
        for listing_url in listing_urls:
            _validate_request_url(listing_url, source, "listing")

        robots_url = urljoin(source.base_url, "/robots.txt")
        robots_response = get(robots_url, "robots")
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

        for page_number, listing_url in enumerate(listing_urls, start=1):
            if not robots.can_fetch(user_agent, listing_url):
                raise RobotsDenied(
                    f"robots.txt disallows listing URL {listing_url}"
                )
            listing_response = get(listing_url, "listing", minimum_interval=delay)
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
            response = get(article_url, "article", minimum_interval=delay)
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
