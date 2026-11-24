import json
import random
import re

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import Player, PvpRoom


def index(request):
    return render(request, "club/index.html")


def json_body(request):
    try:
        return json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return {}


def profile_payload(player: Player):
    user = player.user
    return {
        "firstName": player.first_name,
        "lastName": player.last_name,
        "username": player.display_username,
        "email": user.email,
        "playerId": player.player_id,
        "fullName": f"{player.first_name} {player.last_name}".strip(),
        "stats": {
            "wins": player.wins,
            "losses": player.losses,
            "matches": player.matches,
            "playSeconds": player.play_seconds,
        },
    }


def generate_player_id():
    for _ in range(40):
        pid = f"CV-{random.randint(100000, 999999)}"
        if not Player.objects.filter(player_id=pid).exists():
            return pid
    raise RuntimeError("Could not allocate player id")


def require_player(request):
    if not request.user.is_authenticated:
        return None
    try:
        return request.user.player
    except Player.DoesNotExist:
        return None


def room_payload(room: PvpRoom):
    return {
        "roomId": room.room_id,
        "gameType": room.game_type,
        "status": room.status,
        "host": room.host_json,
        "guest": room.guest_json,
        "gameState": room.game_state or None,
        "actionId": room.action_id,
    }


@require_GET
def api_me(request):
    player = require_player(request)
    if not player:
        return JsonResponse({"ok": False, "profile": None})
    return JsonResponse({"ok": True, "profile": profile_payload(player)})


