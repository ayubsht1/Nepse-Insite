import logging
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils import timezone

from .nepsealpha import MarketDataProviderError, _save_snapshot

logger = logging.getLogger(__name__)

SHARESANSAR = "sharesansar"
MEROLAGANI = "merolagani"
SHARESANSAR_BASE = "https://www.sharesansar.com"
MEROLAGANI_BASE = "https://merolagani.com"
REQUEST_TIMEOUT = 20


def collect_sharesansar_market_data():
    headers = {
        "User-Agent": getattr(settings, "CRAWLER_USER_AGENT", "NEPSEInsight/1.0"),
        "Accept": "text/html",
    }
    with httpx.Client(
        timeout=REQUEST_TIMEOUT,
        headers=headers,
        follow_redirects=True,
    ) as client:
        market_html = _get_html(client, f"{SHARESANSAR_BASE}/market", SHARESANSAR_BASE)
        stocks_html = _get_html(
            client,
            f"{SHARESANSAR_BASE}/today-share-price",
            SHARESANSAR_BASE,
        )
    parsed = _parse_sharesansar(market_html, stocks_html)
    _save_snapshot(parsed)
    logger.info(
        "Saved ShareSansar market snapshot for %s: %s indices, %s stocks",
        parsed["date"],
        len(parsed["indices"]),
        len(parsed["stocks"]),
    )
    return {
        "source": SHARESANSAR,
        "date": parsed["date"].isoformat(),
        "indices": len(parsed["indices"]),
        "stocks": len(parsed["stocks"]),
    }


def collect_merolagani_market_data():
    headers = {
        "User-Agent": getattr(settings, "CRAWLER_USER_AGENT", "NEPSEInsight/1.0"),
        "Accept": "text/html",
    }
    with httpx.Client(
        timeout=REQUEST_TIMEOUT,
        headers=headers,
        follow_redirects=True,
    ) as client:
        html = _get_html(
            client,
            f"{MEROLAGANI_BASE}/LatestMarket.aspx",
            MEROLAGANI_BASE,
        )
    parsed = _parse_merolagani(html)
    _save_snapshot(parsed)
    logger.info(
        "Saved Merolagani market snapshot for %s: %s stocks",
        parsed["date"],
        len(parsed["stocks"]),
    )
    return {
        "source": MEROLAGANI,
        "date": parsed["date"].isoformat(),
        "stocks": len(parsed["stocks"]),
    }


def _get_html(client, url, base_url):
    robots_url = f"{base_url}/robots.txt"
    robots_response = client.get(robots_url)
    if robots_response.status_code not in {200, 404, 410}:
        robots_response.raise_for_status()
    robots = RobotFileParser(robots_url)
    if robots_response.status_code == 200:
        robots.parse(robots_response.text.splitlines())
    if not robots.can_fetch(client.headers.get("User-Agent", "*"), url):
        raise MarketDataProviderError(f"robots.txt disallows market URL: {url}")

    response = client.get(url)
    response.raise_for_status()
    expected_host = urlparse(base_url).hostname
    final_url = urlparse(str(response.url))
    if (
        final_url.scheme != "https"
        or not final_url.hostname
        or final_url.hostname.lower().removeprefix("www.")
        != (expected_host or "").lower().removeprefix("www.")
    ):
        raise MarketDataProviderError(
            f"Market page redirected outside its configured source: {response.url}"
        )
    return response.text


def _table_rows(soup):
    for table in soup.select("table"):
        rows = table.select("tr")
        if not rows:
            continue
        headers = [_normalize(cell.get_text(" ", strip=True)) for cell in rows[0].select("th, td")]
        if not headers or not any(headers):
            continue
        for row in rows[1:]:
            cells = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
            if not cells or not any(cells):
                continue
            yield headers, dict(zip(headers, cells))


