# room_manager.py (room_manager_4.py)
import json
from db import get_room, save_room, delete_room

def init_room(room_id, size=3):
    room = {
        'room_id': room_id,
        'board': [[" " for _ in range(size)] for _ in range(size)],
        'size': size,
        'turn': "X",
        'winner': None,
        'winning_line': [],
        'players': {},
        'last_score': None,
        'game_ended': False,
        'last_move': None
    }
    save_room(room_id, room)
    return room

def get_room_info(room_id):
    return get_room(room_id)

def join_room(room_id, username):
    room = get_room(room_id)
    if not room:
        return None
    
    players = room['players']
    if username in players:
        return players[username]
    
    if len(players) >= 2:
        return None
    
    assigned_symbol = "X" if len(players) == 0 else "O"
    existing_symbols = list(players.values())
    if "X" not in existing_symbols:
        assigned_symbol = "X"
    elif "O" not in existing_symbols:
        assigned_symbol = "O"
        
    players[username] = assigned_symbol
    room['players'] = players
    save_room(room_id, room)
    return assigned_symbol

def leave_room(room_id, username):
    room = get_room(room_id)
    if not room:
        return
    
    players = room['players']
    if username in players:
        del players[username]
        room['players'] = players
        if len(players) == 0:
            delete_room(room_id)
        else:
            save_room(room_id, room)