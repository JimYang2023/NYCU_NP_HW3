GAME_NAME = "Tetris"
DEVELOPER = "developer1"
VERSION = "1.0.0"
DESCRIPTION = "This game support for two player. Block will increase speed in game process. If one of player game over, game end."
PLAYERS = 2

'''
This template file supports both server and player startup.
When executing, the program will call player_start() or server_start().
Actual game logic should be placed in additional files.

⚠ DO NOT move or rename this file.
'''

import socket
import threading
import time
import json
import os, sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)


# Import custom protocol
from tool.common_protocol import (
    send_json, recv_json,
    send_file, recv_file
)

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 10000

class Game:
    def __init__(self, name, version, num_player):
        # These will be replaced by config.json content
        self.name = name
        self.version = version
        self.num_player = num_player

        # Main TCP socket (only used if needed by game logic)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Load config (override constructor values)
        self.get_information()

    # ======================================================
    #  INTERNAL FUNCTION
    # ======================================================

    def get_information(self):
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, "config.json")

            if not os.path.exists(config_path):
                print("[GameTemplate] No config.json found. Using defaults.")
                return

            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.name = data.get("name", self.name)
            self.version = data.get("version", self.version)
            self.num_player = data.get("players", self.num_player)

            print(f"[GameTemplate] Loaded config: name={self.name}, version={self.version}, players={self.num_player}")

        except Exception as e:
            print("[GameTemplate] Error reading config.json:", e)

    def setIP(self, host, port):
        global SERVER_HOST, SERVER_PORT    
        SERVER_HOST = host if host is not None else '0.0.0.0'
        SERVER_PORT = port

    # ======================================================
    #  START FUNCTIONS (ENTRY POINTS)
    # ======================================================

    def player_start(self):
        # TODO: developer need to call function
        
        from client import player_run
        player_run(SERVER_HOST, SERVER_PORT)

    def server_start(self):
        # TODO: developer need to call server side function
        from server import server_run
        server_run('0.0.0.0',SERVER_PORT)
