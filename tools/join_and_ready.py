import sys
sys.path.insert(0, 'tools')
from rp_driver import RPDriver, user32, win32gui, win32con, ctypes
import time

d = RPDriver()
d.attach_desktop()

sub = d.get_sub_win()
print("Partidas sub window:", hex(sub) if sub else None)

# Find treeview and select first item
tv = None
def find_tv(h, _):
    global tv
    if win32gui.GetClassName(h) == "TreeView20WndClass":
        tv = h
win32gui.EnumChildWindows(sub, find_tv, None)
print("TreeView hwnd:", hex(tv) if tv else None)

if tv:
    # Get root item
    root = win32gui.SendMessage(tv, 0x110A, 0, 0) # TVM_GETNEXTITEM, TVGN_ROOT
    print("Root item:", hex(root))
    if root:
        win32gui.SendMessage(tv, 0x110B, 9, root) # TVM_SELECTITEM, TVGN_CARET
        time.sleep(0.2)

# Click "Unirse" button
r0 = win32gui.GetWindowRect(sub)
btn_x = r0[0] + 315
btn_y = r0[1] + 195
print(f"Clicking Unirse at ({btn_x}, {btn_y})")
user32.SetCursorPos(btn_x, btn_y)
time.sleep(0.05)
user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
time.sleep(0.05)
user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
time.sleep(1.0)

# Check if Torneo opened
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
            h_len = r[3] - r[1]
            if w > 700:
                torneo = h
win32gui.EnumDesktopWindows(d.hdesk, find_torneo, None)
print("Torneo window:", hex(torneo) if torneo else "Not found")

if torneo:
    state = d.read_window(torneo)
    print("Torneo controls summary:")
    print("  Checkboxes:", state["checkboxes"])
    print("  Textboxes:", len(state["textboxes"]))
    print("  Buttons:", state["buttons_count"])
    print("  Labels:", state["labels"][:10])
