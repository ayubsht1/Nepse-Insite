from django.db import IntegrityError, transaction

from .models import Company
from apps.market_data.market_sources import collect_sharesansar_company_directory


def sync_company_directory(target=10):
    if target < 1:
        raise ValueError("Company target must be positive.")

    active_count = Company.objects.filter(is_active=True).count()
    if active_count >= target:
        return {"created": 0, "active": active_count, "target": target}

    candidates = collect_sharesansar_company_directory(
        limit=target + Company.objects.count()
    )
    created = 0
    with transaction.atomic():
        for candidate in candidates:
            if active_count + created >= target:
                break
            symbol = candidate["symbol"]
            name = candidate["name"]
            if Company.objects.filter(symbol__iexact=symbol).exists():
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

    return {
        "created": created,
        "active": Company.objects.filter(is_active=True).count(),
        "target": target,
    }