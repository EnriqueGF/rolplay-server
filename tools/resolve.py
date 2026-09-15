"""Mapea cada rama "XXXRPS" de un despachador a su handler rcv_* real.

Uso: python resolve.py <Formulario> <dirección_despachador>
  p. ej.  python resolve.py Principal 0x7c7be0
          python resolve.py Cartas 0x7be700

Necesita analysis/vtmap.json (tools/vtmap.py con el cliente abierto) y
analysis/objtable.json. Escribe analysis/map_<Formulario>.json.

Las entradas de vtable son stubs: `jmp real` para métodos, o
`add [esp+4],N ; jmp [GetMem*/PutMem*]` para variables públicas (this+N).
"""
import json
import os
import re
import sys

from rpexe import IB, Exe

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "analysis")


def follow(exe, va):
    """Devuelve ('var', 'GetMem2@this+0x34') o ('func', addr)."""
    adj = None
    for ins in exe.md.disasm(exe.rd(va, 16), va):
        if ins.mnemonic == "add" and "[esp + 4]" in ins.op_str:
            adj = int(ins.op_str.split(", ")[1], 16)
        if ins.mnemonic == "mov" and ins.op_str.startswith("ecx, 0x"):
            x = int(ins.op_str[5:], 16)
            j = next(exe.md.disasm(exe.rd(x, 8), x))
            m = re.search(r"\[(0x[0-9a-f]+)\]", j.op_str)
            if j.mnemonic == "jmp" and m and int(m.group(1), 16) in exe.iat:
                return "var", f"{exe.iat[int(m.group(1), 16)]}@this+{adj:#x}"
            if j.mnemonic == "jmp" and j.op_str.startswith("0x"):
                return "func", int(j.op_str, 16)
            return "func", x
        if ins.mnemonic == "jmp" and ins.op_str.startswith("0x"):
            return "func", int(ins.op_str, 16)
    return None, None


def resolve(exe, form, disp):
    vtmap = json.load(open(os.path.join(OUT, "vtmap.json")))
    objs = json.load(open(os.path.join(OUT, "objtable.json")))
    info2name = {hex(o["info"]): o["name"] for o in objs}
    fs, fe = exe.func_of(disp)
    cur, obj, out = None, form, {}
    for ins, note in exe.disasm(fs, fe):
        m = re.search(r'; L"([A-Z]+)"$', note)
        if m and (m.group(1).endswith("RPS") or len(m.group(1)) >= 5):
            cur, obj = m.group(1), form
            continue
        if ins.mnemonic == "push" and ins.op_str in info2name:      # __vbaNew2(ObjectInfo, ...)
            obj = info2name[ins.op_str]
        m = re.match(r"dword ptr \[e(?:[a-d]x|si|di|bx|bp) \+ (0x[0-9a-f]+)\]$", ins.op_str)
        if ins.mnemonic == "call" and m and cur and int(m.group(1), 16) >= 0x6F8:
            off = m.group(1)
            stub = vtmap.get(obj, {}).get("methods", {}).get(off)
            kind, real = follow(exe, int(stub, 16)) if stub else (None, None)
            out.setdefault(cur, []).append({
                "obj": obj, "off": off, "stub": stub, "kind": kind,
                "handler": hex(real) if kind == "func" else real,
            })
    return out


def main():
    form, disp = sys.argv[1], int(sys.argv[2], 16)
    out = resolve(Exe(), form, disp)
    for k, v in out.items():
        print(f"{k:26} -> " + ", ".join(f'{x["obj"]}[{x["off"]}]={x["handler"]}' for x in v))
    json.dump(out, open(os.path.join(OUT, f"map_{form}.json"), "w"), indent=0)


if __name__ == "__main__":
    main()
