import logging
import re
import time
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import MarketIndexSnapshot, StockPrice
from .nepsealpha import MarketDataProviderError, _save_snapshot

logger = logging.getLogger(__name__)

SHARESANSAR = "sharesansar"
MEROLAGANI = "merolagani"
SHARESANSAR_BASE = "https://www.sharesansar.com"
MEROLAGANI_BASE = "https://merolagani.com"
SHARESANSAR_INDEX_HISTORY_URL = f"{SHARESANSAR_BASE}/index-history-data"
SHARESANSAR_COMPANY_PRICE_HISTORY_URL = f"{SHARESANSAR_BASE}/company-price-history"
SHARESANSAR_COMPANY_FLOORSHEET_URL = f"{SHARESANSAR_BASE}/company-floor-sheet"
MEROLAGANI_FLOORSHEET_URL = f"{MEROLAGANI_BASE}/Floorsheet.aspx"
REQUEST_TIMEOUT = 20
HISTORY_PAGE_SIZE = 50
FLOORSHEET_PAGE_SIZE = 500

INDEX_HISTORY_COLUMNS = (
    ("DT_Row_Index", False, False),
    ("open", True, True),
    ("high", True, True),
    ("low", True, True),
    ("current", True, True),
    ("change_", True, True),
    ("per_change", True, True),
    ("turnover", True, True),
    ("published_date", True, True),
)
COMPANY_PRICE_HISTORY_COLUMNS = (
    ("DT_Row_Index", False, False),
    ("published_date", True, False),
    ("open", False, False),
    ("high", False, False),
    ("low", False, False),
    ("close", False, False),
    ("per_change", False, False),
    ("traded_quantity", False, False),
    ("traded_amount", False, False),
)
COMPANY_FLOORSHEET_COLUMNS = (
    ("DT_Row_Index", False, False),
    ("contract_no", True, False),
    ("buyer", True, False),
    ("seller", True, False),
    ("quantity", True, False),
    ("rate", True, False),
    ("amount", False, False),
    ("date_", True, False),
)


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


def collect_merolagani_floorsheet_data():
    headers = {
        "User-Agent": getattr(settings, "CRAWLER_USER_AGENT", "NEPSEInsight/1.0"),
        "Accept": "text/html",
    }
    with httpx.Client(
        timeout=REQUEST_TIMEOUT,
        headers=headers,
        follow_redirects=True,
    ) as client:
        html = _get_html(client, MEROLAGANI_FLOORSHEET_URL, MEROLAGANI_BASE)
    rows = _parse_merolagani_floorsheet(html)
    from .services import persist_floorsheet_transactions

    saved = persist_floorsheet_transactions(MEROLAGANI, rows)
    logger.info(
        "Saved Merolagani floorsheet rows: %s created, %s duplicates, %s unmatched",
        saved["created"],
        saved["duplicates"],
        saved["unmatched"],
    )
    return {"source": MEROLAGANI, **saved, "submitted": len(rows)}


