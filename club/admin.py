from django.contrib import admin

from .models import Player, PvpRoom


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("player_id", "display_username", "first_name", "last_name", "wins", "matches")
    search_fields = ("player_id", "display_username", "user__email")


@admin.register(PvpRoom)
class PvpRoomAdmin(admin.ModelAdmin):
    list_display = ("room_id", "game_type", "status", "action_id", "updated_at")
