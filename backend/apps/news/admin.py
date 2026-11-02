from django.contrib import admin

from .models import NewsArticle, NewsCompanyTag, NewsCorrection


class NewsCompanyTagInline(admin.TabularInline):
    model = NewsCompanyTag
    extra = 0


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ["headline", "source", "published_at", "collected_at"]
    list_filter = ["source", "published_at"]
    search_fields = ["headline", "body", "url"]
    inlines = [NewsCompanyTagInline]


@admin.register(NewsCorrection)
class NewsCorrectionAdmin(admin.ModelAdmin):
    list_display = ["article", "corrected_by", "created_at"]
    readonly_fields = [
        "article",
        "corrected_by",
        "previous_tags",
        "corrected_tags",
        "note",
        "created_at",
    ]
