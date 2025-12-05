import socket, json
import os
from tool.common_protocol import send_json, recv_json, send_file, recv_file
from server_client import ServerClient
from tool.file_manager import FileManager, list_games
from tool.game import game_print
from template.create_template import create_template

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 50001

# ==================================================
#                 Developer Client
# ==================================================
class DeveloperClient:
    def __init__(self):
        self.client = ServerClient(SERVER_HOST, SERVER_PORT, auth_type="developer")

    # -------------------------
    # Menu Utility
    # -------------------------
    def choose(self, menu: dict):
        print(f"\n===== {menu['title']} =====")
        for i, item in enumerate(menu["items"], 1):
            print(f"{i}. {item}")

        while True:
            try:
                sel = int(input("Select: "))
                if 1 <= sel <= len(menu["items"]):
                    return sel
            except:
                pass
            print("Invalid selection. Try again.")

    # -------------------------
    # Login / Register
    # -------------------------
    def login_or_register(self):
        return self.client.login_or_register()
    
    # -------------------------
    # Developer Menu
    # -------------------------
    def developer_menu(self):
        while True:
            menu = ["Create New Game", "Upload Game", "Remove Game", "My Upload Game List", "Logout"]
            sel = self.choose({'title': 'Developer Menu', 'items':menu}) - 1

            if menu[sel] == "Create New Game":
                create_template(self.client.id)
            elif menu[sel] == "Upload Game":
                self.upload_game()
            elif menu[sel] == "Remove Game":
                self.remove_game()
            elif menu[sel] == "My Upload Game List":
                self.list_game()
            elif menu[sel] == "Logout":
                self.client.logout()
                break

    def upload_game(self):
        # List local games
        games = list_games('games', type=None)
        if not games:
            print("No games found in local 'games' folder.")
            return

        # Ask developer to choose
        self.client.send({"select":"upload_game"})
        games_name = [g['name'] for g in games]
        sel = self.choose({"title": "Games", "items": games_name})
        selected_game = games[sel - 1]

        # version check
        selected_game['developer'] = self.client.id
        self.client.send({'game':selected_game})
        resp = self.client.recv()
        
        # setting version into new version
        if resp['status'] == 'VERSION ERROR':
            print("Game Version Error. Automatically update version.")
            self.rewrite_version(selected_game, resp['version'])
        elif resp['status'] == 'GAME NAME EXIST':
            print("Others developer is uploaded game with same name.")
            print("Please modify your game name.")
            return

        # upload game
        manager = FileManager(self.client.conn, self.client.id, base_dir="games")
        manager.upload_game(selected_game.get('name'))  # uploads folder and metadata

    def remove_game(self):

        games = self.list_game()

        if len(games) == 0:
            return

        # Provide selection
        self.client.send({"select":"remove_game"})
        sel = int(input("Select game index to remove: ")) - 1
        if sel < 0 or sel >= len(games):
            print("Invalid selection.")
            return

        game_name = games[sel].get('name')

        # Send selected game to server
        self.client.send({"name": game_name})

        # Receive result
        result = self.client.recv()
        print(result.get("msg"))

    def list_game(self):
        self.client.send({"select":"list_game"})
        resp = self.client.recv()

        if resp.get("status") != "OK":
            print("Error fetching game list.")
            return games
        
        games = resp.get("games", [])
        if len(games) == 0:    
            print("============================")
            print("You didn't uploaded games.  ")        
            print("============================")
            return games
        
        game_print(games=games)
        return games

    # -------------------------
    # Helpful Function
    # -------------------------
    
    def rewrite_version(self, game, version):
        # Update version in memory
        game['version'] = version

        # Path: games/<game_name>/config.json
        game_dir = os.path.join("games", game['name'])
        config_path = os.path.join(game_dir, "config.json")

        # Ensure directory exists
        os.makedirs(game_dir, exist_ok=True)

        # Write JSON back to file
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(game, f, indent=4, ensure_ascii=False)

        return True

    # -------------------------
    # Main Run
    # -------------------------
    def start(self):
        self.client.connect()

        while True:
            action = self.login_or_register()
            if action == 'Login':
                break
    
        self.developer_menu()
        self.client.close()


# ==================================================
#                   Entry Point
# ==================================================
if __name__ == "__main__":
    from sys import argv
    SERVER_HOST = argv[1]
    SERVER_PORT = int(argv[2])

    client = DeveloperClient()
    client.start()
