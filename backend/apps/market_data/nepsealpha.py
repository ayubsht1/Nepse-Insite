import logging
import re
from datetime import datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation

import httpx
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from .models import (
    MarketIndexHistory,
    MarketIndexSnapshot,
    MarketSnapshot,
    MarketStockSnapshot,
)

logger = logging.getLogger(__name__)

SOURCE = "nepsealpha"
LIVE_URL = "https://www.nepsealpha.com/live/stocks"
TECHNICAL_URL = "https://www.nepsealpha.com/trading-ta"
REQUEST_TIMEOUT = 20


class MarketDataProviderError(ValueError):
    pass


def collect_market_data():
    headers = {
        "User-Agent": getattr(settings, "CRAWLER_USER_AGENT", "NEPSEInsight/1.0"),
        "Accept": "application/json",
    }
    with httpx.Client(timeout=REQUEST_TIMEOUT, headers=headers) as client:
        live_payload = _get_json(
            client,
            LIVE_URL,
            params={"selectedSector": "NEPSE", "sector": ""},
        )
        parsed = _parse_live_payload(live_payload)
        technical = {}
        existing_technical = MarketSnapshot.objects.filter(
            source=SOURCE, date=parsed["date"]
        ).values_list("technical_indicators", flat=True).first()
        if parsed["market_open"] is True or not existing_technical:
            try:
                technical = _get_json(
                    client,
                    TECHNICAL_URL,
                    params={"frame": "1D", "symbol": "NEPSE"},
                )
            except (httpx.HTTPError, ValueError):
                logger.exception(
                    "Could not retrieve NEPSE Alpha technical indicators; "
                    "saving the live market snapshot without them"
                )

    parsed["technical_indicators"] = technical
    _save_snapshot(parsed)
    logger.info(
        "Saved NEPSE Alpha market snapshot for %s: %s index points, %s stock rows",
        parsed["date"],
        len(parsed["history"]),
        len(parsed["stocks"]),
    )
    return {
        "date": parsed["date"].isoformat(),
        "market_open": parsed["market_open"],
        "index_points": len(parsed["history"]),
        "stocks": len(parsed["stocks"]),
    }


