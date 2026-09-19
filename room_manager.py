"""Room lifecycle and player management."""
import time
from db import get_room, save_room, delete_room


def init_room(room_id, size=3):
    size = max(3, int(size))
    room = {
        "room_id": room_id,
        "board": [[" " for _ in range(size)] for _ in range(size)],
        "size": size,
        "turn": "X",
        "winner": None,
        "winning_line": [],
        "players": {},
        "last_score": None,
        "game_ended": False,
        "elo_already_updated": False,
        "last_move": None,
        "move_history": [],
        "turn_start_time": time.time(),
    }
    save_room(room_id, room)
    return room


def get_room_info(room_id):
    return get_room(room_id)


def join_room(room_id, username):
    room = get_room(room_id)
    if not room:
        return None

    players = room.get("players", {}) or {}

    if username in players:
        return players[username]

    if len(players) >= 2:
        return None

    if "X" not in players.values():
        assigned_symbol = "X"
    elif "O" not in players.values():
        assigned_symbol = "O"
    else:
        return None

    players[username] = assigned_symbol
    room["players"] = players
    save_room(room_id, room)
    return assigned_symbol


def leave_room(room_id, username):
    room = get_room(room_id)
    if not room:
        return

    players = room.get("players", {}) or {}
    if username not in players:
        return

    del players[username]
    room["players"] = players

    if not players:
        delete_room(room_id)
        return

    # Keep the room and board for the remaining player. A new player can join
    # the same room later; the current game state is intentionally preserved.
    save_room(room_id, room)
