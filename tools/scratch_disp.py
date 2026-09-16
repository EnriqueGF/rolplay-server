from rpexe import Exe
import re

exe = Exe()
disp_fs, disp_fe = exe.func_of(0x7c7be0)

cur = None
calls = {}
for ins, note in exe.disasm(disp_fs, disp_fe):
    m = re.search(r'; L"([A-Z0-9_]+)"', note)
    if m:
        cur = m.group(1)
    if cur and ins.mnemonic == 'call' and ('edx' in ins.op_str or 'eax' in ins.op_str or 'ecx' in ins.op_str):
        calls[cur] = calls.get(cur, []) + [f"{ins.address:#x}: {ins.mnemonic} {ins.op_str} ({note})"]

for k in sorted(calls.keys()):
    print(f"{k}")
