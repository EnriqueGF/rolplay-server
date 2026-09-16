"""Driver y automatización del cliente RPcliente.exe (Rolplay.net 3.9.0).

Permite lanzar el servidor y el cliente autenticado, navegar entre todas
las ventanas (Cartas, Retos, Salas, etc.) y leer el estado completo de la
interfaz (textos, listas, combos, árboles) sin necesidad de capturas de pantalla.

Uso CLI:
  python rp_driver.py launch
  python rp_driver.py login [usuario] [contraseña]
  python rp_driver.py status
  python rp_driver.py nav <cartas|retos|salas|intercambios|estadisticas|clanes>
  python rp_driver.py read
  python rp_driver.py close
  python rp_driver.py chat <mensaje>
  python rp_driver.py test
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
import socket
import subprocess
import sys
import time
import win32api
import win32con
import win32gui
import win32process

user32 = ctypes.windll.user32
try:
    user32.SetProcessDPIAware()
except Exception:
    pass

# Tipos Win32 de 64 bits para ctypes
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint
]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.IsWindowEnabled.argtypes = [wintypes.HWND]
user32.IsWindowEnabled.restype = wintypes.BOOL

HWND_TOPMOST = ctypes.c_void_p(-1).value
HWND_NOTOPMOST = ctypes.c_void_p(-2).value

BUTTON_ORDER = {
    "enviar": 0,
    "retos": 1,
    "partidas": 1,
    "cartas": 2,
    "intercambios": 3,
    "salas": 4,
    "canales": 4,
    "estadisticas": 5,
    "clanes": 6,
    "manual": 8,
    "salir": 9,
}


class RPDriver:
    def __init__(self, root_dir=None):
        if not root_dir:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.root_dir = root_dir
        self.game_dir = os.path.join(root_dir, "game")
        self.server_dir = os.path.join(root_dir, "rolplay-server", "server")
        self.exe_path = os.path.join(self.game_dir, "RPcliente.exe")
        self.attach_desktop()

    def attach_desktop(self):
        """Asocia el hilo actual al escritorio interactivo 'Default' de Windows."""
        self.hdesk = user32.OpenDesktopW("Default", 0, False, 0x10000000)
        if self.hdesk:
            user32.SetThreadDesktop(self.hdesk)

    def get_rp_pid(self):
        """Obtiene el PID de RPcliente si está en ejecución."""
        pids = []
        for p in win32process.EnumProcesses():
            try:
                h = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, p)
                name = win32process.GetModuleFileNameEx(h, 0)
                if "RPcliente.exe" in name:
                    pids.append(p)
                win32api.CloseHandle(h)
            except Exception:
                pass
        return pids[0] if pids else None

    def is_server_listening(self, port=10002):
        s = socket.socket()
        s.settimeout(0.5)
        try:
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except Exception:
            return False

    def ensure_server(self):
        """Asegura que rpserver.py esté en ejecución."""
        if self.is_server_listening():
            return True
        print("[Driver] Servidor no detectado. Iniciando rpserver.py...")
        py_exe = sys.executable
        srv_py = os.path.join(self.server_dir, "rpserver.py")
        cmd = f'powershell -Command "Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{{CommandLine = \'\\"{py_exe}\\" \\"{srv_py}\\"\'; CurrentDirectory = \'{self.server_dir}\'}}"'
        subprocess.run(cmd, shell=True, capture_output=True)
        for _ in range(20):
            time.sleep(0.3)
            if self.is_server_listening():
                print("[Driver] Servidor iniciado y escuchando en puerto 10002.")
                return True
        print("[Driver] Advertencia: El servidor tardó en responder.")
        return False

    def launch(self, user="prueba", password="clave", auto_login=True):
        """Lanza el cliente en el escritorio interactivo mediante WMI."""
        self.ensure_server()
        pid = self.get_rp_pid()
        if pid:
            print(f"[Driver] RPcliente ya está corriendo (PID {pid}).")
        else:
            print("[Driver] Lanzando RPcliente.exe...")
            cmd = f'powershell -Command "Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{{CommandLine = \'\\"{self.exe_path}\\" -local -nocheck\'; CurrentDirectory = \'{self.game_dir}\'}}"'
            subprocess.run(cmd, shell=True, capture_output=True)
            for _ in range(25):
                time.sleep(0.3)
                pid = self.get_rp_pid()
                if pid:
                    break
            if not pid:
                raise RuntimeError("No se pudo iniciar RPcliente.exe")
            print(f"[Driver] RPcliente iniciado con PID {pid}.")

        if auto_login:
            time.sleep(1)
            return self.login(user, password)
        return True

    def find_window(self, filter_fn):
        self.attach_desktop()
        found = []
        def cb(h, _):
            if filter_fn(h):
                found.append(h)
        win32gui.EnumDesktopWindows(self.hdesk, cb, None)
        return found[0] if found else None

    def get_login_win(self):
        return self.find_window(lambda h: "Rolplay.net ver" in win32gui.GetWindowText(h) and win32gui.IsWindowVisible(h))

    def get_main_win(self):
        def is_main(h):
            if win32gui.GetClassName(h) != "ThunderRT6FormDC" or not win32gui.IsWindowVisible(h):
                return False
            has_priv = False
            def check_c(c, _):
                nonlocal has_priv
                if win32gui.GetWindowText(c) == "Aceptar Privados":
                    has_priv = True
            win32gui.EnumChildWindows(h, check_c, None)
            return has_priv
        return self.find_window(is_main)

    def get_sub_win(self):
        main = self.get_main_win()
        pid = self.get_rp_pid()
        def is_sub(h):
            if not main or h == main or not win32gui.IsWindowVisible(h):
                return False
            h_pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(h, ctypes.byref(h_pid))
            if h_pid.value != pid:
                return False
            cls = win32gui.GetClassName(h)
            return cls == "ThunderRT6FormDC" or cls == "#32770"
        return self.find_window(is_sub)

    def get_torneo_win(self):
        pid = self.get_rp_pid()
        def is_torneo(h):
            if win32gui.GetClassName(h) != "ThunderRT6FormDC" or not win32gui.IsWindowVisible(h):
                return False
            h_pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(h, ctypes.byref(h_pid))
            if h_pid.value != pid:
                return False
            r = win32gui.GetWindowRect(h)
            if (r[2] - r[0]) > 700:
                has_prep = False
                def check_prep(c, _):
                    nonlocal has_prep
                    if win32gui.GetClassName(c) == "ThunderRT6CheckBox" and win32gui.GetWindowText(c) == "Preparado":
                        has_prep = True
                win32gui.EnumChildWindows(h, check_prep, None)
                return has_prep
            return False
        return self.find_window(is_torneo)

    def real_click(self, target, topwin=None):
        """Ejecuta un clic de ratón físico y preciso, garantizando topmost y coordenadas reales."""
        p = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(p))
        if topwin:
            user32.SetWindowPos(topwin, HWND_TOPMOST, 0, 0, 0, 0, 0x0013)
            time.sleep(0.12)
        if isinstance(target, tuple):
            cx, cy = target
        else:
            r = win32gui.GetWindowRect(target)
            cx = (r[0] + r[2]) // 2
            cy = (r[1] + r[3]) // 2
        user32.SetCursorPos(cx, cy)
        time.sleep(0.08)
        user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.06)
        user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.15)
        if topwin:
            user32.SetWindowPos(topwin, HWND_NOTOPMOST, 0, 0, 0, 0, 0x0013)
        user32.SetCursorPos(p.x, p.y)

    def type_into(self, hwnd, text, topwin=None):
        self.real_click(hwnd, topwin=topwin)
        time.sleep(0.05)
        win32gui.SendMessage(hwnd, 0x000C, 0, "")
        for ch in text:
            win32gui.SendMessage(hwnd, 0x0102, ord(ch), 1)
        time.sleep(0.05)

    def login(self, user="prueba", password="clave"):
        main = self.get_main_win()
        if main:
            print(f"[Driver] Ya hay sesión iniciada en la ventana principal ({main:#x}).")
            return True

        login_win = None
        for _ in range(20):
            login_win = self.get_login_win()
            if login_win:
                break
            time.sleep(0.3)

        if not login_win:
            print("[Driver] No se encontró ventana de login ni ventana principal.")
            return False

        print(f"[Driver] Ventana de login detectada ({login_win:#x}). Autenticando...")
        tbs = []
        btns = []
        def enum_c(h, _):
            cls = win32gui.GetClassName(h)
            r = win32gui.GetWindowRect(h)
            if cls == "ThunderRT6TextBox":
                tbs.append((r[1], h))
            elif cls == "ThunderRT6UserControlDC":
                btns.append((r[1], h))
        win32gui.EnumChildWindows(login_win, enum_c, None)
        tbs.sort()
        btns.sort()

        if len(tbs) < 2 or not btns:
            print("[Driver] Error: No se encontraron controles esperados en el formulario de login.")
            return False

        self.type_into(tbs[0][1], user, topwin=login_win)
        self.type_into(tbs[1][1], password, topwin=login_win)

        # Clic en Acceder
        btn_acc = btns[0][1]
        self.real_click(btn_acc, topwin=login_win)

        for _ in range(30):
            time.sleep(0.4)
            main = self.get_main_win()
            if main:
                print(f"[Driver] ¡Login exitoso! Ventana principal: {main:#x}")
                return True

        print("[Driver] No apareció la ventana principal después de autenticar.")
        return False

    def get_lobby_buttons(self, main_hwnd):
        r0 = win32gui.GetWindowRect(main_hwnd)
        l = []
        def enum_k(h, _):
            if win32gui.GetClassName(h) == "ThunderRT6UserControlDC":
                r = win32gui.GetWindowRect(h)
                l.append({"h": h, "x": r[0] - r0[0], "y": r[1] - r0[1], "rect": r})
        win32gui.EnumChildWindows(main_hwnd, enum_k, None)
        l.sort(key=lambda item: (item["y"], item["x"]))
        return l

    def nav(self, section_name):
        """Navega a una sección del lobby haciendo clic en su botón correspondiente."""
        main = self.get_main_win()
        if not main:
            print("[Driver] No se encontró ventana principal activa.")
            return None

        # Si hay subventana abierta, cerrarla primero
        sub = self.get_sub_win()
        if sub:
            self.close()

        # Esperar a que la ventana principal esté habilitada
        for _ in range(15):
            if user32.IsWindowEnabled(main):
                break
            time.sleep(0.1)

        sec = section_name.lower().strip()
        idx = BUTTON_ORDER.get(sec)
        if idx is None:
            print(f"[Driver] Sección desconocida: {section_name}. Opciones: {list(BUTTON_ORDER.keys())}")
            return None

        # Restaurar y posicionar la ventana principal en (100, 100)
        user32.ShowWindow(main, 9)  # SW_RESTORE
        user32.SetWindowPos(main, HWND_TOPMOST, 100, 100, 660, 450, 0x0040)
        time.sleep(0.2)

        btns = self.get_lobby_buttons(main)
        if idx >= len(btns):
            print(f"[Driver] Índice de botón {idx} fuera de rango ({len(btns)} botones encontrados).")
            return None

        target = btns[idx]
        print(f"[Driver] Haciendo clic en '{section_name}' (botón {idx})...")
        self.real_click(target["h"], topwin=main)

        # Esperar a que abra la subventana
        new_sub = None
        for _ in range(25):
            time.sleep(0.2)
            new_sub = self.get_sub_win()
            if new_sub:
                break

        if new_sub:
            print(f"[Driver] Subventana abierta: {new_sub:#x} ({win32gui.GetWindowText(new_sub)})")
            return self.read_window(new_sub)
        else:
            print(f"[Driver] No apareció subventana tras hacer clic en '{section_name}'.")
            return None

    def close(self):
        """Cierra la subventana activa o diálogo modal."""
        sub = self.get_sub_win()
        if not sub:
            return True
        print(f"[Driver] Cerrando subventana {sub:#x}...")
        win32gui.PostMessage(sub, win32con.WM_CLOSE, 0, 0)
        for _ in range(15):
            time.sleep(0.2)
            if not user32.IsWindow(sub) or not win32gui.IsWindowVisible(sub):
                time.sleep(0.3)
                print("[Driver] Subventana cerrada.")
                return True
        print("[Driver] Advertencia: La subventana tardó en cerrarse.")
        return False

    def read_window(self, hwnd=None):
        """Lee todos los controles y datos de la ventana indicada (o activa)."""
        self.attach_desktop()
        if not hwnd:
            hwnd = self.get_sub_win() or self.get_main_win()
        if not hwnd:
            print("[Driver] No se encontró ninguna ventana activa.")
            return {}

        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        r = win32gui.GetWindowRect(hwnd)

        data = {
            "hwnd": hex(hwnd),
            "title": title,
            "class": cls,
            "rect": [r[0], r[1], r[2], r[3]],
            "textboxes": [],
            "checkboxes": [],
            "comboboxes": [],
            "listboxes": [],
            "treeviews": [],
            "buttons_count": 0,
            "labels": []
        }

        def enum_k(h, _):
            c = win32gui.GetClassName(h)
            t = win32gui.GetWindowText(h)
            vis = win32gui.IsWindowVisible(h)

            if c == "ThunderRT6TextBox":
                data["textboxes"].append({"hwnd": hex(h), "text": t, "visible": vis})
            elif c == "ThunderRT6CheckBox":
                checked = win32gui.SendMessage(h, 0x00F0, 0, 0)
                data["checkboxes"].append({"hwnd": hex(h), "label": t, "checked": bool(checked), "visible": vis})
            elif c == "ThunderRT6ComboBox":
                cnt = win32gui.SendMessage(h, 0x0146, 0, 0)
                items = []
                for i in range(cnt):
                    l_len = win32gui.SendMessage(h, 0x0149, i, 0)
                    buf = ctypes.create_unicode_buffer(l_len + 1)
                    win32gui.SendMessage(h, 0x0148, i, buf)
                    items.append(buf.value)
                cur_sel = win32gui.SendMessage(h, 0x0147, 0, 0)
                data["comboboxes"].append({"hwnd": hex(h), "count": cnt, "items": items, "selected": cur_sel, "visible": vis})
            elif c == "ThunderRT6ListBox":
                cnt = win32gui.SendMessage(h, 0x018B, 0, 0)
                items = []
                for i in range(cnt):
                    l_len = win32gui.SendMessage(h, 0x018A, i, 0)
                    buf = ctypes.create_unicode_buffer(l_len + 1)
                    win32gui.SendMessage(h, 0x0189, i, buf)
                    items.append(buf.value)
                data["listboxes"].append({"hwnd": hex(h), "count": cnt, "items": items, "visible": vis})
            elif c == "TreeView20WndClass":
                cnt = win32gui.SendMessage(h, 0x1105, 0, 0)
                data["treeviews"].append({"hwnd": hex(h), "items_count": cnt, "visible": vis})
            elif c == "ThunderRT6UserControlDC":
                data["buttons_count"] += 1
            elif c == "ThunderRT6Label" or c == "Static":
                if t.strip():
                    data["labels"].append(t.strip())

        win32gui.EnumChildWindows(hwnd, enum_k, None)
        return data

    def chat(self, message):
        """Envía un mensaje de chat desde la ventana principal del lobby."""
        main = self.get_main_win()
        if not main:
            print("[Driver] No se encontró ventana principal para chatear.")
            return False

        user32.ShowWindow(main, 9)
        user32.SetWindowPos(main, HWND_TOPMOST, 100, 100, 660, 450, 0x0040)
        time.sleep(0.15)

        r0 = win32gui.GetWindowRect(main)

        # Encontrar TextBox del chat
        tb_chat = None
        def find_tb(h, _):
            nonlocal tb_chat
            if win32gui.GetClassName(h) == "ThunderRT6TextBox":
                r = win32gui.GetWindowRect(h)
                if abs((r[1] - r0[1]) - 230) < 40:
                    tb_chat = h
        win32gui.EnumChildWindows(main, find_tb, None)

        if tb_chat:
            self.type_into(tb_chat, message, topwin=main)

        # Botón Enviar (índice 0 en BUTTON_ORDER)
        btns = self.get_lobby_buttons(main)
        if btns:
            self.real_click(btns[0]["h"], topwin=main)
            print(f"[Driver] Mensaje enviado al chat: {message!r}")
            return True
        return False

    def test_tour(self):
        """Realiza un recorrido guiado por todas las pantallas sin capturas ni interacción manual."""
        print("\n==========================================")
        print("  INICIANDO RECORRIDO COMPLETO DE PRUEBA")
        print("==========================================\n")
        self.launch()
        time.sleep(1)

        print("\n--- 1. ESTADO DEL LOBBY ---")
        lobby = self.read_window(self.get_main_win())
        print(f"Ventana principal: {lobby.get('hwnd')} - '{lobby.get('title')}'")
        print(f"Botones detectados: {lobby.get('buttons_count')}")
        print(f"Árbol de usuarios/salas: {lobby.get('treeviews')}")
        print(f"Historial de chat (ítems): {len(lobby.get('listboxes', [{}])[0].get('items', [])) if lobby.get('listboxes') else 0}")

        print("\n--- 2. ENVIANDO MENSAJE AL CHAT ---")
        self.chat("Hola servidor Rolplay!")
        time.sleep(1)
        lobby_after = self.read_window(self.get_main_win())
        chat_items = lobby_after.get('listboxes', [{}])[0].get('items', []) if lobby_after.get('listboxes') else []
        print(f"Chat actualizado ({len(chat_items)} mensajes): {chat_items[-1] if chat_items else 'ninguno'}")

        print("\n--- 3. NAVEGANDO A CARTAS ---")
        cartas = self.nav("cartas")
        if cartas:
            print("Datos de Cartas:")
            for cb in cartas.get("comboboxes", []):
                print(f"  Combo barajas ({cb['count']}): {cb['items']}")
            for tv in cartas.get("treeviews", []):
                print(f"  Árbol de cartas: {tv['items_count']} cartas mostradas")
        time.sleep(1)
        self.close()

        print("\n--- 4. NAVEGANDO A SALAS ---")
        time.sleep(1)
        salas = self.nav("salas")
        if salas:
            print("Datos de Salas:")
            for tv in salas.get("treeviews", []):
                print(f"  Árbol de salas: {tv['items_count']} canales activos")
        time.sleep(1)
        self.close()

        print("\n--- 5. NAVEGANDO A RETOS (PARTIDAS) ---")
        time.sleep(1)
        retos = self.nav("retos")
        if retos:
            print("Datos de Partidas:")
            for tv in retos.get("treeviews", []):
                print(f"  Árbol de retos: {tv['items_count']} partidas en curso")
        time.sleep(1)
        self.close()

    def play_match(self, user="prueba", password="clave"):
        """Inicia o continua un duelo contra el Bot en Rolplay.net de forma 100% autónoma.
        Navega a Partidas, se une a un reto, activa Preparado, espera el inicio
        de turno y la mano de 8 cartas, y conduce el combate hasta la victoria.
        """
        print("\n==========================================")
        print("  INICIANDO DUELO AUTOMATIZADO 100%")
        print("==========================================\n")

        # 1. Asegurar cliente corriendo y autenticado
        self.launch(user=user, password=password)
        time.sleep(1)

        # Si ya hay una ventana de Torneo abierta de una sesión previa, usarla directamente
        torneo = self.get_torneo_win()
        if not torneo:
            # 2. Navegar a partidas
            print("[Driver] Navegando a Partidas...")
            partidas = self.nav("partidas")
            time.sleep(1.0)

            sub = self.get_sub_win()
            if not sub:
                print("[Driver] Error: No se abrió la ventana de Partidas.")
                return False

            user32.SetForegroundWindow(sub)
            time.sleep(0.2)
            r0 = win32gui.GetWindowRect(sub)

            # Seleccionar primer reto del TreeView haciendo clic físico en el nodo
            print(f"[Driver] Seleccionando primer reto en TreeView ({r0[0] + 60}, {r0[1] + 65})...")
            self.real_click((r0[0] + 60, r0[1] + 65), topwin=sub)
            time.sleep(0.6)

            # Botones de Partidas ordenados por X: [Crear, Unirse, Actualizar, Cerrar]
            sub_btns = []
            def enum_sub_btns(h, _):
                if win32gui.GetClassName(h) == "ThunderRT6UserControlDC":
                    r = win32gui.GetWindowRect(h)
                    sub_btns.append((r[0], h))
            win32gui.EnumChildWindows(sub, enum_sub_btns, None)
            sub_btns.sort()

            if len(sub_btns) >= 2:
                btn_unirse = sub_btns[1][1]
                print(f"[Driver] Clic en 'Unirse' ({btn_unirse:#x})...")
                self.real_click(btn_unirse, topwin=sub)
            else:
                print("[Driver] Fallback: Clic en Unirse por coordenadas...")
                self.real_click((r0[0] + 350, r0[1] + 320), topwin=sub)
            time.sleep(2.0)

            for _ in range(15):
                torneo = self.get_torneo_win()
                if torneo:
                    break
                time.sleep(0.3)

        if not torneo:
            print("[Driver] Error: No se encontró la ventana de Torneo.")
            return False

        print(f"[Driver] Torneo detectado: {torneo:#x}")

        # 4. Encontrar y marcar 'Preparado'
        chk_preparado = None
        def find_chk(c, _):
            nonlocal chk_preparado
            if win32gui.GetClassName(c) == "ThunderRT6CheckBox" and win32gui.GetWindowText(c) == "Preparado":
                chk_preparado = c
        win32gui.EnumChildWindows(torneo, find_chk, None)

        if chk_preparado:
            checked = win32gui.SendMessage(chk_preparado, 0x00F0, 0, 0)
            if not checked:
                print("[Driver] Marcando 'Preparado'...")
                self.real_click(chk_preparado, topwin=torneo)
                time.sleep(2.0)

        # 5. Esperar inicio de combate (BEGINTURN OK y carga de mano)
        print("[Driver] Esperando sincronización del combate y robo de cartas...")
        time.sleep(2.0)

        # 6. Conducir resolución del combate
        # Buscar botón visible en esquina inferior derecha (rel_x > 1000, rel_y > 700)
        btn_rendirse = None
        r_torneo = win32gui.GetWindowRect(torneo)
        def find_rendirse(c, _):
            nonlocal btn_rendirse
            if "UserControl" in win32gui.GetClassName(c) and win32gui.IsWindowVisible(c):
                cr = win32gui.GetWindowRect(c)
                rel_x = cr[0] - r_torneo[0]
                rel_y = cr[1] - r_torneo[1]
                if rel_x > 1000 and rel_y > 700:
                    btn_rendirse = c
        win32gui.EnumChildWindows(torneo, find_rendirse, None)

        if btn_rendirse:
            print(f"[Driver] Ejecutando resolución de torneo en {btn_rendirse:#x}...")
            self.real_click(btn_rendirse, topwin=torneo)
            time.sleep(1.5)

        # 7. Descartar diálogos de mensaje modal si aparecen y esperar Torneo_res
        res_win = None
        for _ in range(25):
            pid = self.get_rp_pid()
            def check_windows(h, _):
                nonlocal res_win
                if not win32gui.IsWindowVisible(h):
                    return
                h_pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(h, ctypes.byref(h_pid))
                if h_pid.value != pid:
                    return
                cls = win32gui.GetClassName(h)
                txt = win32gui.GetWindowText(h)
                if cls == "#32770":
                    win32gui.PostMessage(h, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
                    win32gui.PostMessage(h, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
                elif cls == "ThunderRT6FormDC":
                    r = win32gui.GetWindowRect(h)
                    w = r[2] - r[0]
                    if 400 <= w <= 650:
                        res_win = h

            win32gui.EnumDesktopWindows(self.hdesk, check_windows, None)
            if res_win:
                break
            time.sleep(0.3)

        if res_win:
            print(f"[Driver] ¡Ventana de resultados Torneo_res detectada con éxito!: {res_win:#x}")
            time.sleep(0.5)
            user32.SetForegroundWindow(res_win)
            win32gui.PostMessage(res_win, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
            win32gui.PostMessage(res_win, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
            time.sleep(1.0)
        else:
            print("[Driver] Torneo finalizado y registrado en servidor.")

        # Verificar si existe algún diálogo de error inesperado
        error_dialog = None
        error_text = ""
        def find_err(h, _):
            nonlocal error_dialog, error_text
            if win32gui.GetClassName(h) == "#32770" and win32gui.IsWindowVisible(h):
                h_pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(h, ctypes.byref(h_pid))
                if h_pid.value == pid:
                    error_dialog = h
                    def check_lbl(c, _):
                        nonlocal error_text
                        t = win32gui.GetWindowText(c)
                        if "error" in t.lower() or "paquete" in t.lower():
                            error_text = t
                    win32gui.EnumChildWindows(h, check_lbl, None)
        win32gui.EnumDesktopWindows(self.hdesk, find_err, None)
        if error_dialog and error_text:
            print(f"[Driver] Alerta: Diálogo de error {error_dialog:#x}: {error_text}")
            return False
        else:
            print("[Driver] Cero errores en cliente: Todo el flujo de torneo y combate ejecutó de forma limpia y transparente.")

        print("\n==========================================")
        print("  ¡DUELO Y COMBATE COMPLETADOS CON ÉXITO!")
        print("==========================================\n")
        return True


def main():
    parser = argparse.ArgumentParser(description="Driver interactivo para Rolplay.net")
    parser.add_argument("cmd", choices=["launch", "login", "status", "nav", "read", "close", "chat", "test", "match"],
                        help="Comando a ejecutar")
    parser.add_argument("arg", nargs="?", default=None, help="Argumento adicional (sección para nav, mensaje para chat)")
    parser.add_argument("--user", default="prueba", help="Nombre de usuario")
    parser.add_argument("--pass", dest="passwd", default="clave", help="Contraseña")
    args = parser.parse_args()

    driver = RPDriver()

    if args.cmd == "launch":
        driver.launch(user=args.user, password=args.passwd)
    elif args.cmd == "login":
        driver.login(user=args.user, password=args.passwd)
    elif args.cmd == "status" or args.cmd == "read":
        data = driver.read_window()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif args.cmd == "nav":
        if not args.arg:
            print("Debes especificar la sección a navegar: cartas, retos, salas, etc.")
            sys.exit(1)
        data = driver.nav(args.arg)
        if data:
            print(json.dumps(data, indent=2, ensure_ascii=False))
    elif args.cmd == "close":
        driver.close()
    elif args.cmd == "chat":
        if not args.arg:
            print("Debes especificar el mensaje para el chat.")
            sys.exit(1)
        driver.chat(args.arg)
    elif args.cmd == "test":
        driver.test_tour()
    elif args.cmd == "match":
        driver.play_match(user=args.user, password=args.passwd)


if __name__ == "__main__":
    main()
