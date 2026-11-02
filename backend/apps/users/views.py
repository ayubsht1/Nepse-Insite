from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdminRole
from common.permissions import user_role
from .models import Watchlist
from .serializers import AdminUserSerializer, UserSummarySerializer, WatchlistSerializer

User = get_user_model()


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSummarySerializer(request.user).data)


class WatchlistViewSet(viewsets.ModelViewSet):
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        queryset = Watchlist.objects.select_related("company", "user")
        if user_role(self.request.user) == "admin":
            requested_user = self.request.query_params.get("user_id")
            if requested_user and not requested_user.isdecimal():
                from rest_framework.exceptions import ValidationError

                raise ValidationError(
                    {"user_id": "User ID must be a positive integer."}
                )
            return queryset.filter(user_id=requested_user) if requested_user else queryset
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        if (
            instance.user_id != self.request.user.id
            and user_role(self.request.user) != "admin"
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You may only remove items from your own watchlist.")
        instance.delete()


class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("profile").all().order_by("id")
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminRole]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    @action(detail=True, methods=["post"])
    def set_role(self, request, pk=None):
        user = self.get_object()
        serializer = AdminUserSerializer(
            user, data={"role": request.data.get("role")}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AdminUserSerializer(user).data)
