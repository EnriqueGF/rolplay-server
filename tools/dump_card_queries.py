import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
# In find_cmds.py:
# #GETCARDTYPE : string@0x434914, refs: [0x734914]
# #GETCARDPOWER: string@0x434997, refs: [0x734997]
# #GETCARDESP  : string@0x434a1a, refs: [0x734a1a]
# #GETCARDESPF : string@0x434a9d, refs: [0x734a9d]

targets = [0x734914, 0x734997, 0x734a1a, 0x734a9d]
for t in targets:
    print(f"\n=== Code around {t:#x} ===")
    for ins, note in exe.disasm(t - 0x30, t + 0x50):
        print(f"  {ins.address:#x}: {ins.mnemonic:7} {ins.op_str:30} {note}")
