import socket
import threading
import time
import queue
import random
from tool.common_protocol import send_json, recv_json
from tetris_logic import TetrisGame

HOST = "0.0.0.0"
PORT = 9000
FPS = 20
FRAME_TIME = 1.0 / FPS


class PlayerThread(threading.Thread):
    def __init__(self, conn, addr, pid, game):
        super().__init__(daemon=True)
        self.conn = conn
        self.addr = addr
        self.pid = pid
        self.game = game
        self.cmd_queue = queue.Queue()
        self.running = True

    def run(self):
        """Background thread to receive commands from client"""
        while self.running:
            try:
                msg = recv_json(self.conn)
                if msg.get("action") == "disconnect":
                    self.game.gameover = True
                    self.running = False
                    break
                else:
                    self.cmd_queue.put(msg)
            except Exception as e:
                print(f"[SERVER] Player {self.pid} receive error: {e}")
                self.running = False
                self.game.gameover = True
                break

    def get_cmd(self):
        """Get next command from queue (non-blocking)"""
        try:
            return self.cmd_queue.get_nowait()
        except queue.Empty:
            return None

    def send(self, obj):
        """Send data to client"""
        try:
            send_json(self.conn, obj)
        except Exception as e:
            print(f"[SERVER] Player {self.pid} send error: {e}")
            self.running = False

    def close(self):
        """Close connection"""
        self.running = False
        try:
            self.conn.close()
        except:
            pass


def server_run(ip=HOST, port=PORT):
    serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serv.bind((ip, port))
    serv.listen(2)

    print(f"[SERVER] Tetris server started on {ip}:{port}")
    print("[SERVER] Waiting for Player 1...")
    c1, a1 = serv.accept()
    print(f"[SERVER] Player 1 connected from {a1}")
    send_json(c1, {"action": "waiting", "msg": "Waiting for opponent..."})

    print("[SERVER] Waiting for Player 2...")
    c2, a2 = serv.accept()
    print(f"[SERVER] Player 2 connected from {a2}")

    # Notify both players game is starting
    send_json(c1, {"action": "start", "role": 1})
    send_json(c2, {"action": "start", "role": 2})

    # Create game instances for each player
    seed = random.randint(0, 1000)
    g1 = TetrisGame(seed=seed)
    g2 = TetrisGame(seed=seed)


    # Create player threads
    p1 = PlayerThread(c1, a1, "P1", g1)
    p2 = PlayerThread(c2, a2, "P2", g2)
    p1.start()
    p2.start()

    print("[SERVER] Game started!")

    # Main game loop
    frame_count = 0
    while True:
        start = time.time()

        # Update game physics
        g1.update()
        g2.update()

        # Apply all pending commands
        cmd = p1.get_cmd()
        while cmd:
            apply_cmd(g1, cmd)
            cmd = p1.get_cmd()
        
        cmd = p2.get_cmd()
        while cmd:
            apply_cmd(g2, cmd)
            cmd = p2.get_cmd()

        # Check for game over
        if check_gameover(p1, p2, g1, g2):
            break

        # Send game state to both players
        frame = {
            "action": "frame",
            "p1": g1.get_game_state("P1", "P2"),
            "p2": g2.get_game_state("P2", "P1"),
        }

        p1.send(frame)
        p2.send(frame)

        frame_count += 1
        if frame_count % 100 == 0:
            print(f"[SERVER] Frame {frame_count} - P1: {g1.score} pts, P2: {g2.score} pts")

        # Maintain frame rate
        dt = time.time() - start
        time.sleep(max(0, FRAME_TIME - dt))

    # Cleanup
    print("[SERVER] Game finished. Cleaning up...")
    time.sleep(1)  # Give time for final messages to send
    p1.close()
    p2.close()
    p1.join(timeout=2)
    p2.join(timeout=2)
    serv.close()
    print("[SERVER] Server closed.")


def apply_cmd(game, cmd):
    """Apply a command to the game"""
    if not cmd:
        return
    act = cmd.get("action")
    if act == "left":
        game.move(-1)
    elif act == "right":
        game.move(1)
    elif act == "rotate":
        game.rotate()
    elif act == "soft_drop":
        game.soft_drop()
    elif act == "hard_drop":
        game.hard_drop()


def check_gameover(p1, p2, g1, g2):
    """Check if game is over and notify players"""
    if g1.gameover and g2.gameover:
        print("[SERVER] Both players lost - DRAW")
        p1.send({"action": "game_over", "result": "draw"})
        p2.send({"action": "game_over", "result": "draw"})
        return True
    if g1.gameover:
        print("[SERVER] Player 1 lost - Player 2 WINS")
        p1.send({"action": "game_over", "result": "lose"})
        p2.send({"action": "game_over", "result": "win"})
        return True
    if g2.gameover:
        print("[SERVER] Player 2 lost - Player 1 WINS")
        p1.send({"action": "game_over", "result": "win"})
        p2.send({"action": "game_over", "result": "lose"})
        return True
    return False
