import sys
sys.path.insert(0, 'tools')
from rp_driver import RPDriver, win32gui, user32, win32con, ctypes
import time

d = RPDriver()
pid = d.get_rp_pid()

# Close existing error dialog if any
def close_dlg(h, _):
    if win32gui.GetClassName(h) == "#32770" and win32gui.IsWindowVisible(h):
        h_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(h, ctypes.byref(h_pid))
        if h_pid.value == pid:
            btn = win32gui.FindWindowEx(h, 0, "Button", "Aceptar")
            if btn:
                print(f"Closing dialog {h:#x} via button {btn:#x}")
                win32gui.SendMessage(btn, 0x00F5, 0, 0)
win32gui.EnumDesktopWindows(d.hdesk, close_dlg, None)
