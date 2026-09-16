import sys
sys.path.insert(0, 'tools')
from rp_driver import RPDriver, win32api, win32con, ctypes

d = RPDriver()
pid = d.get_rp_pid()
h = win32api.OpenProcess(win32con.PROCESS_VM_READ, False, pid)
buf = ctypes.create_string_buffer(4)
bytesRead = ctypes.c_size_t()

# Read Torneo instance pointer
ctypes.windll.kernel32.ReadProcessMemory(h.handle, 0x7ce260, buf, 4, ctypes.byref(bytesRead))
inst = int.from_bytes(buf.raw[:4], 'little')
print(f"Torneo inst: {inst:#x}")

ctypes.windll.kernel32.ReadProcessMemory(h.handle, inst, buf, 4, ctypes.byref(bytesRead))
vt = int.from_bytes(buf.raw[:4], 'little')
print(f"Torneo vtable: {vt:#x}")

# Let's inspect member variables of inst
# In VB6 Form, controls are stored at offsets in the Form struct
for off in range(0x30, 0x150, 4):
    ctypes.windll.kernel32.ReadProcessMemory(h.handle, inst + off, buf, 4, ctypes.byref(bytesRead))
    ptr = int.from_bytes(buf.raw[:4], 'little')
    if ptr > 0x10000:
        # read first dword of ptr (its vtable or control object)
        cbuf = ctypes.create_string_buffer(4)
        ctypes.windll.kernel32.ReadProcessMemory(h.handle, ptr, cbuf, 4, ctypes.byref(bytesRead))
        cv = int.from_bytes(cbuf.raw[:4], 'little')
        print(f"  inst+{off:#x} = {ptr:#x} (vtable={cv:#x})")

win32api.CloseHandle(h)
