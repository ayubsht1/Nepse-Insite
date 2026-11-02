from rest_framework import serializers

from .models import Company


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "symbol",
            "name",
            "aliases",
            "sector",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_aliases(self, aliases):
        if not isinstance(aliases, list) or any(
            not isinstance(alias, str) or not alias.strip() for alias in aliases
        ):
            raise serializers.ValidationError(
                "Aliases must be a list of non-empty strings."
            )
        return list(dict.fromkeys(alias.strip() for alias in aliases))

    def validate_symbol(self, symbol):
        symbol = symbol.strip().upper()
        if not symbol:
            raise serializers.ValidationError("Symbol must not be empty.")
        return symbol

    def validate_name(self, name):
        name = name.strip()
        if not name:
            raise serializers.ValidationError("Name must not be empty.")
        return name
