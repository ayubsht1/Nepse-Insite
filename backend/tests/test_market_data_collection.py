from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.market_data.models import (
    MarketIndexHistory,
    MarketIndexSnapshot,
    MarketSnapshot,
    MarketStockSnapshot,
)
from apps.market_data.nepsealpha import (
    MarketDataProviderError,
    _parse_live_payload,
    _save_snapshot,
)
from apps.market_data.tasks import (
    collect_merolagani_market_data,
    collect_nepsealpha_market_data,
    collect_sharesansar_market_data,
)
from apps.market_data.market_sources import (
    _parse_merolagani,
    _parse_sharesansar,
)


def live_payload(market_open=True):
    observed_at = int(
        datetime(2025, 1, 19, 7, 15, tzinfo=datetime_timezone.utc).timestamp()
        * 1000
    )
    return {
        "is_market_open": market_open,
        "stock_live": {
            "prices": {
                "symbol": ["NEPSE", "BANKING", "ABC", "XYZ"],
                "type": ["index", "index", "stock", "stock"],
                "open": [2700, 1000, 500, 300],
                "high": [2720, 1010, 520, 310],
                "low": [2690, 990, 490, 290],
                "close": [2710, 1005, 510, 295],
                "percent_change": [0.4, 0.5, 2, -1.67],
                "turn_over": [1000, 500, 100, 50],
                "volume": [20, 10, 200, 150],
            }
        },
        "sectors": {"BANKING": "Banking"},
        "latest_price": {
            "today_price": 2710,
            "percent_change": 0.4,
            "previous_close": 2699.2,
            "date": "2025-01-19T13:00:00+05:45",
        },
        "marketSummary": [
            {"detail": "Total Turnover Rs:", "value": 1000},
            {"detail": "Total Traded Shares", "value": 350},
            {"detail": "Total Transactions", "value": 45},
            {"detail": "Total Scrips Traded", "value": 2},
            {"detail": "Total Float Market Capitalization Rs:", "value": 10000},
            {"detail": "NEPSE Market Cap", "value": 20000},
        ],
        "looser_gainer": [
            {
                "gainer": ["ABC", "Alpha Bank", 2],
                "looser": ["XYZ", "Xylophone", -1.67],
                "turnover": ["ABC", "Alpha Bank", 5.2],
            }
        ],
        "live_stock_price": {
            "date": [observed_at],
            "close": [2710],
        },
    }


class NepseAlphaParserTests(TestCase):
    def test_parser_maps_market_sectors_stocks_breadth_leaders_and_history(self):
        parsed = _parse_live_payload(live_payload())

        self.assertEqual(parsed["date"].isoformat(), "2025-01-19")
        self.assertEqual(parsed["market_open"], True)
        self.assertEqual(parsed["index_value"], Decimal("2710"))
        self.assertEqual(parsed["turnover"], Decimal("1000"))
        self.assertEqual(parsed["advancers"], 1)
        self.assertEqual(parsed["decliners"], 1)
        self.assertEqual(parsed["unchanged"], 0)
        self.assertEqual(parsed["indices"][1]["name"], "Banking")
        self.assertTrue(parsed["indices"][1]["is_sector"])
        self.assertEqual(parsed["stocks"][0]["symbol"], "ABC")
        self.assertEqual(parsed["top_gainers"][0]["change_percent"], 2)
        self.assertEqual(parsed["top_traded"][0]["turnover_crore"], 5.2)
        self.assertEqual(parsed["history"][0]["value"], Decimal("2710"))

    def test_parser_rejects_missing_price_columns(self):
        with self.assertRaises(MarketDataProviderError):
            _parse_live_payload({"stock_live": {"prices": {}}})

    def test_parser_uses_stock_rows_when_sentiment_values_are_missing(self):
        payload = live_payload()
        payload["stock_sentiment_summary"] = {"percent_change": ["unavailable"]}

        parsed = _parse_live_payload(payload)

        self.assertEqual(
            (parsed["advancers"], parsed["decliners"], parsed["unchanged"]),
            (1, 1, 0),
        )

    def test_persistence_updates_existing_rows_without_duplicates(self):
        parsed = _parse_live_payload(live_payload())
        parsed["technical_indicators"] = {"summary": {"overall_summary": "Buy"}}
        _save_snapshot(parsed)
        parsed["index_value"] = Decimal("2720")
        parsed["history"][0]["value"] = Decimal("2720")
        parsed["technical_indicators"] = {}
        _save_snapshot(parsed)

        self.assertEqual(MarketSnapshot.objects.count(), 1)
        self.assertEqual(MarketSnapshot.objects.get().index_value, Decimal("2720"))
        self.assertEqual(
            MarketSnapshot.objects.get().technical_indicators,
            {"summary": {"overall_summary": "Buy"}},
        )
        self.assertEqual(MarketIndexSnapshot.objects.count(), 2)
        self.assertEqual(MarketStockSnapshot.objects.count(), 2)
        self.assertEqual(MarketIndexHistory.objects.count(), 1)
        self.assertEqual(MarketIndexHistory.objects.get().value, Decimal("2720"))


