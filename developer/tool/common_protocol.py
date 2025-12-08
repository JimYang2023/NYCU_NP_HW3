# common_protocol.py
import json
import struct
import socket
import select

def send_json(conn: socket.socket, obj: dict):
    data = json.dumps(obj).encode('utf-8')
    conn.sendall(struct.pack('>I', len(data)))
    conn.sendall(data)

def recv_json(conn: socket.socket):
    hdr = conn.recv(4)
    if not hdr or len(hdr) < 4:
        return None
    length = struct.unpack('>I', hdr)[0]
    data = b''
    while len(data) < length:
        chunk = conn.recv(length - len(data))
        if not chunk:
            raise ConnectionError("Connection closed while receiving JSON")
        data += chunk
    return json.loads(data.decode('utf-8'))

def send_file(conn: socket.socket, filename: str, filebytes: bytes):
    # first send metadata JSON
    meta = {"_type": "file", "filename": filename, "size": len(filebytes)}
    send_json(conn, meta)
    # then raw bytes (no length prefix) for the file body
    conn.sendall(filebytes)

def recv_file(conn: socket.socket, dest_path: str):
    meta = recv_json(conn)
    if not meta or meta.get("_type") != "file":
        raise ValueError("Expected file metadata")
    size = meta["size"]
    received = 0
    with open(dest_path, "wb") as f:
        while received < size:
            chunk = conn.recv(min(4096, size - received))
            if not chunk:
                raise ConnectionError("Connection closed during file transfer")
            f.write(chunk)
            received += len(chunk)
    return meta["filename"], size
