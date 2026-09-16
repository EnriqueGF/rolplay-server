import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
with open('../game/RPcliente.exe', 'rb') as f:
    data = f.read()

target = (0x7ce01e).to_bytes(4, 'little')
pos = 0
while True:
    pos = data.find(target, pos)
    if pos == -1: break
    va = pos + 0x400000
    if va < 0x7c7000: # not in the dispatcher!
        try:
            fs, fe = exe.func_of(va)
            print(f"Ref at {va:#x} in func {fs:#x}")
            for ins, note in exe.disasm(max(fs, va-20), min(fe, va+30)):
                if '0x7ce01e' in ins.op_str:
                    print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str:30} {note}")
        except Exception as e:
            print(f"Ref at {va:#x}: {e}")
    pos += 4
