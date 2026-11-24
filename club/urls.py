from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/me/", views.api_me),
    path("api/register/", views.api_register),
    path("api/login/", views.api_login),
    path("api/logout/", views.api_logout),
    path("api/players/search/", views.api_search_player),
    path("api/stats/", views.api_update_stats),
    path("api/pvp/create/", views.api_pvp_create),
    path("api/pvp/join/", views.api_pvp_join),
    path("api/pvp/cancel/", views.api_pvp_cancel),
    path("api/pvp/sync/", views.api_pvp_sync),
    path("api/pvp/room/<str:room_id>/", views.api_pvp_room),
]
