from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from .models import (
    MarketIndexSnapshot,
    MarketSnapshot,
    MarketStockSnapshot,
    StockPrice,
)

INDEX_SOURCE_PRIORITY = {
    "nepsealpha": 0,
    "sharesansar": 1,
    "merolagani": 2,
}
MARKET_DATA_STALE_AFTER = timedelta(hours=24)


def daily_nepse_history(end_date):
    history_by_date = {}
    source_filter = list(INDEX_SOURCE_PRIORITY)
    for row in MarketIndexSnapshot.objects.filter(
        source__in=source_filter,
        symbol="NEPSE",
        close_value__isnull=False,
        date__lte=end_date,
    ).order_by("date", "updated_at"):
        candidate = {
            "date": row.date,
            "value": row.close_value,
            "change_percent": row.change_percent,
            "updated_at": row.updated_at,
            "source": row.source,
        }
        existing = history_by_date.get(row.date)
        if existing is None or INDEX_SOURCE_PRIORITY[row.source] < INDEX_SOURCE_PRIORITY[
            existing["source"]
        ]:
            history_by_date[row.date] = candidate

    for row in MarketSnapshot.objects.filter(
        source__in=source_filter,
        index_value__isnull=False,
        date__lte=end_date,
    ).order_by("date", "updated_at"):
        candidate = {
            "date": row.date,
            "value": row.index_value,
            "change_percent": row.index_change_percent,
            "updated_at": row.updated_at,
            "source": row.source,
        }
        existing = history_by_date.get(row.date)
        if existing is None or INDEX_SOURCE_PRIORITY[row.source] <= INDEX_SOURCE_PRIORITY[
            existing["source"]
        ]:
            history_by_date[row.date] = candidate

    points = []
    previous_value = None
    for row in sorted(history_by_date.values(), key=lambda item: item["date"]):
        change_percent = row["change_percent"]
        if change_percent is None and previous_value:
            change_percent = (
                (row["value"] - previous_value)
                / previous_value
                * Decimal("100")
            ).quantize(Decimal("0.0001"))
        points.append(
            {
                "date": row["date"],
                "value": row["value"],
                "change_percent": change_percent,
                "updated_at": row["updated_at"],
            }
        )
        previous_value = row["value"]
    return points


def market_history_metrics(points):
    returns = [
        (current["value"] - previous["value"])
        / previous["value"]
        * Decimal("100")
        for previous, current in zip(points, points[1:])
        if previous["value"]
    ]
    volatility = None
    if len(returns) >= 2:
        mean = sum(returns, Decimal("0")) / len(returns)
        variance = sum(
            ((value - mean) ** 2 for value in returns),
            Decimal("0"),
        ) / len(returns)
        volatility = variance.sqrt().quantize(Decimal("0.0001"))
    change = None
    if len(points) >= 2 and points[0]["value"]:
        change = (
            (points[-1]["value"] - points[0]["value"])
            / points[0]["value"]
            * Decimal("100")
        )
    return {
        "trend": (
            "up"
            if change is not None and change > 0
            else "down"
            if change is not None and change < 0
            else "flat"
            if change is not None
            else None
        ),
        "daily_volatility_percent": (
            str(volatility) if volatility is not None else None
        ),
    }


def market_data_freshness(updated_at):
    if updated_at is None:
        return {
            "status": "unavailable",
            "updated_at": None,
            "age_minutes": None,
        }
    age = timezone.now() - updated_at
    return {
        "status": "fresh" if age <= MARKET_DATA_STALE_AFTER else "stale",
        "updated_at": updated_at,
        "age_minutes": max(0, int(age.total_seconds() // 60)),
    }


def latest_market_data_updated_at():
    timestamps = [
        value
        for value in (
            MarketSnapshot.objects.order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first(),
            MarketIndexSnapshot.objects.order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first(),
            MarketStockSnapshot.objects.order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first(),
            StockPrice.objects.order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first(),
        )
        if value is not None
    ]
    return max(timestamps, default=None)


def refresh_market_analysis():
    latest_snapshot = (
        MarketSnapshot.objects.filter(index_value__isnull=False)
        .order_by("-date", "-updated_at")
        .first()
    )
    latest_index = (
        MarketIndexSnapshot.objects.filter(
            symbol="NEPSE",
            close_value__isnull=False,
        )
        .order_by("-date", "-updated_at")
        .first()
    )
    latest_stock = MarketStockSnapshot.objects.order_by(
        "-date", "-updated_at"
    ).first()
    latest_price = StockPrice.objects.order_by("-date", "-updated_at").first()
    latest_date = max(
        (
            date
            for date in (
                latest_snapshot.date if latest_snapshot else None,
                latest_index.date if latest_index else None,
                latest_stock.date if latest_stock else None,
                latest_price.date if latest_price else None,
            )
            if date is not None
        ),
        default=None,
    )
    if latest_date is None:
        return {
            "status": "skipped",
            "reason": "No stored market snapshots or company prices are available.",
            "records_processed": 0,
        }

    history = daily_nepse_history(latest_date)
    indices = MarketIndexSnapshot.objects.filter(date=latest_date)
    market_stocks = MarketStockSnapshot.objects.filter(date=latest_date)
    company_prices = StockPrice.objects.filter(date=latest_date)
    sector_count = indices.filter(is_sector=True).count()
    records_processed = (
        len(history)
        + indices.count()
        + market_stocks.count()
        + company_prices.count()
    )
    if records_processed == 0:
        return {
            "status": "skipped",
            "reason": "No usable market records are available for analysis.",
            "records_processed": 0,
        }

    return {
        "status": "collected",
        "date": latest_date.isoformat(),
        "index_points": len(history),
        "sector_indices": sector_count,
        "market_stock_records": market_stocks.count(),
        "company_price_records": company_prices.count(),
        "records_processed": records_processed,
        **market_history_metrics(history),
    }
