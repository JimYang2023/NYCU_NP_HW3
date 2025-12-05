import socket
import json
import os
from tool.common_protocol import send_json, recv_json, send_file, recv_file

# ==================================================
#           Helper: Basic TCP Client
# ==================================================
class ServerClient:
    def __init__(self, host, port, auth_type="player"):
        """
        auth_type: "player" or "developer"
        """
        self.host = host
        self.port = port
        self.auth_type = auth_type
        self.conn = None

    # -------------------------
    # Basic TCP Functions
    # -------------------------
    def connect(self):
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((self.host, self.port))

    def send(self, obj: dict):
        send_json(self.conn, obj)

    def recv(self):
        return recv_json(self.conn)

    def send_file(self, filename: str, filebytes: bytes):
        send_file(self.conn, filename, filebytes)

    def recv_file(self, dest_path: str):
        return recv_file(self.conn, dest_path)

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    # ==================================================
    #               Login / Register
    # ==================================================
    def login_or_register(self):
        """Ask user Login/Register until success, return ('Login'/'Register')."""

        def choose(title, items):
            print(f"\n===== {title} =====")
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

        while True:
            choice = choose("Main Menu", ["Login", "Register"])

            if choice == 1:
                if self.login():
                    return "Login"
                # else:            
                #     print("Account or password error.")
            elif choice == 2:
                if self.register():
                    return "Register"

    # -------------------------
    # Login
    # -------------------------
    def login(self):
        print("============ Login ============")

        # Tell server we want to login
        self.send({"action": "LOGIN_REQUEST"})

        req = self.recv()
        if not req or req.get("request") != "LOGIN_INFO":
            print("Server rejected login.")
            return False

        uid = input("ID: ")
        pw = input("Password: ")

        # Send login info
        self.send({
            "id": uid,
            "password": pw,
            "auth": self.auth_type
        })

        self.id = uid

        resp = self.recv()
        print(resp.get("msg", ""))

        return resp.get("status") == "OK"

    # -------------------------
    # Register
    # -------------------------
    def register(self):
        print("============ Register ============")

        # Request register flow
        self.send({"action": "REGISTER_REQUEST"})

        req = self.recv()
        if not req or req.get("request") != "REGISTER_INFO":
            print("Server rejected register.")
            return False

        uid = input("New ID: ")
        pw = input("Password: ")

        self.send({
            "id": uid,
            "password": pw,
            "auth": self.auth_type
        })

        resp = self.recv()
        print(resp.get("msg", ""))

        return resp.get("status") == "OK"

    # -------------------------
    # Logout
    # -------------------------
    def logout(self):
        self.send({'select':'logout'})
        resp = self.recv()  
        print("\n========================")
        print(resp["msg"])
        print("========================")
        return True
