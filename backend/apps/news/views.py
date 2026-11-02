from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.news.services.categorization import categorize_article
from common.events import broadcast_on_commit
from common.permissions import IsAnalystOrAdmin
from .models import NewsArticle, NewsCompanyTag, NewsCorrection
from .serializers import (
    NewsArticleSerializer,
    NewsCorrectionRequestSerializer,
    NewsCorrectionSerializer,
)


class NewsArticleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NewsArticleSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["headline", "body", "source"]
    ordering_fields = ["published_at", "collected_at", "source"]
    filterset_fields = ["source"]

    def get_queryset(self):
        queryset = NewsArticle.objects.prefetch_related(
            "company_tags__company"
        )
        company_id = self.request.query_params.get("company_id")
        if company_id:
            if not company_id.isdecimal():
                raise serializers.ValidationError(
                    {"company_id": "Company ID must be a positive integer."}
                )
            queryset = queryset.filter(company_tags__company_id=company_id)
        return queryset.distinct()

    def get_permissions(self):
        if self.action in {"recategorize", "classify"}:
            return [IsAnalystOrAdmin()]
        return [permission() for permission in self.permission_classes]

    @action(detail=True, methods=["post"], permission_classes=[IsAnalystOrAdmin])
    def recategorize(self, request, pk=None):
        article = self.get_object()
        serializer = NewsCorrectionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        corrected_tags = serializer.validated_data["tags"]
        with transaction.atomic():
            previous = list(
                article.company_tags.select_related("company")
                .order_by("company__symbol")
            )
            previous_snapshot = [
                {
                    "company_id": tag.company_id,
                    "symbol": tag.company.symbol,
                    "confidence_score": str(tag.confidence_score),
                    "method": tag.method,
                }
                for tag in previous
            ]
            next_snapshot = [
                {
                    "company_id": row["company"].pk,
                    "symbol": row["company"].symbol,
                    "confidence_score": str(row["confidence_score"]),
                    "method": NewsCompanyTag.Method.ANALYST,
                }
                for row in corrected_tags
            ]
            NewsCorrection.objects.create(
                article=article,
                corrected_by=request.user,
                previous_tags=previous_snapshot,
                corrected_tags=next_snapshot,
                note=serializer.validated_data["note"],
            )
            NewsCompanyTag.objects.filter(article=article).delete()
            NewsCompanyTag.objects.bulk_create(
                [
                    NewsCompanyTag(
                        article=article,
                        company=row["company"],
                        confidence_score=row["confidence_score"],
                        method=NewsCompanyTag.Method.ANALYST,
                    )
                    for row in corrected_tags
                ]
            )
            broadcast_on_commit(
                "news.categorization.updated",
                {"article_id": article.pk, "tags": next_snapshot},
            )
        article.refresh_from_db()
        return Response(self.get_serializer(article).data)

    @action(detail=True, methods=["get"], url_path="corrections")
    def corrections(self, request, pk=None):
        article = self.get_object()
        corrections = NewsCorrection.objects.filter(article=article).select_related(
            "corrected_by"
        )
        page = self.paginate_queryset(corrections)
        serializer = NewsCorrectionSerializer(
            page if page is not None else corrections, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def classify(self, request, pk=None):
        article = self.get_object()
        categorize_article(article)
        article.refresh_from_db()
        return Response(self.get_serializer(article).data)
