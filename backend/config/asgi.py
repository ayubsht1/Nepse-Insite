import logging
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

from django.core.asgi import get_asgi_application
from redis.exceptions import RedisError

django_asgi_app = get_asgi_application()

from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from config.routing import websocket_urlpatterns
from config.websocket_auth import JwtWebSocketAuthMiddleware

logger = logging.getLogger(__name__)

http_application = django_asgi_app
if settings.DEBUG:
    http_application = ASGIStaticFilesHandler(http_application)


class RedisErrorLoggingApplication:
    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        try:
            await self.application(scope, receive, send)
        except RedisError:
            logger.exception("Redis operation failed in the ASGI application")
            raise


application = RedisErrorLoggingApplication(
    ProtocolTypeRouter(
        {
            "http": http_application,
            "websocket": AllowedHostsOriginValidator(
                AuthMiddlewareStack(
                    JwtWebSocketAuthMiddleware(URLRouter(websocket_urlpatterns))
                )
            ),
        }
    )
)
