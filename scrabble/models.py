import random

from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)
    wins = models.IntegerField(default=0)
    loses = models.IntegerField(default=0)
    totalScore = models.IntegerField(default=0)


class Room(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    name = models.TextField()
    player1 = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="p1")
    player2 = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="p2")
    player1_points = models.IntegerField(default=0)
    player2_points = models.IntegerField(default=0)

    letters = models.TextField(default="")
    player1_letters = models.TextField(default="")
    player2_letters = models.TextField(default="")
    player1_turn = models.BooleanField(default=True)

    board = models.TextField(default="")
    size = models.IntegerField(default=15)

    in_progress = models.BooleanField(default=False)
    pass_counter = models.IntegerField(default=0)
    finished = models.BooleanField(default=False)

    def get_player_1(self):
        return self.player1

    def get_player_2(self):
        return self.player2

    def is_empty(self):
        return self.player1 is None and self.player2 is None

    def finish(self):
        self.finished = True
        self.save()

    def get_player_1_id(self):
        return self.player1.id

    def get_player_2_id(self):
        return self.player2.id

    def get_winner(self):
        if self.player1_points > self.player2_points:
            return self.player1
        elif self.player1_points < self.player2_points:
            return self.player2
        else:
            return None

    def add_points_to_current_player(self, value):
        if self.player1_turn:
            self.player1_points += value
        else:
            self.player2_points += value

        self.save()

    def remove_letters_for_current_player(self, letters):
        for letter in letters:
            if self.player1_turn:
                for i in range(len(self.player1_letters)):
                    if letter["value"] == self.player1_letters[i]:
                        self.player1_letters = \
                            self.player1_letters[0:i] + self.player1_letters[i + 1:len(self.player1_letters)]
                        break
            else:
                for i in range(len(self.player2_letters)):
                    if letter["value"] == self.player2_letters[i]:
                        self.player2_letters = \
                            self.player2_letters[0:i] + self.player2_letters[i + 1:len(self.player2_letters)]
                        break

        self.save()

    def get_letters_for_player(self, player):
        if self.player1 == player:
            return self.player1_letters
        elif self.player2 == player:
            return self.player2_letters
        else:
            return "BAD PLAYER"

    def get_board(self):
        return self.board

    def set_board(self, value):
        self.board = value
        self.save()

    def get_player_turn(self, player):
        if self.player1 == player:
            return self.player1_turn
        else:
            return not self.player1_turn

    def is_turn_of_player(self, player):
        if (self.player1_turn and self.player1 == player) or \
                (not self.player1_turn and self.player2 == player):
            return True

        return False

    def set_in_progress(self, progress):
        self.in_progress = progress
        self.save()

    def add_points(self, player, points):
        if self.player1 == player:
            self.player1_points += points
        elif self.player2 == player:
            self.player2_points += points
        self.save()

    def toggle_turn(self, turn_passed=False):
        self.player1_turn = not self.player1_turn

        if turn_passed:
            self.pass_counter += 1
        else:
            self.pass_counter = 0

        self.save()

    def join(self, user):
        if self.finished:
            return False

        if self.player1 == user or self.player2 == user:
            return True

        if self.player1 is None:
            self.player1 = user
        elif self.player2 is None:
            self.player2 = user
        else:
            return False

        if self.player1 is not None and self.player2 is not None:
            self.reset_board()
            self.reset_letters()
            self.player1_turn = random.getrandbits(1)

        self.save()
        return True

    def is_full(self):
        return self.player1 is not None and self.player2 is not None

    def is_in_progress(self):
        return self.in_progress

    def leave(self, user):
        if self.player1 == user:
            self.player1 = None
        elif self.player2 == user:
            self.player2 = None

        self.save()

    def reset_letters(self):
        letters = "AAAAAAAAA" + "IIIIIIII" + "EEEEEEE" + "OOOOOO" + \
                  "NNNNN" + "ZZZZZ" + "RRRR" + "SSSS" + "WWWW" + \
                  "YYYY" + "CCC" + "DDD" + "KKK" + "LLL" + "MMM" + \
                  "PPP" + "TTT" + "BB" + "GG" + "HH" + "JJ" + "ŁŁ" + \
                  "UU" + "Ą" + "Ę" + "F" + "Ó" + "Ś" + "Ż" + "Ć" + "Ń" + "Ź"

        self.letters = ''.join(random.sample(letters, len(letters)))
        self.save()

    def reset_board(self):
        self.board = ""
        self.board = self.board.ljust(int(self.size)**2, " ")
        self.save()

    def pass_new_letters(self):
        p1_deficit = 8 - len(self.player1_letters)
        p2_deficit = 8 - len(self.player2_letters)
        p1_new = ""
        p2_new = ""

        for i in range(p1_deficit):
            if len(self.letters) <= 0:
                break

            p1_new = p1_new + self.letters[0]
            self.letters = self.letters[1:]
        self.player1_letters = self.player1_letters + p1_new

        for i in range(p2_deficit):
            if len(self.letters) <= 0:
                break

            p2_new = p2_new + self.letters[0]
            self.letters = self.letters[1:]
        self.player2_letters = self.player2_letters + p2_new

        self.save()
        return {'player_1': p1_new, 'player_2': p2_new}
