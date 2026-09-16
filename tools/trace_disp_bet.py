from rpexe import Exe
import re

exe = Exe()
disp_fs, disp_fe = exe.func_of(0x7c7be0)

cur = None
targets = [
    "SETGAMEREADY", "SETREFRESHBET", "GETGOLDBETRPS", "GETGOLDBETOPPRPS",
    "GETDUELNUMCARDBETRPS", "GETDUELNUMCARDBETOPPRPS", "BEGINTURN", "SETGAMEINFORM"
]

lines = []
for ins, note in exe.disasm(disp_fs, disp_fe):
    m = re.search(r'; L"([A-Z0-9_]+)"', note)
    if m:
        cur = m.group(1)
    if cur in targets:
        lines.append(f"{cur:24} @ {ins.address:#x}: {ins.mnemonic:8} {ins.op_str:30} {note}")

with open("tools/disp_targets.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Wrote {len(lines)} lines")