def collect_sharesansar_index_history():
    headers = {
        "User-Agent": getattr(settings, "CRAWLER_USER_AGENT", "NEPSEInsight/1.0"),
        "Accept": "text/html",
    }
    with httpx.Client(
        timeout=REQUEST_TIMEOUT,
        headers=headers,
        follow_redirects=True,
    ) as client:
        robots = _robots_parser(client, SHARESANSAR_BASE)
        index_history_html = _get_html(
            client,
            SHARESANSAR_INDEX_HISTORY_URL,
            SHARESANSAR_BASE,
            robot_parser=robots,
        )
        index_id = _sharesansar_nepse_index_id(index_history_html)
        _check_robots(
            client,
            SHARESANSAR_INDEX_HISTORY_URL,
            SHARESANSAR_BASE,
            robot_parser=robots,
        )
        oldest_supported_date = timezone.localdate() - timedelta(days=3650)
        latest_stored_date = (
            MarketIndexSnapshot.objects.filter(
                source=SHARESANSAR,
                symbol="NEPSE",
            )
            .order_by("-date")
            .values_list("date", flat=True)
            .first()
        )
        from_date = (
            max(oldest_supported_date, latest_stored_date - timedelta(days=30))
            if latest_stored_date
            else oldest_supported_date
        )
        to_date = timezone.localdate()
        start = 0
        draw = 1
        rows = []
        total = None
        while total is None or start < total:
            params = _datatable_params(
                INDEX_HISTORY_COLUMNS,
                draw=draw,
                start=start,
                length=HISTORY_PAGE_SIZE,
            )
            params.update(
                {
                    "index_id": index_id,
                    "from": from_date.isoformat(),
                    "to": to_date.isoformat(),
                    "order[0][column]": "8",
                    "order[0][dir]": "desc",
                }
            )
            response = client.get(
                SHARESANSAR_INDEX_HISTORY_URL,
                params=params,
                headers={
                    "Referer": SHARESANSAR_INDEX_HISTORY_URL,
                    "Accept": "application/json, text/html",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )
            response.raise_for_status()
            _validate_source_response(response, SHARESANSAR_BASE)
            try:
                payload = response.json()
            except ValueError as exc:
                raise MarketDataProviderError(
                    "ShareSansar index history returned invalid JSON."
                ) from exc
            if not isinstance(payload, dict) or not isinstance(
                payload.get("data"), list
            ):
                raise MarketDataProviderError(
                    "ShareSansar index history returned an unexpected response."
                )
            total = payload.get("recordsFiltered", payload.get("recordsTotal", 0))
            if not isinstance(total, int) or total < 0:
                raise MarketDataProviderError(
                    "ShareSansar index history returned an invalid record count."
                )
            page_rows = payload["data"]
            rows.extend(page_rows)
            start += len(page_rows)
            draw += 1
            if not page_rows or len(rows) >= 10000:
                break
            if start < total:
                time.sleep(0.25)

    parsed = _parse_sharesansar_index_history(rows)
    if parsed:
        updated_at = timezone.now()
        with transaction.atomic():
            MarketIndexSnapshot.objects.bulk_create(
                [
                    MarketIndexSnapshot(
                        source=SHARESANSAR,
                        date=row["date"],
                        symbol="NEPSE",
                        name="NEPSE Index",
                        is_sector=False,
                        open_value=row["open"],
                        high_value=row["high"],
                        low_value=row["low"],
                        close_value=row["close"],
                        change_percent=row["change_percent"],
                        turnover=row["turnover"],
                        updated_at=updated_at,
                    )
                    for row in parsed
                ],
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
                    "turnover",
                    "updated_at",
                ],
            )
    logger.info("Saved %s ShareSansar historical NEPSE index records", len(parsed))
    return {"source": SHARESANSAR, "records": len(parsed)}


def collect_sharesansar_company_history(company):
    from .services import (
        persist_company_price_history,
        persist_floorsheet_transactions,
    )

    headers = {
        "User-Agent": getattr(settings, "CRAWLER_USER_AGENT", "NEPSEInsight/1.0"),
        "Accept": "text/html",
    }
    company_url = f"{SHARESANSAR_BASE}/company/{company.symbol.lower()}"
    with httpx.Client(
        timeout=REQUEST_TIMEOUT,
        headers=headers,
        follow_redirects=True,
    ) as client:
        robots = _robots_parser(client, SHARESANSAR_BASE)
        html = _get_html(
            client,
            company_url,
            SHARESANSAR_BASE,
            robot_parser=robots,
        )
        soup = BeautifulSoup(html, "html.parser")
        company_id = _text(soup.select_one("#companyid"))
        provider_symbol = _text(soup.select_one("#symbol"))
        token = soup.select_one('meta[name="_token"]')
        if (
            not company_id.isdecimal()
            or provider_symbol.upper() != company.symbol.upper()
            or token is None
            or not token.get("content")
        ):
            raise MarketDataProviderError(
                f"ShareSansar profile did not identify {company.symbol} correctly."
            )

        request_headers = {
            "Referer": company_url,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-Token": token["content"],
        }
        _check_robots(
            client,
            SHARESANSAR_COMPANY_PRICE_HISTORY_URL,
            SHARESANSAR_BASE,
            robot_parser=robots,
        )
        price_result = _collect_company_price_history(
            client,
            company,
            company_id,
            request_headers,
            persist_company_price_history,
        )

        _check_robots(
            client,
            SHARESANSAR_COMPANY_FLOORSHEET_URL,
            SHARESANSAR_BASE,
            robot_parser=robots,
        )
        floorsheet_result = _collect_company_floorsheet(
            client,
            company,
            request_headers,
            persist_floorsheet_transactions,
        )

    return {
        "source": SHARESANSAR,
        "symbol": company.symbol,
        "prices": price_result,
        "floorsheet": floorsheet_result,
    }


