import logging
from datetime import datetime, timezone

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

logger = logging.getLogger(__name__)


def broadcast_update(event, data):
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        "updates",
        {
            "type": "broadcast.update",
            "payload": {
                "event": event,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "data": data,
            },
        },
    )


def broadcast_on_commit(event, data):
    transaction.on_commit(
        lambda: _broadcast_safely(event, data),
        robust=True,
    )


def _broadcast_safely(event, data):
    try:
        broadcast_update(event, data)
    except Exception:
        logger.exception("Could not broadcast event %s", event)
