from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers

from apps.companies.models import Company
from .models import UserProfile, Watchlist

User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "email", "role"]

    def get_role(self, user):
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
        result["role"] = profile_role or UserProfile.Role.VIEWER
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


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "email", "password"]
        read_only_fields = ["id"]

    def validate_password(self, password):
        password_validation.validate_password(password)
        return password

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": UserProfile.Role.VIEWER}
        )
        return user