def _collect_company_price_history(
    client,
    company,
    company_id,
    request_headers,
    persist_prices,
):
    existing_count = StockPrice.objects.filter(
        company=company,
        source=SHARESANSAR,
    ).count()
    full_history = existing_count == 0
    start = 0
    draw = 1
    total = None
    created = 0
    updated = 0
    invalid = 0
    while True:
        payload = _post_datatable(
            client,
            SHARESANSAR_COMPANY_PRICE_HISTORY_URL,
            COMPANY_PRICE_HISTORY_COLUMNS,
            company_id,
            request_headers,
            draw,
            start,
            HISTORY_PAGE_SIZE,
        )
        page_rows = payload["data"]
        total = payload.get("recordsFiltered", payload.get("recordsTotal", 0))
        if not isinstance(total, int) or total < 0:
            raise MarketDataProviderError(
                "ShareSansar company history returned an invalid record count."
            )
        parsed = _parse_sharesansar_company_prices(page_rows)
        result = persist_prices(company, SHARESANSAR, parsed)
        created += result["created"]
        updated += result["updated"]
        invalid += result["invalid"]
        if not full_history or not page_rows:
            break
        start += len(page_rows)
        draw += 1
        if start >= total or start >= 10000:
            break
        time.sleep(0.25)
    return {
        "created": created,
        "updated": updated,
        "invalid": invalid,
        "provider_records": total,
    }


def _collect_company_floorsheet(
    client,
    company,
    request_headers,
    persist_transactions,
):
    start = 0
    draw = 1
    total = None
    rows = []
    while total is None or start < total:
        payload = _post_datatable(
            client,
            SHARESANSAR_COMPANY_FLOORSHEET_URL,
            COMPANY_FLOORSHEET_COLUMNS,
            company.symbol,
            request_headers,
            draw,
            start,
            FLOORSHEET_PAGE_SIZE,
        )
        page_rows = payload["data"]
        total = payload.get("recordsFiltered", payload.get("recordsTotal", 0))
        if not isinstance(total, int) or total < 0:
            raise MarketDataProviderError(
                "ShareSansar floorsheet returned an invalid record count."
            )
        rows.extend(_parse_sharesansar_company_floorsheet(page_rows, company.symbol))
        start += len(page_rows)
        draw += 1
        if not page_rows:
            break
        if start < total:
            time.sleep(0.25)
    saved = persist_transactions(SHARESANSAR, rows)
    return {**saved, "provider_records": total or 0}


def _post_datatable(
    client,
    url,
    columns,
    company_value,
    headers,
    draw,
    start,
    length,
):
    data = _datatable_params(columns, draw=draw, start=start, length=length)
    data["company"] = company_value
    response = client.post(url, data=data, headers=headers)
    response.raise_for_status()
    _validate_source_response(response, SHARESANSAR_BASE)
    try:
        payload = response.json()
    except ValueError as exc:
        raise MarketDataProviderError(
            "ShareSansar returned invalid historical JSON."
        ) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise MarketDataProviderError(
            "ShareSansar returned an unexpected historical response."
        )
    return payload


