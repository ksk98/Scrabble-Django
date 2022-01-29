import json
import math
from functools import cmp_to_key

import scrabble.algorithm as algorithms
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
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

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        if await sync_to_async(room_instance.is_full)():
            if await sync_to_async(room_instance.is_in_progress)():
                await self.send_letters_and_turn_for_player()
            else:
                await sync_to_async(room_instance.set_in_progress)(True)
                await self.send_new_letters()
                await self.start_game()
            await self.send_board()

    async def disconnect(self, close_code):
        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        await sync_to_async(room_instance.leave)(self.scope["user"])

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        if await sync_to_async(room_instance.is_empty)():
            await sync_to_async(room_instance.delete)()

    async def receive(self, text_data):
        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        user = self.scope["user"]
        text_data_json = json.loads(text_data)
        action = text_data_json['action']

        if action == "request_letters":
            await self.send_new_letters()
        elif action == "accept":
            if not await sync_to_async(room_instance.is_turn_of_player)(user):
                return

            if await self.verify_word_and_update_board(text_data_json['data']):
                # TODO: calculate and add points
                await self.send_board()
                await self.switch_turn()
        elif action == "pass":
            if not await sync_to_async(room_instance.is_turn_of_player)(user):
                return

            await self.switch_turn()

    async def verify_word_and_update_board(self, new_letters):
        def compare(a, b):
            if a["x"] < b["x"] or a["y"] < b["y"]:
                return -1
            elif a["x"] == b["x"] and a["y"] == b["y"]:
                return 0
            else:
                return 1

        new_letters = sorted(new_letters, key=cmp_to_key(compare))
        print(new_letters)

        # validate if new letters are in straight line, what is the direction of the word
        word_direction_axis = "x"
        if len(new_letters) > 1:
            print(str(new_letters[0]["x"]) + " " + str(new_letters[1]["x"]))
            print(str(new_letters[0]["y"]) + " " + str(new_letters[1]["y"]))
            if new_letters[0]["x"] == new_letters[1]["x"]:
                word_direction_axis = "x"
            elif new_letters[0]["y"] == new_letters[1]["y"]:
                word_direction_axis = "y"
            else:
                return False

            value = new_letters[0][word_direction_axis]
            for letter in new_letters:
                if letter[word_direction_axis] != value:
                    return False

        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        board = await self.array_of_board(room_instance.board, room_instance.size)

        print("straight line ok, axis: " + word_direction_axis)
        # if board is empty the new word has to touch the middle tile
        if room_instance.board == len(room_instance.board) * room_instance.board[0]:
            middle = math.floor(room_instance.size/2)   # 7 for 15x15

            goes_trough_middle = False
            for letter in new_letters:
                if letter["x"] == middle and letter["y"] == middle:
                    goes_trough_middle = True
                    break

            if not goes_trough_middle:
                return False

        print("middle tile ok")
        # add letters to new board, verify if new letters don't overlap with existing letters
        for letter in new_letters:
            if board[letter["y"]][letter["x"]] != " ":
                return False

            board[letter["y"]][letter["x"]] = letter["value"]

        print("overlap ok")
        # validate every new word created by the change
        if not algorithms.creates_valid_word(
                board, new_letters[0]["x"], new_letters[0]["y"], word_direction_axis == "x"):
            return False

        print("first word ok")

        for letter in new_letters:
            if not algorithms.creates_valid_word(board, letter["x"], letter["y"], word_direction_axis != "x"):
                return False
            print("word ok")

        await sync_to_async(room_instance.set_board)(algorithms.board_to_string(board))
        print(algorithms.board_to_string(board))
        return True

    @staticmethod
    async def array_of_board(board_string: str, border_size):
        out = []

        for i in range(border_size):
            out.append([])
            for j in range(border_size):
                out[i].append(board_string[(i*border_size) + j])

        return out

    async def set_letters(self, event):
        target = event['user_id']
        if not target == self.scope["user"].id:
            return

        await self.send(text_data=json.dumps({
            'operation': event['operation'],
            'letters': event['letters'],
            'turn': event['turn']
        }))

    async def set_board(self, event):
        await self.send(text_data=json.dumps({
            'operation': event['operation'],
            'board': event['board']
        }))

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

    async def switch_turn(self):
        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        await sync_to_async(room_instance.toggle_turn)()
        await self.send_new_letters()

    async def start_game(self):
        await self.send(text_data=json.dumps({
            'operation': 'game_started'
        }))

    async def stop_game(self):
        await self.send(text_data=json.dumps({
            'operation': 'game_stopped'
        }))

    async def send_new_letters(self):
        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        letters = await sync_to_async(room_instance.pass_new_letters)()
        p1 = await sync_to_async(room_instance.get_player_1)()
        p1_id = await sync_to_async(room_instance.get_player_1_id)()
        p1_turn = await sync_to_async(room_instance.get_player_turn)(p1)
        p2 = await sync_to_async(room_instance.get_player_2)()
        p2_id = await sync_to_async(room_instance.get_player_2_id)()
        p2_turn = await sync_to_async(room_instance.get_player_turn)(p2)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'set_letters',
                'operation': 'set_letters',
                'user_id': p1_id,
                'letters': letters['player_1'],
                'turn': p1_turn
            }
        )
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'set_letters',
                'operation': 'set_letters',
                'user_id': p2_id,
                'letters': letters['player_2'],
                'turn': p2_turn
            }
        )

    async def send_letters_and_turn_for_player(self):
        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        user: User = self.scope["user"]
        letters = await sync_to_async(room_instance.get_letters_for_player)(user)
        turn = await sync_to_async(room_instance.get_player_turn)(user)
        game_started = room_instance.in_progress

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'set_letters',
                'operation': 'set_letters',
                'user_id': user.id,
                'letters': letters,
                'turn': turn,
                'game_started': game_started
            }
        )
