from django.db import IntegrityError, transaction

from .models import Company
from apps.market_data.market_sources import collect_sharesansar_company_directory


def sync_company_directory(target=None):
    if target is not None and target < 1:
        raise ValueError("Company target must be positive.")

    active_count = Company.objects.filter(is_active=True).count()
    if target is not None and active_count >= target:
        return {"created": 0, "active": active_count, "target": target}

    candidates = collect_sharesansar_company_directory(
        limit=target + Company.objects.count() if target is not None else None
    )
    created = 0
    updated = 0
    with transaction.atomic():
        for candidate in candidates:
            if target is not None and active_count >= target:
                break
            symbol = candidate["symbol"]
            name = candidate["name"]
            company = Company.objects.filter(symbol__iexact=symbol).first()
            if company is not None:
                was_active = company.is_active
                changed = (
                    company.name != name
                    or company.sector != candidate["sector"]
                    or not was_active
                )
                if changed:
                    company.name = name
                    company.sector = candidate["sector"]
                    company.is_active = True
                    try:
                        with transaction.atomic():
                            company.save(
                                update_fields=[
                                    "name",
                                    "sector",
                                    "is_active",
                                    "updated_at",
                                ]
                            )
                    except IntegrityError:
                        continue
                    updated += 1
                    active_count += int(not was_active)
                continue
            if Company.objects.filter(name__iexact=name).exists():
                continue
            try:
                with transaction.atomic():
                    Company.objects.create(
                        symbol=symbol,
                        name=name,
                        sector=candidate["sector"],
                    )
            except IntegrityError:
                continue
            created += 1
            active_count += 1

    return {
        "created": created,
        "updated": updated,
        "active": Company.objects.filter(is_active=True).count(),
        "target": target,
    }