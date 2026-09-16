from rpexe import Exe

exe = Exe()
fs, fe = exe.func_of(0x733650)
lines = []
for ins, note in exe.disasm(fs, fe):
    lines.append(f"{ins.address:#x}: {ins.mnemonic:8} {ins.op_str:35} {note}")

with open("tools/disasm_733650.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Func 0x733650: {fs:#x} to {fe:#x}, {len(lines)} instructions")
