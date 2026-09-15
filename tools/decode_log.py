"""Decodifica el log.log que escribe el cliente (tráfico recibido, ofuscado).

Uso: python decode_log.py "C:\\Program Files (x86)\\Rolplay\\log.log"
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server"))
from rp_proto import decode  # noqa: E402

raw = open(sys.argv[1], "rb").read()
for line in raw.split(b"\r\n"):
    if line.startswith(b">in "):
        print("IN      ", repr(decode(line[4:])))
    elif line.startswith(b">>process "):
        print("PROCESS ", repr(decode(line[10:])))
    elif line.strip():
        print("OTHER   ", repr(decode(line)))
