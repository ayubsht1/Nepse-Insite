from decimal import Decimal
from bisect import bisect_left, bisect_right

from django.db.models import Sum
from django.utils import timezone

from apps.market_data.models import FloorsheetTransaction, StockPrice
from apps.news.models import NewsArticle

VOLUME_ANOMALY_MULTIPLIER = Decimal("2.0")
VOLUME_ANOMALY_LOOKBACK = 20


def calculate_vwap(company, start_date, end_date):
    transactions = FloorsheetTransaction.objects.filter(
        company=company, trade_date__range=(start_date, end_date)
    )
    quantity = transactions.aggregate(quantity=Sum("quantity"))["quantity"] or 0
    if not quantity:
        return {
            "available": False,
            "value": None,
            "method": "floorsheet_weighted_average",
            "transactions": 0,
            "limitation": "No transaction-level floorsheet data exists for this period.",
        }

    turnover = sum(
        (row.price * row.quantity for row in transactions.iterator()),
        Decimal("0"),
    )
    return {
        "available": True,
        "value": str((turnover / quantity).quantize(Decimal("0.0001"))),
        "method": "floorsheet_weighted_average",
        "transactions": transactions.count(),
        "limitation": None,
    }


def calculate_pressure(price):
    daily_range = price.high_price - price.low_price
    if daily_range == 0:
        score = Decimal("0")
    else:
        score = (
            (Decimal("2") * price.close_price - price.high_price - price.low_price)
            / daily_range
        )
    score = max(Decimal("-1"), min(Decimal("1"), score))
    return {
        "available": True,
        "score": str(score.quantize(Decimal("0.0001"))),
        "method": "(2 * close - high - low) / (high - low)",
        "volume": price.volume,
        "interpretation": (
            "Estimated close-location pressure indicator; it is not actual buyer or seller volume."
        ),
    }


def detect_volume_anomaly(company, target_date):
    current = StockPrice.objects.filter(company=company, date=target_date).first()
    previous = list(
        StockPrice.objects.filter(company=company, date__lt=target_date)
        .order_by("-date")
        .values_list("volume", flat=True)[:VOLUME_ANOMALY_LOOKBACK]
    )
    if current is None:
        return {
            "available": False,
            "date": target_date.isoformat(),
            "reason": "No daily OHLCV record exists for this date.",
        }
    if len(previous) < VOLUME_ANOMALY_LOOKBACK:
        return {
            "available": False,
            "date": target_date.isoformat(),
            "reason": (
                f"Requires {VOLUME_ANOMALY_LOOKBACK} prior trading days; "
                f"only {len(previous)} are available."
            ),
            "prior_days_available": len(previous),
        }
    average = Decimal(sum(previous)) / VOLUME_ANOMALY_LOOKBACK
    ratio = (
        Decimal(current.volume) / average
        if average
        else None
    )
    return {
        "available": True,
        "date": target_date.isoformat(),
        "volume": current.volume,
        "prior_trading_days": VOLUME_ANOMALY_LOOKBACK,
        "prior_average_volume": str(average.quantize(Decimal("0.01"))),
        "ratio_to_average": (
            str(ratio.quantize(Decimal("0.0001"))) if ratio is not None else None
        ),
        "threshold_multiplier": str(VOLUME_ANOMALY_MULTIPLIER),
        "is_anomaly": bool(
            ratio is not None and ratio > VOLUME_ANOMALY_MULTIPLIER
        ),
    }


def broker_breakdown(company, start_date, end_date):
    transactions = FloorsheetTransaction.objects.filter(
        company=company, trade_date__range=(start_date, end_date)
    )
    if not transactions.exists():
        return {
            "available": False,
            "brokers": [],
            "limitation": "No transaction-level floorsheet data exists for this period.",
        }
    buyers = {}
    sellers = {}
    for row in transactions.values(
        "buyer_broker", "seller_broker", "price", "quantity"
    ).iterator():
        turnover = row["price"] * row["quantity"]
        for broker_code, totals in (
            (row["buyer_broker"], buyers),
            (row["seller_broker"], sellers),
        ):
            if not broker_code:
                continue
            aggregate = totals.setdefault(
                broker_code, {"quantity": 0, "turnover": Decimal("0")}
            )
            aggregate["quantity"] += row["quantity"]
            aggregate["turnover"] += turnover
    broker_codes = sorted(set(buyers) | set(sellers))
    return {
        "available": True,
        "brokers": [
            {
                "broker_code": code,
                "buy_quantity": buyers.get(code, {}).get("quantity", 0),
                "sell_quantity": sellers.get(code, {}).get("quantity", 0),
                "buy_turnover": str(buyers.get(code, {}).get("turnover") or 0),
                "sell_turnover": str(sellers.get(code, {}).get("turnover") or 0),
            }
            for code in broker_codes
        ],
        "limitation": "Broker-side labels are taken from the submitted floorsheet records.",
    }


