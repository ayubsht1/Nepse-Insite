from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from config.asgi import application
from .factories import create_user


@override_settings(
    CHANNEL_LAYERS={
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
)
class WebSocketTests(TransactionTestCase):
    def test_authenticated_client_receives_update_envelope(self):
        user = create_user(username="socket-viewer")
        token = str(AccessToken.for_user(user))
        async_to_sync(self._assert_receives_event)(token)

    async def _assert_receives_event(self, token):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/updates/?token={token}",
            headers=[(b"origin", b"http://localhost")],
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await get_channel_layer().group_send(
            "updates",
            {
                "type": "broadcast.update",
                "payload": {
                    "event": "news.article.created",
                    "occurred_at": "2026-11-02T00:00:00+00:00",
                    "data": {"article_id": 12},
                },
            },
        )
        payload = await communicator.receive_json_from()
        self.assertEqual(payload["event"], "news.article.created")
        self.assertEqual(payload["data"]["article_id"], 12)
        await communicator.disconnect()

    def test_anonymous_client_is_rejected(self):
        async_to_sync(self._assert_anonymous_rejected)()

    async def _assert_anonymous_rejected(self):
        communicator = WebsocketCommunicator(
            application,
            "/ws/updates/",
            headers=[(b"origin", b"http://localhost")],
        )
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4401)
