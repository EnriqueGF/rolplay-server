import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = exe.func_of(0x7365e0)
print(f"GETCARDHANDRPS func {fs:#x}..{fe:#x} (len {fe-fs})")
# Let's inspect the first 150 instructions of GETCARDHANDRPS
c = 0
for ins, note in exe.disasm(fs, fs + 0x400):
    if note or ins.mnemonic in ("call", "cmp", "push", "mov") and any(k in ins.op_str for k in ("0x4", "0x7", "ebp")):
        print(f"  {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:30} {note}")
        c += 1
        if c > 50: break
