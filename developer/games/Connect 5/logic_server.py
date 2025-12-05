import socket
from tool.common_protocol import send_json, recv_json

BOARD_SIZE = 10  # match player limit (0-9)

def create_board():
    return [["." for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

def check_five(board, x, y, symbol):
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
    for dx, dy in directions:
        count = 1

        # forward
        nx, ny = x + dx, y + dy
        while 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[nx][ny] == symbol:
            count += 1
            nx += dx
            ny += dy

        # backward
        nx, ny = x - dx, y - dy
        while 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[nx][ny] == symbol:
            count += 1
            nx -= dx
            ny -= dy

        if count >= 5:
            return True

    return False

def run_server_game(server_host, server_port):
    HOST = server_host
    PORT = server_port

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(2)

    print("[SERVER] Waiting for two players...")

    # Accept two players
    p1, addr1 = server.accept()
    print(f"[SERVER] Player 1 connected from {addr1}")

    p2, addr2 = server.accept()
    print(f"[SERVER] Player 2 connected from {addr2}")

    send_json(p1, {"role": 1})
    send_json(p2, {"role": 2})

    BOARD = create_board()
    SYMBOL = {1: "X", 2: "O"}
    turn = 1

    while True:
        current = p1 if turn == 1 else p2
        other = p2 if turn == 1 else p1

        valid_move = False
        while not valid_move:
            # ask for move
            send_json(current, {"action": "your_turn", "board": BOARD})
            msg = recv_json(current)

            try:
                x = int(msg["x"])
                y = int(msg["y"])
            except (KeyError, ValueError, TypeError):
                send_json(current, {"action": "invalid", "reason": "Invalid input format"})
                continue

            if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
                send_json(current, {"action": "invalid", "reason": f"Coordinates must be 0-{BOARD_SIZE-1}"})
                continue
            if BOARD[x][y] != ".":
                send_json(current, {"action": "invalid", "reason": "Cell already occupied"})
                continue

            valid_move = True

        # apply move
        BOARD[x][y] = SYMBOL[turn]

        # broadcast update
        send_json(p1, {"action": "update", "board": BOARD})
        send_json(p2, {"action": "update", "board": BOARD})

        # check win
        if check_five(BOARD, x, y, SYMBOL[turn]):
            send_json(p1, {"action": "game_over", "winner": turn, "board": BOARD})
            send_json(p2, {"action": "game_over", "winner": turn, "board": BOARD})
            print(f"[SERVER] Player {turn} wins!")
            break

        # next turn
        turn = 2 if turn == 1 else 1

    p1.close()
    p2.close()
    server.close()
