import sys
sys.path.insert(0, 'tools')
from rp_driver import RPDriver, user32, win32gui, win32con, ctypes
import time

d = RPDriver()
d.attach_desktop()

sub = d.get_sub_win()
if not sub:
    print("No sub window found!")
    sys.exit(1)
user32.SetForegroundWindow(sub)
time.sleep(0.2)

r0 = win32gui.GetWindowRect(sub)
print("Partidas rect:", r0)

# 1. Click on first item in TreeView (rel x=50, y=45)
tv_x = r0[0] + 50
tv_y = r0[1] + 45
print(f"Clicking TreeView first item at ({tv_x}, {tv_y})")
user32.SetCursorPos(tv_x, tv_y)
time.sleep(0.05)
user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
time.sleep(0.05)
user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
time.sleep(0.3)

# 2. Click Unirse button (rel x=352, y=213)
btn_x = r0[0] + 352
btn_y = r0[1] + 213
print(f"Clicking Unirse at ({btn_x}, {btn_y})")
user32.SetCursorPos(btn_x, btn_y)
time.sleep(0.05)
user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
time.sleep(0.05)
user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
time.sleep(1.0)

# Check for Torneo window
torneo = None
pid = d.get_rp_pid()
def find_torneo(h, _):
    global torneo
    if win32gui.GetClassName(h) == "ThunderRT6FormDC" and win32gui.IsWindowVisible(h):
        h_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(h, ctypes.byref(h_pid))
        if h_pid.value == pid:
            r = win32gui.GetWindowRect(h)
            w = r[2] - r[0]
            if w > 700 and h != 0xad0756: # not main lobby
                torneo = h
win32gui.EnumDesktopWindows(d.hdesk, find_torneo, None)
print("Torneo window:", hex(torneo) if torneo else "Not found")

if torneo:
    state = d.read_window(torneo)
    print("Torneo found! Title:", repr(state["title"]))
    print("  Checkboxes:", state["checkboxes"])
    print("  Buttons count:", state["buttons_count"])
