import sys
sys.path.insert(0, 'tools')
from rp_driver import RPDriver, win32api, win32con, ctypes

d = RPDriver()
pid = d.get_rp_pid()
h = win32api.OpenProcess(win32con.PROCESS_VM_READ, False, pid)
buf = ctypes.create_string_buffer(32)
bytesRead = ctypes.c_size_t()

for addr in [0x7ce100, 0x7ce0c0, 0x7cf688, 0x7ce29c]:
    ctypes.windll.kernel32.ReadProcessMemory(h.handle, addr, buf, 16, ctypes.byref(bytesRead))
    val = buf.raw[:16]
    ptr = int.from_bytes(val[:4], 'little')
    print(f"{addr:#x}: raw={val.hex(' ')}, ptr={ptr:#x}")
    if ptr > 0x10000:
        str_buf = ctypes.create_string_buffer(64)
        ctypes.windll.kernel32.ReadProcessMemory(h.handle, ptr, str_buf, 64, ctypes.byref(bytesRead))
        print(f"   -> at ptr {ptr:#x}: {str_buf.raw[:32]}")

win32api.CloseHandle(h)