class MarketSourceParserTests(TestCase):
    def test_sharesansar_parser_maps_index_summary_and_stock_change(self):
        market_html = """
          <table>
            <tr><th>Index</th><th>Open</th><th>High</th><th>Low</th>
              <th>Close</th><th>% Change</th></tr>
            <tr><td>NEPSE Index</td><td>2700</td><td>2720</td><td>2690</td>
              <td>2710</td><td>0.4</td></tr>
          </table>
          <table>
            <tr><td>Total Turnovers (Rs.)</td><td>12,500,000,000</td></tr>
            <tr><td>Total Traded Shares</td><td>1,200</td></tr>
            <tr><td>Total Transactions</td><td>13</td></tr>
            <tr><td>Total Scrips Traded</td><td>2</td></tr>
          </table>
          <table>
            <tr><th>Sub Index</th><th>Open</th><th>High</th><th>Low</th>
              <th>Close</th><th>% Change</th></tr>
            <tr><td>Banking Sub Index</td><td>1000</td><td>1010</td><td>990</td>
              <td>1005</td><td>0.5</td></tr>
          </table>
        """
        stocks_html = """
          <table>
            <tr><th>Symbol</th><th>Open</th><th>High</th><th>Low</th>
              <th>LTP</th><th>Vol</th><th>Turnover</th><th>Diff</th><th>Diff %</th></tr>
            <tr><td>ABC</td><td>500</td><td>520</td><td>490</td>
              <td>495</td><td>100</td><td>49,500</td><td>-10</td><td>-2.0</td></tr>
            <tr><td>XYZ</td><td>300</td><td>310</td><td>290</td>
              <td>305</td><td>200</td><td>61,000</td><td>5</td><td>1.67</td></tr>
          </table>
        """

        parsed = _parse_sharesansar(market_html, stocks_html)

        self.assertEqual(parsed["index_value"], Decimal("2710"))
        self.assertEqual(parsed["turnover"], Decimal("12500000000"))
        self.assertEqual(parsed["traded_volume"], Decimal("1200"))
        self.assertEqual(parsed["transaction_count"], 13)
        self.assertEqual(parsed["scrips_traded"], 2)
        self.assertEqual(parsed["indices"][1]["symbol"], "BANKING")
        self.assertEqual(parsed["stocks"][0]["change_percent"], Decimal("-2.0"))
        self.assertEqual(parsed["advancers"], 1)
        self.assertEqual(parsed["decliners"], 1)

    def test_merolagani_parser_maps_quotes_and_turnover_leaders(self):
        html = """
          <table>
            <tr><th>Symbol</th><th>LTP</th><th>% Change</th><th>Open</th>
              <th>High</th><th>Low</th><th>Qty.</th></tr>
            <tr><td>ABC</td><td>495</td><td>-2.0</td><td>500</td>
              <td>520</td><td>490</td><td>100</td></tr>
            <tr><td>XYZ</td><td>305</td><td>1.67</td><td>300</td>
              <td>310</td><td>290</td><td>200</td></tr>
          </table>
          <table>
            <tr><th>Symbol</th><th>Turnover</th></tr>
            <tr><td>XYZ</td><td>61,000</td></tr>
            <tr><td>ABC</td><td>49,500</td></tr>
          </table>
        """

        parsed = _parse_merolagani(html)

        self.assertIsNone(parsed["index_value"])
        self.assertEqual(parsed["indices"], [])
        self.assertIsNone(parsed["traded_volume"])
        self.assertEqual(parsed["stocks"][0]["close"], Decimal("495"))
        self.assertEqual(parsed["stocks"][0]["change_percent"], Decimal("-2.0"))
        self.assertEqual(parsed["top_traded"][0]["symbol"], "XYZ")
        self.assertEqual(parsed["top_traded"][0]["turnover_crore"], 0.0061)

    def test_snapshot_persistence_uses_provider_source_and_is_idempotent(self):
        market_html = """
          <table>
            <tr><th>Index</th><th>Open</th><th>High</th><th>Low</th>
              <th>Close</th><th>% Change</th></tr>
            <tr><td>NEPSE Index</td><td>2700</td><td>2720</td><td>2690</td>
              <td>2710</td><td>0.4</td></tr>
          </table>
        """
        stocks_html = """
          <table>
            <tr><th>Symbol</th><th>Open</th><th>High</th><th>Low</th>
              <th>LTP</th><th>Vol</th><th>Turnover</th><th>Diff %</th></tr>
            <tr><td>ABC</td><td>500</td><td>520</td><td>490</td>
              <td>495</td><td>100</td><td>49,500</td><td>-2.0</td></tr>
          </table>
        """
        parsed = _parse_sharesansar(market_html, stocks_html)

        _save_snapshot(parsed)
        _save_snapshot(parsed)

        self.assertEqual(
            MarketSnapshot.objects.get().source,
            "sharesansar",
        )
        self.assertEqual(MarketIndexSnapshot.objects.count(), 1)
        self.assertEqual(MarketStockSnapshot.objects.count(), 1)


class MarketOverviewApiTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="market-reader",
            password="test-password",
        )
        self.client.force_authenticate(user)
        now = timezone.now()
        self.snapshot = MarketSnapshot.objects.create(
            source="nepsealpha",
            date=now.date(),
            as_of=now,
            market_open=True,
            index_value=Decimal("2700"),
        )
        MarketIndexSnapshot.objects.create(
            source="nepsealpha",
            date=now.date(),
            symbol="BANKING",
            name="Banking",
            is_sector=True,
            close_value=Decimal("1000"),
            change_percent=Decimal("0.5"),
        )
        MarketIndexHistory.objects.create(
            source="nepsealpha",
            observed_at=now,
            value=Decimal("2700"),
        )
        MarketStockSnapshot.objects.create(
            source="sharesansar",
            date=now.date(),
            symbol="ABC",
            close_price=Decimal("500"),
            turnover=Decimal("1000"),
        )
        MarketStockSnapshot.objects.create(
            source="nepsealpha",
            date=now.date(),
            symbol="NO-TURNOVER",
            close_price=Decimal("200"),
        )

    def test_analysis_endpoint_returns_saved_snapshot_history_and_sectors(self):
        response = self.client.get("/api/market-data/analysis/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["snapshot"]["index_value"], "2700.0000")
        self.assertEqual(len(response.data["intraday"]), 1)
        self.assertEqual(response.data["sectors"][0]["symbol"], "BANKING")
        self.assertEqual(response.data["indices"][0]["symbol"], "BANKING")
        self.assertEqual(response.data["stocks"][0]["source"], "sharesansar")

    def test_analysis_endpoint_returns_quotes_without_an_index_snapshot(self):
        self.snapshot.delete()
        MarketStockSnapshot.objects.create(
            source="merolagani",
            date=timezone.localdate(),
            symbol="XYZ",
            close_price=Decimal("300"),
        )

        response = self.client.get("/api/market-data/analysis/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["snapshot"])
        self.assertEqual(
            {stock["source"] for stock in response.data["stocks"]},
            {"nepsealpha", "sharesansar", "merolagani"},
        )


class NepseAlphaTaskTests(TestCase):
    @patch("apps.market_data.tasks.collect_market_data")
    @patch("apps.market_data.tasks.timezone.localtime")
    def test_task_skips_requests_outside_market_hours(
        self, localtime_mock, collect_mock
    ):
        localtime_mock.return_value = timezone.make_aware(
            datetime(2025, 1, 19, 16, 0)
        )

        result = collect_nepsealpha_market_data()

        self.assertEqual(result["reason"], "outside_market_hours")
        collect_mock.assert_not_called()

    @patch("apps.market_data.tasks.collect_market_data")
    @patch("apps.market_data.tasks.timezone.localtime")
    def test_task_skips_repeated_requests_after_provider_reports_closed(
        self, localtime_mock, collect_mock
    ):
        now = timezone.make_aware(datetime(2025, 1, 19, 12, 0))
        localtime_mock.return_value = now
        snapshot = MarketSnapshot.objects.create(
            source="nepsealpha",
            date=now.date(),
            as_of=now,
            market_open=False,
        )
        MarketSnapshot.objects.filter(pk=snapshot.pk).update(updated_at=now)

        result = collect_nepsealpha_market_data()

        self.assertEqual(result["reason"], "market_closed")
        collect_mock.assert_not_called()

    @patch("apps.market_data.nepsealpha._save_snapshot")
    @patch("apps.market_data.nepsealpha._get_json")
    @patch("apps.market_data.nepsealpha.httpx.Client")
    def test_first_closed_collection_fetches_technical_indicators_once(
        self, client_class, get_json, save_snapshot
    ):
        client_class.return_value.__enter__.return_value = Mock()
        get_json.side_effect = [
            live_payload(market_open=False),
            {"indicators": {"overall": "Neutral"}},
        ]
        from apps.market_data.nepsealpha import collect_market_data

        collect_market_data()
        self.assertEqual(get_json.call_count, 2)
        self.assertEqual(
            save_snapshot.call_args.args[0]["technical_indicators"],
            {"indicators": {"overall": "Neutral"}},
        )

    @patch("apps.market_data.nepsealpha._save_snapshot")
    @patch("apps.market_data.nepsealpha._get_json")
    @patch("apps.market_data.nepsealpha.httpx.Client")
    def test_closed_collection_skips_technical_request_when_cached(
        self, client_class, get_json, save_snapshot
    ):
        client_class.return_value.__enter__.return_value = Mock()
        parsed = _parse_live_payload(live_payload(market_open=False))
        MarketSnapshot.objects.create(
            source="nepsealpha",
            date=parsed["date"],
            as_of=parsed["as_of"],
            market_open=True,
            technical_indicators={"summary": {"overall_summary": "Buy"}},
        )
        get_json.return_value = live_payload(market_open=False)
        from apps.market_data.nepsealpha import collect_market_data

        collect_market_data()

        self.assertEqual(get_json.call_count, 1)
        self.assertEqual(save_snapshot.call_args.args[0]["technical_indicators"], {})


class HtmlMarketProviderTaskTests(TestCase):
    @patch("apps.market_data.tasks.collect_sharesansar")
    @patch("apps.market_data.tasks.timezone.localtime")
    def test_sharesansar_task_skips_after_alpha_reports_market_closed(
        self, localtime_mock, collect_mock
    ):
        now = timezone.make_aware(datetime(2025, 1, 19, 12, 0))
        localtime_mock.return_value = now
        MarketSnapshot.objects.create(
            source="nepsealpha",
            date=now.date(),
            as_of=now,
            market_open=False,
        )

        result = collect_sharesansar_market_data()

        self.assertEqual(result["reason"], "market_closed")
        collect_mock.assert_not_called()

    @patch("apps.market_data.tasks.collect_merolagani")
    @patch("apps.market_data.tasks.timezone.localtime")
    def test_merolagani_task_runs_during_market_hours(
        self, localtime_mock, collect_mock
    ):
        localtime_mock.return_value = timezone.make_aware(
            datetime(2025, 1, 19, 12, 0)
        )
        collect_mock.return_value = {"source": "merolagani", "stocks": 2}

        result = collect_merolagani_market_data()

        self.assertEqual(
            result,
            {"status": "collected", "source": "merolagani", "stocks": 2},
        )
        collect_mock.assert_called_once_with()
