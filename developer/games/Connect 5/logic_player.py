import socket
import os
from tool.common_protocol import send_json, recv_json

BOARD_SIZE = 10  # limit rows and columns to 0-9

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def print_board(board):
    # Header
    print("\n  " + " ".join(str(i) for i in range(len(board))))
    for i, row in enumerate(board):
        print(f"{i} " + " ".join(row))
    print()


def run_player_game(server_ip, server_port):
    HOST = server_ip
    PORT = server_port

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("[CLIENT] Connecting...")
    sock.connect((HOST, PORT))

    # ----------------------------------------------------
    # Wait max 10 seconds for the server to send role info
    # ----------------------------------------------------
    sock.settimeout(10)

    try:
        msg = recv_json(sock)
    except socket.timeout:
        print("\n⏳ No other player joined within 10 seconds.")
        print("❌ Game canceled. Returning to menu...")
        sock.close()
        return

    # Once role is received, no more timeout needed
    sock.settimeout(None)

    # Receive role
    role = msg["role"]
    symbol = "X" if role == 1 else "O"
    print(f"[CLIENT] You are Player {role} ({symbol})")

    while True:
        msg = recv_json(sock)

        if msg["action"] == "update":
            clear_screen()
            print_board(msg["board"])

        elif msg["action"] == "your_turn":
            board = msg["board"]
            while True:
                clear_screen()
                print_board(board)
                print("[CLIENT] Your turn!")

                try:
                    line = input("Enter move (row col): ").strip().split()
                    if len(line) != 2:
                        raise ValueError("Input must contain exactly 2 numbers.")

                    x, y = int(line[0]), int(line[1])

                    if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
                        raise ValueError(f"Coordinates must be between 0 and {BOARD_SIZE-1}.")

                    if board[x][y] != ".":
                        raise ValueError("Cell already occupied.")

                    break  # valid move
                except ValueError as e:
                    print(f"❌ Invalid move: {e}")
                    input("Press Enter to try again...")

            send_json(sock, {"x": x, "y": y})

        elif msg["action"] == "game_over":
            clear_screen()
            board = msg.get("board", board)
            print_board(board)
            winner = msg["winner"]
            if winner == role:
                print("🎉 YOU WIN!")
            else:
                print("❌ YOU LOSE!")
            break

    sock.close()
