import re
from urllib.parse import urlparse

from rest_framework import serializers

from .models import CrawlRun, CrawlSource


class CrawlSourceSerializer(serializers.ModelSerializer):
    request_interval_seconds = serializers.IntegerField(
        min_value=1, max_value=3600
    )
    max_listing_pages = serializers.IntegerField(min_value=1, max_value=100)
    max_articles_per_run = serializers.IntegerField(min_value=1, max_value=500)

    class Meta:
        model = CrawlSource
        fields = [
            "id",
            "name",
            "key",
            "base_url",
            "listing_url",
            "listing_pagination",
            "article_url_pattern",
            "enabled",
            "request_interval_seconds",
            "max_listing_pages",
            "max_articles_per_run",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        base_url = attrs.get("base_url", getattr(self.instance, "base_url", ""))
        listing_url = attrs.get("listing_url", getattr(self.instance, "listing_url", ""))
        listing_pagination = attrs.get(
            "listing_pagination",
            getattr(self.instance, "listing_pagination", ""),
        )
        enabled = attrs.get("enabled", getattr(self.instance, "enabled", False))
        pattern = attrs.get(
            "article_url_pattern", getattr(self.instance, "article_url_pattern", "")
        )
        base = urlparse(base_url)
        if base.scheme not in {"http", "https"} or not base.hostname:
            raise serializers.ValidationError(
                {"base_url": "A valid HTTP or HTTPS base URL is required."}
            )
        if listing_url:
            listing = urlparse(listing_url)
            if (
                listing.scheme not in {"http", "https"}
                or listing.hostname != base.hostname
            ):
                raise serializers.ValidationError(
                    {"listing_url": "Listing URL must use the source's host."}
                )
        if listing_pagination:
            if listing_pagination.count("{page}") != 1:
                raise serializers.ValidationError(
                    {
                        "listing_pagination": (
                            "Pagination URL must contain exactly one {page} placeholder."
                        )
                    }
                )
            try:
                pagination = urlparse(listing_pagination.format(page=1))
            except (KeyError, ValueError) as exc:
                raise serializers.ValidationError(
                    {"listing_pagination": "Invalid pagination URL template."}
                ) from exc
            if (
                pagination.scheme not in {"http", "https"}
                or pagination.hostname != base.hostname
            ):
                raise serializers.ValidationError(
                    {"listing_pagination": "Pagination URL must use the source's host."}
                )
        if enabled and (not listing_url or not pattern):
            raise serializers.ValidationError(
                "Enabled sources require a listing URL and article URL pattern."
            )
        if pattern:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise serializers.ValidationError(
                    {"article_url_pattern": f"Invalid regular expression: {exc}"}
                ) from exc
        return attrs


class CrawlRunSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)
    triggered_by = serializers.CharField(
        source="triggered_by.username", read_only=True, allow_null=True
    )

    class Meta:
        model = CrawlRun
        fields = [
            "id",
            "source",
            "source_name",
            "triggered_by",
            "status",
            "task_id",
            "started_at",
            "finished_at",
            "requests_made",
            "articles_created",
            "articles_duplicates",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields
