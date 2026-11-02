from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from apps.companies.models import Company
from apps.crawlers.models import CrawlRun
from apps.market_data.models import FloorsheetTransaction, StockPrice
from apps.news.models import NewsArticle, NewsCompanyTag
from apps.users.models import UserProfile

User = get_user_model()


class SeedCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_is_idempotent_labeled_and_preserves_existing_values(self):
        call_command("seed", stdout=StringIO())
        company = Company.objects.get(symbol="NABIL")
        price = StockPrice.objects.filter(company=company).first()
        price_source = price.source
        price.close_price = Decimal("123.4500")
        price.save(update_fields=["close_price"])

        viewer_profile = User.objects.get(username="demo-viewer").profile
        viewer_profile.role = UserProfile.Role.ANALYST
        viewer_profile.save(update_fields=["role"])
        counts = {
            "companies": Company.objects.count(),
            "prices": StockPrice.objects.count(),
            "floorsheet": FloorsheetTransaction.objects.count(),
            "articles": NewsArticle.objects.count(),
            "tags": NewsCompanyTag.objects.count(),
            "users": User.objects.count(),
            "runs": CrawlRun.objects.count(),
        }

        call_command("seed", stdout=StringIO())

        self.assertEqual(Company.objects.count(), counts["companies"])
        self.assertEqual(StockPrice.objects.count(), counts["prices"])
        self.assertEqual(FloorsheetTransaction.objects.count(), counts["floorsheet"])
        self.assertEqual(NewsArticle.objects.count(), counts["articles"])
        self.assertEqual(NewsCompanyTag.objects.count(), counts["tags"])
        self.assertEqual(User.objects.count(), counts["users"])
        self.assertEqual(CrawlRun.objects.count(), counts["runs"])
        self.assertEqual(
            StockPrice.objects.get(pk=price.pk).close_price, Decimal("123.4500")
        )
        self.assertEqual(StockPrice.objects.get(pk=price.pk).source, price_source)
        self.assertEqual(
            User.objects.get(username="demo-viewer").profile.role,
            UserProfile.Role.ANALYST,
        )

        self.assertEqual(Company.objects.filter(symbol__in=[
            "NABIL", "NICA", "GBIME", "NTC", "SHIVM", "CHCL", "HDL", "EBL"
        ]).count(), 8)
        self.assertEqual(
            StockPrice.objects.filter(company=company).count(),
            22,
        )
        self.assertTrue(
            StockPrice.objects.filter(source__startswith="DEMO SEED").exists()
        )
        self.assertTrue(
            FloorsheetTransaction.objects.filter(
                source__startswith="DEMO SEED"
            ).exists()
        )
        self.assertTrue(
            NewsArticle.objects.filter(
                source__startswith="DEMO SEED",
                url__startswith="https://demo.invalid/",
            ).exists()
        )
        self.assertEqual(
            NewsCompanyTag.objects.filter(article__source__startswith="DEMO SEED")
            .count(),
            6,
        )
        self.assertTrue(
            CrawlRun.objects.filter(
                task_id__startswith="demo-seed-",
                error_message__startswith="DEMO SEED",
            ).exists()
        )

    def test_seed_rejects_production_settings(self):
        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError):
                call_command("seed", stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_seed_creates_demo_password_only_when_explicitly_requested(self):
        call_command(
            "seed",
            password="SampleDemoP@ssw0rd-2026!",
            stdout=StringIO(),
        )
        demo_admin = User.objects.get(username="demo-admin")
        self.assertTrue(demo_admin.check_password("SampleDemoP@ssw0rd-2026!"))
        self.assertEqual(demo_admin.profile.role, UserProfile.Role.ADMIN)
        self.assertFalse(demo_admin.is_staff)
        self.assertFalse(demo_admin.is_superuser)
