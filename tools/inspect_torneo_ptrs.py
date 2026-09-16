import sys
sys.path.insert(0, 'tools')
from rp_driver import RPDriver, win32api, win32con, ctypes

d = RPDriver()
pid = d.get_rp_pid()
h = win32api.OpenProcess(win32con.PROCESS_VM_READ, False, pid)
buf = ctypes.create_string_buffer(4)
bytesRead = ctypes.c_size_t()

# Read Torneo instance pointer from 0x7ce260
ctypes.windll.kernel32.ReadProcessMemory(h.handle, 0x7ce260, buf, 4, ctypes.byref(bytesRead))
inst = int.from_bytes(buf.raw[:4], 'little')
print(f"Torneo inst at 0x7ce260: {inst:#x}")

offsets = [0x334, 0x354, 0x358, 0x35c, 0x360, 0x3b0, 0x3b4, 0x420, 0x424]
for off in offsets:
    ctypes.windll.kernel32.ReadProcessMemory(h.handle, inst + off, buf, 4, ctypes.byref(bytesRead))
    val = int.from_bytes(buf.raw[:4], 'little')
    print(f"  inst + {off:#x}: {val:#x}")

win32api.CloseHandle(h)
