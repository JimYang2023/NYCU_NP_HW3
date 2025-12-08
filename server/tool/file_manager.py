import os
import json, shutil
from tool.common_protocol import send_json, recv_json, send_file, recv_file

# Path Setting
DIR_NAME = 'games'
CONFIG_FILE = 'config.json'


# ==================================================
#                  FileManger
# ==================================================

class FileManager:
    def __init__(self, conn, developer_id = None, base_dir=None):
        """
        conn: TCP socket (ServerClient.conn)
        base_dir: root directory for client-side game folders
        """
        self.conn = conn
        self.developer_id = developer_id
        self.base_dir = base_dir or os.getcwd()  # client only

    # -------------------------
    # Client: find folder by game name
    # -------------------------
    def _find_game_dir(self, game_name):
        for root, dirs, files in os.walk(self.base_dir):
            if CONFIG_FILE in files:
                try:
                    with open(os.path.join(root, CONFIG_FILE), "r") as f:
                        config = json.load(f)
                    if config.get("name") == game_name:
                        return root
                except:
                    continue
        return None

    # -------------------------
    # Validate config
    # -------------------------
    def _check_config(self, folder_path):
        config_file = os.path.join(folder_path, CONFIG_FILE)
        if not os.path.isfile(config_file):
            return False, "Missing game_config.json"
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
        except:
            return False, "Invalid JSON"
        for key in ["name", "version"]:
            if key not in config:
                return False, f"Missing key: {key}"

        if self.developer_id:
            config["developer"] = self.developer_id
            with open(config_file, "w") as f:
                json.dump(config, f, indent=4)

        return True, config

    # -------------------------
    # Upload folder recursively (client)
    # -------------------------
    def _upload_folder(self, folder_path):
        # Tell server that file transfer is starting
        send_json(self.conn, {"_type": "FILE_TRANSFER_BEGIN"})

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, folder_path)

                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                    send_file(self.conn, rel_path, file_bytes)

        # Tell server all files are done
        send_json(self.conn, {"_type": "FILE_TRANSFER_END"})

        print(f"Folder '{folder_path}' uploaded successfully.")

    # -------------------------
    # Receive folder (server)
    # -------------------------
    def _receive_folder(self, save_dir):
        os.makedirs(save_dir, exist_ok=True)
        print(f"Receiving files into '{save_dir}'...")

        # Wait for BEGIN signal
        msg = recv_json(self.conn)
        if not msg or msg.get("_type") != "FILE_TRANSFER_BEGIN":
            raise ValueError("Expected FILE_TRANSFER_BEGIN")

        while True:
            header = recv_json(self.conn)

            # If END, stop receiving
            if header.get("_type") == "FILE_TRANSFER_END":
                print("File transfer complete.")
                break

            # Must be file metadata
            if header.get("_type") != "file":
                raise ValueError("Expected file metadata")

            filename = header["filename"]
            size = header["size"]

            # Receive file body
            final_path = os.path.join(save_dir, filename)
            os.makedirs(os.path.dirname(final_path), exist_ok=True)

            received = 0
            with open(final_path, "wb") as f:
                while received < size:
                    chunk = self.conn.recv(min(4096, size - received))
                    if not chunk:
                        raise ConnectionError("Connection dropped during file receive")
                    f.write(chunk)
                    received += len(chunk)

            print(f"Received file: {filename}")

        print(f"All files for '{save_dir}' received.")

    def _delete_pycache(self):
        for root, dirs, files in os.walk(self.base_dir):
            for d in dirs[:]:
                if d == "__pycache__":
                    pycache_path = os.path.join(root, d)
                    try:
                        shutil.rmtree(pycache_path)
                        print(f"Deleted: {pycache_path}")
                    except Exception as e:
                        print(f"Failed to delete {pycache_path}: {e}")

    # =========================
    # Client function
    # =========================
    def upload_game(self, game_name=None):
        if not game_name:
            game_name = input("Enter Game Name to upload: ")

        folder_path = self._find_game_dir(game_name)
        if not folder_path:
            print("Game folder not found.")
            return False

        valid, config_or_msg = self._check_config(folder_path)
        if not valid:
            print(f"Config error: {config_or_msg}")
            return False

        
        print("============================")
        print("     Game Uplaoad Start     ")
        print("============================")
        
        # Send metadata using send_json
        send_json(self.conn, {"name": config_or_msg["name"], "version": config_or_msg["version"]})

        # Wait server OK
        resp = recv_json(self.conn)
        if not resp or resp.get("status") != "OK":
            print("Server rejected metadata:", resp.get("msg"))
            return False

        # delete __pycache__
        self._delete_pycache()

        # Upload all files
        self._upload_folder(folder_path)

        print("============================")
        print("     Game Upload Finished   ")
        print("============================")
        
        return True

    # =========================
    # Server function
    # =========================
    def receive_game(self):
        print("============================")
        print("     Game Download Start    ")
        print("============================")
        # Receive metadata using recv_json
        metadata = recv_json(self.conn)
        if not metadata or "name" not in metadata or "version" not in metadata:
            send_json(self.conn, {"status": "FAIL", "msg": "Invalid metadata"})
            return False

        game_name = metadata["name"]
        save_dir = os.path.join(self.base_dir, game_name)
        send_json(self.conn, {"status": "OK", "msg": "Ready to receive files"})

        # Receive all files
        self._delete_pycache()
        try:
            print("[FileManager] Remove Game Files.")
            remove_games(self.base_dir, game_name)
        except:
            print("[FileManager] There is nothing to remove.")

        self._receive_folder(save_dir)
        
        print("============================")
        print("     Game Download End      ")
        print("============================")
        return True


# ==================================================
#             Useful Function
# ==================================================

def list_games(base_dir="games", config_name=CONFIG_FILE, type='name'):
    """
    Scan the base_dir for all game folders, read each folder's config.json,
    and return a list of game names found inside the configuration.

    Returns:
        game_list (list): ["My RPG", "Space Shooter", ...]
    """
    if not os.path.isdir(base_dir):
        print(f"Base directory '{base_dir}' does not exist.")
        return []

    game_list = []

    for folder in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder)

        if not os.path.isdir(folder_path):
            continue

        config_path = os.path.join(folder_path, config_name)

        if not os.path.isfile(config_path):
            # Skip folders without config
            continue

        # Load config.json
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            # Extract game name
            if type is None or type in config:
                if type:
                    game_list.append(config[type])
                else:
                    game_list.append(config)
            else:
                print(f"Warning: {config_path} missing 'name' field, skipping.")
        except Exception as e:
            print(f"Error reading {config_path}: {e}")

    # return sorted(game_list)
    return game_list


def remove_games(base_dir='games', game_name=''):
    for game in os.listdir(base_dir):
        path = os.path.join(base_dir, game)
        cfg_path = os.path.join(path, "config.json")
        if not os.path.isfile(cfg_path):
            continue

        try:
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
        except:
            continue

        if cfg.get("name") == game_name:
            found_path = path
            found_config = cfg
            break

    try:
        import shutil
        shutil.rmtree(found_path)
        return True
        
    except Exception as e:
        return False