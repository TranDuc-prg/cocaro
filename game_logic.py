# game_logic.py (Tối ưu triệt để giới hạn nhánh tìm kiếm cho bàn cờ lớn)
import math
import random
import time
from db import get_room, save_room
from elo import update_elo_online

def check_winner(board, size):
    win_len = 3 if size == 3 else 5
    
    for r in range(size):
        for c in range(size - win_len + 1):
            symbol = board[r][c]
            if symbol != " " and all(board[r][c+k] == symbol for k in range(win_len)):
                if size > 3:
                    left_blocked = (c > 0 and board[r][c-1] != " " and board[r][c-1] != symbol)
                    right_blocked = (c + win_len < size and board[r][c+win_len] != " " and board[r][c+win_len] != symbol)
                    if left_blocked and right_blocked:
                        continue
                return symbol, [(r, c+k) for k in range(win_len)]
                
    for c in range(size):
        for r in range(size - win_len + 1):
            symbol = board[r][c]
            if symbol != " " and all(board[r+k][c] == symbol for k in range(win_len)):
                if size > 3:
                    top_blocked = (r > 0 and board[r-1][c] != " " and board[r-1][c] != symbol)
                    bot_blocked = (r + win_len < size and board[r+win_len][c] != " " and board[r+win_len][c] != symbol)
                    if top_blocked and bot_blocked:
                        continue
                return symbol, [(r+k, c) for k in range(win_len)]
                
    for r in range(size - win_len + 1):
        for c in range(size - win_len + 1):
            symbol = board[r][c]
            if symbol != " " and all(board[r+k][c+k] == symbol for k in range(win_len)):
                return symbol, [(r+k, c+k) for k in range(win_len)]
                
    for r in range(size - win_len + 1):
        for c in range(win_len - 1, size):
            symbol = board[r][c]
            if symbol != " " and all(board[r+k][c-k] == symbol for k in range(win_len)):
                return symbol, [(r+k, c-k) for k in range(win_len)]
                
    return None, []

def is_full(board, size):
    return all(board[r][c] != " " for r in range(size) for c in range(size))

def evaluate_board(board, size, ai_symbol, human_symbol):
    score = 0
    center = size // 2
    for r in range(size):
        for c in range(size):
            if board[r][c] == ai_symbol:
                score += 10 + (size - max(abs(r - center), abs(c - center)))
            elif board[r][c] == human_symbol:
                score -= 10 + (size - max(abs(r - center), abs(c - center)))
    return score

_node_counter = 0

