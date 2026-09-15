"""Lee de la memoria del cliente en ejecución la vtable de cada formulario VB6.

Las vtables de formularios se rellenan en tiempo de ejecución en .data, así que
no se pueden obtener del archivo. Hay que tener RPcliente.exe abierto (basta con
la ventana de login; los formularios que aún no se han instanciado no aparecen).

Genera analysis/vtmap.json: nombre de formulario -> {vtable, inst, methods{offset: stub}}.
Necesita analysis/objtable.json (ver objtable.py).
"""
import ctypes
import json
import os
import struct
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "analysis")
TXT = (0x401000, 0x7CE000)
DATA = (0x7CE000, 0x7E4000)

k32 = ctypes.windll.kernel32
k32.OpenProcess.restype = ctypes.c_void_p
k32.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]


def open_client():
    out = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq RPcliente.exe", "/FO", "CSV"]).decode("latin-1")
    lines = [l for l in out.strip().splitlines() if l.startswith('"RPcliente.exe"')]
    if not lines:
        raise SystemExit("RPcliente.exe no está en ejecución")
    pid = int(lines[0].split('","')[1])
    h = k32.OpenProcess(0x410, False, pid)
    if not h:
        raise SystemExit("OpenProcess falló")
    return h


def reader(h):
    def rd(a, n):
        b = ctypes.create_string_buffer(n)
        g = ctypes.c_size_t()
        return b.raw[:g.value] if k32.ReadProcessMemory(h, a, b, n, ctypes.byref(g)) else None

    def dw(a):
        b = rd(a, 4)
        return struct.unpack("<I", b)[0] if b and len(b) == 4 else None

    return rd, dw


def main():
    rd, dw = reader(open_client())
    objs = json.load(open(os.path.join(OUT, "objtable.json")))
    res = {}
    for o in objs:
        # ObjectInfo+0x1c -> puntero -> estructura -> instancia -> vtable
        p = dw(o["info"] + 0x1C)
        st = dw(p) if p and p > 0x10000 else None
        inst = dw(st) if st and st > 0x10000 else None
        vt = dw(inst) if inst and inst > 0x10000 else None
        if not vt or not (DATA[0] <= vt < DATA[1]):
            res[o["name"]] = {"vtable": None}
            continue
        tbl = rd(vt, 0x1200) or b""
        ents = struct.unpack_from("<%dI" % (len(tbl) // 4), tbl, 0)
        meth = {}
        k = 0x6F8 // 4  # 446 entradas de runtime; después vienen variables públicas y métodos
        while k < len(ents) and TXT[0] <= ents[k] < TXT[1]:
            meth[hex(k * 4)] = hex(ents[k])
            k += 1
        res[o["name"]] = {"vtable": hex(vt), "inst": hex(inst), "methods": meth}
        print(f"{o['name']:22} vtable={vt:#x} métodos públicos={len(meth)}")
    json.dump(res, open(os.path.join(OUT, "vtmap.json"), "w"), indent=0)


if __name__ == "__main__":
    main()
