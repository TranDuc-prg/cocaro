import sqlite3
from db import get_connection, get_room, save_room, get_user_elo, set_user_elo, add_match_history

WIN_SCORE = 15
LOSS_SCORE = -10
MIN_ELO = 100


def _claim_elo_update(room_id):
    """Atomically claim the right to update ELO for one finished room."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT elo_already_updated FROM rooms WHERE room_id = ?",
            (room_id,),
        ).fetchone()
        if not row or bool(row[0]):
            conn.rollback()
            return False
        conn.execute(
            "UPDATE rooms SET elo_already_updated = 1 WHERE room_id = ?",
            (room_id,),
        )
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False
    finally:
        conn.close()


def update_elo_online(room_id, winner):
    room = get_room(room_id)
    if not room or not room.get("game_ended"):
        return False

    players = room.get("players", {}) or {}
    if len(players) != 2:
        return False

    if winner not in ("X", "O", "Draw"):
        return False

    if not _claim_elo_update(room_id):
        return False

    user_list = list(players.keys())
    p1, p2 = user_list[0], user_list[1]
    s1, s2 = players[p1], players[p2]
    score_changes = {p1: "0", p2: "0"}

    if winner in ("X", "O"):
        win_user = p1 if s1 == winner else p2
        lose_user = p2 if win_user == p1 else p1

        elo_win = get_user_elo(win_user) + WIN_SCORE
        elo_lose = max(MIN_ELO, get_user_elo(lose_user) + LOSS_SCORE)

        set_user_elo(win_user, elo_win)
        set_user_elo(lose_user, elo_lose)

        score_changes[win_user] = "+15"
        score_changes[lose_user] = "-10"

        add_match_history(win_user, lose_user, "Thắng", "+15")
        add_match_history(lose_user, win_user, "Thua", "-10")

    else:
        add_match_history(p1, p2, "Hòa", "0")
        add_match_history(p2, p1, "Hòa", "0")

    room = get_room(room_id)
    if room:
        room["last_score"] = score_changes
        room["elo_already_updated"] = True
        save_room(room_id, room)

    return True
