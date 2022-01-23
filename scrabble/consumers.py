import json

from asgiref.sync import async_to_sync, sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from django.contrib.auth.models import User

from scrabble.models import Room


class PlayerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = 'room_%s' % self.room_id

        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        user = self.scope["user"]
        if not await (user.is_authenticated and sync_to_async(room_instance.join)(user)):
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        if await sync_to_async(room_instance.is_full)():
            if await sync_to_async(room_instance.is_in_progress)():
                await self.send_letters_for_player()
            else:
                await self.send_new_letters()
            await self.send_board()

    async def disconnect(self, close_code):
        room_instance = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        await sync_to_async(room_instance.leave)(self.scope["user"])

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        action = text_data_json['action']

        if action == "request_letters":
            await self.send_new_letters()

    async def set_letters(self, event):
        target = event['user_id']
        if not target == self.scope["user"].id:
            return

        await self.send(text_data=json.dumps({
            'operation': event['operation'],
            'letters': event['letters']
        }))

    async def set_board(self, event):
        await self.send(text_data=json.dumps({
            'operation': event['operation'],
            'board': event['board']
        }))

    # Receive message from room group
    async def action(self, event):
        message = event['action']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    async def send_board(self):
        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        board = await sync_to_async(room_instance.get_board)()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'set_board',
                'operation': 'set_board',
                'board': board
            }
        )

    async def send_new_letters(self):
        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        letters = await sync_to_async(room_instance.pass_new_letters)()
        p1_id = await sync_to_async(room_instance.get_player_1_id)()
        p2_id = await sync_to_async(room_instance.get_player_2_id)()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'set_letters',
                'operation': 'set_letters',
                'user_id': p1_id,
                'letters': letters['player_1']
            }
        )
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'set_letters',
                'operation': 'set_letters',
                'user_id': p2_id,
                'letters': letters['player_2']
            }
        )

    async def send_letters_for_player(self):
        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        user: User = self.scope["user"]
        letters = await sync_to_async(room_instance.get_letters_for_player)(user)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'set_letters',
                'operation': 'set_letters',
                'user_id': user.id,
                'letters': letters
            }
        )
