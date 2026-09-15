from rpexe import Exe
import re

exe = Exe()

def check_func(va):
    fs, fe = exe.func_of(va)
    print(f"\n================ Func {fs:#x}..{fe:#x} (len {fe-fs}) ================")
    for ins, note in exe.disasm(fs, fe):
        if note or ins.mnemonic in ("call", "ret"):
            # filter out boring calls
            if "rtc" in note or "vba" in note and "Free" in note:
                continue
            print(f"  {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:30} {note}")

# Check 0x733b20 (GETGAMEOPP caller)
check_func(0x733bc8)
# Check 0x7280f0 (GETDUELBEGINGUS caller)
check_func(0x728d2d)
