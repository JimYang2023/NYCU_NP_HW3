
RUNNING_GAME = []

def set_running_game(game_name):
    RUNNING_GAME.append(game_name)

def remove_running_game(game_name):
    try:
        RUNNING_GAME.remove(game_name)
    except:
        print("[RUNNING GAME] running game remove error. Skip action.")

def find_running_game(game_name):
    return game_name in RUNNING_GAME