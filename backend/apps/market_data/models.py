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
    change_amount = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True
    )
    change_percent = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    volume = models.PositiveBigIntegerField()
    source = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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


class MarketSnapshot(models.Model):
    source = models.CharField(max_length=64, default="nepsealpha")
    date = models.DateField()
    as_of = models.DateTimeField()
    market_open = models.BooleanField(null=True, blank=True)
    index_value = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True
    )
    index_change_percent = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    previous_close = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True
    )
    turnover = models.DecimalField(
        max_digits=24, decimal_places=4, null=True, blank=True
    )
    traded_volume = models.DecimalField(
        max_digits=24, decimal_places=4, null=True, blank=True
    )
    transaction_count = models.PositiveBigIntegerField(null=True, blank=True)
    scrips_traded = models.PositiveIntegerField(null=True, blank=True)
    float_market_cap = models.DecimalField(
        max_digits=24, decimal_places=4, null=True, blank=True
    )
    market_cap = models.DecimalField(
        max_digits=24, decimal_places=4, null=True, blank=True
    )
    advancers = models.PositiveIntegerField(null=True, blank=True)
    decliners = models.PositiveIntegerField(null=True, blank=True)
    unchanged = models.PositiveIntegerField(null=True, blank=True)
    top_gainers = models.JSONField(default=list, blank=True)
    top_losers = models.JSONField(default=list, blank=True)
    top_traded = models.JSONField(default=list, blank=True)
    technical_indicators = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "date"], name="unique_market_snapshot_source_date"
            )
        ]

    def __str__(self):
        return f"{self.source} market snapshot {self.date}"


class MarketIndexSnapshot(models.Model):
    source = models.CharField(max_length=64, default="nepsealpha")
    date = models.DateField()
    symbol = models.CharField(max_length=32)
    name = models.CharField(max_length=128)
    is_sector = models.BooleanField(default=False)
    open_value = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True
    )
    high_value = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True
    )
    low_value = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True
    )
    close_value = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True
    )
    change_percent = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    volume = models.DecimalField(
        max_digits=24, decimal_places=4, null=True, blank=True
    )
    turnover = models.DecimalField(
        max_digits=24, decimal_places=4, null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["symbol"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "date", "symbol"],
                name="unique_market_index_source_date_symbol",
            )
        ]

    def __str__(self):
        return f"{self.symbol} {self.date}"


class MarketStockSnapshot(models.Model):
    source = models.CharField(max_length=64, default="nepsealpha")
    date = models.DateField()
    symbol = models.CharField(max_length=32)
    instrument_type = models.CharField(max_length=32, blank=True)
    open_price = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True
    )
    high_price = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True
    )
    low_price = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True
    )
    close_price = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True
    )
    change_amount = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True
    )
    change_percent = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    turnover = models.DecimalField(
        max_digits=24, decimal_places=4, null=True, blank=True
    )
    volume = models.DecimalField(
        max_digits=24, decimal_places=4, null=True, blank=True
    )

    class Meta:
        ordering = ["-turnover", "symbol"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "date", "symbol"],
                name="unique_market_stock_source_date_symbol",
            )
        ]
        indexes = [models.Index(fields=["date", "-turnover"])]

    def __str__(self):
        return f"{self.symbol} {self.date}"


class MarketIndexHistory(models.Model):
    source = models.CharField(max_length=64, default="nepsealpha")
    symbol = models.CharField(max_length=32, default="NEPSE")
    observed_at = models.DateTimeField()
    value = models.DecimalField(max_digits=16, decimal_places=4)

    class Meta:
        ordering = ["observed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "symbol", "observed_at"],
                name="unique_market_index_history_point",
            )
        ]
        indexes = [models.Index(fields=["symbol", "-observed_at"])]

    def __str__(self):
        return f"{self.symbol} {self.observed_at}"
