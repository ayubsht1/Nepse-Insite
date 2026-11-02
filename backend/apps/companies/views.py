from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.analytics.services import company_behavior_summary
from apps.market_data.models import StockPrice
from apps.market_data.serializers import StockPriceSerializer
from common.date_ranges import parse_date_range
from rest_framework.permissions import IsAuthenticated

from common.permissions import IsAdminOrReadOnly
from .models import Company
from .serializers import CompanySerializer


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ["symbol", "name", "sector"]
    ordering_fields = ["symbol", "name", "sector", "created_at"]
    filterset_fields = ["sector", "is_active"]

    def get_permissions(self):
        if self.action in {"list", "retrieve", "prices", "behavior_summary", "compare"}:
            return [permission() for permission in [IsAuthenticated]]
        return super().get_permissions()

    @action(detail=True, methods=["get"])
    def prices(self, request, pk=None):
        company = self.get_object()
        start, end = parse_date_range(request)
        prices = StockPrice.objects.filter(company=company, date__lte=end)
        if start is not None:
            prices = prices.filter(date__gte=start)
        page = self.paginate_queryset(prices)
        serializer = StockPriceSerializer(
            page if page is not None else prices, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="behavior-summary")
    def behavior_summary(self, request, pk=None):
        company = self.get_object()
        start, end = parse_date_range(request)
        if start is None:
            start = StockPrice.objects.filter(company=company).order_by("date").values_list(
                "date", flat=True
            ).first()
            if start is None:
                from django.utils import timezone

                start = timezone.localdate()
        return Response(company_behavior_summary(company, start, end))

    @action(detail=False, methods=["get"])
    def compare(self, request):
        raw_ids = request.query_params.get("ids", "")
        ids = list(dict.fromkeys(value.strip() for value in raw_ids.split(",") if value.strip()))
        if not 2 <= len(ids) <= 10:
            raise serializers.ValidationError(
                {"ids": "Provide between 2 and 10 comma-separated company IDs."}
            )
        if any(not value.isdecimal() for value in ids):
            raise serializers.ValidationError(
                {"ids": "Company IDs must be positive integers."}
            )
        companies = list(Company.objects.filter(id__in=ids))
        if len(companies) != len(ids):
            raise serializers.ValidationError(
                {"ids": "One or more company IDs do not exist."}
            )
        start, end = parse_date_range(request)
        if start is None:
            start = StockPrice.objects.filter(company__in=companies).order_by(
                "date"
            ).values_list("date", flat=True).first()
        if start is None:
            from django.utils import timezone

            start = timezone.localdate()
        return Response(
            {
                "period": {"from": start.isoformat(), "to": end.isoformat()},
                "companies": [
                    company_behavior_summary(company, start, end)
                    for company in companies
                ],
            }
        )
