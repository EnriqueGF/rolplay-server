import sys
sys.path.insert(0, 'tools')
from rp_driver import RPDriver, win32gui, user32, win32con, ctypes
import threading
import time

d = RPDriver()
pid = d.get_rp_pid()
print(f"Target PID: {pid}")

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
    _fields_ = [
        ("ExceptionRecord", EXCEPTION_RECORD),
        ("dwFirstChance", ctypes.c_ulong),
    ]

class DEBUG_EVENT_UNION(ctypes.Union):
    _fields_ = [
        ("Exception", EXCEPTION_DEBUG_INFO),
        ("pad", ctypes.c_byte * 160),
    ]

class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [
        ("dwDebugEventCode", ctypes.c_ulong),
        ("dwProcessId", ctypes.c_ulong),
        ("dwThreadId", ctypes.c_ulong),
        ("u", DEBUG_EVENT_UNION),
    ]

# Start thread to click Preparado
def trigger_click():
    time.sleep(0.5)
    chk = 0x6d06e4
    if user32.IsWindow(chk):
        r = win32gui.GetWindowRect(chk)
        cx = (r[0] + r[2]) // 2
        cy = (r[1] + r[3]) // 2
        print(f"[Thread] Clicking Preparado at ({cx}, {cy})...")
        user32.SetCursorPos(cx, cy)
        time.sleep(0.05)
        user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

threading.Thread(target=trigger_click, daemon=True).start()

if not ctypes.windll.kernel32.DebugActiveProcess(pid):
    print("Failed to attach debugger! Error:", ctypes.windll.kernel32.GetLastError())
    sys.exit(1)

print("Debugger attached. Waiting for events...")
de = DEBUG_EVENT()
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001
EXCEPTION_DEBUG_EVENT = 1

t0 = time.time()
while time.time() - t0 < 6:
    if ctypes.windll.kernel32.WaitForDebugEvent(ctypes.byref(de), 100):
        code = de.dwDebugEventCode
        if code == EXCEPTION_DEBUG_EVENT:
            rec = de.u.Exception.ExceptionRecord
            first = de.u.Exception.dwFirstChance
            addr = rec.ExceptionAddress
            ex_code = rec.ExceptionCode
            if ex_code != 0x80000003: # ignore breakpoint
                print(f"[EXCEPTION] Addr={addr:#x}, Code={ex_code:#x}, FirstChance={first}")
        ctypes.windll.kernel32.ContinueDebugEvent(de.dwProcessId, de.dwThreadId, DBG_CONTINUE)

ctypes.windll.kernel32.DebugActiveProcessStop(pid)
print("Debugger detached.")