def minimax(board, size, depth, alpha, beta, maximizing_player, ai_symbol, human_symbol):
    global _node_counter
    _node_counter += 1

    winner, _ = check_winner(board, size)
    if winner == ai_symbol:
        return 100000 + depth, None
    elif winner == human_symbol:
        return -100000 - depth, None
    elif winner == "Draw" or depth == 0 or is_full(board, size):
        return evaluate_board(board, size, ai_symbol, human_symbol), None

    valid_moves = []
    
    # Nếu bàn cờ trống hoàn toàn, trả về luôn ô giữa
    if all(board[r][c] == " " for r in range(size) for c in range(size)):
        return 0, (size // 2, size // 2)

    # Lọc các ô lân cận có chứa quân cờ (bán kính 2 ô)
    for r in range(size):
        for c in range(size):
            if board[r][c] == " ":
                if size > 5:
                    has_neighbor = any(
                        0 <= r+dr < size and 0 <= c+dc < size and board[r+dr][c+dc] != " "
                        for dr in [-2, -1, 0, 1, 2] for dc in [-2, -1, 0, 1, 2] if not (dr == 0 and dr == 0)
                    )
                    if has_neighbor:
                        valid_moves.append((r, c))
                else:
                    valid_moves.append((r, c))

    if not valid_moves:
        for r in range(size):
            for c in range(size):
                if board[r][c] == " ":
                    valid_moves.append((r, c))

    # QUAN TRỌNG: Nếu bàn cờ lớn và số lượng ô trống quá nhiều, chỉ lấy tối đa 15 ô gần tâm/gần quân đã đánh nhất để chống đơ
    if size >= 10 and len(valid_moves) > 15:
        center = size // 2
        valid_moves.sort(key=lambda pos: abs(pos[0] - center) + abs(pos[1] - center))
        valid_moves = valid_moves[:15]

    if not valid_moves:
        return 0, None

    best_move = valid_moves[0]

    if maximizing_player:
        max_eval = -math.inf
        for (r, c) in valid_moves:
            board[r][c] = ai_symbol
            eval, _ = minimax(board, size, depth - 1, alpha, beta, False, ai_symbol, human_symbol)
            board[r][c] = " "
            if eval > max_eval:
                max_eval = eval
                best_move = (r, c)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = math.inf
        for (r, c) in valid_moves:
            board[r][c] = human_symbol
            eval, _ = minimax(board, size, depth - 1, alpha, beta, True, ai_symbol, human_symbol)
            board[r][c] = " "
            if eval < min_eval:
                min_eval = eval
                best_move = (r, c)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval, best_move

def ai_move(size, board, difficulty="Trung bình", ai_symbol="O", human_symbol="X"):
    global _node_counter
    _node_counter = 0
    
    start_time = time.time()
    
    empty_count = sum(row.count(" ") for row in board)
    if empty_count == size * size:
        center = size // 2
        return center, center, 1, 0.0
    
    # Ép độ sâu an toàn tối đa cho bàn cờ lớn (10x10, 12x12) để tuyệt đối không bị treo
    if size >= 10:
        depth = 1 if difficulty == "Dễ" else 2
    else:
        if difficulty == "Dễ":
            depth = 1
        elif difficulty == "Trung bình":
            depth = 2
        else:
            depth = 3
        
    _, move = minimax(board, size, depth, -math.inf, math.inf, True, ai_symbol, human_symbol)
    elapsed_time = (time.time() - start_time) * 1000
    
    if move is None:
        empty_cells = [(r, c) for r in range(size) for c in range(size) if board[r][c] == " "]
        move = random.choice(empty_cells) if empty_cells else (0, 0)
        
    return move[0], move[1], _node_counter, elapsed_time

def get_ai_hint(size, board, human_symbol="X", ai_symbol="O"):
    global _node_counter
    _node_counter = 0
    depth = 2 if size >= 10 else 3
    _, move = minimax(board, size, depth, -math.inf, math.inf, True, human_symbol, ai_symbol)
    if not move:
        empty_cells = [(r, c) for r in range(size) for c in range(size) if board[r][c] == " "]
        return random.choice(empty_cells) if empty_cells else (0, 0)
    return move

def apply_move(room_id, row, col, username):
    room = get_room(room_id)
    if not room: 
        return False, "Phòng không tồn tại."
    if username not in room["players"]: 
        return False, "Bạn chưa tham gia phòng."
    
    symbol = room["players"][username]
    if room["winner"] is not None: 
        return False, "Trận đã kết thúc."
    if room["turn"] != symbol: 
        return False, "Chưa đến lượt bạn."
        
    board = room["board"]
    size = room["size"]
    
    if row < 0 or row >= size or col < 0 or col >= size: 
        return False, "Ô không hợp lệ."
    if board[row][col] != " ": 
        return False, "Ô đã bị chiếm."
        
    board[row][col] = symbol
    winner, win_line = check_winner(board, size)
    room["last_move"] = (row, col)
    
    if winner:
        room["winner"] = winner
        room["winning_line"] = win_line
        room["game_ended"] = True
        save_room(room_id, room)
        update_elo_online(room_id, winner)
    elif is_full(board, size):
        room["winner"] = "Draw"
        room["game_ended"] = True
        save_room(room_id, room)
        update_elo_online(room_id, "Draw")
    else:
        room["turn"] = "O" if symbol == "X" else "X"
        save_room(room_id, room)
        
    return True, "Thành công"