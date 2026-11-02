import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from config.routing import websocket_urlpatterns
from config.websocket_auth import JwtWebSocketAuthMiddleware

http_application = django_asgi_app
if settings.DEBUG:
    http_application = ASGIStaticFilesHandler(http_application)

application = ProtocolTypeRouter(
    {
        "http": http_application,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                JwtWebSocketAuthMiddleware(URLRouter(websocket_urlpatterns))
            )
        ),
    }
)
