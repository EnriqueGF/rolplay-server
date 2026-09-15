import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
# Let's search around 0x786000..0x787500
for fs, fe in zip(exe.starts, exe.starts[1:]):
    if 0x786500 <= fs <= 0x787500:
        strs = []
        for ins, note in exe.disasm(fs, fe):
            if note and 'L"' in note:
                strs.append(note.strip())
        print(f"{fs:#x}..{fe:#x} (len {fe-fs}): {strs[:4]}")
