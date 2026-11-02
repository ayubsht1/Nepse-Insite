from channels.generic.websocket import AsyncJsonWebsocketConsumer


class UpdatesConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return
        await self.channel_layer.group_add("updates", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.channel_layer is not None:
            await self.channel_layer.group_discard("updates", self.channel_name)

    async def broadcast_update(self, event):
        await self.send_json(event["payload"])
