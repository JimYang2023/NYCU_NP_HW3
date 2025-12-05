import sqlite3
import socket
import threading
from tool.common_protocol import send_json, recv_json

DB_NAME = "game_system.db"
HOST = "0.0.0.0"
PORT = 50000

# =============================
#   Database Manager Class
# =============================
class DatabaseManager:
    def __init__(self, db_name: str):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_tables()

    def init_tables(self):
        """Initialize all required tables"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT NOT NULL,
                auth TEXT NOT NULL,
                password TEXT NOT NULL,
                state INTEGER DEFAULT 0,
                room INTEGER DEFAULT NULL,
                PRIMARY KEY (id, auth)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                master TEXT NOT NULL,
                players INTEGER DEFAULT 0,
                game TEXT NOT NULL,
                port INTEGER DEFAULT -1
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                name TEXT NOT NULL,
                developer TEXT NOT NULL
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS records (
                player_id TEXT NOT NULL,
                game TEXT NOT NULL,
                message TEXT,
                PRIMARY KEY (player_id, game)
            )
        """)

        self.conn.commit()

    # =============================
    #   User Operations
    # =============================
    def register_user(self, uid, password, auth):
        try:
            self.cursor.execute(
                "INSERT INTO users (id, password, auth) VALUES (?, ?, ?)",
                (uid, password, auth)
            )
            self.conn.commit()
            return {"status": "OK", "msg": "Register success"}
        except sqlite3.IntegrityError:
            return {"status": "FAIL", "msg": "User already exists"}

    def login_user(self, uid, password, auth):
        """
        Login a user with ID, password, and auth type ('player' or 'developer')
        """
        self.cursor.execute(
            "SELECT password, state FROM users WHERE id=? AND auth=?",
            (uid,auth)
        )
        data = self.cursor.fetchone()

        if not data:
            return {"status": "FAIL", "msg": "User not found"}

        real_pw, state = data

        # if real_auth != auth:
        #     return {"status": "FAIL", "msg": f"Auth type mismatch: expected {real_auth}"}

        if state == 1:
            return {"status": "FAIL", "msg": "User already logged in"}

        if real_pw != password:
            return {"status": "FAIL", "msg": "Password incorrect"}

        self.cursor.execute(
            "UPDATE users SET state = 1 WHERE id = ? AND auth = ?",
            (uid,auth)
        )
        self.conn.commit()
        return {"status": "OK", "msg": "Login success"}

    def logout_user(self, uid, auth):
        """
        Logout a user with ID and auth type ('player' or 'developer')
        """
        self.cursor.execute(
            "UPDATE users SET state = 0 WHERE id=? AND auth=?",
            (uid,auth)
        )
        self.conn.commit()
        return {"status": "OK", "msg": "Logout success"}

    def get_players(self):
        self.cursor.execute("SELECT id, state, room FROM users WHERE auth='player'")
        data = self.cursor.fetchall()
        return {"status":"OK","players":data}

    # =============================
    #   Room Operations
    # =============================
    def get_rooms(self):
        self.cursor.execute("SELECT id, master, players, game, port FROM rooms")
        data = self.cursor.fetchall()
        return {"status": "OK", "rooms": data}

    def create_room(self, master_id, game, port):
        self.cursor.execute(
            "INSERT INTO rooms (master, players, game, port) VALUES (?, ?, ?, ?)",
            (master_id, 0, game, port)
        )
        self.conn.commit()
        room_id = self.cursor.lastrowid

        # update user's room
        self.cursor.execute(
            "UPDATE users SET room = ? WHERE id = ?",
            (room_id, master_id)
        )
        self.conn.commit()
        return {"status": "OK", "msg": f"Room #{room_id} created", "room_id": room_id}

    def update_room(self, room_id, players, player_id=None):
        self.cursor.execute(
            "UPDATE rooms SET players = ? WHERE id = ?",
            (players, room_id)
        )

        if player_id:
            self.cursor.execute(
                "UPDATE users SET room = ? WHERE id = ?",
                (room_id, player_id)
            )

        self.conn.commit()
        return {"status": "OK"}
    
    def remove_room(self, room_id):
        # Check if room exists
        self.cursor.execute("SELECT id FROM rooms WHERE id = ?", (room_id,))
        room = self.cursor.fetchone()
        if room is None:
            return {"status": "ERROR", "msg": "Room does not exist"}

        # Remove all players from this room
        self.cursor.execute(
            "UPDATE users SET room = NULL WHERE room = ?",
            (room_id,)
        )

        # Delete the room
        self.cursor.execute(
            "DELETE FROM rooms WHERE id = ?",
            (room_id,)
        )

        self.conn.commit()

        return {"status": "OK", "msg": f"Room #{room_id} removed"}

    def player_exit_room(self, player_id):
        # Find player's room
        self.cursor.execute("SELECT room FROM users WHERE id = ?", (player_id,))
        row = self.cursor.fetchone()

        if row is None:
            return {"status": "ERROR", "msg": "Player not found"}

        room_id = row[0]

        # Player was not in any room
        if room_id is None or room_id == -1:
            return {"status": "OK", "msg": "Player was not in a room"}

        # Get current players count
        self.cursor.execute("SELECT players FROM rooms WHERE id = ?", (room_id,))
        room = self.cursor.fetchone()
        if room is None:
            return {"status": "OK", "msg": "Room already removed"}

        players = room[0] - 1  # decrease count

        # Update user room to NULL
        self.cursor.execute(
            "UPDATE users SET room = NULL WHERE id = ?",
            (player_id,)
        )

        # If room empty → remove
        if players <= 0:
            self.conn.commit()
            return self.remove_room(room_id)

        # Otherwise just update count
        self.cursor.execute(
            "UPDATE rooms SET players = ? WHERE id = ?",
            (players, room_id)
        )

        self.conn.commit()

        return {"status": "OK", "msg": f"Player left room #{room_id}"}

    def set_room_port(self, room_id, port):
        self.cursor.execute(
            "UPDATE rooms SET port = ? WHERE id = ?",
            (port, room_id)
        )

        self.conn.commit()
        return {"status":"OK"}

    # =============================
    #   Game Operations
    # =============================
    def add_game(self, gid, version, name, dev):
        try:
            self.cursor.execute(
                "INSERT INTO games VALUES (?, ?, ?, ?)",
                (gid, version, name, dev)
            )
            self.conn.commit()
            return {"status": "OK", "msg": "Game added"}
        except sqlite3.IntegrityError:
            return {"status": "FAIL", "msg": "Game already exists"}

    def remove_game(self, gid):
        self.cursor.execute(
            "DELETE FROM games WHERE id = ?",
            (gid,)
        )
        self.conn.commit()
        return {"status": "OK", "msg": "Game removed"}

    # =============================
    #   Record
    # =============================

    def add_record(self, id, game):
        self.cursor.execute("""
            INSERT OR IGNORE INTO records (player_id, game, message)
            VALUES (?, ?, NULL)
        """, (id, game))
        self.conn.commit()
        return {"status":"OK"}

    def get_record(self, id=None, game=None):
        # Base query
        query = """
            SELECT player_id, game, message
            FROM records
        """
        
        # Dynamic WHERE clause
        conditions = []
        params = []

        if id is not None:
            conditions.append("player_id = ?")
            params.append(id)

        if game is not None:
            conditions.append("game = ?")
            params.append(game)

        # If any conditions exist, attach them
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        self.cursor.execute(query, tuple(params))
        record = self.cursor.fetchall()

        return {"status": "OK", "record": record}


    def set_message(self, id, game, msg):
        self.cursor.execute("""
            INSERT INTO records (player_id, game, message)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id, game)
            DO UPDATE SET message=excluded.message
        """, (id, game, msg))
        self.conn.commit()
        return {"status":"OK"}

