import sys
sys.path.insert(0, 'tools')
from rp_driver import RPDriver, win32api, win32con, ctypes

d = RPDriver()
pid = d.get_rp_pid()

# Find main thread of PID
import win32process
# Open process
h_proc = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)

# Enumerate threads
class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_ulong),
        ("cntUsage", ctypes.c_ulong),
        ("th32ThreadID", ctypes.c_ulong),
        ("th32OwnerProcessID", ctypes.c_ulong),
        ("tpBasePri", ctypes.c_long),
        ("tpDeltaPri", ctypes.c_long),
        ("dwFlags", ctypes.c_ulong),
    ]

TH32CS_SNAPTHREAD = 0x00000004
h_snap = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
te = THREADENTRY32()
te.dwSize = ctypes.sizeof(THREADENTRY32)

main_tid = None
if ctypes.windll.kernel32.Thread32First(h_snap, ctypes.byref(te)):
    while True:
        if te.th32OwnerProcessID == pid:
            main_tid = te.th32ThreadID
            break
        if not ctypes.windll.kernel32.Thread32Next(h_snap, ctypes.byref(te)):
            break
ctypes.windll.kernel32.CloseHandle(h_snap)

print(f"Main Thread ID: {main_tid}")
if main_tid:
    h_thread = ctypes.windll.kernel32.OpenThread(0x001F03FF, False, main_tid) # THREAD_ALL_ACCESS
    ctypes.windll.kernel32.SuspendThread(h_thread)
    
    class WOW64_CONTEXT(ctypes.Structure):
        _fields_ = [
            ("ContextFlags", ctypes.c_ulong),
            ("Dr0", ctypes.c_ulong), ("Dr1", ctypes.c_ulong), ("Dr2", ctypes.c_ulong),
            ("Dr3", ctypes.c_ulong), ("Dr6", ctypes.c_ulong), ("Dr7", ctypes.c_ulong),
            ("FloatSave", ctypes.c_byte * 112),
            ("SegGs", ctypes.c_ulong), ("SegFs", ctypes.c_ulong), ("SegEs", ctypes.c_ulong), ("SegDs", ctypes.c_ulong),
            ("Edi", ctypes.c_ulong), ("Esi", ctypes.c_ulong), ("Ebx", ctypes.c_ulong), ("Edx", ctypes.c_ulong),
            ("Ecx", ctypes.c_ulong), ("Eax", ctypes.c_ulong), ("Ebp", ctypes.c_ulong), ("Eip", ctypes.c_ulong),
            ("SegCs", ctypes.c_ulong), ("EFlags", ctypes.c_ulong), ("Esp", ctypes.c_ulong), ("SegSs", ctypes.c_ulong),
            ("ExtendedRegisters", ctypes.c_byte * 512),
        ]
    ctx = WOW64_CONTEXT()
    ctx.ContextFlags = 0x00010007 # CONTEXT_FULL
    ctypes.windll.kernel32.Wow64GetThreadContext(h_thread, ctypes.byref(ctx))
    print(f"EIP: {ctx.Eip:#x}, ESP: {ctx.Esp:#x}, EBP: {ctx.Ebp:#x}")

    # Read 512 dwords from ESP to find return addresses in 0x700000 - 0x7eb000
    stack_buf = (ctypes.c_ulong * 512)()
    bytesRead = ctypes.c_size_t()
    ctypes.windll.kernel32.ReadProcessMemory(h_proc.handle, ctx.Esp, ctypes.byref(stack_buf), ctypes.sizeof(stack_buf), ctypes.byref(bytesRead))
    
    print("Call stack frames in RPcliente code:")
    for i, val in enumerate(stack_buf):
        if 0x700000 <= val <= 0x7eb000:
            print(f"  [ESP+{i*4:#04x}] = {val:#x}")

    ctypes.windll.kernel32.ResumeThread(h_thread)
    ctypes.windll.kernel32.CloseHandle(h_thread)

win32api.CloseHandle(h_proc)
