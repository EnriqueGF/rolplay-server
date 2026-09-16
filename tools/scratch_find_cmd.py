import sys
sys.path.insert(0, 'tools')
from rpexe import Exe
import re

exe = Exe()
disp_fs, disp_fe = exe.func_of(0x7c7be0)
cur = None
for ins, note in exe.disasm(disp_fs, disp_fe):
    m = re.search(r'; L"([A-Z0-9_]+)"', note)
    if m:
        cur = m.group(1)
    if ins.address in (0x7c8198, 0x7c9f32, 0x7ca086, 0x7ca30a):
        print(f"{str(cur):20} @ {ins.address:#x}: {ins.mnemonic} {ins.op_str} {note}")
