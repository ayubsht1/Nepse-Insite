from django.conf import settings
from django.db import models
from django.db.models import Q


class NewsArticle(models.Model):
    url = models.URLField(max_length=2048, unique=True)
    source = models.CharField(max_length=128)
    headline = models.CharField(max_length=512)
    body = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    collected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-collected_at"]
        indexes = [
            models.Index(fields=["-published_at"]),
            models.Index(fields=["source", "-collected_at"]),
        ]

    def __str__(self):
        return self.headline


class NewsCompanyTag(models.Model):
    class Method(models.TextChoices):
        RULE = "rule", "Rule-based"
        ANALYST = "analyst", "Analyst"

    article = models.ForeignKey(
        NewsArticle, on_delete=models.CASCADE, related_name="company_tags"
    )
    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, related_name="news_tags"
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3)
    method = models.CharField(max_length=16, choices=Method.choices)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company__symbol"]
        constraints = [
            models.UniqueConstraint(
                fields=["article", "company"], name="unique_news_article_company"
            ),
            models.CheckConstraint(
                condition=Q(confidence_score__gte=0, confidence_score__lte=1),
                name="news_tag_confidence_between_zero_one",
            ),
        ]
        indexes = [models.Index(fields=["company", "article"])]


class NewsCorrection(models.Model):
    article = models.ForeignKey(
        NewsArticle, on_delete=models.CASCADE, related_name="corrections"
    )
    corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="news_corrections",
    )
    previous_tags = models.JSONField(default=list)
    corrected_tags = models.JSONField(default=list)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["article", "-created_at"])]

    def __str__(self):
        return f"Correction for article {self.article_id} by {self.corrected_by}"
