import sys, re
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
print("Strings in 0x73e960..0x73fa90:")
for ins, note in exe.disasm(0x73e960, 0x73fa90):
    m = re.search(r'; L"([^"]+)"', note)
    if m:
        print(f"  {ins.address:#x}: {m.group(1)!r}")
