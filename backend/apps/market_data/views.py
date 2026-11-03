from decimal import Decimal

from django.db import transaction
from django.db.models import Case, F, IntegerField, Max, Q, Value, When
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.events import broadcast_on_commit
from common.permissions import IsAdminRole
from common.date_ranges import parse_date_range
from .models import (
    MarketIndexHistory,
    MarketIndexSnapshot,
    MarketSnapshot,
    MarketStockSnapshot,
    FloorsheetTransaction,
    StockPrice,
)
from .serializers import (
    FloorsheetImportSerializer,
    FloorsheetTransactionSerializer,
    MarketIndexSnapshotSerializer,
    MarketSnapshotSerializer,
    MarketStockSnapshotSerializer,
    PriceImportSerializer,
    StockPriceSerializer,
)

INDEX_SOURCE_PRIORITY = {
    "nepsealpha": 0,
    "sharesansar": 1,
    "merolagani": 2,
}


def _daily_nepse_history(end_date):
    history_by_date = {}
    source_filter = list(INDEX_SOURCE_PRIORITY)
    for row in MarketIndexSnapshot.objects.filter(
        source__in=source_filter,
        symbol="NEPSE",
        close_value__isnull=False,
        date__lte=end_date,
    ).order_by("date", "updated_at"):
        candidate = {
            "date": row.date,
            "value": row.close_value,
            "change_percent": row.change_percent,
            "updated_at": row.updated_at,
            "source": row.source,
        }
        existing = history_by_date.get(row.date)
        if existing is None or INDEX_SOURCE_PRIORITY[row.source] < INDEX_SOURCE_PRIORITY[
            existing["source"]
        ]:
            history_by_date[row.date] = candidate

    for row in MarketSnapshot.objects.filter(
        source__in=source_filter,
        index_value__isnull=False,
        date__lte=end_date,
    ).order_by("date", "updated_at"):
        candidate = {
            "date": row.date,
            "value": row.index_value,
            "change_percent": row.index_change_percent,
            "updated_at": row.updated_at,
            "source": row.source,
        }
        existing = history_by_date.get(row.date)
        if existing is None or INDEX_SOURCE_PRIORITY[row.source] <= INDEX_SOURCE_PRIORITY[
            existing["source"]
        ]:
            history_by_date[row.date] = candidate

    points = []
    previous_value = None
    for row in sorted(history_by_date.values(), key=lambda item: item["date"]):
        change_percent = row["change_percent"]
        if change_percent is None and previous_value:
            change_percent = (
                (row["value"] - previous_value)
                / previous_value
                * Decimal("100")
            ).quantize(Decimal("0.0001"))
        points.append(
            {
                "date": row["date"],
                "value": row["value"],
                "change_percent": change_percent,
                "updated_at": row["updated_at"],
            }
        )
        previous_value = row["value"]
    return points


class StockPriceListView(generics.ListAPIView):
    serializer_class = StockPriceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["company", "date"]
    ordering_fields = ["date", "volume", "close_price"]

    def get_queryset(self):
        company_id = self.request.query_params.get("company_id")
        if not company_id:
            raise serializers.ValidationError(
                {"company_id": "This query parameter is required."}
            )
        if not company_id.isdecimal():
            raise serializers.ValidationError(
                {"company_id": "Company ID must be a positive integer."}
            )
        return StockPrice.objects.filter(company_id=company_id).select_related(
            "company"
        )


class MarketAnalysisOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date, end_date = parse_date_range(request)
        stock_dates = MarketStockSnapshot.objects.filter(
            source__in=["nepsealpha", "sharesansar", "merolagani"]
        ).values("source").annotate(latest_date=Max("date"))
        stock_filter = Q(pk__in=[])
        for stock_date in stock_dates:
            stock_filter |= Q(
                source=stock_date["source"],
                date=stock_date["latest_date"],
            )
        stocks = MarketStockSnapshot.objects.filter(stock_filter).order_by(
            F("turnover").desc(nulls_last=True), "symbol"
        )[:60]
        snapshot = (
            MarketSnapshot.objects.filter(
                source__in=["nepsealpha", "sharesansar"],
                index_value__isnull=False,
            )
            .order_by(
                "-date",
                Case(
                    When(source="nepsealpha", then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                ),
                "-updated_at",
            )
            .first()
        )
        all_history = _daily_nepse_history(end_date)
        history = [
            point
            for point in all_history
            if start_date is None or point["date"] >= start_date
        ]
        first_value = history[0]["value"] if history else None
        last_value = history[-1]["value"] if history else None
        history_change_percent = (
            (
                (last_value - first_value)
                / first_value
                * Decimal("100")
            ).quantize(Decimal("0.01"))
            if first_value and last_value is not None
            else None
        )
        history_period = {
            "requested_range": request.query_params.get("range", "30d"),
            "from": history[0]["date"] if history else None,
            "to": history[-1]["date"] if history else None,
            "available_from": all_history[0]["date"] if all_history else None,
            "available_to": all_history[-1]["date"] if all_history else None,
            "change_percent": (
                str(history_change_percent)
                if history_change_percent is not None
                else None
            ),
            "updated_at": (
                max(point["updated_at"] for point in history)
                if history
                else None
            ),
        }
        if snapshot is None:
            return Response(
                {
                    "snapshot": None,
                    "history": [
                        {
                            "date": point["date"],
                            "value": point["value"],
                            "change_percent": point["change_percent"],
                        }
                        for point in history
                    ],
                    "history_period": history_period,
                    "intraday": [],
                    "sectors": [],
                    "indices": [],
                    "stocks": MarketStockSnapshotSerializer(
                        stocks, many=True
                    ).data,
                }
            )

        intraday = list(
            MarketIndexHistory.objects.filter(
                source=snapshot.source,
                symbol="NEPSE",
                observed_at__date=snapshot.date,
            )
            .order_by("observed_at")
            .values("observed_at", "value")[:6000]
        )
        sectors = MarketIndexSnapshot.objects.filter(
            source=snapshot.source,
            date=snapshot.date,
            is_sector=True,
        ).order_by("name")
        indices = MarketIndexSnapshot.objects.filter(
            source=snapshot.source,
            date=snapshot.date,
        ).order_by("is_sector", "name")
        return Response(
            {
                "snapshot": MarketSnapshotSerializer(snapshot).data,
                "history": [
                    {
                        "date": point["date"],
                        "value": point["value"],
                        "change_percent": point["change_percent"],
                    }
                    for point in history
                ],
                "history_period": history_period,
                "intraday": intraday,
                "sectors": MarketIndexSnapshotSerializer(sectors, many=True).data,
                "indices": MarketIndexSnapshotSerializer(indices, many=True).data,
                "stocks": MarketStockSnapshotSerializer(stocks, many=True).data,
            }
        )


class FloorsheetListView(generics.ListAPIView):
    serializer_class = FloorsheetTransactionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["company", "trade_date", "buyer_broker", "seller_broker"]
    ordering_fields = ["trade_date", "price", "quantity"]

    def get_queryset(self):
        queryset = FloorsheetTransaction.objects.select_related("company")
        company_id = self.request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        return queryset


class PriceImportView(APIView):
    permission_classes = [IsAdminRole]

    @transaction.atomic
    def post(self, request):
        serializer = PriceImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created = 0
        updated = 0
        for row in serializer.validated_data["prices"]:
            company = row.pop("company")
            values = {
                **row,
                "source": serializer.validated_data["source"],
            }
            _, was_created = StockPrice.objects.update_or_create(
                company=company,
                date=values["date"],
                defaults=values,
            )
            created += int(was_created)
            updated += int(not was_created)
        broadcast_on_commit(
            "market.prices.updated",
            {
                "source": serializer.validated_data["source"],
                "created": created,
                "updated": updated,
            },
        )
        return Response({"created": created, "updated": updated})


class FloorsheetImportView(APIView):
    permission_classes = [IsAdminRole]

    @transaction.atomic
    def post(self, request):
        serializer = FloorsheetImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = serializer.validated_data["source"]
        rows = [
            FloorsheetTransaction(source=source, **row)
            for row in serializer.validated_data["transactions"]
        ]
        record_ids = {row.source_record_id for row in rows}
        existing_count = FloorsheetTransaction.objects.filter(
            source=source, source_record_id__in=record_ids
        ).count()
        FloorsheetTransaction.objects.bulk_create(rows, ignore_conflicts=True)
        total_count = FloorsheetTransaction.objects.filter(
            source=source, source_record_id__in=record_ids
        ).count()
        created_count = total_count - existing_count
        broadcast_on_commit(
            "market.floorsheet.updated",
            {"source": source, "created": created_count},
        )
        return Response(
            {
                "created": created_count,
                "submitted": len(rows),
                "duplicates_skipped": len(rows) - created_count,
            }
        )
