# elo.py (elo_6.py)
from db import get_room, save_room, get_user_elo, set_user_elo, add_match_history

def update_elo_online(room_id, winner):
    room = get_room(room_id)
    if not room: 
        return
    
    if room.get("elo_already_updated", False):
        return

    players = room["players"]
    if len(players) != 2: 
        return
        
    user_list = list(players.keys())
    p1, p2 = user_list[0], user_list[1]
    s1, s2 = players[p1], players[p2]
    score_changes = {}

    if winner in ["X", "O"]:
        win_symbol = winner
        win_user = p1 if s1 == win_symbol else p2
        lose_user = p2 if s1 == win_symbol else p1
        
        elo_win = get_user_elo(win_user) + 15
        elo_lose = max(100, get_user_elo(lose_user) - 10)
        
        set_user_elo(win_user, elo_win)
        set_user_elo(lose_user, elo_lose)
        
        score_changes[win_user] = "+15"
        score_changes[lose_user] = "-10"
        
        add_match_history(win_user, lose_user, "Thắng", "+15")
        add_match_history(lose_user, win_user, "Thua", "-10")
        
    elif winner == "Draw":
        for u in [p1, p2]:
            score_changes[u] = "0"
            opponent = p2 if u == p1 else p1
            add_match_history(u, opponent, "Hòa", "0")

    room["last_score"] = score_changes
    room["elo_already_updated"] = True
    save_room(room_id, room)