from tool.common_protocol import send_json, recv_json, send_file, recv_file
from tool.file_manager import FileManager
import os, json, re
import running_control as run_games


# ==========================
# DeveloperHandler
# ==========================

class DeveloperHandler:
    def __init__(self, conn, id, addr):
        self.conn = conn
        self.user_id = id
        self.addr = addr


    def send(self, msg: dict):
        send_json(self.conn, msg)

    def recv(self):
        return recv_json(self.conn)
        
    def menu(self):
        while True:
            choice = self.recv()
            if not choice:
                return
            sel = choice.get("select")
            if sel == 'upload_game':
                self.upload_game()
            elif sel == 'remove_game':
                self.remove_game()
            elif sel == 'list_game':
                self.list_game()
            elif sel == 'logout':
                return
            
    def upload_game(self):
        print(f"{self.addr} : Game upload request")

        # version compare
        game = self.recv().get('game')
        games = self.search_games()
        target_game = [g for g in games if g['name'] == game['name']]

        # duplicate name of game checking
        if len(target_game) != 0 and target_game[0]['developer'] != game['developer']:
            self.send({'status': 'GAME NAME EXIST'})
            return

        # game version checking
        if len(target_game) != 0:
            result, new_version = check_version(game['version'], target_game[0]['version'])
        else:
            result = True
            new_version = game['version']

        self.send({
            'status': 'OK' if result else 'VERSION ERROR',
            'version': new_version
        })

        # uplaod game
        manager = FileManager(self.conn, base_dir='games')
        manager.receive_game()  # receives metadata and files

    def remove_game(self):
        print(f"{self.addr}: {self.user_id}, developer remove_game request.")
        dev_id = self.user_id
        game_dir = "games"

        # receive select game
        msg = self.recv()
        if not msg or "name" not in msg:
            self.send({"status": "FAIL", "msg": "Invalid remove request"})
            return

        target_name = msg["name"]

        # Validate existence + owner + name
        found_path = None
        found_config = None

        for game in os.listdir(game_dir):
            path = os.path.join(game_dir, game)
            cfg_path = os.path.join(path, "config.json")
            if not os.path.isfile(cfg_path):
                continue

            try:
                with open(cfg_path, "r") as f:
                    cfg = json.load(f)
            except:
                continue

            if cfg.get("name") == target_name and cfg.get("developer") == dev_id:
                found_path = path
                found_config = cfg
                break

        if not found_path:
            self.send({"status": "FAIL", "msg": "Game not found or permission denied"})
            return
        
        if run_games.find_running_game(target_name):
            self.send({"status":"FAIL", "msg":"Game is running. Please remove game at another time."})
            return

        # delete game
        try:
            import shutil
            shutil.rmtree(found_path)
            self.send({"status": "OK", "msg": f"Game '{target_name}' removed successfully"})

        except Exception as e:
            self.send({"status": "FAIL", "msg": f"Error removing game: {str(e)}"})

        print(f"{self.addr}: {self.user_id}, developer remove_game successfully.")
 
    def list_game(self):
        print(f"{self.addr}: {self.user_id} developer list game.")
        owned_games = self.search_games(mode=1)
        self.send({"status": "OK", "games": owned_games})

    def search_games(self, mode = 0):
        game_dir = "games"
        owned_games = []

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

                if mode:
                    if cfg['developer'] == self.user_id:
                        owned_games.append(cfg) 
                else:
                    owned_games.append(cfg) 
                    
        else:
            owned_games = []

        return owned_games
    
    
# ==========================
# Helpful Function
# ==========================

def check_version(uploaded: str, current: str):
    """
    Compare uploaded version to current version.

    Returns:
        (is_valid, next_version)

    is_valid:
        True  -> uploaded version can be used (uploaded >= current)
        False -> uploaded version too old or invalid

    next_version:
        If invalid or older, returns incremented patch of current version.
        If valid and newer, returns uploaded version.
    """

    def is_valid_format(v):
        return re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", v) is not None

    def parse(v):
        return tuple(map(int, v.split(".")))

    def increment_patch(v):
        major, minor, patch = parse(v)
        return f"{major}.{minor}.{patch + 1}"

    # If either version format is invalid → fail and auto bump
    if not is_valid_format(uploaded) or not is_valid_format(current):
        return (False, increment_patch(current))

    up = parse(uploaded)
    cur = parse(current)

    if up > cur:
        return (True, uploaded)
    else:
        return (False, increment_patch(current))
