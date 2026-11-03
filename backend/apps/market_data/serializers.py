from decimal import Decimal

from rest_framework import serializers

from apps.companies.models import Company
from .models import (
    FloorsheetTransaction,
    MarketIndexSnapshot,
    MarketSnapshot,
    MarketStockSnapshot,
    StockPrice,
)


class MarketSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketSnapshot
        fields = [
            "source",
            "date",
            "as_of",
            "market_open",
            "index_value",
            "index_change_percent",
            "previous_close",
            "turnover",
            "traded_volume",
            "transaction_count",
            "scrips_traded",
            "float_market_cap",
            "market_cap",
            "advancers",
            "decliners",
            "unchanged",
            "top_gainers",
            "top_losers",
            "top_traded",
            "technical_indicators",
            "updated_at",
        ]


class MarketIndexSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketIndexSnapshot
        fields = [
            "symbol",
            "name",
            "is_sector",
            "open_value",
            "high_value",
            "low_value",
            "close_value",
            "change_percent",
            "volume",
            "turnover",
        ]


class MarketStockSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketStockSnapshot
        fields = [
            "source",
            "date",
            "symbol",
            "instrument_type",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "change_amount",
            "change_percent",
            "turnover",
            "volume",
        ]


class StockPriceSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="company.symbol", read_only=True)

    class Meta:
        model = StockPrice
        fields = [
            "id",
            "company",
            "symbol",
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "change_amount",
            "change_percent",
            "volume",
            "source",
            "updated_at",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        low = attrs.get("low_price", getattr(self.instance, "low_price", None))
        high = attrs.get("high_price", getattr(self.instance, "high_price", None))
        open_price = attrs.get("open_price", getattr(self.instance, "open_price", None))
        close_price = attrs.get("close_price", getattr(self.instance, "close_price", None))
        if low is not None and high is not None and low > high:
            raise serializers.ValidationError(
                {"high_price": "High price must be greater than or equal to low."}
            )
        for field, value in (("open_price", open_price), ("close_price", close_price)):
            if low is not None and high is not None and value is not None:
                if not low <= value <= high:
                    raise serializers.ValidationError(
                        {field: "Open and close prices must be within the daily range."}
                    )
        return attrs


class FloorsheetTransactionSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="company.symbol", read_only=True)

    class Meta:
        model = FloorsheetTransaction
        fields = [
            "id",
            "company",
            "symbol",
            "trade_date",
            "trade_time",
            "transaction_id",
            "price",
            "quantity",
            "buyer_broker",
            "seller_broker",
            "source",
            "source_record_id",
        ]
        read_only_fields = ["id"]


class PriceImportRowSerializer(serializers.Serializer):
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.filter(is_active=True), source="company"
    )
    date = serializers.DateField()
    open_price = serializers.DecimalField(max_digits=16, decimal_places=4)
    high_price = serializers.DecimalField(max_digits=16, decimal_places=4)
    low_price = serializers.DecimalField(max_digits=16, decimal_places=4)
    close_price = serializers.DecimalField(max_digits=16, decimal_places=4)
    change_amount = serializers.DecimalField(
        max_digits=16, decimal_places=4, required=False, allow_null=True
    )
    change_percent = serializers.DecimalField(
        max_digits=10, decimal_places=4, required=False, allow_null=True
    )
    volume = serializers.IntegerField(min_value=0)

    def validate(self, attrs):
        low, high = attrs["low_price"], attrs["high_price"]
        if (
            low > high
            or not low <= attrs["open_price"] <= high
            or not low <= attrs["close_price"] <= high
        ):
            raise serializers.ValidationError("Invalid daily OHLC price range.")
        return attrs


class PriceImportSerializer(serializers.Serializer):
    source = serializers.CharField(max_length=128)
    prices = PriceImportRowSerializer(many=True, allow_empty=False, max_length=5000)


class FloorsheetImportRowSerializer(serializers.Serializer):
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.filter(is_active=True), source="company"
    )
    trade_date = serializers.DateField()
    trade_time = serializers.TimeField(required=False, allow_null=True)
    transaction_id = serializers.CharField(
        required=False, allow_blank=True, max_length=128
    )
    price = serializers.DecimalField(
        max_digits=16, decimal_places=4, min_value=Decimal("0.0001")
    )
    quantity = serializers.IntegerField(min_value=1)
    buyer_broker = serializers.CharField(
        required=False, allow_blank=True, max_length=64
    )
    seller_broker = serializers.CharField(
        required=False, allow_blank=True, max_length=64
    )
    source_record_id = serializers.CharField(max_length=128)


class FloorsheetImportSerializer(serializers.Serializer):
    source = serializers.CharField(max_length=128)
    transactions = FloorsheetImportRowSerializer(
        many=True, allow_empty=False, max_length=10000
    )
