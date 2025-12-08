import json

def game_print(games, reviews=None):

    if len(games) == 0:
        print("-----------------------------------")
        print(" No game is uploaded in game shop. ")
        print("-----------------------------------")
        return

    print("--------------------------------")
    for i, g in enumerate(games, 1):
        print(f"{i}. {g['name']}")
        print(f"    version:   {g['version']}")
        print(f"    developer: {g['developer']}")
        print(f"    number of players: {g.get('players')}")
        print(f"    description: {g.get('description')}")
        
        if reviews:
            print('\nReviews: ')
            for r in reviews[i-1]:
                if r[2]:
                    print(f"        {r[0]}: {r[2]}")

        print("--------------------------------")
    