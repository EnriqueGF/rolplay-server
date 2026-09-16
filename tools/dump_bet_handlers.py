import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
targets = [
    (0x74f620, "GETGOLDBETRPS (0x820)"),
    (0x750a20, "GETDUELNUMCARDBETRPS (0x824)"),
    (0x750dc0, "GETGOLDBETOPPRPS (0x828)"),
    (0x751160, "GETDUELNUMCARDBETOPPRPS (0x82c)"),
    (0x751500, "SETREFRESHBET (0x830)"),
]

for addr, name in targets:
    fs, fe = exe.func_of(addr)
    print(f"=== {name} ({fs:#x} - {fe:#x}) ===")
    for ins, note in exe.disasm(fs, fe):
        if any(w in ins.mnemonic for w in ['call', 'jmp']) or any(w in note for w in ['L"', 'Apuesta', 'Show', 'New']):
            print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str:30} {note}")
