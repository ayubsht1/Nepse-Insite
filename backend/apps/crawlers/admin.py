from django.contrib import admin

from .models import CrawlRun, CrawlSource


@admin.register(CrawlSource)
class CrawlSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "key", "enabled", "request_interval_seconds"]
    list_filter = ["enabled"]
    search_fields = ["name", "key", "base_url"]


@admin.register(CrawlRun)
class CrawlRunAdmin(admin.ModelAdmin):
    list_display = ["id", "source", "status", "articles_created", "created_at"]
    list_filter = ["status", "source"]
    readonly_fields = [field.name for field in CrawlRun._meta.fields]