@require_POST
def api_register(request):
    data = json_body(request)
    first_name = (data.get("firstName") or "").strip()
    last_name = (data.get("lastName") or "").strip()
    raw_user = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not first_name or not last_name:
        return JsonResponse({"ok": False, "error": "Пожалуйста, введите Имя и Фамилию."}, status=400)
    username_core = raw_user.lstrip("@")
    if len(username_core) < 3:
        return JsonResponse({"ok": False, "error": "Username должен содержать минимум 3 символа."}, status=400)
    if not re.match(r"^[\w.\-]+$", username_core, re.UNICODE):
        return JsonResponse({"ok": False, "error": "Username может содержать буквы, цифры, точку и подчёркивание."}, status=400)
    if not email or "@" not in email:
        return JsonResponse({"ok": False, "error": "Введите корректный Email адрес."}, status=400)
    if len(password) < 6:
        return JsonResponse({"ok": False, "error": "Пароль должен содержать минимум 6 символов."}, status=400)
    if User.objects.filter(username__iexact=username_core).exists():
        return JsonResponse({"ok": False, "error": "Этот username уже занят."}, status=400)
    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"ok": False, "error": "Этот email уже зарегистрирован."}, status=400)

    user = User.objects.create_user(
        username=username_core,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    player = Player.objects.create(
        user=user,
        player_id=generate_player_id(),
        first_name=first_name,
        last_name=last_name,
        display_username=f"@{username_core}",
    )
    login(request, user)
    return JsonResponse({"ok": True, "profile": profile_payload(player)})


@require_POST
def api_login(request):
    data = json_body(request)
    raw_id = (data.get("identifier") or "").strip()
    password = data.get("password") or ""
    if not raw_id or not password:
        return JsonResponse({"ok": False, "error": "Введите Email / Username / ID и пароль."}, status=400)

    user = None
    lower = raw_id.lower()
    username_core = raw_id.lstrip("@")
    upper_id = raw_id.upper()
    if not upper_id.startswith("CV-") and raw_id.replace("-", "").isdigit():
        upper_id = f"CV-{raw_id.upper()}"
    elif raw_id.upper().startswith("CV-"):
        upper_id = raw_id.upper()

    player = Player.objects.filter(player_id__iexact=upper_id).select_related("user").first()
    if player:
        user = player.user
    if user is None:
        user = User.objects.filter(Q(email__iexact=lower) | Q(username__iexact=username_core)).first()

    if user is None:
        return JsonResponse(
            {"ok": False, "error": "Аккаунт не найден. Проверьте данные или перейдите во вкладку «Регистрация»."},
            status=400,
        )

    authed = authenticate(request, username=user.username, password=password)
    if authed is None:
        return JsonResponse({"ok": False, "error": "Неверный пароль. Попробуйте ещё раз."}, status=400)

    login(request, authed)
    try:
        player = authed.player
    except Player.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Профиль игрока не найден."}, status=400)
    return JsonResponse({"ok": True, "profile": profile_payload(player)})


@require_POST
def api_logout(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_GET
def api_search_player(request):
    raw = (request.GET.get("q") or "").strip()
    if not raw:
        return JsonResponse({"ok": False, "error": "Введите ID или Username игрока."}, status=400)

    upper = raw.upper()
    id_candidate = upper if upper.startswith("CV-") else f"CV-{upper}"
    username = raw if raw.startswith("@") else f"@{raw}"

    player = (
        Player.objects.filter(Q(player_id__iexact=id_candidate) | Q(display_username__iexact=username))
        .select_related("user")
        .first()
    )
    if not player:
        return JsonResponse({"ok": False, "error": "Игрок не найден."}, status=404)

    me = require_player(request)
    is_own = bool(me and me.id == player.id)
    return JsonResponse({"ok": True, "profile": profile_payload(player), "isOwn": is_own})


@require_POST
def api_update_stats(request):
    player = require_player(request)
    if not player:
        return JsonResponse({"ok": False, "error": "Нужна авторизация."}, status=401)
    data = json_body(request)
    did_win = bool(data.get("didWin"))
    elapsed = int(data.get("elapsedSec") or 0)
    elapsed = max(10, min(elapsed, 24 * 3600))
    player.matches += 1
    if did_win:
        player.wins += 1
    else:
        player.losses += 1
    player.play_seconds += elapsed
    player.save(update_fields=["matches", "wins", "losses", "play_seconds"])
    return JsonResponse({"ok": True, "profile": profile_payload(player)})


@require_POST
def api_pvp_create(request):
    player = require_player(request)
    if not player:
        return JsonResponse({"ok": False, "error": "Войдите в аккаунт, чтобы создать стол."}, status=401)
    data = json_body(request)
    game_type = data.get("gameType") or "uno"
    room, _created = PvpRoom.objects.update_or_create(
        room_id=player.player_id,
        defaults={
            "game_type": game_type,
            "status": "waiting",
            "host_json": {
                "playerId": player.player_id,
                "name": player.display_username,
                "avatar": "😎",
            },
            "guest_json": None,
            "game_state": "",
            "action_id": 0,
        },
    )
    return JsonResponse({"ok": True, "room": room_payload(room)})


@require_POST
def api_pvp_join(request):
    player = require_player(request)
    if not player:
        return JsonResponse({"ok": False, "error": "Войдите в аккаунт, чтобы подключиться."}, status=401)
    data = json_body(request)
    raw = (data.get("roomId") or "").strip().upper()
    target = raw if raw.startswith("CV-") else f"CV-{raw}"
    try:
        room = PvpRoom.objects.get(room_id=target)
    except PvpRoom.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Комната с таким ID не найдена или игра уже идёт."}, status=404)
    if room.status != "waiting":
        return JsonResponse({"ok": False, "error": "Комната с таким ID не найдена или игра уже идёт."}, status=400)
    if room.room_id == player.player_id:
        return JsonResponse({"ok": False, "error": "Нельзя подключиться к своему столу."}, status=400)
    room.status = "active"
    room.guest_json = {
        "playerId": player.player_id,
        "name": player.display_username,
        "avatar": "🔥",
    }
    room.save(update_fields=["status", "guest_json", "updated_at"])
    return JsonResponse({"ok": True, "room": room_payload(room)})


@require_POST
def api_pvp_cancel(request):
    player = require_player(request)
    if not player:
        return JsonResponse({"ok": False})
    PvpRoom.objects.filter(room_id=player.player_id, status="waiting").update(status="closed")
    return JsonResponse({"ok": True})


@require_POST
def api_pvp_sync(request):
    player = require_player(request)
    if not player:
        return JsonResponse({"ok": False, "error": "Нужна авторизация."}, status=401)
    data = json_body(request)
    room_id = (data.get("roomId") or "").strip().upper()
    try:
        room = PvpRoom.objects.get(room_id=room_id)
    except PvpRoom.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Комната не найдена."}, status=404)

    host_id = (room.host_json or {}).get("playerId")
    guest_id = (room.guest_json or {}).get("playerId") if room.guest_json else None
    if player.player_id not in {host_id, guest_id}:
        return JsonResponse({"ok": False, "error": "Нет доступа к этой комнате."}, status=403)

    room.game_state = data.get("gameState") or ""
    room.action_id = int(data.get("actionId") or room.action_id)
    room.status = "active"
    room.save(update_fields=["game_state", "action_id", "status", "updated_at"])
    return JsonResponse({"ok": True, "room": room_payload(room)})


@require_http_methods(["GET"])
def api_pvp_room(request, room_id):
    player = require_player(request)
    if not player:
        return JsonResponse({"ok": False, "error": "Нужна авторизация."}, status=401)
    try:
        room = PvpRoom.objects.get(room_id=room_id.upper())
    except PvpRoom.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Комната не найдена."}, status=404)
    host_id = (room.host_json or {}).get("playerId")
    guest_id = (room.guest_json or {}).get("playerId") if room.guest_json else None
    if player.player_id not in {host_id, guest_id}:
        return JsonResponse({"ok": False, "error": "Нет доступа к этой комнате."}, status=403)
    return JsonResponse({"ok": True, "room": room_payload(room)})
