from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company

from .models import FloorsheetTransaction, MarketStockSnapshot, StockPrice

PRICE_SOURCE_PRIORITY = {
    "nepsealpha": 0,
    "sharesansar": 1,
    "merolagani": 2,
}


def persist_company_prices(source, date, rows):
    priority = PRICE_SOURCE_PRIORITY.get(source)
    if priority is None:
        return {"created": 0, "updated": 0, "unmatched": len(rows), "invalid": 0}

    latest_rows = {}
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        if symbol:
            latest_rows[symbol] = row
    companies = {
        company.symbol.strip().upper(): company
        for company in Company.objects.filter(is_active=True)
        if company.symbol.strip().upper() in latest_rows
    }
    company_ids = [company.pk for company in companies.values()]
    existing_prices = {
        price.company_id: price
        for price in StockPrice.objects.filter(
            company_id__in=company_ids, date=date
        )
    }

    records = []
    created = 0
    updated = 0
    unmatched = 0
    invalid = 0
    for symbol, row in latest_rows.items():
        company = companies.get(symbol)
        if company is None:
            unmatched += 1
            continue

        values = _valid_ohlcv(row)
        if values is None:
            invalid += 1
            continue

        existing = existing_prices.get(company.pk)
        if existing and existing.source not in PRICE_SOURCE_PRIORITY:
            continue
        if (
            existing
            and existing.source in PRICE_SOURCE_PRIORITY
            and PRICE_SOURCE_PRIORITY[existing.source] < priority
        ):
            continue

        records.append(
            StockPrice(
                company=company,
                date=date,
                source=source,
                change_amount=row.get("change_amount"),
                change_percent=row.get("change_percent"),
                **values,
            )
        )
        if existing:
            updated += 1
        else:
            created += 1

    if records:
        StockPrice.objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=["company", "date"],
            update_fields=[
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "change_amount",
                "change_percent",
                "volume",
                "source",
                "updated_at",
            ],
        )

    return {
        "created": created,
        "updated": updated,
        "unmatched": unmatched,
        "invalid": invalid,
    }


def persist_company_price_history(company, source, rows):
    priority = PRICE_SOURCE_PRIORITY.get(source)
    if priority is None:
        return {"created": 0, "updated": 0, "invalid": len(rows)}

    valid_rows = {}
    invalid = 0
    for row in rows:
        date = row.get("date")
        values = _valid_ohlcv(row)
        if date is None or values is None:
            invalid += 1
            continue
        valid_rows[date] = (row, values)

    existing_prices = {
        price.date: price
        for price in StockPrice.objects.filter(
            company=company,
            date__in=valid_rows,
        )
    }
    records = []
    created = 0
    updated = 0
    for date, (row, values) in valid_rows.items():
        existing = existing_prices.get(date)
        if existing and existing.source not in PRICE_SOURCE_PRIORITY:
            continue
        if existing and PRICE_SOURCE_PRIORITY[existing.source] < priority:
            continue

        records.append(
            StockPrice(
                company=company,
                date=date,
                source=source,
                change_amount=row.get("change_amount"),
                change_percent=row.get("change_percent"),
                **values,
            )
        )
        if existing:
            updated += 1
        else:
            created += 1

    if records:
        StockPrice.objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=["company", "date"],
            update_fields=[
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "change_amount",
                "change_percent",
                "volume",
                "source",
                "updated_at",
            ],
        )

    return {"created": created, "updated": updated, "invalid": invalid}


def backfill_company_prices(company):
    if not company.is_active:
        return {"created": 0, "updated": 0}

    preferred_rows = {}
    snapshots = MarketStockSnapshot.objects.filter(
        symbol__iexact=company.symbol,
        source__in=PRICE_SOURCE_PRIORITY,
    ).order_by("date", "source")
    for snapshot in snapshots.iterator():
        row = {
            "open": snapshot.open_price,
            "high": snapshot.high_price,
            "low": snapshot.low_price,
            "close": snapshot.close_price,
            "volume": snapshot.volume,
        }
        values = _valid_ohlcv(row)
        if values is None:
            continue

        existing = preferred_rows.get(snapshot.date)
        priority = PRICE_SOURCE_PRIORITY[snapshot.source]
        if existing is None or priority < existing[0]:
            preferred_rows[snapshot.date] = (priority, snapshot, values)

    existing_prices = {
        price.date: price
        for price in StockPrice.objects.filter(
            company=company,
            date__in=preferred_rows,
        )
    }
    records = []
    created = 0
    updated = 0
    for date, (_, snapshot, values) in preferred_rows.items():
        existing = existing_prices.get(date)
        if existing and existing.source not in PRICE_SOURCE_PRIORITY:
            continue
        if (
            existing
            and PRICE_SOURCE_PRIORITY[existing.source]
            < PRICE_SOURCE_PRIORITY[snapshot.source]
        ):
            continue

        records.append(
            StockPrice(
                company=company,
                date=date,
                source=snapshot.source,
                change_amount=snapshot.change_amount,
                change_percent=snapshot.change_percent,
                **values,
            )
        )
        if existing:
            updated += 1
        else:
            created += 1

    if records:
        StockPrice.objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=["company", "date"],
            update_fields=[
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "change_amount",
                "change_percent",
                "volume",
                "source",
                "updated_at",
            ],
        )

    return {"created": created, "updated": updated}


def persist_floorsheet_transactions(source, rows):
    symbols = {
        str(row.get("symbol") or "").strip().upper()
        for row in rows
        if row.get("symbol")
    }
    companies = {
        company.symbol.strip().upper(): company
        for company in Company.objects.filter(is_active=True, symbol__in=symbols)
    }
    records = []
    unmatched = 0
    for row in rows:
        company = companies.get(str(row.get("symbol") or "").strip().upper())
        if company is None:
            unmatched += 1
            continue
        records.append(
            FloorsheetTransaction(
                company=company,
                trade_date=row["trade_date"],
                trade_time=row.get("trade_time"),
                transaction_id=row["transaction_id"],
                price=row["price"],
                quantity=row["quantity"],
                buyer_broker=row.get("buyer_broker", ""),
                seller_broker=row.get("seller_broker", ""),
                source=source,
                source_record_id=row["source_record_id"],
            )
        )

    with transaction.atomic():
        before = FloorsheetTransaction.objects.filter(
            source=source,
            source_record_id__in=[row.source_record_id for row in records],
        ).count()
        FloorsheetTransaction.objects.bulk_create(records, ignore_conflicts=True)
        after = FloorsheetTransaction.objects.filter(
            source=source,
            source_record_id__in=[row.source_record_id for row in records],
        ).count()
    return {
        "created": after - before,
        "duplicates": len(records) - (after - before),
        "unmatched": unmatched,
    }


def _valid_ohlcv(row):
    values = {
        "open_price": row.get("open"),
        "high_price": row.get("high"),
        "low_price": row.get("low"),
        "close_price": row.get("close"),
        "volume": row.get("volume"),
    }
    prices = [
        values[field]
        for field in ("open_price", "high_price", "low_price", "close_price")
    ]
    volume = values["volume"]
    if any(not isinstance(value, Decimal) or value <= 0 for value in prices):
        return None
    if (
        values["high_price"] < values["low_price"]
        or not values["low_price"] <= values["open_price"] <= values["high_price"]
        or not values["low_price"] <= values["close_price"] <= values["high_price"]
        or not isinstance(volume, Decimal)
        or volume < 0
        or volume != volume.to_integral_value()
    ):
        return None
    return {
        **values,
        "volume": int(volume),
    }
