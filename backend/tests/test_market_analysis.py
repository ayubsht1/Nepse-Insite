from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from django.db import IntegrityError, transaction

from apps.analytics.services import (
    broker_breakdown,
    calculate_pressure,
    calculate_vwap,
    detect_volume_anomaly,
    news_market_relationship,
)
from apps.market_data.models import FloorsheetTransaction, StockPrice
from apps.news.models import NewsArticle, NewsCompanyTag
from .factories import create_company


class MarketAnalysisTests(TestCase):
    def setUp(self):
        self.company = create_company()
        self.today = timezone.localdate()

    def test_vwap_uses_transaction_turnover_and_returns_unavailable_without_data(self):
        unavailable = calculate_vwap(self.company, self.today, self.today)
        self.assertFalse(unavailable["available"])
        self.assertIsNone(unavailable["value"])

        FloorsheetTransaction.objects.create(
            company=self.company,
            trade_date=self.today,
            price=Decimal("10"),
            quantity=10,
            source="verified-source",
            source_record_id="first",
        )
        FloorsheetTransaction.objects.create(
            company=self.company,
            trade_date=self.today,
            price=Decimal("12"),
            quantity=20,
            source="verified-source",
            source_record_id="second",
        )
        result = calculate_vwap(self.company, self.today, self.today)
        self.assertTrue(result["available"])
        self.assertEqual(result["value"], "11.3333")
        self.assertEqual(result["transactions"], 2)

    def test_merolagani_vwap_reports_source_pagination_limit(self):
        FloorsheetTransaction.objects.create(
            company=self.company,
            trade_date=self.today,
            price=Decimal("10"),
            quantity=5,
            source="merolagani",
            source_record_id="merolagani-record",
        )

        result = calculate_vwap(self.company, self.today, self.today)

        self.assertTrue(result["available"])
        self.assertIn("pagination may limit coverage", result["limitation"])

    def test_close_location_pressure_is_bounded_and_labeled_as_estimated(self):
        price = StockPrice(
            company=self.company,
            date=self.today,
            open_price=Decimal("10"),
            high_price=Decimal("12"),
            low_price=Decimal("8"),
            close_price=Decimal("11"),
            volume=100,
        )
        result = calculate_pressure(price)
        self.assertEqual(result["score"], "0.5000")
        self.assertIn("not actual buyer or seller volume", result["interpretation"])

    def test_company_price_day_is_unique_in_database(self):
        StockPrice.objects.create(
            company=self.company,
            date=self.today,
            open_price=10,
            high_price=12,
            low_price=8,
            close_price=11,
            volume=100,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StockPrice.objects.create(
                    company=self.company,
                    date=self.today,
                    open_price=10,
                    high_price=12,
                    low_price=8,
                    close_price=11,
                    volume=100,
                )

    def test_volume_anomaly_requires_twenty_prior_observations(self):
        for day in range(1, 21):
            StockPrice.objects.create(
                company=self.company,
                date=self.today - timedelta(days=day),
                open_price=10,
                high_price=12,
                low_price=8,
                close_price=10,
                volume=100,
            )
        current = StockPrice.objects.create(
            company=self.company,
            date=self.today,
            open_price=10,
            high_price=12,
            low_price=8,
            close_price=11,
            volume=201,
        )
        result = detect_volume_anomaly(self.company, current.date)
        self.assertTrue(result["available"])
        self.assertTrue(result["is_anomaly"])
        self.assertEqual(result["ratio_to_average"], "2.0100")

        StockPrice.objects.filter(company=self.company).delete()
        StockPrice.objects.create(
            company=self.company,
            date=self.today,
            open_price=10,
            high_price=12,
            low_price=8,
            close_price=11,
            volume=201,
        )
        insufficient = detect_volume_anomaly(self.company, self.today)
        self.assertFalse(insufficient["available"])
        self.assertEqual(insufficient["prior_days_available"], 0)

    def test_broker_breakdown_uses_only_recorded_floorsheet_sides(self):
        FloorsheetTransaction.objects.create(
            company=self.company,
            trade_date=self.today,
            price=Decimal("10"),
            quantity=4,
            buyer_broker="58",
            seller_broker="12",
            source="verified-source",
            source_record_id="broker-record",
        )
        result = broker_breakdown(self.company, self.today, self.today)
        self.assertTrue(result["available"])
        self.assertEqual(result["brokers"][0]["broker_code"], "12")
        self.assertEqual(result["brokers"][0]["sell_quantity"], 4)
        self.assertEqual(result["brokers"][1]["broker_code"], "58")
        self.assertEqual(result["brokers"][1]["buy_quantity"], 4)

    def test_news_relationship_uses_next_recorded_trading_day(self):
        previous_day = self.today - timedelta(days=3)
        next_day = self.today + timedelta(days=1)
        StockPrice.objects.create(
            company=self.company,
            date=previous_day,
            open_price=10,
            high_price=10,
            low_price=10,
            close_price=10,
            volume=100,
        )
        StockPrice.objects.create(
            company=self.company,
            date=next_day,
            open_price=11,
            high_price=11,
            low_price=11,
            close_price=11,
            volume=150,
        )
        article = NewsArticle.objects.create(
            url="https://news.example.test/article/1",
            source="fixture",
            headline="Nabil Bank reports",
            published_at=timezone.now(),
        )
        NewsCompanyTag.objects.create(
            article=article,
            company=self.company,
            confidence_score=Decimal("0.900"),
            method=NewsCompanyTag.Method.RULE,
        )
        result = news_market_relationship(self.company)
        observation = result["observations"][0]
        self.assertEqual(observation["baseline_trading_date"], previous_day.isoformat())
        self.assertEqual(
            observation["next_observed_trading_date"], next_day.isoformat()
        )
        self.assertEqual(observation["close_change_percent"], "10.00")
        self.assertIn("does not establish", result["limitation"])
