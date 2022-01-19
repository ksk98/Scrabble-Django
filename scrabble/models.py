import uuid

from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)
    wins = models.IntegerField(default=0)
    loses = models.IntegerField(default=0)
    totalScore = models.IntegerField(default=0)


class Room(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4(), editable=False)
    name = models.TextField()
    player1 = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="p1")
    player2 = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="p2")

    def join(self, user):
        if self.player1 is None:
            self.player1 = user
        elif self.player2 is None:
            self.player2 = user
        else:
            return False

        return True

    def leave(self, user):
        if self.player1 == user:
            self.player1 = None
        elif self.player2 == user:
            self.player2 = None
