import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = 0x7365e0, 0x739340

# Find every call to 0x721fe0 in GETCARDHANDRPS and the token number passed
print("=== All GetToken calls in GETCARDHANDRPS ===")
for ins, note in exe.disasm(fs, fe):
    if ins.mnemonic == "mov" and "dword ptr [ebp - 0x244]" in ins.op_str:
        tok_num = ins.op_str.split(", ")[1]
        print(f"  {ins.address:#x}: token #{tok_num}")
    elif note and any(k in note for k in ("Poder", "Criatura", "Amuleto", "jpg", "gif")):
        print(f"  {ins.address:#x}: {note.strip()}")
