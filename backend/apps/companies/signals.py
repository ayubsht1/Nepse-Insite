from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Company


@receiver(post_save, sender=Company)
def backfill_market_prices(sender, instance, **kwargs):
    if not instance.is_active:
        return

    from apps.market_data.services import backfill_company_prices

    backfill_company_prices(instance)