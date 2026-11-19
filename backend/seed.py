import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company
from apps.news.models import NewsArticle
from apps.users.models import UserProfile

DEMO_COMPANIES = (
    ("DEMO1", "Himalaya Demo Bank Limited", "Commercial Banks"),
    ("DEMO2", "Sagarmatha Demo Hydropower Limited", "Hydropower"),
)
DEMO_NEWS = (
    (
        "DEMO1",
        "Hypothetical quarterly-results overview",
        "https://demo.invalid/news/demo1/quarterly-results",
    ),
    (
        "DEMO2",
        "Hypothetical hydropower-sector outlook",
        "https://demo.invalid/news/demo2/sector-outlook",
    ),
)


def seed_superuser():
    username = os.getenv("DJANGO_SUPERUSER_USERNAME", "ayub").strip() or "ayub"
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

    User = get_user_model()

    user = User.objects.filter(username=username).first()

    if user is None:
        if not password:
            print("[seed] Superuser creation skipped: password is not configured.")
            return

        user = User.objects.create_superuser(
            username=username,
            email=os.getenv("DJANGO_SUPERUSER_EMAIL", ""),
            password=password,
        )
        print("[seed] Deployment superuser created.")

    elif not user.is_superuser:
        print("[seed] Existing user is not a superuser; permissions unchanged.")
        return

    UserProfile.objects.update_or_create(
        user=user,
        defaults={"role": UserProfile.Role.ADMIN},
    )

    print("[seed] Admin UserProfile created or updated.")


def seed_companies():
    if Company.objects.exists():
        print("[seed] Company table is not empty; demo companies skipped.")
        return

    for symbol, name, sector in DEMO_COMPANIES:
        Company.objects.get_or_create(
            symbol=symbol,
            defaults={"name": name, "sector": sector, "is_active": True},
        )
    print("[seed] Demo companies created.")


def seed_news():
    if NewsArticle.objects.exists():
        print("[seed] News table is not empty; demo news skipped.")
        return

    for symbol, subject, url in DEMO_NEWS:
        NewsArticle.objects.get_or_create(
            url=url,
            defaults={
                "source": "DEMO SEED (fictional; not crawled)",
                "headline": f"[DEMO] {subject} for {symbol}",
                "body": (
                    "Fictional sample content for deployment setup. "
                    "This is not a real company announcement or news report."
                ),
                "published_at": timezone.now(),
            },
        )
    print("[seed] Demo news created.")


def main():
    with transaction.atomic():
        seed_superuser()
        seed_companies()
        seed_news()


if __name__ == "__main__":
    main()
