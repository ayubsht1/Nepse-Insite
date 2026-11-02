from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers

from apps.companies.models import Company
from .models import UserProfile, Watchlist

User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]

    def get_role(self, user):
        if user.is_superuser:
            return UserProfile.Role.ADMIN
        return (
            UserProfile.objects.filter(user_id=user.pk)
            .values_list("role", flat=True)
            .first()
            or UserProfile.Role.VIEWER
        )


class AdminUserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(
        choices=UserProfile.Role.choices, required=False, write_only=True
    )
    password = serializers.CharField(
        write_only=True, required=False, min_length=8, trim_whitespace=False
    )

    class Meta:
        model = User
        fields = ["id", "username", "email", "is_active", "role", "password"]
        read_only_fields = ["id"]

    def validate_password(self, password):
        password_validation.validate_password(password)
        return password

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError(
                {"password": "A password is required when creating a user."}
            )
        if (
            self.instance
            and self.instance.is_superuser
            and attrs.get("role", UserProfile.Role.ADMIN) != UserProfile.Role.ADMIN
        ):
            raise serializers.ValidationError(
                {"role": "A superuser must retain the admin role."}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        role = validated_data.pop("role", UserProfile.Role.VIEWER)
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        UserProfile.objects.update_or_create(user=user, defaults={"role": role})
        return user

    def update(self, instance, validated_data):
        role = validated_data.pop("role", None)
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        if role is not None:
            UserProfile.objects.update_or_create(
                user=instance, defaults={"role": role}
            )
        return instance

    def to_representation(self, instance):
        result = super().to_representation(instance)
        profile_role = (
            UserProfile.objects.filter(user_id=instance.pk)
            .values_list("role", flat=True)
            .first()
        )
        result["role"] = (
            UserProfile.Role.ADMIN
            if instance.is_superuser
            else profile_role
            if profile_role
            else UserProfile.Role.VIEWER
        )
        return result


class WatchlistSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.filter(is_active=True)
    )
    symbol = serializers.CharField(source="company.symbol", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Watchlist
        fields = ["id", "company", "symbol", "company_name", "created_at"]
        read_only_fields = ["id", "created_at"]
