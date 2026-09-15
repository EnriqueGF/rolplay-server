"""Extrae la tabla de sustitución de Encriptar/Desencriptar de RPcliente.exe.

Cada rutina es un Select Case por carácter: compara con un literal BSTR y emite
Chr(N) o un literal. Escribe server/table.json {"enc": {...}, "dec": {...}}.
"""
import json
import os
import re

from rpexe import Exe

DESENCRIPTAR = (0x71EAF0, 0x7205F0)   # codificado -> claro
ENCRIPTAR = (0x7205F0, 0x721FE0)      # claro -> codificado


def parse(exe, a, b):
    esi = None
    table = {}
    key = lastlit = pend = None
    state = 0
    for ins in exe.md.disasm(exe.rd(a, b - a), a):
        m = re.search(r"\[(0x[0-9a-f]+)\]", ins.op_str)
        if ins.mnemonic == "mov" and ins.op_str.startswith("esi, dword ptr [") and m and int(m.group(1), 16) in exe.iat:
            esi = exe.iat[int(m.group(1), 16)]
        if ins.mnemonic == "mov" and re.match(r"dword ptr \[ebp - 0x[0-9a-f]+\], 0x4[0-9a-f]{5}$", ins.op_str):
            lastlit = exe.bstr(int(ins.op_str.split(", ")[1], 16))
            continue
        if ins.mnemonic == "mov" and re.match(r"dword ptr \[ebp - 0x[0-9a-f]+\], 0x8008$", ins.op_str) and lastlit is not None:
            key, state = lastlit, 1
            continue
        is_tst = ins.mnemonic == "call" and (
            (ins.op_str == "esi" and esi == "__vbaVarTstEq") or (m and exe.iat.get(int(m.group(1), 16)) == "__vbaVarTstEq"))
        if state == 1 and is_tst:
            state = 2
            continue
        if state == 2:
            if ins.mnemonic == "push" and re.fullmatch(r"-?(0x[0-9a-f]+|\d+)", ins.op_str):
                pend, state = int(ins.op_str, 0) & 0xFF, 3
            elif ins.mnemonic == "mov" and re.match(r"edx, 0x4[0-9a-f]{5}$", ins.op_str):
                table[key] = exe.bstr(int(ins.op_str.split(", ")[1], 16))
                state = 0
            elif ins.mnemonic in ("call", "jmp") and not ins.op_str.startswith("dword ptr [0x4010a0]"):
                state = 0
        elif state == 3:
            if ins.mnemonic == "jmp" or (ins.mnemonic == "call" and m and exe.iat.get(int(m.group(1), 16)) == "ord608"):
                table[key] = chr(pend)
                state = 0
            elif ins.mnemonic == "call" and ins.op_str == "esi":
                state = 0
    return table


def main():
    exe = Exe()
    dec = parse(exe, *DESENCRIPTAR)
    enc = parse(exe, *ENCRIPTAR)
    print(f"dec={len(dec)} enc={len(enc)}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server", "table.json")
    json.dump({"enc": enc, "dec": dec}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main()
