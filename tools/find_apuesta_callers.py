import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
# Let's search all code from 0x720000 to 0x760000 (Torneo form code)
for ins, note in exe.disasm(0x720000, 0x760000):
    if any(addr in ins.op_str for addr in ['0x729670', '0x732640', '0x42ed4f', '0x42edf8']):
        print(f"Direct call at {ins.address:#x}: {ins.mnemonic} {ins.op_str} {note}")
    if ins.mnemonic in ('call', 'jmp') and any(off in ins.op_str for off in ['884', '8b8', '884h', '8b8h']):
        print(f"Offset call at {ins.address:#x}: {ins.mnemonic} {ins.op_str} {note}")
