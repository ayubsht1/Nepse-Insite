import logging

import httpx
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from common.events import broadcast_on_commit
from .models import CrawlRun, CrawlSource
from .services import RobotsDenied, crawl_source as execute_crawl

logger = logging.getLogger(__name__)


def _publish_run(run):
    broadcast_on_commit(
        "crawl.run.updated",
        {
            "run_id": run.pk,
            "source": run.source.key if run.source else None,
            "status": run.status,
        },
    )


def _mark_failed(run, error):
    run.refresh_from_db()
    run.status = CrawlRun.Status.FAILED
    run.error_message = str(error)[:4000]
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "error_message", "finished_at"])
    _publish_run(run)


@shared_task(
    bind=True,
    name="apps.crawlers.tasks.crawl_source",
    max_retries=3,
    default_retry_delay=60,
)
def crawl_source(self, source_id, run_id=None):
    source = CrawlSource.objects.get(pk=source_id)
    if not source.enabled:
        raise ValueError(f"Crawl source {source.key} is disabled.")
    run = (
        CrawlRun.objects.get(pk=run_id)
        if run_id is not None
        else CrawlRun.objects.create(source=source)
    )
    run.status = CrawlRun.Status.RUNNING
    run.started_at = timezone.now()
    run.finished_at = None
    run.task_id = self.request.id or ""
    run.error_message = ""
    run.save(
        update_fields=[
            "status",
            "started_at",
            "finished_at",
            "task_id",
            "error_message",
        ]
    )
    _publish_run(run)
    user_agent = getattr(settings, "CRAWLER_USER_AGENT", "NEPSEInsightBot/1.0")
    client = httpx.Client(
        timeout=httpx.Timeout(20.0),
        follow_redirects=True,
        headers={"User-Agent": user_agent},
    )

    def count_request():
        CrawlRun.objects.filter(pk=run.pk).update(requests_made=F("requests_made") + 1)

    def count_article(was_created):
        field = "articles_created" if was_created else "articles_duplicates"
        CrawlRun.objects.filter(pk=run.pk).update(**{field: F(field) + 1})

    try:
        execute_crawl(
            source,
            client=client,
            on_request=count_request,
            on_article=count_article,
        )
        with transaction.atomic():
            run.refresh_from_db()
            run.status = CrawlRun.Status.SUCCEEDED
            run.finished_at = timezone.now()
            run.save(
                update_fields=[
                    "status",
                    "finished_at",
                ]
            )
            _publish_run(run)
        run.refresh_from_db()
        return {
            "run_id": run.pk,
            "status": run.status,
            "articles_created": run.articles_created,
            "articles_duplicates": run.articles_duplicates,
        }
    except RobotsDenied as exc:
        run.refresh_from_db()
        run.status = CrawlRun.Status.PARTIAL
        run.error_message = str(exc)
        run.finished_at = timezone.now()
        run.save(
            update_fields=["status", "error_message", "finished_at"]
        )
        _publish_run(run)
        logger.warning("Crawl run %s skipped by robots.txt: %s", run.pk, exc)
        return {"run_id": run.pk, "status": run.status, "reason": str(exc)}
    except httpx.HTTPError as exc:
        if (
            isinstance(exc, httpx.HTTPStatusError)
            and 400 <= exc.response.status_code < 500
            and exc.response.status_code != 429
        ):
            _mark_failed(run, exc)
            logger.error("Permanent HTTP error in crawl run %s", run.pk, exc_info=True)
            raise
        logger.exception("Network failure in crawl run %s", run.pk)
        run.refresh_from_db()
        run.error_message = str(exc)[:4000]
        run.save(update_fields=["error_message"])
        if self.request.retries >= self.max_retries:
            _mark_failed(run, exc)
            raise
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.exception("Crawl run %s failed for source %s", run.pk, source.key)
        _mark_failed(run, exc)
        raise
    finally:
        client.close()


@shared_task(name="apps.crawlers.tasks.crawl_enabled_sources")
def crawl_enabled_sources():
    return [
        crawl_source.delay(source_id).id
        for source_id in CrawlSource.objects.filter(enabled=True).values_list(
            "id", flat=True
        )
    ]
