from rest_framework.permissions import BasePermission, SAFE_METHODS


def user_role(user):
    from apps.users.models import UserProfile

    return (
        UserProfile.objects.filter(user_id=user.pk)
        .values_list("role", flat=True)
        .first()
        or UserProfile.Role.VIEWER
    )


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and user_role(request.user) == "admin"
        )


class IsAnalystOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and user_role(request.user) in {"admin", "analyst"}
        )


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return IsAdminRole().has_permission(request, view)
