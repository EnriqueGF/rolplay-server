"""Desensambla la función que contiene una dirección de RPcliente.exe.

Uso: python funcdump.py [-b] 0x765810 [0x...]
  -b  modo breve: solo llamadas, saltos, comparaciones, inmediatos y cadenas.
"""
import re
import sys

from rpexe import Exe

BRIEF_MN = {"call", "jmp", "ret", "cmp", "add", "sub", "xor", "imul", "idiv", "and", "or", "shl", "shr", "sar"}


def keep(ins, note):
    if note or ins.mnemonic in BRIEF_MN or ins.mnemonic.startswith("j"):
        return True
    if re.match(r"push -?(0x[0-9a-f]+|\d+)$", ins.op_str) and ins.mnemonic == "push":
        return True
    return bool("word ptr" in ins.op_str and re.search(r", (0x)?[0-9a-f]+$", ins.op_str))


def main():
    brief = "-b" in sys.argv
    exe = Exe()
    for a in sys.argv[1:]:
        if a.startswith("-"):
            continue
        va = int(a, 16)
        fs, fe = exe.func_of(va)
        print(f"\n===== func {fs:#x}..{fe:#x} (contiene {va:#x}) =====")
        for ins, note in exe.disasm(fs, fe):
            if brief and not keep(ins, note):
                continue
            print(f"{ins.address:#x}: {ins.mnemonic} {ins.op_str}{note}")


if __name__ == "__main__":
    main()
