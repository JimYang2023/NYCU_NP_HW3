import socket
import threading
from tool.common_protocol import send_json, recv_json

# ==================================================
#        Helper: DB Communication (Client)
# ==================================================
class DBClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def send_request(self, req: dict):
        """Send JSON request to DB server using length-prefixed protocol"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            send_json(sock, req)
            resp = recv_json(sock)
            sock.close()
            return resp
        except Exception as e:
            return {"status": "FAIL", "msg": f"DB ERROR: {e}"}