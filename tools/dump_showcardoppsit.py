import sys, re
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = 0x73fa90, 0x741000
print(f"SHOWCARDOPPSITACT strings in {fs:#x}..{fe:#x}:")
for ins, note in exe.disasm(fs, fe):
    m = re.search(r'; L"([^"]+)"', note)
    if m:
        print(f"  {ins.address:#x}: {m.group(1)!r}")
