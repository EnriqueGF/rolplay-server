import sys
sys.path.insert(0, 'tools')
from rp_driver import RPDriver, win32gui, user32, win32con, ctypes
import time

d = RPDriver()
d.attach_desktop()

pid = d.get_rp_pid()
torneo = None
chk = None

def find_torneo(h, _):
    global torneo, chk
    if win32gui.GetClassName(h) == "ThunderRT6FormDC" and win32gui.IsWindowVisible(h):
        h_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(h, ctypes.byref(h_pid))
        if h_pid.value == pid:
            r = win32gui.GetWindowRect(h)
            if (r[2] - r[0]) > 700 and win32gui.GetWindowText(h) == "Rolplay.net ":
                def find_chk(c, _):
                    global chk
                    if win32gui.GetClassName(c) == "ThunderRT6CheckBox" and win32gui.GetWindowText(c) == "Preparado":
                        chk = c
                win32gui.EnumChildWindows(h, find_chk, None)
                if chk:
                    torneo = h

win32gui.EnumDesktopWindows(d.hdesk, find_torneo, None)
print(f"Torneo: {hex(torneo) if torneo else 'None'}, Preparado Checkbox: {hex(chk) if chk else 'None'}")

if chk and torneo:
    user32.SetForegroundWindow(torneo)
    time.sleep(0.1)
    lparam = (8 << 16) | 8
    print("Clicking Preparado checkbox...")
    win32gui.SendMessage(chk, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.05)
    win32gui.SendMessage(chk, win32con.WM_LBUTTONUP, 0, lparam)
    print("Clicked! Waiting 2s for response...")
    time.sleep(2.0)