def _datatable_params(columns, draw, start, length):
    params = {
        "draw": str(draw),
        "start": str(start),
        "length": str(length),
        "search[value]": "",
        "search[regex]": "false",
    }
    for index, (name, searchable, orderable) in enumerate(columns):
        for key, value in (
            ("data", name),
            ("name", ""),
            ("searchable", str(searchable).lower()),
            ("orderable", str(orderable).lower()),
            ("search[value]", ""),
            ("search[regex]", "false"),
        ):
            params[f"columns[{index}][{key}]"] = value
    return params


def _sharesansar_nepse_index_id(html):
    soup = BeautifulSoup(html, "html.parser")
    index_select = soup.select_one("select#index")
    if index_select is None:
        raise MarketDataProviderError(
            "ShareSansar index history page has no index selector."
        )
    option = index_select.select_one("option[selected]") or index_select.select_one(
        "option"
    )
    if option is None or "nepse" not in option.get_text(" ", strip=True).lower():
        raise MarketDataProviderError(
            "ShareSansar index history page did not select NEPSE."
        )
    return option.get("value", "")


def _parse_sharesansar_company_prices(rows):
    prices = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        date = _parse_history_date(row.get("published_date"))
        if date is None:
            continue
        prices.append(
            {
                "date": date,
                "open": _number(row.get("open")),
                "high": _number(row.get("high")),
                "low": _number(row.get("low")),
                "close": _number(row.get("close")),
                "change_percent": _number(row.get("per_change")),
                "volume": _number(row.get("traded_quantity")),
            }
        )
    return prices


def _parse_sharesansar_company_floorsheet(rows, symbol):
    transactions = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        date = _parse_history_date(row.get("date_"))
        contract_no = str(row.get("contract_no") or "").strip()
        price = _number(row.get("rate"))
        quantity = _number(row.get("quantity"))
        if (
            date is None
            or not contract_no
            or price is None
            or price <= 0
            or quantity is None
            or quantity <= 0
            or quantity != quantity.to_integral_value()
        ):
            continue
        transactions.append(
            {
                "symbol": symbol,
                "trade_date": date,
                "trade_time": None,
                "transaction_id": contract_no,
                "price": price,
                "quantity": int(quantity),
                "buyer_broker": str(row.get("buyer") or "").strip(),
                "seller_broker": str(row.get("seller") or "").strip(),
                "source_record_id": f"{symbol.upper()}:{contract_no}",
            }
        )
    return transactions


def _robots_parser(client, base_url):
    robots_url = f"{base_url}/robots.txt"
    robots_response = client.get(robots_url)
    if robots_response.status_code not in {200, 404, 410}:
        robots_response.raise_for_status()
    robots = RobotFileParser(robots_url)
    if robots_response.status_code == 200:
        robots.parse(robots_response.text.splitlines())
    return robots


def _check_robots(client, url, base_url, robot_parser=None):
    robots = robot_parser or _robots_parser(client, base_url)
    if not robots.can_fetch(client.headers.get("User-Agent", "*"), url):
        raise MarketDataProviderError(f"robots.txt disallows market URL: {url}")


def _get_html(client, url, base_url, robot_parser=None):
    _check_robots(client, url, base_url, robot_parser=robot_parser)

    response = client.get(url)
    response.raise_for_status()
    _validate_source_response(response, base_url)
    return response.text


def _validate_source_response(response, base_url):
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


