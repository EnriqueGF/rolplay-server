"""Utilidades comunes para analizar RPcliente.exe.

La ruta del ejecutable se toma de la variable de entorno RPCLIENTE o, si no
existe, de ../game/RPcliente.exe relativo a este repositorio.
"""
import bisect
import os
import re

import capstone
import pefile

IB = 0x400000
TXT = (0x401000, 0x7CE000)
DATA = (0x7CE000, 0x7E4000)


def exe_path():
    p = os.environ.get("RPCLIENTE")
    if not p:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "game", "RPcliente.exe")
    if not os.path.exists(p):
        raise SystemExit(f"No encuentro RPcliente.exe ({p}); define la variable RPCLIENTE")
    return p


class Exe:
    def __init__(self, path=None):
        self.pe = pefile.PE(path or exe_path())
        self.data = self.pe.__data__
        self.iat = {
            i.address: (i.name or b"ord%d" % i.ordinal).decode()
            for e in self.pe.DIRECTORY_ENTRY_IMPORT
            for i in e.imports
        }
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        pro8 = rb"\x55\x8b\xec\x83\xec.\x68\xf6\x42\x40\x00"
        pro32 = rb"\x55\x8b\xec\x81\xec....\x68\xf6\x42\x40\x00"
        self.starts = sorted(
            {m.start() + IB for m in re.finditer(pro8, self.data)}
            | {m.start() + IB for m in re.finditer(pro32, self.data)}
        )

    def rd(self, va, n):
        return self.pe.get_data(va - IB, n)

    def bstr(self, va, maxlen=120):
        b = self.rd(va, maxlen * 2)
        s = ""
        for k in range(0, len(b) - 1, 2):
            cu = b[k] | (b[k + 1] << 8)
            if cu == 0:
                break
            s += chr(cu)
        return s

    def func_of(self, va):
        i = bisect.bisect_right(self.starts, va) - 1
        return self.starts[i], self.starts[i + 1]

    def note(self, ins):
        m = re.search(r"\[(0x[0-9a-f]+)\]", ins.op_str)
        if m and int(m.group(1), 16) in self.iat:
            return "  ; " + self.iat[int(m.group(1), 16)]
        m2 = re.search(r"\b(0x4[0-9a-f]{5})\b", ins.op_str)
        if m2:
            s = self.bstr(int(m2.group(1), 16))
            if s and all(0x20 <= ord(c) < 0x7F for c in s):
                return f'  ; L"{s}"'
        return ""

    def disasm(self, a, b):
        for ins in self.md.disasm(self.rd(a, b - a), a):
            yield ins, self.note(ins)