# =============================
#       TCP DB Server
# =============================
class DBServer:
    def __init__(self, host, port, db_name):
        self.host = host
        self.port = port
        self.db = DatabaseManager(db_name)

    def handle_client(self, conn, addr):
        print(f"[DB SERVER] Client connected: {addr}")

        try:
            while True:
                request = recv_json(conn)
                if request is None:
                    break

                response = self.process_request(request)
                send_json(conn, response)

        except Exception as e:
            print("[DB SERVER ERROR]", e)
        finally:
            conn.close()
            print(f"[DB SERVER] Client disconnected: {addr}")

    def process_request(self, req):
        cmd = req.get("cmd")
        print(f"[DB Server] Accept request {cmd}")
        match cmd:
            # User
            case "REGISTER":
                return self.db.register_user(
                    req["id"], req["password"], req["auth"]
                )

            case "LOGIN":
                return self.db.login_user(req["id"], req["password"], req["auth"])

            case "LOGOUT":
                return self.db.logout_user(req["id"], req["auth"])

            case "GET_PLAYERS":
                return self.db.get_players()

            # Rooms
            case "GET_ROOMS":
                return self.db.get_rooms()

            case "CREATE_ROOM":
                return self.db.create_room(req["master"], req["game"], req["port"])

            case "UPDATE_ROOM":
                return self.db.update_room(req["room_id"], req["players"], req.get('player_id'))

            case "PLAYER_EXIT_ROOM":
                return self.db.player_exit_room(req["id"])
            
            case "SET_PORT":
                return self.db.set_room_port(req["id"], req["port"])

            # Game
            case "ADD_GAME":
                return self.db.add_game(
                    req["id"], req["version"], req["name"], req["developer"]
                )

            case "REMOVE_GAME":
                return self.db.remove_game(req["id"])
            
            # Record & Review
            case "ADD_RECORD":
                return self.db.add_record(req.get('id'), req.get('game'))
            
            case "GET_RECORD":
                return self.db.get_record(req.get('id'), req.get('game'))
            
            case "SER_MSG":
                return self.db.set_message(req.get('id'), req.get('game'), req.get('msg'))

        return {"status": "FAIL", "msg": "Invalid command"}

    def start(self):
        print(f"[DB SERVER] Starting on {self.host}:{self.port}")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.host, self.port))
        sock.listen()

        try:
            while True:
                conn, addr = sock.accept()
                thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr),
                    daemon=True
                )
                thread.start()
        except KeyboardInterrupt:
            print("\n[DB SERVER] Shutting down...")
        finally:
            sock.close()


if __name__ == "__main__":
    from sys import argv
    if len(argv) != 3:
        print("Usage: python db_server.py <PORT> <DB_NAME>")
        exit(1)

    PORT = int(argv[1])
    DB_NAME = argv[2]

    server = DBServer(HOST, PORT, DB_NAME)
    server.start()
