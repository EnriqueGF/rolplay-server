"""Servidor de Rolplay.net reconstruido.

Uso:  python rpserver.py [--port 10002] [--log server.log]

Los handlers viven en handlers.py y se recargan en caliente en cada mensaje,
así que se pueden editar sin reiniciar el servidor ni el cliente.
"""
import argparse
import datetime
import importlib
import os
import socket
import sys
import threading
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rp_proto import decode, frame, split  # noqa: E402
import handlers  # noqa: E402

STATE = {"users": {}}   # estado compartido entre conexiones (persiste entre recargas)
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stdout.log")
_log = open(LOG_FILE, "a", encoding="utf-8", buffering=1)


def L(s: str):
    line = f"[{datetime.datetime.now():%H:%M:%S}] {s}"
    try:
        if _log:
            _log.write(line + "\n")
            _log.flush()
    except Exception:
        pass
    print(line, flush=True)


class Conn:
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self.user = None

    def send(self, payload: str):
        L(f"  -> {payload!r}")
        try:
            self.sock.sendall(frame(payload))
        except OSError as e:
            L(f"  error enviando: {e}")


def serve_client(sock, addr, reload_handlers):
    cn = Conn(sock, addr)
    L(f"CONNECT {addr}")
    buf = b""
    try:
        while True:
            data = sock.recv(65536)
            if not data:
                break
            buf += data
            msgs, buf = split(buf)
            for m in msgs:
                text = decode(m)
                L(f"<- {text!r}")
                parts = text.split(" ")
                cmd, args = parts[0], parts[1:]
                try:
                    if reload_handlers:
                        importlib.reload(handlers)
                    h = getattr(handlers, "h_" + cmd, None)
                    if h is None:
                        L(f"  ?? sin handler: {cmd} {args}")
                        continue
                    for reply in h(cn, args, STATE):
                        cn.send(reply)
                except Exception:
                    L(traceback.format_exc())
    except OSError as e:
        L(f"ERR {e}")
    if cn.user:
        STATE["users"].pop(cn.user, None)
    L("CLOSE")


def main():
    global _log
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=10002)
    ap.add_argument("--log", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.log"))
    ap.add_argument("--no-reload", action="store_true", help="no recargar handlers.py en cada mensaje")
    a = ap.parse_args()
    _log = open(a.log, "a", encoding="utf-8")
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", a.port))
    s.listen(5)
    L(f"LISTEN {a.port}")
    while True:
        c, addr = s.accept()
        threading.Thread(target=serve_client, args=(c, addr, not a.no_reload), daemon=True).start()


if __name__ == "__main__":
    main()
