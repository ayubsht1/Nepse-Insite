import httpx
from django.core.management.base import BaseCommand, CommandError

from apps.companies.market_directory import sync_company_directory
from apps.market_data.nepsealpha import MarketDataProviderError


class Command(BaseCommand):
    help = "Sync real listed-company directory records from ShareSansar."

    def add_arguments(self, parser):
        parser.add_argument(
            "--target",
            type=int,
            default=10,
            help="Ensure at least this many active company records exist (default: 10).",
        )

    def handle(self, *args, **options):
        target = options["target"]
        if target < 1:
            raise CommandError("--target must be a positive integer.")
        try:
            result = sync_company_directory(target=target)
        except (httpx.HTTPError, MarketDataProviderError, ValueError) as exc:
            raise CommandError(f"Company directory sync failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Company directory sync complete: "
                f"created={result['created']}, active={result['active']}, "
                f"target={result['target']}"
            )
        )