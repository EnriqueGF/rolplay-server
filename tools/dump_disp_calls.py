from rpexe import Exe
import json

exe = Exe()
# Let's inspect the dispatcher 0x7c7be0 where these are called!
disp_fs, disp_fe = exe.func_of(0x7c7be0)

# In resolve.py, we saw how it parses dispatchers.
# Let's find the call for GETDUELNUMCARDSRPS and GETDUELBEGINGUSRPS and BEGINTURN
import re

cur = None
for ins, note in exe.disasm(disp_fs, disp_fe):
    m = re.search(r'; L"([A-Z]+)"$', note)
    if m:
        cur = m.group(1)
    if cur in ("GETDUELNUMCARDSRPS", "GETDUELBEGINGUSRPS", "BEGINTURN", "ENDTURN", "GETCARDHANDRPS", "GETCARDTYPERPS", "GETCARDPOWERRPS", "GETCARDESPRPS", "GETCARDESPFRPS", "SETCATTACKRPS", "SETCDEFENDRPS", "KILLCARD", "DEDUCTPV"):
        if ins.mnemonic in ("call", "push", "mov") and any(k in ins.op_str for k in ("0x7", "0x8", "0x4")):
            print(f"{cur:20} @ {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:30} {note}")