def _normalize(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _number(value):
    if value is None:
        return None
    cleaned = str(value).strip().replace(",", "").replace("%", "")
    if cleaned in {"", "-", "—", "N/A"}:
        return None
    try:
        number = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _table_with_headers(html, required):
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.select("table"):
        first_row = table.select_one("tr")
        if first_row is None:
            continue
        headers = [_normalize(cell.get_text(" ", strip=True)) for cell in first_row.select("th, td")]
        if set(required).issubset(headers):
            return soup, table, headers
    return soup, None, []


def _symbol(name):
    base = re.sub(r"\s+(sub\s*index|index)$", "", name, flags=re.IGNORECASE)
    return re.sub(r"[^A-Za-z0-9]", "", base).upper()[:32]


def _sharesansar_stock_rows(html):
    soup, table, headers = _table_with_headers(
        html, {"symbol", "open", "high", "low", "ltp", "vol", "turnover"}
    )
    if table is None:
        raise MarketDataProviderError(
            "ShareSansar today-share-price page did not contain the expected quote table."
        )

    stocks = []
    for row in table.select("tr")[1:]:
        values = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
        record = dict(zip(headers, values))
        symbol = record.get("symbol", "").strip()
        if not symbol:
            continue
        stocks.append(
            {
                "symbol": symbol,
                "instrument_type": "",
                "open": _number(record.get("open")),
                "high": _number(record.get("high")),
                "low": _number(record.get("low")),
                "close": _number(record.get("ltp")),
                "change_percent": _number(record.get("diff")),
                "turnover": _number(record.get("turnover")),
                "volume": _number(record.get("vol")),
            }
        )
    if not stocks:
        raise MarketDataProviderError("ShareSansar returned no stock quote rows.")
    return soup, stocks


def _sharesansar_summary(soup):
    summary = {}
    for table in soup.select("table"):
        for row in table.select("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
            if len(cells) < 2:
                continue
            label, value = cells[0], cells[1]
            key = _normalize(label)
            if key in {"totalturnoversrs", "totalturnovers"}:
                summary["turnover"] = _number(value)
            elif key == "totaltradedshares":
                summary["traded_volume"] = _number(value)
            elif key in {"totaltransaction", "totaltransactions"}:
                summary["transaction_count"] = _number(value)
            elif key in {"totalscripstraded", "scripstraded"}:
                summary["scrips_traded"] = _number(value)
    return summary


def _sharesansar_indices(soup):
    indices = []
    for headers, row in _table_rows(soup):
        name = next(
            (row.get(key, "") for key in ("index", "subindex") if row.get(key)),
            "",
        )
        if not name or not {"open", "high", "low", "close"}.issubset(headers):
            continue
        is_sector = "subindex" in headers
        indices.append(
            {
                "symbol": _symbol(name),
                "name": name,
                "is_sector": is_sector,
                "open": _number(row.get("open")),
                "high": _number(row.get("high")),
                "low": _number(row.get("low")),
                "close": _number(row.get("close")),
                "change_percent": _number(row.get("change")),
                "turnover": _number(row.get("turnover")),
                "volume": None,
            }
        )
    if not any(row["symbol"] == "NEPSE" for row in indices):
        raise MarketDataProviderError("ShareSansar market page did not include NEPSE index.")
    return indices


def _leader_lists(stocks):
    gainers = sorted(
        (row for row in stocks if row["change_percent"] is not None and row["change_percent"] > 0),
        key=lambda row: row["change_percent"],
        reverse=True,
    )[:10]
    losers = sorted(
        (row for row in stocks if row["change_percent"] is not None and row["change_percent"] < 0),
        key=lambda row: row["change_percent"],
    )[:10]
    traded = sorted(
        (row for row in stocks if row["turnover"] is not None),
        key=lambda row: row["turnover"],
        reverse=True,
    )[:10]

    def records(rows, key):
        return [
            {
                "symbol": row["symbol"],
                "name": row["symbol"],
                key: (
                    float(row[key] / Decimal("10000000"))
                    if key == "turnover_crore"
                    else float(row["change_percent"])
                ),
            }
            for row in rows
        ]

    return (
        records(gainers, "change_percent"),
        records(losers, "change_percent"),
        records(
            [
                {**row, "turnover_crore": row["turnover"]}
                for row in traded
            ],
            "turnover_crore",
        ),
    )


def _parse_sharesansar(market_html, stocks_html):
    market_soup = BeautifulSoup(market_html, "html.parser")
    _, stocks = _sharesansar_stock_rows(stocks_html)
    indices = _sharesansar_indices(market_soup)
    market_index = next(row for row in indices if row["symbol"] == "NEPSE")
    summary = _sharesansar_summary(market_soup)
    gainers, losers, top_traded = _leader_lists(stocks)
    changes = [row["change_percent"] for row in stocks if row["change_percent"] is not None]
    now = timezone.now()
    return {
        "source": SHARESANSAR,
        "date": timezone.localdate(now),
        "as_of": now,
        "market_open": None,
        "index_value": market_index["close"],
        "index_change_percent": market_index["change_percent"],
        "previous_close": None,
        "turnover": summary.get("turnover"),
        "traded_volume": summary.get("traded_volume"),
        "transaction_count": summary.get("transaction_count"),
        "scrips_traded": summary.get("scrips_traded"),
        "float_market_cap": None,
        "market_cap": None,
        "advancers": sum(value > 0 for value in changes),
        "decliners": sum(value < 0 for value in changes),
        "unchanged": sum(value == 0 for value in changes),
        "top_gainers": gainers,
        "top_losers": losers,
        "top_traded": top_traded,
        "technical_indicators": {},
        "indices": indices,
        "stocks": stocks,
        "history": [],
    }


def _parse_merolagani(html):
    soup, table, headers = _table_with_headers(
        html,
        {"symbol", "ltp", "change", "open", "high", "low", "qty"},
    )
    if table is None:
        raise MarketDataProviderError(
            "Merolagani LatestMarket page did not contain the expected quote table."
        )

    stocks_by_symbol = {}
    for row in table.select("tr")[1:]:
        values = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
        record = dict(zip(headers, values))
        symbol = record.get("symbol", "").strip()
        if not symbol:
            continue
        stocks_by_symbol[symbol] = {
            "symbol": symbol,
            "instrument_type": "",
            "open": _number(record.get("open")),
            "high": _number(record.get("high")),
            "low": _number(record.get("low")),
            "close": _number(record.get("ltp")),
            "change_percent": _number(record.get("change")),
            "turnover": _number(record.get("turnover")),
            "volume": _number(record.get("qty")),
        }
    if not stocks_by_symbol:
        raise MarketDataProviderError("Merolagani returned no stock quote rows.")

    for headers, row in _table_rows(soup):
        if "symbol" in headers and "turnover" in headers:
            symbol = row.get("symbol", "").strip()
            if symbol in stocks_by_symbol:
                stocks_by_symbol[symbol]["turnover"] = _number(row.get("turnover"))

    stocks = list(stocks_by_symbol.values())
    gainers, losers, top_traded = _leader_lists(stocks)
    now = timezone.now()
    return {
        "source": MEROLAGANI,
        "date": timezone.localdate(now),
        "as_of": now,
        "market_open": None,
        "index_value": None,
        "index_change_percent": None,
        "previous_close": None,
        "turnover": None,
        "traded_volume": None,
        "transaction_count": None,
        "scrips_traded": None,
        "float_market_cap": None,
        "market_cap": None,
        "advancers": None,
        "decliners": None,
        "unchanged": None,
        "top_gainers": gainers,
        "top_losers": losers,
        "top_traded": top_traded,
        "technical_indicators": {},
        "indices": [],
        "stocks": stocks,
        "history": [],
    }
