from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company
from apps.crawlers.models import CrawlRun, CrawlSource
from apps.market_data.models import FloorsheetTransaction, StockPrice
from apps.news.models import NewsArticle, NewsCompanyTag
from apps.users.models import UserProfile

User = get_user_model()
DEMO_SOURCE = "DEMO SEED (fabricated; not crawled)"
DEMO_END_DATE = date(2026, 10, 30)
SAMPLE_COMPANIES = (
    ("NABIL", "Nabil Bank Limited", ["Nabil Bank"], "Commercial Banks", Decimal("510")),
    ("NICA", "NIC Asia Bank Limited", ["NIC Asia"], "Commercial Banks", Decimal("390")),
    ("GBIME", "Global IME Bank Limited", ["Global IME Bank"], "Commercial Banks", Decimal("280")),
    ("NTC", "Nepal Doorsanchar Company Limited", ["Nepal Telecom"], "Others", Decimal("920")),
    ("SHIVM", "Shivam Cements Limited", ["Shivam Cement"], "Manufacturing", Decimal("610")),
    ("CHCL", "Chilime Hydropower Company Limited", ["Chilime"], "Hydropower", Decimal("480")),
    ("HDL", "Himalayan Distillery Limited", ["Himalayan Distillery"], "Manufacturing", Decimal("1450")),
    ("EBL", "Everest Bank Limited", ["Everest Bank"], "Commercial Banks", Decimal("690")),
)
SAMPLE_SOURCES = (
    ("Mero Lagani", "merolagani", "https://merolagani.com"),
    ("ShareSansar", "sharesansar", "https://www.sharesansar.com"),
    ("NEPSE Alpha", "nepsealpha", "https://nepsealpha.com"),
    ("Bizmandu", "bizmandu", "https://bizmandu.com"),
)
SAMPLE_NEWS = (
    ("merolagani", "A hypothetical quarterly-results review", 0),
    ("sharesansar", "A hypothetical dividend-policy discussion", 1),
    ("bizmandu", "A hypothetical hydropower-sector outlook", 2),
    ("sharesansar", "A hypothetical banking-sector overview", 3),
    ("merolagani", "A hypothetical telecom-sector comparison", 4),
    ("bizmandu", "A hypothetical cement-industry analysis", 5),
)
DEMO_ARTICLE_NOTICE = (
    "DEMO DATA: This fictional example is not a real company announcement, "
    "market event, or publisher article."
)


def _recent_weekdays(count=22):
    dates = []
    current = DEMO_END_DATE
    while len(dates) < count:
        if current.weekday() < 5:
            dates.append(current)
        current -= timedelta(days=1)
    return list(reversed(dates))


def _price_values(base_price, company_index, day_index):
    daily_offset = Decimal((day_index * 3 + company_index * 2) % 9 - 4) / Decimal("1000")
    close = (base_price * (Decimal("1") + daily_offset)).quantize(Decimal("0.01"))
    open_offset = Decimal((day_index + company_index) % 3 - 1) / Decimal("1000")
    opening = (close * (Decimal("1") + open_offset)).quantize(Decimal("0.01"))
    high = (max(opening, close) * Decimal("1.01")).quantize(Decimal("0.01"))
    low = (min(opening, close) * Decimal("0.99")).quantize(Decimal("0.01"))
    volume = 25000 + ((day_index * 7919 + company_index * 13007) % 175000)
    return opening, high, low, close, volume


