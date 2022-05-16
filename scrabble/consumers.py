import json
import math
from functools import cmp_to_key

import scrabble.algorithm as algorithms
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User

from scrabble import profile_manager
from scrabble.models import Room, UserProfile


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
        else:
            if not room_instance.finished:
                await self.finish_game()

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
                await self.send_new_letters()
                await self.send_board()
                await self.switch_turn()
        elif action == "pass":
            if not await sync_to_async(room_instance.is_turn_of_player)(user):
                return

            await self.switch_turn(True)

    async def verify_word_and_update_board(self, new_letters):
        def compare(a, b):
            if a["x"] < b["x"] or a["y"] < b["y"]:
                return -1
            elif a["x"] == b["x"] and a["y"] == b["y"]:
                return 0
            else:
                return 1

        new_letters_sorted = sorted(new_letters, key=cmp_to_key(compare))
        if len(new_letters_sorted) == 0:
            return

        # validate if new letters are in straight line, what is the direction of the word
        word_direction_axis = "x"
        if len(new_letters_sorted) > 1:
            if new_letters_sorted[0]["x"] == new_letters_sorted[1]["x"]:
                word_direction_axis = "y"

                value = new_letters_sorted[0]["x"]
                for letter in new_letters_sorted:
                    if letter["x"] != value:
                        return False
            elif new_letters_sorted[0]["y"] == new_letters_sorted[1]["y"]:
                word_direction_axis = "x"

                value = new_letters_sorted[0]["y"]
                for letter in new_letters_sorted:
                    if letter["y"] != value:
                        return False
            else:
                return False

        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        board = await self.array_of_board(room_instance.board, room_instance.size)

        # all the letters should connect to at least one other letter
        # also check if the words is built on another word which is used later
        connected_to_other_word = False
        current_pos = algorithms.get_starting_pos_of_word(
            board, new_letters_sorted[0]["x"], new_letters_sorted[0]["y"], word_direction_axis == "x")
        print(current_pos)
        ind = 0
        if word_direction_axis == "x":
            while current_pos[0] < room_instance.size:
                if ind < len(new_letters_sorted) and \
                        current_pos[0] == new_letters_sorted[ind]["x"] and \
                        current_pos[1] == new_letters_sorted[ind]["y"]:
                    current_pos[0] += 1
                    ind += 1
                else:
                    if board[current_pos[1]][current_pos[0]] == " ":
                        if ind < len(new_letters_sorted):
                            return False
                        else:
                            break
                    else:
                        connected_to_other_word = True
                    current_pos[0] += 1
        else:
            while current_pos[1] < room_instance.size:
                if ind < len(new_letters_sorted) and \
                        current_pos[0] == new_letters_sorted[ind]["x"] and \
                        current_pos[1] == new_letters_sorted[ind]["y"]:
                    current_pos[1] += 1
                    ind += 1
                else:
                    if board[current_pos[1]][current_pos[0]] == " ":
                        if ind < len(new_letters_sorted):
                            return False
                        else:
                            break
                    else:
                        connected_to_other_word = True
                    current_pos[1] += 1

        # if board is empty the new word has to touch the middle tile
        board_empty = room_instance.board == len(room_instance.board) * room_instance.board[0]
        if board_empty:
            middle = math.floor(room_instance.size/2)   # 7 for 15x15

            goes_trough_middle = False
            for letter in new_letters_sorted:
                if letter["x"] == middle and letter["y"] == middle:
                    goes_trough_middle = True
                    break

            if not goes_trough_middle:
                return False

        # add letters to new board, verify if new letters don't overlap with existing letters
        for letter in new_letters_sorted:
            if board[letter["y"]][letter["x"]] != " ":
                return False

            board[letter["y"]][letter["x"]] = letter["value"]

        points = 0
        # validate every new word created by the change
        creates_valid_word = algorithms.creates_valid_word(
                board, new_letters_sorted[0]["x"], new_letters_sorted[0]["y"], word_direction_axis == "x")
        if not creates_valid_word[0]:
            return False

        points += creates_valid_word[2]

        # if board is not empty, the new word has to connect to some other word
        for letter in new_letters_sorted:
            valid_word = algorithms.creates_valid_word(board, letter["x"], letter["y"], word_direction_axis != "x")
            if not valid_word[0]:
                return False
            if valid_word[1] > 1:
                connected_to_other_word = True

            points += valid_word[2]

        if not board_empty:
            if not connected_to_other_word:
                return False

        await sync_to_async(room_instance.set_board)(algorithms.board_to_string(board))
        await sync_to_async(room_instance.remove_letters_for_current_player)(new_letters_sorted)
        await sync_to_async(room_instance.add_points_to_current_player)(points)
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

    async def switch_turn(self, turn_passed=False):
        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        await sync_to_async(room_instance.toggle_turn)(turn_passed)

        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        if room_instance.pass_counter >= 3:
            await self.finish_game()
            return

        await self.send_new_letters()

    async def start_game(self):
        await self.send(text_data=json.dumps({
            'operation': 'game_started'
        }))

    async def finish_game(self):
        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        winner: User = await sync_to_async(room_instance.get_winner)()
        if winner is None:
            winner_out = "DRAW"
        else:
            winner_out = winner.username

        p1 = await sync_to_async(room_instance.get_player_1)()
        p2 = await sync_to_async(room_instance.get_player_2)()
        await self.reward_player(p1, winner != p2, room_instance.player1_points)
        await self.reward_player(p2, winner != p1, room_instance.player2_points)

        await sync_to_async(room_instance.finish)()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'send_finish',
                'winner': winner_out
            }
        )

    async def send_finish(self, event):
        await self.send(text_data=json.dumps({
            'operation': 'game_stopped',
            'winner': event['winner']
        }))

    @staticmethod
    async def reward_player(user: User, round_won: bool, points: int):

        profile: UserProfile = await sync_to_async(profile_manager.get_profile_for)(user)
        if round_won:
            profile.wins += 1
        else:
            profile.loses += 1

        profile.totalScore += points
        await database_sync_to_async(profile.save)()

    async def send_new_letters(self):
        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        letters = await sync_to_async(room_instance.pass_new_letters)()

        room_instance: Room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
        if len(room_instance.player1_letters) == 0 or len(room_instance.player2_letters) == 0:
            await self.finish_game()
            return

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
