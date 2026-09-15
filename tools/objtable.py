"""Vuelca la ObjectTable de VB6 de RPcliente.exe (formularios y sus ObjectInfo).

Genera analysis/objtable.json. Nota: los arrays lpMethods están corrompidos a
propósito por el ofuscador con el que se compiló el cliente; no usarlos.
"""
import json
import os
import struct

from rpexe import IB, Exe

OBJECT_TABLE = 0x42F2EC  # lpObjectTable del ObjectInfo de rmGblComunicador (0x41070c)


def main():
    exe = Exe()
    d = exe.data

    def dw(va):
        return struct.unpack_from("<I", d, va - IB)[0]

    def w(va):
        return struct.unpack_from("<H", d, va - IB)[0]

    def cstr(va):
        e = d.find(b"\0", va - IB)
        return d[va - IB:e].decode("latin-1")

    total = w(OBJECT_TABLE + 0x2A)
    arr = dw(OBJECT_TABLE + 0x30)
    objs = []
    for i in range(total):
        o = arr + 0x30 * i
        objs.append({"idx": i, "obj": o, "info": dw(o), "name": cstr(dw(o + 0x18)), "mcount": dw(o + 0x1C)})
        print(f"[{i:2}] {objs[-1]['name']:22} info={objs[-1]['info']:#x}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analysis", "objtable.json")
    json.dump(objs, open(out, "w"), indent=0)


if __name__ == "__main__":
    main()
