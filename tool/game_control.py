import os
import importlib.util
import sys

class GameControl:

    def __init__(self, game_name, host='0.0.0.0', port=10000, base_dir="games"):
        self.game_name = game_name
        self.game_path = os.path.join(base_dir, game_name, "main.py")
        self.host = host
        self.port = port
        self.game_instance = None

    def _load_game_module(self):
        if not os.path.exists(self.game_path):
            raise FileNotFoundError(f"Game not found: {self.game_path}")

        module_name = f"game_{self.game_name}"

        # remove module
        game_dir = os.path.dirname(os.path.abspath(self.game_path))
        to_delete = []
        for mod_name, module in list(sys.modules.items()):
            mod_file = getattr(module, "__file__", None)
            if mod_file:
                mod_file = os.path.abspath(mod_file)
                if mod_file.startswith(game_dir):
                    to_delete.append(mod_name)

        for mod_name in to_delete:
            del sys.modules[mod_name]

        # load new module
        spec = importlib.util.spec_from_file_location(module_name, self.game_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "Game"):
            raise RuntimeError("main.py does not contain class Game")

        return module.Game


    # -----------------------------------------------------
    # Create new game instance every time
    # -----------------------------------------------------
    def prepare_game(self):
        GameClass = self._load_game_module()

        self.game_instance = GameClass(
            name="",
            version="",
            num_player=0,
        )

        return self.game_instance

    # -----------------------------------------------------
    # Start player mode (always reload)
    # -----------------------------------------------------
    def start_player(self):
        self.prepare_game()
        
        self.game_instance.setIP(self.host, self.port)
        print(f"[GameControl] Starting player mode for {self.game_name}")
        self.game_instance.player_start()

    # -----------------------------------------------------
    # Start server mode (always reload)
    # -----------------------------------------------------
    def start_server(self):
        self.prepare_game()

        self.game_instance.setIP(self.host, self.port)
        print(f"[GameControl] Starting server mode for {self.game_name}")
        self.game_instance.server_start()
