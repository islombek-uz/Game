from django.contrib.auth.models import User
from django.db import models


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="player")
    player_id = models.CharField(max_length=16, unique=True, db_index=True)
    first_name = models.CharField(max_length=24)
    last_name = models.CharField(max_length=24)
    display_username = models.CharField(max_length=24)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    matches = models.PositiveIntegerField(default=0)
    play_seconds = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.display_username} ({self.player_id})"


class PvpRoom(models.Model):
    room_id = models.CharField(max_length=16, primary_key=True)
    game_type = models.CharField(max_length=32)
    status = models.CharField(max_length=16, default="waiting")
    host_json = models.JSONField(default=dict)
    guest_json = models.JSONField(null=True, blank=True)
    game_state = models.TextField(blank=True, default="")
    action_id = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.room_id} [{self.status}]"