class Command(BaseCommand):
    help = "Create clearly labeled sample data in a development database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            help=(
                "Set this password on newly created demo users only. Existing "
                "users and passwords are never changed."
            ),
        )

    def handle(self, *args, **options):
        if args:
            raise CommandError("The seed command does not accept positional arguments.")
        if not settings.DEBUG:
            raise CommandError(
                "The seed command is disabled unless DEBUG=True. It never runs "
                "against production settings."
            )

        demo_password = options.get("password")
        if demo_password:
            for username in ("demo-admin", "demo-analyst", "demo-viewer"):
                password_validation.validate_password(
                    demo_password, User(username=username)
                )

        with transaction.atomic():
            summary = self._seed(demo_password)

        self.stdout.write(
            self.style.SUCCESS(
                "Development demo seed complete (idempotent): "
                + ", ".join(f"{key}={value}" for key, value in summary.items())
            )
        )
        if not demo_password:
            self.stdout.write(
                "Demo accounts have unusable passwords; set passwords with "
                "manage.py changepassword if interactive demo login is needed."
            )

    def _seed(self, demo_password):
        dates = _recent_weekdays()
        companies = []
        created = {
            "companies": 0,
            "prices": 0,
            "floorsheet": 0,
            "articles": 0,
            "tags": 0,
            "users": 0,
            "crawl_runs": 0,
        }

        for symbol, name, aliases, sector, base_price in SAMPLE_COMPANIES:
            company, was_created = Company.objects.get_or_create(
                symbol=symbol,
                defaults={
                    "name": name,
                    "aliases": aliases,
                    "sector": sector,
                    "is_active": True,
                },
            )
            created["companies"] += was_created
            companies.append((company, base_price))

        for company_index, (company, base_price) in enumerate(companies):
            for day_index, day in enumerate(dates):
                opening, high, low, close, volume = _price_values(
                    base_price, company_index, day_index
                )
                _, was_created = StockPrice.objects.get_or_create(
                    company=company,
                    date=day,
                    defaults={
                        "open_price": opening,
                        "high_price": high,
                        "low_price": low,
                        "close_price": close,
                        "volume": volume,
                        "source": DEMO_SOURCE,
                    },
                )
                created["prices"] += was_created

        sample_day = dates[-1]
        for company_entry in companies:
            company = company_entry[0]
            price = StockPrice.objects.get(company=company, date=sample_day)
            for trade_number, (broker_buy, broker_sell, quantity) in enumerate(
                (("58", "12", 25), ("34", "58", 40), ("12", "19", 15)),
                start=1,
            ):
                _, was_created = FloorsheetTransaction.objects.get_or_create(
                    source=DEMO_SOURCE,
                    source_record_id=(
                        f"demo-seed-{company.symbol}-{sample_day:%Y%m%d}-{trade_number}"
                    ),
                    defaults={
                        "company": company,
                        "trade_date": sample_day,
                        "trade_time": time(11, 0 + trade_number),
                        "transaction_id": f"DEMO-{company.symbol}-{trade_number}",
                        "price": price.close_price,
                        "quantity": quantity,
                        "buyer_broker": broker_buy,
                        "seller_broker": broker_sell,
                    },
                )
                created["floorsheet"] += was_created

        articles = []
        news_dates = dates[-len(SAMPLE_NEWS) :]
        companies_by_index = [entry[0] for entry in companies]
        for index, (source_key, title, company_index) in enumerate(SAMPLE_NEWS):
            company = companies_by_index[company_index]
            day = news_dates[index]
            headline = f"[DEMO] {title} — {company.symbol}"
            url = f"https://demo.invalid/news/{source_key}/{company.symbol.lower()}/{day:%Y%m%d}"
            article, was_created = NewsArticle.objects.get_or_create(
                url=url,
                defaults={
                    "source": f"DEMO SEED · {source_key} (fabricated; not crawled)",
                    "headline": headline,
                    "body": (
                        f"{DEMO_ARTICLE_NOTICE} This sample discusses {company.name} "
                        "only to demonstrate company tagging and the news interface."
                    ),
                    "published_at": timezone.make_aware(
                        datetime.combine(day, time(10, 0)),
                        timezone.get_default_timezone(),
                    ),
                },
            )
            created["articles"] += was_created
            articles.append((article, company))

        for article, company in articles:
            _, was_created = NewsCompanyTag.objects.get_or_create(
                article=article,
                company=company,
                defaults={
                    "confidence_score": Decimal("0.900"),
                    "method": NewsCompanyTag.Method.RULE,
                },
            )
            created["tags"] += was_created

        demo_users = (
            ("demo-admin", "Demo Administrator", UserProfile.Role.ADMIN),
            ("demo-analyst", "Demo Analyst", UserProfile.Role.ANALYST),
            ("demo-viewer", "Demo Viewer", UserProfile.Role.VIEWER),
        )
        for username, first_name, role in demo_users:
            user, was_created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.invalid",
                    "first_name": first_name,
                    "is_active": True,
                },
            )
            if was_created:
                if demo_password:
                    user.set_password(demo_password)
                    user.save(update_fields=["password"])
                else:
                    user.set_unusable_password()
                    user.save(update_fields=["password"])
                UserProfile.objects.update_or_create(
                    user=user, defaults={"role": role}
                )
            else:
                UserProfile.objects.get_or_create(
                    user=user, defaults={"role": role}
                )
            created["users"] += was_created

        for name, key, base_url in SAMPLE_SOURCES:
            source, _ = CrawlSource.objects.get_or_create(
                key=key,
                defaults={"name": name, "base_url": base_url, "enabled": False},
            )
            created["crawl_runs"] += CrawlRun.objects.get_or_create(
                source=source,
                task_id=f"demo-seed-{key}",
                defaults={
                    "status": CrawlRun.Status.PARTIAL,
                    "started_at": timezone.now(),
                    "finished_at": timezone.now(),
                    "error_message": (
                        "DEMO SEED only — this sample status was not produced by "
                        "a network crawl; no HTTP requests were made."
                    ),
                },
            )[1]

        return created
