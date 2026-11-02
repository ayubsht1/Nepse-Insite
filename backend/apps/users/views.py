from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from common.permissions import IsAdminRole
from common.permissions import user_role
from .models import Watchlist
from .serializers import (
    AdminUserSerializer,
    RegistrationSerializer,
    UserSummarySerializer,
    WatchlistSerializer,
)

User = get_user_model()
REFRESH_COOKIE_NAME = "nepse_refresh"
REFRESH_COOKIE_PATH = "/api/auth/"


def _set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response):
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        samesite="Lax",
    )


class CsrfCookieView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, _request):
        return Response(status=status.HTTP_204_NO_CONTENT)


class JwtLoginView(TokenObtainPairView):
    @method_decorator(csrf_protect)
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            refresh = response.data.pop("refresh")
            _set_refresh_cookie(response, refresh)
        return response


class JwtRefreshView(TokenRefreshView):
    @method_decorator(csrf_protect)
    def post(self, request, *args, **kwargs):
        token = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not token:
            raise ValidationError({"refresh": "A refresh cookie is required."})
        serializer = TokenRefreshSerializer(data={"refresh": token})
        serializer.is_valid(raise_exception=True)
        response = Response(serializer.validated_data)
        rotated_refresh = response.data.pop("refresh", None)
        if rotated_refresh:
            _set_refresh_cookie(response, rotated_refresh)
        return response


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSummarySerializer(request.user).data)


class RegistrationView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(csrf_protect)
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSummarySerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect)
    def post(self, request):
        token_value = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not token_value:
            raise ValidationError({"refresh": "A refresh cookie is required."})
        try:
            token = RefreshToken(token_value)
            token_user_id = token.get(
                "user_id",
                None,
            )
            if str(token_user_id) != str(request.user.pk):
                raise ValidationError(
                    {"refresh": "The refresh cookie does not belong to this user."}
                )
            token.blacklist()
        except TokenError as exc:
            raise ValidationError({"refresh": "The refresh cookie is invalid."}) from exc
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response


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
