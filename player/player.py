import socket, os, sys
from tool.common_protocol import send_json, recv_json, send_file, recv_file
from server_client import ServerClient
from tool.file_manager import FileManager, list_games, remove_games
from tool.game import game_print
from tool.game_control import GameControl
from typing import Tuple

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 50001

# ==================================================
#                   Player Client
# ==================================================

class PlayerClient:
    def __init__(self):
        self.client = ServerClient(SERVER_HOST, SERVER_PORT)

    # -------------------------
    # Hard-coded main menu
    # -------------------------

    def choose(self, menu_title, items):
        print(f"\n===== {menu_title} =====")
        for i, item in enumerate(items, 1):
            print(f"{i}. {item}")

        while True:
            try:
                sel = int(input("Select: "))
                if 1 <= sel <= len(items):
                    return sel
            except:
                pass
            print("Invalid selection. Try again.")

    # -------------------------
    # Login or Register Flow
    # -------------------------

    def login_or_register(self):
        return self.client.login_or_register()

    # -------------------------
    # Main Player Menu
    # -------------------------

    def player_menu(self):
        while True:
            menu_items = ["Player List","Room Menu","Game Shop", "Logout"]
            sel = self.choose("Player Menu", menu_items) -1 

            # room menu
            if menu_items[sel] == "Player List":
                self.player_list()
            elif menu_items[sel] == "Room Menu":
                self.room_menu()
            # game shop
            elif menu_items[sel] == "Game Shop":
                self.game_shop()
            # logout
            elif menu_items[sel] == "Logout":
                self.client.logout()
                break

    def player_list(self):
        self.client.send({"select":"list_player"})
        resp = self.client.recv()

        players = resp.get("players")

        if players == None:
            print("player_list error: players not in response.")

        print("\n=========================")
        print("Online Players:")
        count = 0
        for player in players:
            if player[1] == 1 and player[0] != self.client.id:
                print(f"    {player[0]}: "+ (f"{player[2]}" if player[2] != -1 else f"not in room" ))
                count += 1
        if count == 0:
            print("    There is no player online.")
        print("=========================")
        
    # -------------------------
    # Room Menu
    # -------------------------

    def room_menu(self):
        os.system('clear')
        print("=============================")
        print("         Room Menu           ")
        print("=============================")

        menu = ["Create Room", "Enter Room", "List Room", "Exit"]

        while True:
            sel = self.choose("Room Menu", menu) - 1

            if sel == 0:   # Create Room
                room_id = self.create_room()
                if not room_id: 
                    continue
                game = self.enter_room(room_id)
                if room_id != -1 and game:
                    self.game_stage(game)

            elif sel == 1: # Enter Room
                self.list_room()
                game = self.enter_room(-1)
                if game:
                    self.game_stage(game)

            elif sel == 2: # List Room
                self.list_room()

            elif sel == 3: # Exit
                return

    def create_room(self) -> int:
        self.client.send({"select": "create_room"})

        # Select game
        base_path = os.path.join("downloads", self.client.id)
        games = list_games(base_path, type=None)
        game_print(games)

        try:
            sel = int(input("Select game index: ")) - 1
            if sel < 0 or sel >= len(games):
                print("Invalid selection.")
                self.client.send({"status":"Error"})
                self.client.recv()
                return None
        except:
            print("Invalid selection.")
            self.client.send({"status":"Error"})
            self.client.recv()
            return None

        target_game = games[sel]

        # Request server version check
        self.client.send({"req": "check_version", "game": target_game})
        resp = self.client.recv()

        # If server says update required
        if resp["status"] == "Version Error":
            print(resp["msg"])
            FileManager(self.client.conn, base_dir=base_path).receive_game()

        elif resp["status"] == "Game Remove":
            print(resp["msg"])
            return None

        # Create room response
        resp = self.client.recv()
        print(resp["msg"])
        return resp["room_id"]

    # return: success enter, game_name
    def enter_room(self, room_id) -> str:
        self.client.send({"select": "enter_room"})

        if room_id == -1:
            room_id = int(input("Enter room ID (-1 for exit): "))
            if room_id == -1:
                self.client.send({"status":"Fail"})
                return None

        self.client.send({"room": room_id})
        resp = self.client.recv()
        print("arrive first receiev.")

        if resp["status"] == "Fail":
            print(resp["msg"])
            return None

        # Version compare
        target_game = resp["game"]
        base_path = os.path.join("downloads", self.client.id)

        # tell server whether local version is correct
        self.check_and_update_game(target_game, base_path)
        print("arrive check game and update")

        # enter confirmation
        resp = self.client.recv()
        print("arrive enter information")
        print(resp["msg"])

        if resp["status"] == "OK":
            self.room_id = room_id
            return target_game['name']

        return None

    # send room id and automatically update game into latest version
    def check_and_update_game(self, target_game, base_path) -> None:
        """Check local version vs server version & update automatically."""
        
        games = list_games(base_path, type=None)
        local = [g for g in games if g['name'] == target_game['name']]

        manager = FileManager(self.client.conn, base_dir=base_path)

        if not local:
            self.client.send({"status":"Game Error"})
            print(f"[Version] Local copy missing → Downloading...")
            manager.receive_game()
        elif local[0]['version'] != target_game['version']:
            self.client.send({"status":"Game Error"})
            print(f"[Version] Version mismatch → Updating...")
            manager.receive_game()
        else:
            self.client.send({"status":"OK"})

    def list_room(self):
        self.client.send({"select": 'list_room'})
        resp = self.client.recv()
        print('\n===============================')
        print("         Current Rooms           ")
        print('===============================')
        for room in resp["rooms"]:
            print(f"Room #{room[0]}:")
            print(f"    Master: {room[1]}")
            print(f"    Current Player in room: {room[2]}")
            print(f"    Game: {room[3]}")
            print(f"-------------------------------")
        if len(resp["rooms"]) == 0:
            print(f"There is no room in server.")
        print('===============================')
    
    # -------------------------
    # Game Shop
    # -------------------------
    
    def game_shop(self):
        self.client.send({"select":'game_shop'})
        os.system("clear")

        # get game list

        resp = self.client.recv()
        games = resp['games']
        reviews = resp.get('reviews')

        print("==============================")
        print("         Game Shop          ")
        print("==============================")
        game_print(games=games, reviews=reviews)

        while True:
            menu_items = ["Download Game", "Remove Game","Current Downloads Games", "Game Review","Exit"]
            sel = self.choose("Game Shop", menu_items)

            # download request
            if sel == 1: 
                self.download_game(games)
            # remove game
            elif sel == 2: 
                self.remove_game()
            # list download game
            elif sel == 3:
                self.show_current_game()
            elif sel == 4:
                self.game_review()
            # Exit request
            elif sel == 5:
                self.client.send({"action":"exit"})
                return
    
    def download_game(self, games):
        target_game = input("Please input game name which you want to download: ")
                
        if target_game not in [game['name'] for game in games]:            
            # self.client.send({"action":"exit"})
            print("Invalid game name.")
            print("Please input game name in above list.")
            return

        self.client.send({"action":"download","game":target_game})
        resp = self.client.recv()
        
        if resp['status'] == 'OK':
            base_dir = os.path.join("downloads",self.client.id)
            manager = FileManager(conn = self.client.conn, base_dir=base_dir)
            manager.receive_game()
        else:
            print(f"Download Fail. {resp['msg']}")

    def remove_game(self):
        path = os.path.join('downloads',self.client.id)
        games = list_games(base_dir=path, type=None)
        if len(games) == 0:
            print("\nNo game is download.")
            return
        
        game_print(games=games)

        try:
            sel = int(input("Please select id of game: ")) - 1
            name = games[sel].get('name')
            if remove_games(base_dir=path, game_name=name):
                print(f"Game [{name}] remove success.")
            else:
                print(f"Game [{name}] remove fail.")
        except:
            print("Invalid input, please try again.")

    def show_current_game(self):
        print('=================================')
        print('     Current Download Games      ')
        print('=================================')
        path = os.path.join('downloads', self.client.id)
        games = list_games(base_dir=path, type=None)
        game_print(games=games)

    def game_review(self):
        print('=================================')
        print('         Game Reviews            ')
        print('=================================')
        
        # Request review mode
        self.client.send({'action': 'review'})

        # Receive all game records
        response = self.client.recv()
        records = response['record']

        # No records found
        if len(records) == 0:
            print("No game record found. Nothing to review.")
            return 

        # player selection
        if len(records) > 1:
            print("\nYou have multiple game records:")
            for idx, (player_id, game, message) in enumerate(records, 1):
                print(f"{idx}. {game}  (Message: {message})")

            # Input selection
            while True:
                try:
                    choice = int(input("\nSelect a game to review (number): "))
                    if 1 <= choice <= len(records):
                        break
                    else:
                        print("Invalid selection. Try again.")
                except ValueError:
                    print("Please enter a valid number.")
            
            player_id, game, message = records[choice - 1]

        else:
            player_id, game, message = records[0]

        print(f"\nSelected Game: {game}")
        print(f"Existing Message: {message}\n")

        # Input new review message
        new_review = input("Enter your updated review message: ")

        # Send review update request
        self.client.send({
            'action': 'set_review',
            'id': player_id,
            'game': game,
            'message': new_review
        })

        # Receive server response
        result = self.client.recv()
        print("\nServer Response:", result.get('status', 'Unknown response'))

    # -------------------------
    # Game Stage
    # -------------------------

    def game_stage(self, game_name) -> None: 

        room_selection = ["Wating State", "Exit Room"]
        sel = self.choose("Room Action", room_selection) - 1
        self.client.send({"room_action":sel})
        if sel == 1:
            return

        print("========================")
        print("  Enter in game stage.  ")     
        print("========================")

        # get port
        port = self.client.recv().get('port')
        print(f"Get game port: {port}")

        path = os.path.join("downloads", self.client.id)
        GameControl(host=SERVER_HOST, port=port, game_name=game_name, base_dir=path).start_player()
    
        self.client.send({"select":"end_game"})

    # -------------------------
    # Main Running
    # -------------------------
    
    def start(self):
        self.client.connect()

        # login and register
        while True:
            action = self.login_or_register()
            if action == 'Login':
                break

        # After login: player menu
        self.player_menu()
        self.client.close()

# ==================================================
#                   Entry Point
# ==================================================
if __name__ == "__main__":
    from sys import argv

    if len(argv) >= 3:
        SERVER_HOST = argv[1]
        SERVER_PORT = int(argv[2])

    client = PlayerClient()
    client.start()