def _text(element):
    return element.get_text(strip=True) if element else ""


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
    header_cells = table.select_one("tr").select("th, td")
    raw_headers = [cell.get_text(" ", strip=True) for cell in header_cells]
    change_amount_index = next(
        (
            index
            for index, header in enumerate(raw_headers)
            if _normalize(header) == "diff" and "%" not in header
        ),
        None,
    )
    change_percent_index = next(
        (
            index
            for index, header in enumerate(raw_headers)
            if _normalize(header) == "diff" and "%" in header
        ),
        None,
    )
    for row in table.select("tr")[1:]:
        values = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
        record = dict(zip(headers, values))
        symbol = record.get("symbol", "").strip()
        if not symbol:
            continue
        change_amount = (
            _number(values[change_amount_index])
            if change_amount_index is not None and change_amount_index < len(values)
            else None
        )
        change_percent = (
            _number(values[change_percent_index])
            if change_percent_index is not None and change_percent_index < len(values)
            else _number(record.get("diff"))
        )
        stocks.append(
            {
                "symbol": symbol,
                "instrument_type": "",
                "open": _number(record.get("open")),
                "high": _number(record.get("high")),
                "low": _number(record.get("low")),
                "close": _number(record.get("ltp")),
                "change_amount": change_amount,
                "change_percent": change_percent,
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


def _parse_sharesansar_index_history(rows):
    history_by_date = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        date_value = next(
            (
                row[key]
                for key in (
                    "date_ad",
                    "date_en",
                    "index_date",
                    "published_date",
                    "date",
                    "datewise",
                )
                if row.get(key)
            ),
            None,
        )
        date = _parse_history_date(date_value)
        open_value = _number(row.get("open"))
        high_value = _number(row.get("high"))
        low_value = _number(row.get("low"))
        close_value = _number(row.get("current") or row.get("close"))
        if (
            date is None
            or any(
                value is None or value <= 0
                for value in (open_value, high_value, low_value, close_value)
            )
            or high_value < low_value
            or not low_value <= open_value <= high_value
            or not low_value <= close_value <= high_value
        ):
            continue
        history_by_date[date] = {
            "date": date,
            "open": open_value,
            "high": high_value,
            "low": low_value,
            "close": close_value,
            "change_percent": _number(
                row.get("per_change")
                if row.get("per_change") is not None
                else row.get("change_percent")
            ),
            "turnover": _number(row.get("turnover")),
        }
    return [history_by_date[day] for day in sorted(history_by_date)]


def _parse_history_date(value):
    if not value:
        return None
    text = str(value).strip()
    parsed = parse_date(text[:10])
    if parsed:
        return parsed
    for date_format in ("%Y/%m/%d", "%Y%m%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    return None


def _parse_merolagani_floorsheet(html):
    soup, table, headers = _table_with_headers(
        html,
        {"transactno", "symbol", "buyer", "seller", "quantity", "rate"},
    )
    if table is None:
        raise MarketDataProviderError(
            "Merolagani Floorsheet page did not contain the expected transaction table."
        )

    page_date_match = re.search(
        r"As of\s+(\d{4}/\d{2}/\d{2})", soup.get_text(" ", strip=True)
    )
    page_date = (
        _parse_history_date(page_date_match.group(1))
        if page_date_match
        else None
    )
    transactions = []
    for row in table.select("tr")[1:]:
        values = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
        record = dict(zip(headers, values))
        transaction_id = record.get("transactno", "").strip()
        symbol = record.get("symbol", "").strip()
        price = _number(record.get("rate"))
        quantity = _number(record.get("quantity"))
        transaction_date = (
            _parse_history_date(transaction_id[:8])
            if re.fullmatch(r"\d{8}\d+", transaction_id)
            else page_date
        )
        if (
            not transaction_id
            or not symbol
            or transaction_date is None
            or price is None
            or price <= 0
            or quantity is None
            or quantity <= 0
            or quantity != quantity.to_integral_value()
        ):
            continue
        transactions.append(
            {
                "symbol": symbol,
                "trade_date": transaction_date,
                "trade_time": None,
                "transaction_id": transaction_id,
                "price": price,
                "quantity": int(quantity),
                "buyer_broker": record.get("buyer", "").strip(),
                "seller_broker": record.get("seller", "").strip(),
                "source_record_id": transaction_id,
            }
        )
    if not transactions:
        raise MarketDataProviderError(
            "Merolagani returned no valid floorsheet transaction rows."
        )
    return transactions
