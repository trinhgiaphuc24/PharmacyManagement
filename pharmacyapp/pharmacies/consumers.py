import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = self.scope.get("query_string", b"").decode()
        
        for param in query_string.split("&"):
            if param.startswith("user_id="):
                user_id = param.split("=", 1)[1]
                break
        
        self.user_group_name = f"user_{user_id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()

    async def order_created(self, event):
        await self.send(text_data=json.dumps(event))

    async def order_status_update(self, event):
        await self.send(text_data=json.dumps(event))

class StaffNotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "staff_notifications"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def new_order_notification(self, event):
        await self.send(text_data=json.dumps(event))