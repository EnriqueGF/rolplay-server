import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = 0x7365e0, 0x739000

# Let's map all the local variables stored from the tokens to their card struct offsets!
vars_of_interest = {
    "0x100": "token 1",
    "0x90": "token 2",
    "0x170": "token 3",
    "0x11c": "token 4",
    "0x8c": "token 5 (Type)",
    "0x178": "token 6",
    "0x16c": "token 7",
    "0x168": "token 8",
    "0xfc": "token 9",
    "0xf8": "token 10",
    "0x164": "token 11",
    "0xe0": "token 12",
    "0x160": "token 13",
    "0xf4": "token 14",
    "0x2c": "token 15",
    "0xb8": "token 16",
    "0x28": "token 17",
    "0xb4": "token 18",
    "0x144": "token 19",
    "0x118": "token 20",
    "0x114": "token 21",
    "0x68": "token 22",
}

print("Tracing usages of parsed tokens:")
for ins, note in exe.disasm(0x738500, 0x738e00):
    for v, name in vars_of_interest.items():
        if f"[ebp - {v}]" in ins.op_str or f"[ebp - 0{v[2:]}]" in ins.op_str:
            print(f"  {ins.address:#x}: {name:15} in {ins.mnemonic:6} {ins.op_str:30} {note}")