def _get_json(client, url, params=None):
    response = client.get(url, params=params)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        logger.error("NEPSE Alpha returned invalid JSON from %s", response.url)
        raise MarketDataProviderError("NEPSE Alpha returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        logger.error("NEPSE Alpha returned a non-object JSON payload from %s", response.url)
        raise MarketDataProviderError("NEPSE Alpha returned an unexpected response.")
    return payload


def _parse_live_payload(payload):
    live = payload.get("stock_live")
    if not isinstance(live, dict) or not isinstance(live.get("prices"), dict):
        logger.error("NEPSE Alpha live response is missing stock_live.prices")
        raise MarketDataProviderError("NEPSE Alpha live response has no price data.")

    columns = live["prices"]
    symbols = columns.get("symbol")
    if not isinstance(symbols, list):
        logger.error("NEPSE Alpha live response has no symbol column")
        raise MarketDataProviderError("NEPSE Alpha live response has no symbol list.")

    sectors = payload.get("sectors")
    sectors = sectors if isinstance(sectors, dict) else {}
    rows = []
    for index, symbol in enumerate(symbols):
        if not symbol:
            continue
        instrument_type = str(_column(columns, "type", index) or "").lower()
        row = {
            "symbol": str(symbol),
            "instrument_type": instrument_type,
            "open": _decimal(_column(columns, "open", index)),
            "high": _decimal(_column(columns, "high", index)),
            "low": _decimal(_column(columns, "low", index)),
            "close": _decimal(_column(columns, "close", index)),
            "change_percent": _decimal(_column(columns, "percent_change", index)),
            "turnover": _decimal(_column(columns, "turn_over", index)),
            "volume": _decimal(_column(columns, "volume", index)),
        }
        rows.append(row)

    index_rows = []
    for row in rows:
        if row["instrument_type"] != "index":
            continue
        index_rows.append(
            {
                **row,
                "name": str(sectors.get(row["symbol"]) or row["symbol"]),
                "is_sector": row["symbol"] != "NEPSE"
                and row["symbol"] in sectors,
            }
        )

    stock_rows = [
        row for row in rows if row["instrument_type"] != "index"
    ]
    latest = payload.get("latest_price")
    latest = latest if isinstance(latest, dict) else {}
    nepse_row = next(
        (row for row in index_rows if row["symbol"] == "NEPSE"), None
    )
    index_value = _decimal(latest.get("today_price"))
    if index_value is None:
        index_value = _decimal(latest.get("price"))
    if index_value is None and nepse_row:
        index_value = nepse_row["close"]
    index_change = _decimal(latest.get("percent_change"))
    if index_change is None and nepse_row:
        index_change = nepse_row["change_percent"]

    market_summary = payload.get("marketSummary")
    market_summary = (
        market_summary
        if isinstance(market_summary, (dict, list))
        else {}
    )
    sentiment = payload.get("stock_sentiment_summary")
    breadth_changes = _sentiment_changes(sentiment)
    if breadth_changes is None:
        breadth_changes = [
            row["change_percent"]
            for row in stock_rows
            if row["change_percent"] is not None
        ]
    breadth = {
        "advancers": sum(value > 0 for value in breadth_changes),
        "decliners": sum(value < 0 for value in breadth_changes),
        "unchanged": sum(value == 0 for value in breadth_changes),
    }

    now = timezone.now()
    as_of = _source_datetime(latest.get("date")) or now
    source_date = timezone.localtime(as_of).date()
    market_open = _as_bool(payload.get("is_market_open"))
    if market_open is None:
        logger.warning("NEPSE Alpha response did not include is_market_open")

    return {
        "date": source_date,
        "as_of": as_of,
        "market_open": market_open,
        "index_value": index_value,
        "index_change_percent": index_change,
        "previous_close": _decimal(latest.get("previous_close")),
        "turnover": _summary_decimal(
            market_summary,
            "Total Turnover Rs:",
            "Total Turnover",
            fallback=_decimal(latest.get("actual_volume")),
        ),
        "traded_volume": _summary_decimal(
            market_summary, "Total Traded Shares", "Total Traded Volume"
        ),
        "transaction_count": _summary_integer(
            market_summary, "Total Transactions", "Transactions"
        ),
        "scrips_traded": _summary_integer(
            market_summary, "Total Scrips Traded", "Scrips Traded"
        ),
        "float_market_cap": _summary_decimal(
            market_summary, "Total Float Market Capitalization Rs:"
        ),
        "market_cap": _summary_decimal(
            market_summary, "NEPSE Market Cap", "Market Capitalization"
        ),
        **breadth,
        "top_gainers": _leader_records(
            payload.get("looser_gainer"), "gainers", "change_percent"
        ),
        "top_losers": _leader_records(
            payload.get("looser_gainer"), "losers", "change_percent"
        ),
        "top_traded": _leader_records(
            payload.get("looser_gainer"), "turnover", "turnover_crore"
        ),
        "indices": index_rows,
        "stocks": stock_rows,
        "history": _index_history(payload.get("live_stock_price")),
        "technical_indicators": {},
    }


def _column(columns, key, index):
    values = columns.get(key)
    if isinstance(values, list) and index < len(values):
        return values[index]
    return None


def _decimal(value):
    if value is None or value == "":
        return None
    try:
        result = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    return result if result.is_finite() else None


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    return None


def _normalized_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _summary_value(summary, *names):
    if isinstance(summary, list):
        summary = {
            row.get("detail"): row.get("value")
            for row in summary
            if isinstance(row, dict) and row.get("detail") is not None
        }
    if not isinstance(summary, dict):
        return None
    normalized = {_normalized_key(key): value for key, value in summary.items()}
    for name in names:
        value = normalized.get(_normalized_key(name))
        if value is not None:
            return value
    return None


def _summary_decimal(summary, *names, fallback=None):
    value = _decimal(_summary_value(summary, *names))
    return value if value is not None else fallback


def _summary_integer(summary, *names):
    value = _decimal(_summary_value(summary, *names))
    return int(value) if value is not None and value >= 0 else None


def _sentiment_changes(value):
    if isinstance(value, dict):
        changes = value.get("percent_change")
        if isinstance(changes, list):
            parsed = [
                number
                for item in changes
                if (number := _decimal(item)) is not None
            ]
            return parsed or None
        return None
    if isinstance(value, list):
        changes = []
        for item in value:
            if isinstance(item, dict):
                number = _decimal(item.get("percent_change"))
                if number is not None:
                    changes.append(number)
        return changes or None
    return None


def _leader_records(data, category, value_key):
    if isinstance(data, list):
        category_key = {
            "gainers": "gainer",
            "losers": "looser",
            "turnover": "turnover",
        }[category]
        source_rows = [
            row.get(category_key)
            for row in data
            if isinstance(row, dict) and row.get(category_key) is not None
        ]
    elif isinstance(data, dict):
        source_rows = data.get(category)
    else:
        source_rows = None
    if not isinstance(source_rows, list):
        logger.warning("NEPSE Alpha response did not include leader list %s", category)
        return []
    records = []
    for row in source_rows:
        if isinstance(row, dict):
            symbol = row.get("symbol")
            name = row.get("name") or row.get("company_name") or symbol
            value = row.get(value_key)
            if value is None:
                value = row.get("change") or row.get("turnover")
        elif isinstance(row, (list, tuple)) and row:
            symbol = row[0]
            name = row[1] if len(row) > 1 else symbol
            value = row[2] if len(row) > 2 else None
        else:
            continue
        if symbol:
            records.append(
                {
                    "symbol": str(symbol),
                    "name": str(name or symbol),
                    value_key: value,
                }
            )
    return records


def _source_datetime(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        epoch = float(value)
        if epoch > 10_000_000_000:
            epoch /= 1000
        return datetime.fromtimestamp(epoch, tz=datetime_timezone.utc)
    parsed = parse_datetime(str(value))
    if parsed is None:
        parsed_date = parse_date(str(value))
        if parsed_date is None:
            return None
        parsed = datetime.combine(parsed_date, datetime.min.time())
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_default_timezone())
    return parsed


def _index_history(value):
    if not isinstance(value, dict):
        return []
    timestamps = value.get("date")
    closes = value.get("close")
    if not isinstance(timestamps, list) or not isinstance(closes, list):
        return []
    points = []
    for timestamp, close in zip(timestamps, closes):
        observed_at = _source_datetime(timestamp)
        index_value = _decimal(close)
        if observed_at is not None and index_value is not None:
            points.append({"observed_at": observed_at, "value": index_value})
    return points


def _save_snapshot(data):
    source = data.get("source", SOURCE)
    date = data["date"]
    with transaction.atomic():
        if not data["technical_indicators"]:
            previous_technical = MarketSnapshot.objects.filter(
                source=source, date=date
            ).values_list("technical_indicators", flat=True).first()
            if previous_technical:
                data["technical_indicators"] = previous_technical
        MarketSnapshot.objects.update_or_create(
            source=source,
            date=date,
            defaults={
                key: data[key]
                for key in (
                    "as_of",
                    "market_open",
                    "index_value",
                    "index_change_percent",
                    "previous_close",
                    "turnover",
                    "traded_volume",
                    "transaction_count",
                    "scrips_traded",
                    "float_market_cap",
                    "market_cap",
                    "advancers",
                    "decliners",
                    "unchanged",
                    "top_gainers",
                    "top_losers",
                    "top_traded",
                    "technical_indicators",
                )
            },
        )

        index_rows = {
            row["symbol"]: row for row in data["indices"] if row.get("symbol")
        }
        indices = [
            MarketIndexSnapshot(
                source=source,
                date=date,
                symbol=row["symbol"],
                name=row["name"],
                is_sector=row["is_sector"],
                open_value=row["open"],
                high_value=row["high"],
                low_value=row["low"],
                close_value=row["close"],
                change_percent=row["change_percent"],
                volume=row["volume"],
                turnover=row["turnover"],
                updated_at=timezone.now(),
            )
            for row in index_rows.values()
        ]
        if indices:
            MarketIndexSnapshot.objects.bulk_create(
                indices,
                update_conflicts=True,
                unique_fields=["source", "date", "symbol"],
                update_fields=[
                    "name",
                    "is_sector",
                    "open_value",
                    "high_value",
                    "low_value",
                    "close_value",
                    "change_percent",
                    "volume",
                    "turnover",
                    "updated_at",
                ],
            )

        stock_rows = {
            str(row["symbol"]).strip().upper(): row
            for row in data["stocks"]
            if row.get("symbol")
        }
        stocks = [
            MarketStockSnapshot(
                source=source,
                date=date,
                symbol=row["symbol"],
                instrument_type=row["instrument_type"],
                open_price=row["open"],
                high_price=row["high"],
                low_price=row["low"],
                close_price=row["close"],
                change_amount=row.get("change_amount"),
                change_percent=row["change_percent"],
                turnover=row["turnover"],
                volume=row["volume"],
            )
            for row in stock_rows.values()
        ]
        if stocks:
            MarketStockSnapshot.objects.bulk_create(
                stocks,
                update_conflicts=True,
                unique_fields=["source", "date", "symbol"],
                update_fields=[
                    "instrument_type",
                    "open_price",
                    "high_price",
                    "low_price",
                    "close_price",
                    "change_amount",
                    "change_percent",
                    "turnover",
                    "volume",
                ],
            )
        from .services import persist_company_prices

        price_result = persist_company_prices(source, date, list(stock_rows.values()))
        logger.info(
            "Synced %s company prices from %s for %s: %s created, %s updated, "
            "%s unmatched, %s invalid",
            len(stock_rows),
            source,
            date,
            price_result["created"],
            price_result["updated"],
            price_result["unmatched"],
            price_result["invalid"],
        )

        latest_history_at = (
            MarketIndexHistory.objects.filter(source=source, symbol="NEPSE")
            .order_by("-observed_at")
            .values_list("observed_at", flat=True)
            .first()
        )
        history_cutoff = (
            latest_history_at - timedelta(minutes=5)
            if latest_history_at is not None
            else None
        )
        history_by_time = {
            point["observed_at"]: point for point in data["history"]
        }
        history = [
            MarketIndexHistory(
                source=source,
                symbol="NEPSE",
                observed_at=point["observed_at"],
                value=point["value"],
            )
            for point in history_by_time.values()
            if history_cutoff is None or point["observed_at"] >= history_cutoff
        ]
        if history:
            MarketIndexHistory.objects.bulk_create(
                history,
                update_conflicts=True,
                unique_fields=["source", "symbol", "observed_at"],
                update_fields=["value"],
            )
