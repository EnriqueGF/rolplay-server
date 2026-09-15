from rpexe import Exe

exe = Exe()

def show(va1, va2):
    for ins, note in exe.disasm(va1, va2):
        print(f"  {ins.address:#x}: {ins.mnemonic:7} {ins.op_str:35} {note}")

print("=== 0x728c40 .. 0x728e20 ===")
show(0x728c40, 0x728e20)
