from django.conf import settings
from django.db import models


class CrawlSource(models.Model):
    name = models.CharField(max_length=128, unique=True)
    key = models.SlugField(max_length=64, unique=True)
    base_url = models.URLField(max_length=512)
    listing_url = models.URLField(max_length=1024, blank=True)
    article_url_pattern = models.CharField(max_length=512, blank=True)
    enabled = models.BooleanField(default=False)
    request_interval_seconds = models.PositiveSmallIntegerField(default=10)
    max_articles_per_run = models.PositiveSmallIntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CrawlRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(
        CrawlSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="runs",
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crawl_runs",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True
    )
    task_id = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    requests_made = models.PositiveIntegerField(default=0)
    articles_created = models.PositiveIntegerField(default=0)
    articles_duplicates = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["source", "-created_at"])]

    def __str__(self):
        return f"{self.source or 'Unknown source'}: {self.status}"
