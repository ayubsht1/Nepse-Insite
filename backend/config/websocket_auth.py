from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _user_from_access_token(token):
    access_token = AccessToken(token)
    user_id = access_token[settings.SIMPLE_JWT.get("USER_ID_CLAIM", "user_id")]
    user_field = settings.SIMPLE_JWT.get("USER_ID_FIELD", "id")
    return get_user_model().objects.get(**{user_field: user_id}, is_active=True)


class JwtQueryAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        query = parse_qs(scope.get("query_string", b"").decode("utf-8"))
        tokens = query.get("token", [])
        if tokens:
            try:
                scope["user"] = await _user_from_access_token(tokens[0])
            except (TokenError, get_user_model().DoesNotExist, KeyError, ValueError):
                scope["user"] = AnonymousUser()
        return await self.app(scope, receive, send)
