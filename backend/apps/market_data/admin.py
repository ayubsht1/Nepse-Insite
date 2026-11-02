from django.contrib import admin

from .models import FloorsheetTransaction, StockPrice


@admin.register(StockPrice)
class StockPriceAdmin(admin.ModelAdmin):
    list_display = ["company", "date", "close_price", "volume", "source"]
    list_filter = ["date", "source"]
    search_fields = ["company__symbol", "company__name"]


@admin.register(FloorsheetTransaction)
class FloorsheetTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "company",
        "trade_date",
        "price",
        "quantity",
        "buyer_broker",
        "seller_broker",
    ]
    list_filter = ["trade_date", "source"]
    search_fields = ["company__symbol", "transaction_id", "source_record_id"]
