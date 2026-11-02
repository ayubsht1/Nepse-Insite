from django.db import transaction
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.events import broadcast_on_commit
from common.permissions import IsAdminRole
from .models import FloorsheetTransaction, StockPrice
from .serializers import (
    FloorsheetImportSerializer,
    FloorsheetTransactionSerializer,
    PriceImportSerializer,
    StockPriceSerializer,
)


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
