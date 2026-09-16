import sys
sys.path.insert(0, 'tools')
from rp_driver import RPDriver, win32gui, user32, win32con, ctypes
import threading, time

d = RPDriver()
pid = d.get_rp_pid()
print(f"Target PID: {pid}")

checkpoints = [
    (0x7336c8, "01_call_424"),
    (0x7336dc, "02_call_lateidst_424"),
    (0x733718, "03_call_420"),
    (0x73372c, "04_call_lateidst_420"),
    (0x733734, "05_call_354_preparado"),
    (0x733748, "06_call_preparado_enabled_false"),
    (0x73379b, "07_call_41c"),
    (0x7337a9, "08_call_lateidst_41c"),
    (0x7337b7, "09_call_3b4"),
    (0x7337cb, "10_call_visible_true"),
    (0x7337f5, "11_call_3b0"),
    (0x73380a, "12_call_3b0_enabled_false"),
    (0x733833, "13_call_358_pv"),
    (0x73388c, "14_call_35c_opp_pv"),
    (0x7338e5, "15_call_360"),
    (0x73392b, "16_call_334"),
    (0x7339ae, "17_call_remove_apuesta"),
    (0x7339b5, "18_at_patch_jmp"),
    (0x7339cb, "19_start_build_getcardcountopp"),
    (0x733a28, "20_send_getcardcountopp"),
    (0x733a67, "21_start_build_getcardcount"),
    (0x733aa0, "22_send_getcardcount"),
    (0x733ac1, "23_func_end"),
]

# Structure for context (WOW64 x86 32-bit on x64 Windows)
class WOW64_CONTEXT(ctypes.Structure):
    _fields_ = [
        ("ContextFlags", ctypes.c_ulong),
        ("Dr0", ctypes.c_ulong), ("Dr1", ctypes.c_ulong), ("Dr2", ctypes.c_ulong),
        ("Dr3", ctypes.c_ulong), ("Dr6", ctypes.c_ulong), ("Dr7", ctypes.c_ulong),
        ("FloatSave", ctypes.c_byte * 112),
        ("SegGs", ctypes.c_ulong), ("SegFs", ctypes.c_ulong),
        ("SegEs", ctypes.c_ulong), ("SegDs", ctypes.c_ulong),
        ("Edi", ctypes.c_ulong), ("Esi", ctypes.c_ulong),
        ("Ebx", ctypes.c_ulong), ("Edx", ctypes.c_ulong),
        ("Ecx", ctypes.c_ulong), ("Eax", ctypes.c_ulong),
        ("Ebp", ctypes.c_ulong), ("Eip", ctypes.c_ulong),
        ("SegCs", ctypes.c_ulong), ("EFlags", ctypes.c_ulong),
        ("Esp", ctypes.c_ulong), ("SegSs", ctypes.c_ulong),
        ("ExtendedRegisters", ctypes.c_byte * 512),
    ]

class EXCEPTION_RECORD(ctypes.Structure):
    pass
EXCEPTION_RECORD._fields_ = [
    ("ExceptionCode", ctypes.c_ulong),
    ("ExceptionFlags", ctypes.c_ulong),
    ("ExceptionRecord", ctypes.POINTER(EXCEPTION_RECORD)),
    ("ExceptionAddress", ctypes.c_void_p),
    ("NumberParameters", ctypes.c_ulong),
    ("ExceptionInformation", ctypes.c_ulong * 15),
]
class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("ExceptionRecord", EXCEPTION_RECORD), ("dwFirstChance", ctypes.c_ulong)]
class DEBUG_EVENT_UNION(ctypes.Union):
    _fields_ = [("Exception", EXCEPTION_DEBUG_INFO), ("pad", ctypes.c_byte * 160)]
class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [
        ("dwDebugEventCode", ctypes.c_ulong),
        ("dwProcessId", ctypes.c_ulong),
        ("dwThreadId", ctypes.c_ulong),
        ("u", DEBUG_EVENT_UNION),
    ]

hProc = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, pid)

# Save original bytes and write INT3 (0xCC)
orig_bytes = {}
for addr, name in checkpoints:
    b = ctypes.c_byte()
    read = ctypes.c_size_t()
    ctypes.windll.kernel32.ReadProcessMemory(hProc, addr, ctypes.byref(b), 1, ctypes.byref(read))
    orig_bytes[addr] = b.value
    cc = ctypes.c_byte(0xCC)
    written = ctypes.c_size_t()
    ctypes.windll.kernel32.WriteProcessMemory(hProc, addr, ctypes.byref(cc), 1, ctypes.byref(written))

print(f"Patched {len(checkpoints)} breakpoints with INT3.")

# Find Preparado checkbox
chk = 0x770c8c
def trigger_click():
    time.sleep(0.5)
    lparam = (8 << 16) | 8
    print("[Thread] Clicking Preparado...")
    win32gui.SendMessage(chk, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.05)
    win32gui.SendMessage(chk, win32con.WM_LBUTTONUP, 0, lparam)

threading.Thread(target=trigger_click, daemon=True).start()

if not ctypes.windll.kernel32.DebugActiveProcess(pid):
    print("DebugActiveProcess failed!")
    sys.exit(1)
ctypes.windll.kernel32.DebugSetProcessKillOnExit(False)

de = DEBUG_EVENT()
t0 = time.time()
cp_map = dict(checkpoints)

try:
    while time.time() - t0 < 6:
        if ctypes.windll.kernel32.WaitForDebugEvent(ctypes.byref(de), 100):
            if de.dwDebugEventCode == 1: # EXCEPTION_DEBUG_EVENT
                rec = de.u.Exception.ExceptionRecord
                addr = rec.ExceptionAddress
                code = rec.ExceptionCode
                if code == 0x80000003: # STATUS_BREAKPOINT
                    # The exception address is at the INT3
                    if addr in cp_map:
                        print(f"  --> HIT CHECKPOINT: {addr:#x} ({cp_map[addr]})")
                        # Restore original byte
                        orig = ctypes.c_byte(orig_bytes[addr])
                        written = ctypes.c_size_t()
                        ctypes.windll.kernel32.WriteProcessMemory(hProc, addr, ctypes.byref(orig), 1, ctypes.byref(written))
                        # Rewind EIP by 1
                        hThread = ctypes.windll.kernel32.OpenThread(0x001F03FF, False, de.dwThreadId)
                        ctx = WOW64_CONTEXT()
                        ctx.ContextFlags = 0x00010007
                        ctypes.windll.kernel32.Wow64GetThreadContext(hThread, ctypes.byref(ctx))
                        ctx.Eip = addr
                        ctypes.windll.kernel32.Wow64SetThreadContext(hThread, ctypes.byref(ctx))
                        ctypes.windll.kernel32.CloseHandle(hThread)
                elif code == 0xc000008f:
                    print(f"  *** VB6 RUNTIME ERROR at {addr:#x}! ***")
                elif code != 0x80000003:
                    print(f"  *** Other exception {code:#x} at {addr:#x} ***")
            ctypes.windll.kernel32.ContinueDebugEvent(de.dwProcessId, de.dwThreadId, 0x00010002)
finally:
    # Restore all bytes
    for addr, orig in orig_bytes.items():
        b = ctypes.c_byte(orig)
        written = ctypes.c_size_t()
        ctypes.windll.kernel32.WriteProcessMemory(hProc, addr, ctypes.byref(b), 1, ctypes.byref(written))
    ctypes.windll.kernel32.DebugActiveProcessStop(pid)
    ctypes.windll.kernel32.CloseHandle(hProc)
    print("Done tracing, all bytes restored.")
