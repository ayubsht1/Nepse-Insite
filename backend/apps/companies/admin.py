from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["symbol", "name", "sector", "is_active"]
    list_filter = ["is_active", "sector"]
    search_fields = ["symbol", "name"]
