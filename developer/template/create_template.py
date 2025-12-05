import json
import os

TEMPLATE_FILE = "template/game_template.py"


def create_template(dev):
    print("=== Game Template Generator ===")

    name = input("Game Name: ").strip()
    ver = input("Version (e.g., 1.0.0): ").strip()
    desc = input("Description: ").strip()
    players = int(input("Number of players: ").strip())  # <-- convert to int

    # Folder Name
    folder = name.replace(" ", " ")
    folder = os.path.join("games", folder)
    os.makedirs(folder, exist_ok=True)

    # Read template content
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    # ---------- Insert constants at TOP of file ----------
    header = (
        f'GAME_NAME = "{name}"\n'
        f'DEVELOPER = "{dev}"\n'
        f'VERSION = "{ver}"\n'
        f'DESCRIPTION = "{desc}"\n'
        f'PLAYERS = {players}\n\n'
    )

    replaced = header + template

    # Write main.py
    main_path = os.path.join(folder, "main.py")
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(replaced)

    # Write config.json
    config_path = os.path.join(folder, "config.json")
    with open(config_path, "w", encoding="utf-8") as meta:
        json.dump({
            "name": name,
            "developer": dev,
            "version": ver,
            "description": desc,
            "players": players
        }, meta, indent=4)

    print(f"\n[OK] Game template created in folder: {folder}")
    print(" - main.py generated")
    print(" - config.json generated")
