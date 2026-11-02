import logging

import httpx
from celery import shared_task
from django.utils import timezone

from .models import MarketSnapshot
from .market_sources import (
    collect_merolagani_market_data as collect_merolagani,
    collect_sharesansar_market_data as collect_sharesansar,
)
from .nepsealpha import MarketDataProviderError, SOURCE, collect_market_data

logger = logging.getLogger(__name__)


@shared_task
def collect_nepsealpha_market_data():
    local_now = timezone.localtime()
    trading_weekdays = {6, 0, 1, 2, 3}
    within_market_hours = (
        11 <= local_now.hour < 15
        or (local_now.hour == 15 and local_now.minute == 0)
    )
    if local_now.weekday() not in trading_weekdays or not within_market_hours:
        logger.info("Skipping NEPSE Alpha collection outside market hours")
        return {"status": "skipped", "reason": "outside_market_hours"}

    if MarketSnapshot.objects.filter(
        source=SOURCE,
        updated_at__date=local_now.date(),
        market_open=False,
    ).exists():
        logger.info("Skipping NEPSE Alpha collection after market was reported closed")
        return {"status": "skipped", "reason": "market_closed"}

    try:
        return {"status": "collected", **collect_market_data()}
    except (httpx.HTTPError, MarketDataProviderError):
        logger.exception("NEPSE Alpha market-data collection failed")
        raise


def _collect_html_provider(source, collector):
    local_now = timezone.localtime()
    trading_weekdays = {6, 0, 1, 2, 3}
    within_market_hours = (
        11 <= local_now.hour < 15
        or (local_now.hour == 15 and local_now.minute == 0)
    )
    if local_now.weekday() not in trading_weekdays or not within_market_hours:
        logger.info("Skipping %s collection outside market hours", source)
        return {"status": "skipped", "reason": "outside_market_hours"}

    if MarketSnapshot.objects.filter(
        source=SOURCE,
        date=local_now.date(),
        market_open=False,
    ).exists():
        logger.info(
            "Skipping %s collection after NEPSE Alpha reported market closed",
            source,
        )
        return {"status": "skipped", "reason": "market_closed"}

    try:
        return {"status": "collected", **collector()}
    except (httpx.HTTPError, MarketDataProviderError):
        logger.exception("%s market-data collection failed", source)
        raise


@shared_task
def collect_sharesansar_market_data():
    return _collect_html_provider("ShareSansar", collect_sharesansar)


@shared_task
def collect_merolagani_market_data():
    return _collect_html_provider("Merolagani", collect_merolagani)
