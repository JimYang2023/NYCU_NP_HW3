import socket
import threading
import os, json
from tool.common_protocol import send_json, recv_json
from db_client import DBClient
from tool.file_manager import FileManager, list_games
from developer_handler import DeveloperHandler
from tool.game_control import GameControl
import running_control as run_game
from typing import Tuple

DB_HOST = "127.0.0.1"
DB_PORT = 50000
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 50001


# ==================================================
#           Useful Function
# ==================================================

def find_free_port():
    """
    Bind a temporary socket to port 0 to let the OS assign a free port.
    Returns the port number and closes the socket.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))  # Bind to port 0 → OS assigns free port
    port = s.getsockname()[1]
    s.close()
    return port

# ==================================================
#           Player & Developer Connection
# ==================================================
class ClientHandler:
    def __init__(self, conn, addr, db_client):
        self.conn = conn
        self.addr = addr
        self.db = db_client
        self.user_id = None
        self.auth = None
        print(f"[SERVER] Client connected: {addr}")

    # -------------------------
    # Basic Network Send/Recv
    # -------------------------

    def send(self, msg: dict):
        send_json(self.conn, msg)

    def recv(self):
        return recv_json(self.conn)

    # -------------------------
    # Login & Register
    # -------------------------

    def login_menu(self):
        while True:
            choice = self.recv()
            if not choice:
                return False

            sel = choice["action"]
            if sel == 'LOGIN_REQUEST':
                result = self.handle_login()
                if result:
                    break
            elif sel == 'REGISTER_REQUEST':
                result = self.handle_register()
            else:
                result = False

    def handle_login(self):
        print(f"[{self.addr}] login request")
        self.send({"request": "LOGIN_INFO"})
        info = self.recv()

        resp = self.db.send_request({
            "cmd": "LOGIN",
            "id": info["id"],
            "password": info["password"],
            "auth": info["auth"]
        })
        self.send(resp)
        if resp["status"] == "OK":
            self.user_id = info["id"]
            self.auth = info["auth"]
            return True
        return False

    def handle_register(self):
        print(f"[{self.addr}] register request")
        self.send({"request": "REGISTER_INFO"})
        info = self.recv()
        resp = self.db.send_request({
            "cmd": "REGISTER",
            "id": info["id"],
            "password": info["password"],
            "auth": info["auth"]
        })
        self.send(resp)
        return resp["status"] == "OK"

    # -------------------------
    # Main Menu
    # -------------------------

    def main_page(self):
        if self.auth == "player":
            self.player_menu()
        elif self.auth == "developer":
            DeveloperHandler(self.conn, self.user_id, self.addr).menu()
        self.logout()

    # -------------------------
    # Player Menu
    # -------------------------
    
    def player_menu(self):
        game_name = None

        while True:
            choice = self.recv()
            if not choice:
                return

            sel = choice["select"]
            if sel == 'create_room':
                print(f"[{self.addr}]: {self.user_id} create room request.")
                game_name, port = self.create_room()
                if game_name is not None:
                    print(f"Get game port: {port}")
                    controller = GameControl(host="0.0.0.0", port=port, game_name=game_name)
                    self.game_thread = threading.Thread(
                    target=controller.start_server,
                        daemon=True
                    )
                    self.game_thread.start()

            elif sel == 'enter_room':
                print(f"[{self.addr}]: {self.user_id} enter room request.")
                game_name, port = self.enter_room()
                if game_name != None:
                    resp = self.recv()
                    if resp['room_action'] == 0:
                        run_game.set_running_game(game_name)
                        self.send({'port':port})
                    else:
                        self.db.send_request({"cmd": "PLAYER_EXIT_ROOM", "id": self.user_id})

            elif sel == 'list_room':        
                print(f"[{self.addr}]: {self.user_id} check room request.")
                self.check_rooms()

            elif sel == 'logout':        
                print(f"[{self.addr}]: {self.user_id} logout request.")
                return

            elif sel == 'game_shop':
                print(f"[{self.addr}]: {self.user_id} game shop request.")
                self.game_shop()
            
            elif sel == 'list_player':
                print(f"[{self.addr}]: {self.user_id} player list request.")
                self.send(self.db.send_request({"cmd":"GET_PLAYERS"}))
            
            elif sel == 'end_game':
                try:
                    if self.game_thread:
                        self.game_thread.join(timeout=2)
                        print("Game thread terminated.")
                except:
                    print("Game thread has been closed.")
                run_game.remove_running_game(game_name)

                resp = self.db.send_request({"cmd": "PLAYER_EXIT_ROOM", "id": self.user_id})

                if resp['status'] != 'OK':
                    print(f"[ERROR MESSAGE] end game {resp.get('msg')}")

                self.db.send_request({
                    "cmd": "ADD_RECORD",
                    "id": self.user_id,
                    "game": game_name
                })

    # -------------------------
    # Room Management
    # -------------------------

    # return game_name, port
    def create_room(self) -> Tuple[str, int] :
        target_game = self.recv().get("game")

        if target_game == None:
            self.send({"status":"Fail", "msg":"Invalid game data"})
            return None, -1

        game_cfg = self.get_game_config(target_game['name'])

        if not game_cfg:
            self.send({"status":"Game Remove", "msg":"Game is removed"})
            return None, -1

        if game_cfg['version'] != target_game['version']:
            self.send({"status":"Version Error", "msg":"Updating game..."})
            self.update_version(target_game['name'], "games")
        else:
            self.send({"status":"OK"})

        # finally create room
        port = find_free_port()

        resp = self.db.send_request({
            "cmd": "CREATE_ROOM",
            "master": self.user_id,
            "game": target_game['name'],
            "port": port
        })
        self.send(resp)

        return target_game['name'], port

    # return game_name, port
    def enter_room(self) -> Tuple[str, int]:
        room_id = self.recv().get("room")

        # exit room
        if room_id == None:
            return None, -1

        # get room info
        rooms = self.db.send_request({"cmd": "GET_ROOMS"})["rooms"]
        match = [r for r in rooms if r[0] == room_id]

        if not match:
            self.send({"status": "Fail", "msg": "Room not found"})
            return None, -1

        room = match[0]
        game_name = room[3]

        game_cfg = self.get_game_config(game_name)
        if not game_cfg:
            self.send({"status":"Fail", "msg":"Game removed from server"})
            return None, -1

        # send server game info to client
        self.send({"status":"OK", "game":game_cfg})

        # wait for client to check its version
        resp = self.recv()
        if resp["status"] == "Game Error":  
            self.update_version(game_name, "games")

        # update room player count
        updated = room[2] + 1
        self.db.send_request({
            "cmd":"UPDATE_ROOM",
            "room_id": room_id,
            "players": updated,
            "player_id": self.user_id
        })

        self.send({"status":"OK", "msg":f"Entered room #{room_id}"})
        return game_name, room[4]

    def check_rooms(self) -> None:
        resp = self.db.send_request({"cmd": "GET_ROOMS"})
        self.send(resp)

    def update_version(self, target_game_name, base_dir) -> None:
        FileManager(self.conn, base_dir=base_dir).upload_game(target_game_name)

    def get_game_config(self, game_name, game_dir="games") -> dict:
        """
        Search the server's game directory for a game with the given name
        and return its config.json contents as a dict.

        Returns:
            dict  - if game exists
            None  - if not found or config invalid
        """

        for folder in os.listdir(game_dir):
            game_path = os.path.join(game_dir, folder)
            config_path = os.path.join(game_path, "config.json")

            if not os.path.isfile(config_path):
                continue

            try:
                with open(config_path, "r") as f:
                    cfg = json.load(f)
            except:
                continue

            # match by config name
            if cfg.get("name") == game_name:
                return cfg

        # not found
        return None
        
    # -------------------------
    # Logout
    # -------------------------

    def logout(self):
        print(f"[{self.addr}] {self.user_id} Logout Request")
        self.db.send_request({"cmd": "PLAYER_EXIT_ROOM", "id": self.user_id})
        resp = self.db.send_request({"cmd": "LOGOUT", "id": self.user_id, "auth":self.auth})
        self.send(resp)

    # -------------------------
    # Game Shop
    # -------------------------

    def game_shop(self):
        # search games
        game_dir = "games"
        owned_games = []
        game_review = []

        if os.path.isdir(game_dir):
            for game in os.listdir(game_dir):
                path = os.path.join(game_dir, game)
                config_path = os.path.join(path, "config.json")
                if not os.path.isfile(config_path):
                    continue

                try:
                    with open(config_path, "r") as f:
                        cfg = json.load(f)
                except:
                    continue

                owned_games.append(cfg)
                review = self.db.send_request({'cmd':'GET_RECORD','game':cfg['name']})
                game_review.append(review.get('record'))
        else:
            owned_games = []

        self.send({'status':'OK', 'games':owned_games, 'reviews':game_review})

        while True:
            # Download and Exit
            resp = self.recv()
            print(resp)
            if resp['action'] == 'download':
                print(f"[{self.addr}]: {self.user_id} game download request")
                self.player_download(resp['game'])
            if resp['action'] == 'review':
                print(f"[{self.addr}]: {self.user_id} game review request")
                self.game_review()
            elif resp['action'] == 'exit':
                print(f"[{self.addr}]: {self.user_id} game shop exit.")
                return

    def player_download(self, target_game):

        games = list_games("games")
        if target_game in games:
            self.send({"status":"OK"})
            manager = FileManager(conn=self.conn, base_dir="games")
            manager.upload_game(target_game)
        else:
            self.send({"status":"Fail", "msg":"Game is removed from game shop."})

    def game_review(self):
        
        # Fetch record from DB
        resp = self.db.send_request({'cmd': 'GET_RECORD','id': self.user_id})

        # Send record back to player
        self.send(resp)

        if len(resp['record']) == 0:
            return

        # Receive updated review request
        req = self.recv()
        
        if req.get('action') != 'set_review':
            self.send({"status": "ERROR", "msg": "Invalid action"})
            return

        # Update the review in DB
        update_result = self.db.send_request({
            'cmd': 'SER_MSG',
            'id': req['id'],
            'game': req['game'],
            'msg': req['message']
        })

        # Return result to player
        self.send({"status": "OK" if update_result else "FAILED"})


# ==================================================
#                    Main Server
# ==================================================
class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.db = DBClient(DB_HOST, DB_PORT)

    def start(self):
        print(f"[SERVER] Running at {self.host}:{self.port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.host, self.port))
        sock.listen()

        try:
            while True:
                conn, addr = sock.accept()
                thread = threading.Thread(target=self.client_thread, args=(conn, addr), daemon=True)
                thread.start()
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down...")
        finally:
            sock.close()

    def client_thread(self, conn, addr):
        handler = ClientHandler(conn, addr, self.db)

        # action
        try:
            handler.login_menu()
            print(f"{addr} : Login success as {handler.auth}")
            handler.main_page()
        except Exception as e:
            print(f"[DEBUG MESSAGE] {e}")
            conn.close()
        resp = self.db.send_request({"cmd": "LOGOUT", "id": handler.user_id, "auth":handler.auth})

        print(f"[SERVER] Client disconnected: {addr}")

if __name__ == "__main__":
    from sys import argv
    if len(argv) != 3:
        print("Usage: python server.py <DB_PORT> <SERVER_PORT>")
        exit(1)

    DB_PORT = int(argv[1])
    SERVER_PORT = int(argv[2])
    server = Server(SERVER_HOST, SERVER_PORT)
    server.start()
