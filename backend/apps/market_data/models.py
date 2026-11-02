from django.db import models
from django.db.models import Q


class StockPrice(models.Model):
    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, related_name="prices"
    )
    date = models.DateField()
    open_price = models.DecimalField(max_digits=16, decimal_places=4)
    high_price = models.DecimalField(max_digits=16, decimal_places=4)
    low_price = models.DecimalField(max_digits=16, decimal_places=4)
    close_price = models.DecimalField(max_digits=16, decimal_places=4)
    volume = models.PositiveBigIntegerField()
    source = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "company__symbol"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "date"], name="unique_company_price_date"
            ),
            models.CheckConstraint(
                condition=Q(
                    open_price__gt=0,
                    high_price__gt=0,
                    low_price__gt=0,
                    close_price__gt=0,
                ),
                name="stock_prices_positive",
            ),
            models.CheckConstraint(
                condition=Q(high_price__gte=models.F("low_price")),
                name="stock_price_high_gte_low",
            ),
            models.CheckConstraint(
                condition=Q(volume__gte=0), name="stock_price_volume_nonnegative"
            ),
        ]
        indexes = [models.Index(fields=["company", "-date"])]

    def __str__(self):
        return f"{self.company.symbol} {self.date}"


class FloorsheetTransaction(models.Model):
    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, related_name="transactions"
    )
    trade_date = models.DateField()
    trade_time = models.TimeField(null=True, blank=True)
    transaction_id = models.CharField(max_length=128, blank=True)
    price = models.DecimalField(max_digits=16, decimal_places=4)
    quantity = models.PositiveBigIntegerField()
    buyer_broker = models.CharField(max_length=64, blank=True)
    seller_broker = models.CharField(max_length=64, blank=True)
    source = models.CharField(max_length=128)
    source_record_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-trade_date", "-trade_time", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gt=0), name="floorsheet_price_positive"
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0), name="floorsheet_quantity_positive"
            ),
            models.UniqueConstraint(
                fields=["source", "source_record_id"],
                condition=~Q(source_record_id=""),
                name="unique_floorsheet_source_record",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "-trade_date"]),
            models.Index(fields=["trade_date", "buyer_broker"]),
            models.Index(fields=["trade_date", "seller_broker"]),
        ]

    def __str__(self):
        return f"{self.company.symbol} {self.trade_date} x{self.quantity}"
