from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.news.models import NewsArticle, NewsCompanyTag
from apps.users.models import UserProfile
from .factories import create_company, create_user


class CategorizationAndApiTests(TestCase):
    def setUp(self):
        self.company = create_company()
        self.article = NewsArticle.objects.create(
            url="https://news.example.test/nabil/1",
            source="fixture",
            headline="NABIL Bank announces an update",
            body="Nabil Bank Limited is mentioned in this report.",
        )
        self.viewer = create_user(UserProfile.Role.VIEWER, username="viewer")
        self.analyst = create_user(UserProfile.Role.ANALYST, username="analyst")
        self.admin = create_user(UserProfile.Role.ADMIN, username="admin")
        self.client = APIClient()

    def test_rule_categorization_matches_symbol_and_does_not_duplicate_tags(self):
        from apps.news.services.categorization import categorize_article

        tags = categorize_article(self.article)
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0].confidence_score, Decimal("0.980"))
        self.assertEqual(tags[0].method, NewsCompanyTag.Method.RULE)
        self.assertEqual(len(categorize_article(self.article)), 1)
        self.assertEqual(
            NewsCompanyTag.objects.filter(article=self.article).count(), 1
        )

    def test_company_list_requires_authentication_and_viewer_can_read(self):
        response = self.client.get("/api/companies/")
        self.assertEqual(response.status_code, 401)

        self.client.force_authenticate(self.viewer)
        response = self.client.get("/api/companies/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["symbol"], self.company.symbol)

    def test_analyst_correction_is_permission_checked_and_audited(self):
        self.client.force_authenticate(self.viewer)
        denied = self.client.post(
            f"/api/news/{self.article.pk}/recategorize/",
            {"tags": [], "note": "Remove incorrect tag"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(self.analyst)
        response = self.client.post(
            f"/api/news/{self.article.pk}/recategorize/",
            {
                "tags": [
                    {
                        "company_id": self.company.pk,
                        "confidence_score": "0.750",
                    }
                ],
                "note": "Analyst confirmed a weaker company reference.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["company_tags"][0]["method"], "analyst")
        self.assertEqual(
            NewsCompanyTag.objects.get(article=self.article).confidence_score,
            Decimal("0.750"),
        )
        correction = self.article.corrections.get()
        self.assertEqual(correction.corrected_by, self.analyst)
        self.assertEqual(correction.note, "Analyst confirmed a weaker company reference.")

    def test_admin_role_can_access_admin_crawl_api_and_viewer_cannot(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get("/api/admin/crawl-runs/").status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/admin/crawl-runs/").status_code, 200)

    def test_viewer_cannot_import_prices_and_admin_can(self):
        body = {
            "source": "verified-import",
            "prices": [
                {
                    "company_id": self.company.pk,
                    "date": "2026-10-30",
                    "open_price": "10",
                    "high_price": "12",
                    "low_price": "9",
                    "close_price": "11",
                    "volume": 100,
                }
            ],
        }
        self.client.force_authenticate(self.viewer)
        denied = self.client.post(
            "/api/market-data/admin/prices/import/", body, format="json"
        )
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.admin)
        accepted = self.client.post(
            "/api/market-data/admin/prices/import/", body, format="json"
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.data, {"created": 1, "updated": 0})

    def test_floorsheet_import_reports_duplicate_source_records(self):
        record = {
            "company_id": self.company.pk,
            "trade_date": "2026-10-30",
            "price": "10",
            "quantity": 3,
            "buyer_broker": "58",
            "seller_broker": "12",
            "source_record_id": "record-001",
        }
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/market-data/admin/floorsheet/import/",
            {"source": "verified-source", "transactions": [record, record]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {"created": 1, "submitted": 2, "duplicates_skipped": 1},
        )

    def test_company_behavior_summary_reports_missing_data(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.get(
            f"/api/companies/{self.company.pk}/behavior-summary/?range=30d"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["vwap"]["available"])
        self.assertIsNone(response.data["latest_price"])
