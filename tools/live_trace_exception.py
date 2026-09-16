import sys
sys.path.insert(0, 'tools')
from rp_driver import RPDriver, win32gui, user32, win32con, ctypes
import threading
import time

d = RPDriver()
pid = d.get_rp_pid()
print(f"Target PID: {pid}")

# First, close any open error dialogs
def close_all_dlgs():
    def cb(h, _):
        if win32gui.GetClassName(h) == "#32770" and win32gui.IsWindowVisible(h):
            h_pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(h, ctypes.byref(h_pid))
            if h_pid.value == pid:
                btn = win32gui.FindWindowEx(h, 0, "Button", "Aceptar")
                if btn:
                    win32gui.SendMessage(btn, 0x00F5, 0, 0)
    win32gui.EnumDesktopWindows(d.hdesk, cb, None)

close_all_dlgs()
time.sleep(0.3)
close_all_dlgs()

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

def trigger_toggle():
    time.sleep(0.8)
    chk = 0x6d06e4
    torneo = 0xf06f6
    user32.SetForegroundWindow(torneo)
    time.sleep(0.1)
    lparam = (8 << 16) | 8
    print("[Thread] Sending toggle click 1 (uncheck)...")
    win32gui.SendMessage(chk, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.05)
    win32gui.SendMessage(chk, win32con.WM_LBUTTONUP, 0, lparam)
    time.sleep(0.5)
    print("[Thread] Sending toggle click 2 (recheck)...")
    win32gui.SendMessage(chk, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.05)
    win32gui.SendMessage(chk, win32con.WM_LBUTTONUP, 0, lparam)

threading.Thread(target=trigger_toggle, daemon=True).start()

if not ctypes.windll.kernel32.DebugActiveProcess(pid):
    print("Failed to attach debugger! Error:", ctypes.windll.kernel32.GetLastError())
    sys.exit(1)

print("Debugger attached. Listening for exceptions...")
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
                print(f"*** EXCEPTION *** Addr={addr:#x}, Code={ex_code:#x}, FirstChance={first}")
        ctypes.windll.kernel32.ContinueDebugEvent(de.dwProcessId, de.dwThreadId, DBG_CONTINUE)

ctypes.windll.kernel32.DebugActiveProcessStop(pid)
print("Debugger detached.")
