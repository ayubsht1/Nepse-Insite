from django.contrib.auth import get_user_model

from apps.companies.models import Company
from apps.users.models import UserProfile

User = get_user_model()


def create_company(**overrides):
    values = {
        "symbol": "NABIL",
        "name": "Nabil Bank Limited",
        "aliases": ["Nabil Bank"],
        "sector": "Commercial Banks",
    }
    values.update(overrides)
    return Company.objects.create(**values)


def create_user(role=UserProfile.Role.VIEWER, **overrides):
    username = overrides.pop("username", f"{role}-user")
    user = User.objects.create_user(username=username, password="Strong-test-pass-934")
    UserProfile.objects.update_or_create(user=user, defaults={"role": role})
    return user