def news_market_relationship(company, limit=100):
    articles = list(
        NewsArticle.objects.filter(
            company_tags__company=company,
            published_at__isnull=False,
        )
        .distinct()
        .order_by("-published_at")[:limit]
    )
    if not articles:
        return {
            "observations": [],
            "method": (
                "Each article is compared with the next recorded trading session after its "
                "publication date and the last recorded session before that date. Recorded "
                "sessions naturally skip weekends and holidays."
            ),
            "limitation": (
                "This is observational only; it does not establish that news caused price or volume changes."
            ),
        }

    earliest_article_date = min(
        timezone.localtime(article.published_at).date() for article in articles
    )
    previous_price = (
        StockPrice.objects.filter(
            company=company, date__lt=earliest_article_date
        )
        .only("date", "close_price", "volume")
        .order_by("-date")
        .first()
    )
    prices = list(
        StockPrice.objects.filter(company=company, date__gte=earliest_article_date)
        .only("date", "close_price", "volume")
        .order_by("date")
    )
    if previous_price:
        prices.insert(0, previous_price)
    trading_dates = [price.date for price in prices]
    observations = []
    for article in articles:
        published_date = timezone.localtime(article.published_at).date()
        prior_index = bisect_left(trading_dates, published_date) - 1
        following_index = bisect_right(trading_dates, published_date)
        prior = prices[prior_index] if prior_index >= 0 else None
        following = (
            prices[following_index] if following_index < len(prices) else None
        )
        observations.append(
            {
                "article_id": article.id,
                "headline": article.headline,
                "published_at": article.published_at.isoformat(),
                "baseline_trading_date": prior.date.isoformat() if prior else None,
                "next_observed_trading_date": (
                    following.date.isoformat() if following else None
                ),
                "close_change_percent": _percent_change(
                    prior.close_price if prior else None,
                    following.close_price if following else None,
                ),
                "volume_change_percent": _percent_change(
                    Decimal(prior.volume) if prior else None,
                    Decimal(following.volume) if following else None,
                ),
                "available": prior is not None and following is not None,
            }
        )
    return {
        "observations": observations,
        "method": (
            "Each article is compared with the next recorded trading session after its "
            "publication date and the last recorded session before that date. Recorded "
            "sessions naturally skip weekends and holidays."
        ),
        "limitation": (
            "This is observational only; it does not establish that news caused price or volume changes."
        ),
    }


def _percent_change(previous, current):
    if previous is None or current is None or previous == 0:
        return None
    return str(
        (((current - previous) / previous) * Decimal("100")).quantize(
            Decimal("0.01")
        )
    )


def company_behavior_summary(company, start_date, end_date):
    latest = (
        StockPrice.objects.filter(company=company, date__range=(start_date, end_date))
        .order_by("-date")
        .first()
    )
    transactions = FloorsheetTransaction.objects.filter(
        company=company, trade_date__range=(start_date, end_date)
    )
    total_quantity = transactions.aggregate(total=Sum("quantity"))["total"] or 0
    total_turnover = sum(
        (row.price * row.quantity for row in transactions.iterator()),
        Decimal("0"),
    )
    first = (
        StockPrice.objects.filter(company=company, date__range=(start_date, end_date))
        .order_by("date")
        .values_list("close_price", flat=True)
        .first()
    )
    last = (
        StockPrice.objects.filter(company=company, date__range=(start_date, end_date))
        .order_by("-date")
        .values_list("close_price", flat=True)
        .first()
    )
    return {
        "company": {
            "id": company.id,
            "symbol": company.symbol,
            "name": company.name,
        },
        "period": {"from": start_date.isoformat(), "to": end_date.isoformat()},
        "price_change_percent": _percent_change(first, last),
        "latest_price": (
            {
                "date": latest.date.isoformat(),
                "close": str(latest.close_price),
                "volume": latest.volume,
            }
            if latest
            else None
        ),
        "vwap": calculate_vwap(company, start_date, end_date),
        "latest_pressure_indicator": (
            calculate_pressure(latest) if latest else {"available": False}
        ),
        "latest_volume_anomaly": (
            detect_volume_anomaly(company, latest.date)
            if latest
            else {"available": False, "reason": "No daily OHLCV data is available."}
        ),
        "floorsheet": {
            "available": bool(total_quantity),
            "transactions": transactions.count(),
            "quantity": total_quantity,
            "turnover": str(total_turnover),
            "brokers": broker_breakdown(company, start_date, end_date),
        },
        "news_relationship": news_market_relationship(company),
    }
