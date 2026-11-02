from rest_framework import serializers

from apps.companies.models import Company
from apps.companies.serializers import CompanySerializer
from .models import NewsArticle, NewsCompanyTag, NewsCorrection


class NewsCompanyTagSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)

    class Meta:
        model = NewsCompanyTag
        fields = ["company", "confidence_score", "method", "updated_at"]


class NewsArticleSerializer(serializers.ModelSerializer):
    company_tags = NewsCompanyTagSerializer(many=True, read_only=True)

    class Meta:
        model = NewsArticle
        fields = [
            "id",
            "url",
            "source",
            "headline",
            "body",
            "published_at",
            "collected_at",
            "company_tags",
        ]


class CorrectionTagSerializer(serializers.Serializer):
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.filter(is_active=True), source="company"
    )
    confidence_score = serializers.DecimalField(
        max_digits=4, decimal_places=3, min_value=0, max_value=1
    )


class NewsCorrectionRequestSerializer(serializers.Serializer):
    tags = CorrectionTagSerializer(many=True, allow_empty=True, max_length=100)
    note = serializers.CharField(min_length=3, max_length=2000)

    def validate_tags(self, tags):
        company_ids = [tag["company"].pk for tag in tags]
        if len(company_ids) != len(set(company_ids)):
            raise serializers.ValidationError("Each company may appear only once.")
        return tags


class NewsCorrectionSerializer(serializers.ModelSerializer):
    corrected_by = serializers.CharField(source="corrected_by.username")

    class Meta:
        model = NewsCorrection
        fields = [
            "id",
            "corrected_by",
            "previous_tags",
            "corrected_tags",
            "note",
            "created_at",
        ]
