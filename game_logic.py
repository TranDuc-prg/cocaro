import math
import random
import time
from db import get_room_info, save_room
from elo import update_elo_online

def check_winner(board, size):
    win_len = 3 if size == 3 else 5
    
    for r in range(size):
        for c in range(size - win_len + 1):
            symbol = board[r][c]
            if symbol != " " and all(board[r][c+k] == symbol for k in range(win_len)):
                if size >= 5:
                    left_blocked = (c > 0 and board[r][c-1] != " " and board[r][c-1] != symbol)
                    right_blocked = (c + win_len < size and board[r][c+win_len] != " " and board[r][c+win_len] != symbol)
                    if left_blocked and right_blocked:
                        continue
                return symbol, [(r, c+k) for k in range(win_len)]
                
    for c in range(size):
        for r in range(size - win_len + 1):
            symbol = board[r][c]
            if symbol != " " and all(board[r+k][c] == symbol for k in range(win_len)):
                if size >= 5:
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

def minimax(board, size, depth, alpha, beta, maximizing_player, ai_symbol, human_symbol, use_alpha_beta=True):
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
    
    for r in range(size):
        for c in range(size):
            if board[r][c] == " ":
                if size > 5:
                    has_neighbor = any(
                        0 <= r+dr < size and 0 <= c+dc < size and board[r+dr][c+dc] != " "
                        for dr in [-2, -1, 0, 1, 2] for dc in [-2, -1, 0, 1, 2] if not (dr == 0 and dc == 0)
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
            eval, _ = minimax(board, size, depth - 1, alpha, beta, False, ai_symbol, human_symbol, use_alpha_beta)
            board[r][c] = " "
            if eval > max_eval:
                max_eval = eval
                best_move = (r, c)
            alpha = max(alpha, eval)
            if use_alpha_beta and beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = math.inf
        for (r, c) in valid_moves:
            board[r][c] = human_symbol
            eval, _ = minimax(board, size, depth - 1, alpha, beta, True, ai_symbol, human_symbol, use_alpha_beta)
            board[r][c] = " "
            if eval < min_eval:
                min_eval = eval
                best_move = (r, c)
            beta = min(beta, eval)
            if use_alpha_beta and beta <= alpha:
                break
        return min_eval, best_move

def ai_move(size, board, difficulty="Trung bình", ai_symbol="O", human_symbol="X", use_alpha_beta=True):
    global _node_counter
    _node_counter = 0
    
    start_time = time.time()
    
    empty_count = sum(row.count(" ") for row in board)
    if empty_count == size * size:
        center = size // 2
        return center, center, 1, 0.0
    
    if size >= 10:
        depth = 1 if difficulty == "Dễ" else 2
    else:
        if difficulty == "Dễ":
            depth = 1
        elif difficulty == "Trung bình":
            depth = 2
        else:
            depth = 3
        
    _, move = minimax(board, size, depth, -math.inf, math.inf, True, ai_symbol, human_symbol, use_alpha_beta)
    elapsed_time = (time.time() - start_time) * 1000
    
    if move is None:
        empty_cells = [(r, c) for r in range(size) for c in range(size) if board[r][c] == " "]
        move = random.choice(empty_cells) if empty_cells else (0, 0)
        
    return move[0], move[1], _node_counter, elapsed_time

def get_ai_hint(size, board, human_symbol="X", ai_symbol="O"):
    global _node_counter
    _node_counter = 0
    depth = 2 if size >= 10 else 3
    _, move = minimax(board, size, depth, -math.inf, math.inf, True, human_symbol, ai_symbol, use_alpha_beta=True)
    if not move:
        empty_cells = [(r, c) for r in range(size) for c in range(size) if board[r][c] == " "]
        return random.choice(empty_cells) if empty_cells else (0, 0)
    return move

def benchmark_algorithms(size, depth=2, board_state=None):
    
    global _node_counter

    if board_state is None:
        board_state = [[" " for _ in range(size)] for _ in range(size)]
        center = size // 2
        board_state[center][center] = "X"
        if center + 1 < size:
            board_state[center][center + 1] = "O"

    # Minimax thuần
    board_copy_1 = [row[:] for row in board_state]
    _node_counter = 0
    start_time = time.time()
    minimax(
        board_copy_1, size, depth, -math.inf, math.inf,
        True, "O", "X", use_alpha_beta=False
    )
    pure_nodes = _node_counter
    pure_time = (time.time() - start_time) * 1000

    # Minimax + Alpha-Beta
    board_copy_2 = [row[:] for row in board_state]
    _node_counter = 0
    start_time = time.time()
    minimax(
        board_copy_2, size, depth, -math.inf, math.inf,
        True, "O", "X", use_alpha_beta=True
    )
    ab_nodes = _node_counter
    ab_time = (time.time() - start_time) * 1000

    return {
        "depth": int(depth),
        "pure_nodes": int(pure_nodes),
        "pure_time": round(pure_time, 2),
        "ab_nodes": int(ab_nodes),
        "ab_time": round(ab_time, 2),
        "node_saved_percent": round((1 - ab_nodes / max(pure_nodes, 1)) * 100, 1),
    }

def apply_move(room_id, r, c, username):
    """Apply one online move and persist the complete room state."""
    room = get_room_info(room_id)
    if not room:
        return False, "Phòng không tồn tại!"

    if room.get("game_ended", False):
        return False, "Ván đấu đã kết thúc!"

    players = room.get("players", {}) or {}
    if username not in players:
        return False, "Bạn không phải người chơi trong phòng này!"

    try:
        r = int(r)
        c = int(c)
    except (TypeError, ValueError):
        return False, "Vị trí nước đi không hợp lệ!"

    size = int(room.get("size", 3))
    if not (0 <= r < size and 0 <= c < size):
        return False, "Vị trí nước đi nằm ngoài bàn cờ!"

    my_symbol = players[username]
    if room.get("turn", "X") != my_symbol:
        return False, "Chưa tới lượt của bạn!"

    board = room.get("board", [])
    if len(board) != size or any(len(row) != size for row in board):
        return False, "Dữ liệu bàn cờ không hợp lệ!"

    if board[r][c] != " ":
        return False, "Ô này đã được đánh!"

    # Apply the move.
    board[r][c] = my_symbol
    room["board"] = board
    room["last_move"] = (r, c)

    history = room.get("move_history", []) or []
    history.append({
        "row": r + 1,
        "col": c + 1,
        "symbol": my_symbol,
        "player": username,
        "timestamp": time.time(),
    })
    room["move_history"] = history

    winner, winning_line = check_winner(board, size)
    if winner:
        room["winner"] = winner
        room["winning_line"] = winning_line
        room["game_ended"] = True
    elif is_full(board, size):
        room["winner"] = "Draw"
        room["winning_line"] = []
        room["game_ended"] = True
    else:
        room["winner"] = None
        room["winning_line"] = []
        room["turn"] = "O" if my_symbol == "X" else "X"
        room["turn_start_time"] = time.time()

    save_room(room_id, room)
    return True, "Thành công"
