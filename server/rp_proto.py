"""Protocolo de red de Rolplay.net 3.9.0.

Derivado por ingeniería inversa de RPcliente.exe (VB6): rutinas Encriptar (0x7205f0)
y Desencriptar (0x71eaf0). El "cifrado" es una tabla de sustitución por carácter
(table.json). Cada trama es:

    b'#' + encode(texto) + MARK + b'\\r'

Los campos van separados por espacio y las listas terminan siempre en coma.
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "table.json"), encoding="utf-8") as f:
    _t = json.load(f)

DEC = dict(_t["dec"])                 # carácter codificado -> carácter en claro
ENC = {v: k for k, v in DEC.items()}  # inverso
ENC.update({k: v for k, v in _t["enc"].items() if k not in ENC})

MARK = b"4CR\xcfPT"  # terminador de trama (bytes crudos, no se codifica)


def encode(s: str) -> bytes:
    return bytes(ord(ENC.get(c, c)) & 0xFF for c in s)


def decode(b: bytes) -> str:
    return "".join(DEC.get(chr(c), chr(c)) for c in b)


def frame(payload: str) -> bytes:
    return b"#" + encode(payload) + MARK + b"\r"


def split(buf: bytes):
    """Separa tramas completas de un buffer. Devuelve (lista_de_payloads_crudos, resto)."""
    out = []
    while True:
        i = buf.find(MARK)
        if i < 0:
            return out, buf
        m = buf[:i]
        buf = buf[i + len(MARK):].lstrip(b"\r\n")
        if m.startswith(b"#"):
            m = m[1:]
        out.append(m)


if __name__ == "__main__":
    # Autocomprobación con una trama de login capturada del cliente real.
    cap = bytes.fromhex(
        "234e51494b4f57554754434658fd434445464748494a4b4c4d4ed14f5152535455565758595a41422c5f3d26a128"
        "fd636465666768696a6b6c6d6ef16f7172737475767778797a6162dae1e9edf3fac1c9cdd3fded2cd32cdafd47"
        "6f746b7377675f5245fde1e9c92cda2cda2ce1fdc1e9c1dacdfd596b6f667179754f56fdc12ce9fdd3e9dada"
        "344352cf50540d"
    )
    msgs, rest = split(cap)
    text = decode(msgs[0])
    print(text)
    assert frame(text) == cap, "round-trip incorrecto"
    print("round-trip OK")
