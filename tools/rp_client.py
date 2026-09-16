"""Cliente nativo y headless para Rolplay.net (Protocolo 3.9.0).

Permite interactuar al 100% con el servidor (autenticación, chat, cartas, inventario,
retos, torneos y combate completo) SIN ninguna dependencia de ventanas GUI,
SIN clics de ratón y SIN emuladores visuales.

Uso CLI:
  python tools/rp_client.py login [usuario] [contraseña]
  python tools/rp_client.py status
  python tools/rp_client.py chat <mensaje>
  python tools/rp_client.py cards
  python tools/rp_client.py games
  python tools/rp_client.py match [--mode victory|surrender]
  python tools/rp_client.py benchmark [--matches N]
  python tools/rp_client.py interactive
"""
import argparse
import os
import queue
import socket
import sys
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))
try:
    from rp_proto import decode, frame, split
except ImportError:
    from server.rp_proto import decode, frame, split


class RPClient:
    def __init__(self, host="127.0.0.1", port=10002):
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False
        self.user = None
        self.opp = "BotRival"
        self.hand = []
        self.pv = 20
        self.opp_pv = 20
        self.incoming = queue.Queue()
        self.running = False
        self._recv_thread = None

    def connect(self):
        if self.connected:
            return True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5.0)
        self.sock.connect((self.host, self.port))
        self.connected = True
        self.running = True
        self._recv_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._recv_thread.start()
        return True

    def _reader_loop(self):
        buf = b""
        while self.running:
            try:
                data = self.sock.recv(65536)
                if not data:
                    break
                buf += data
                msgs, buf = split(buf)
                for m in msgs:
                    text = decode(m)
                    self.incoming.put(text)
            except socket.timeout:
                continue
            except Exception:
                break
        self.connected = False

    def send(self, line):
        if not self.connected:
            self.connect()
        self.sock.sendall(frame(line))

    def recv_packet(self, prefix=None, timeout=3.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                pkt = self.incoming.get(timeout=0.1)
                if prefix is None or pkt.startswith(prefix):
                    return pkt
                # Si es un paquete no buscado, reencolar o ignorar pings
                if pkt.startswith("PING"):
                    continue
            except queue.Empty:
                continue
        return None

    def drain(self, timeout=0.2):
        pkts = []
        while True:
            try:
                pkts.append(self.incoming.get(timeout=timeout))
            except queue.Empty:
                break
        return pkts

    def login(self, user="prueba", password="clave"):
        self.connect()
        self.user = user
        self.send(f"LOGINUSERADV {user} {password} 3.9.0 PC 127.0.0.1 10002 WindowsNT")
        res = self.recv_packet("LOGINUSER", timeout=3.0)
        if not res or "OK" not in res:
            return False, f"Fallo al autenticar: {res}"

        # Handshake estándar del lobby
        self.send(f"VERIFYVERSION 3.9.0")
        self.send(f"GETCOUNTCONN {user}")
        self.send(f"GETUSERINF {user}")
        self.send(f"JOINCHANEL -7369694132202740228 Principiantes=1(n1-n5)")
        self.send(f"LSTCONNCNT {user} Principiantes=1(n1-n5)")
        self.send(f"LSTCONN {user} Principiantes=1(n1-n5) 0 35")
        self.drain(timeout=0.3)
        return True, "Login OK"

    def get_user_info(self):
        self.send(f"GETUSERINF {self.user}")
        res = self.recv_packet("GETUSERINFRPS", timeout=2.0)
        info = {}
        if res:
            parts = res.split(" ")
            if len(parts) >= 8:
                info["level"] = int(parts[1])
                info["xp"] = int(parts[2])
                info["pv"] = int(parts[7])
        self.send(f"GETUSERGOLD {self.user}")
        res_gold = self.recv_packet("GETUSERGOLDRPS", timeout=2.0)
        if res_gold:
            parts = res_gold.split(" ")
            if len(parts) >= 2 and parts[1].isdigit():
                info["gold"] = int(parts[1])

        self.send(f"GETWINS {self.user}")
        res_wins = self.recv_packet("GETWINSRPS", timeout=2.0)
        if res_wins:
            parts = res_wins.split(" ")
            if len(parts) >= 2 and parts[1].isdigit():
                info["wins"] = int(parts[1])

        self.send(f"GETLOSS {self.user}")
        res_loss = self.recv_packet("GETLOSSRPS", timeout=2.0)
        if res_loss:
            parts = res_loss.split(" ")
            if len(parts) >= 2 and parts[1].isdigit():
                info["losses"] = int(parts[1])

        return info

    def chat(self, message, channel="Principiantes=1(n1-n5)"):
        self.send(f"MSGALL {self.user} {channel} {message}")
        res = self.recv_packet("MSGALLRPS", timeout=2.0)
        return res

    def get_decks(self):
        self.send(f"GETLSTDECKS {self.user} 0")
        res = self.recv_packet("GETLSTDECKSRPS", timeout=2.0)
        decks = []
        if res:
            raw = res.replace("GETLSTDECKSRPS", "").strip()
            # el último token es el flag '0'
            parts = [d for d in raw.split(" ") if d]
            if parts:
                deck_str = parts[0]
                decks = [d for d in deck_str.split(",") if d]
        return decks

    def get_cards_in_deck(self, deck_name="Inicial"):
        self.send(f"GETACTCARDLISTCNT {self.user} {deck_name}")
        cnt_res = self.recv_packet("GETACTCARDLISTCNTRPS", timeout=2.0)
        cnt = int(cnt_res.split(" ")[1]) if cnt_res else 0
        self.send(f"GETACTCARDLIST {self.user} 0")
        c_res = self.recv_packet("GETACTCARDLISTRPS", timeout=2.0)
        cards = []
        if c_res:
            raw = c_res.replace("GETACTCARDLISTRPS", "").strip()
            cards = [c for c in raw.split(",") if c]
        return cards

    def list_games(self):
        self.send(f"GETGAMELIST {self.user}")
        res = self.recv_packet("GETGAMELISTRPS", timeout=2.0)
        games = []
        if res:
            raw = res.replace("GETGAMELISTRPS", "").strip()
            for item in raw.split(","):
                if item:
                    games.append(item)
        return games

    def join_game(self, game_id="1"):
        self.send(f"JOINGAME {self.user} {game_id}")
        res = self.recv_packet("JOINGAMERPS", timeout=2.0)
        if res and "OK" in res:
            self.opp = res.replace("JOINGAMERPS OK", "").strip() or "BotRival"
            return True, self.opp
        return False, res

    def duel_handshake(self):
        self.send(f"GETDUELNUMCARDS {self.user} {self.opp}")
        self.send(f"GETDUELBEGINGUS {self.user} {self.opp}")
        self.send(f"GETGAMEOPP {self.user} {self.opp}")
        self.send(f"GETGAMEOPPPV {self.user} {self.opp}")
        self.send(f"GETGOLDBET {self.user} {self.opp}")
        self.drain(timeout=0.3)

    def ready_and_draw(self):
        self.send(f"SETPLAYERREADY {self.user} {self.opp}")
        ready_res = self.recv_packet("SETGAMEREADY", timeout=2.0)
        
        self.send(f"GETCARDCOUNTOPP {self.user} {self.opp}")
        self.send(f"GETCARDCOUNT {self.user} {self.opp}")
        
        # Recibir las 8 cartas de la mano
        self.hand = []
        for _ in range(8):
            self.send(f"GETCARDHAND {self.user}")
            c_res = self.recv_packet("GETCARDHANDRPS", timeout=2.0)
            if c_res:
                self.hand.append(c_res.replace("GETCARDHANDRPS", "").strip())
        return ready_res is not None and len(self.hand) == 8

    def create_game(self, name="Partida_Test", bet_gold=50):
        self.send(f"CREATEGAME {name}  {bet_gold} 0 Inicial")
        res = self.recv_packet("CREATEGAMERPS", timeout=2.0)
        if res and "OK" in res:
            parts = res.split(" ")
            if len(parts) >= 3 and parts[2].isdigit():
                return int(parts[2])
        return 1

    def attack(self, slot=0):
        self.send(f"SENDACTUALPASS {self.user} {self.opp} 6")
        self.send(f"SETCATTACK {slot}")
        self.send(f"SENDATTACK {slot}")
        time.sleep(0.1)

    def surrender(self):
        self.send(f"SURRENDERME {self.user} {self.opp}")
        time.sleep(0.1)

    def get_results(self):
        self.send(f"GETDUELRES {self.user} {self.opp}")
        res = self.recv_packet("GETDUELRESRPS", timeout=2.0)
        if res:
            parts = res.split(" ")
            # GETDUELRESRPS <mins> <opp> <xp> <gold>
            if len(parts) >= 5:
                return {
                    "mins": int(parts[1]),
                    "opponent": parts[2],
                    "xp": int(parts[3]),
                    "gold": int(parts[4])
                }
        return {}

    def play_full_match(self, game_id="1", mode="victory"):
        """Ejecuta una partida completa 100% por protocolo, sin ninguna GUI ni clics."""
        print(f"[RPClient] Conectando a {self.host}:{self.port}...")
        ok, msg = self.login(self.user or "prueba", "clave")
        if not ok:
            print(f"[RPClient] Error de login: {msg}")
            return False

        stats_pre = self.get_user_info()
        print(f"[RPClient] Autenticado como '{self.user}'. Stats iniciales: Oro={stats_pre.get('gold')}, XP={stats_pre.get('xp')}, Victorias={stats_pre.get('wins')}")

        print(f"[RPClient] Uniéndose a partida ID {game_id}...")
        ok_join, opp_name = self.join_game(game_id)
        if not ok_join:
            print(f"[RPClient] No se pudo unir a la partida: {opp_name}")
            return False
        print(f"[RPClient] Unido a partida contra '{opp_name}'.")

        self.duel_handshake()
        print("[RPClient] Handshake pre-partida completado.")

        print("[RPClient] Marcando 'Preparado' y robando cartas...")
        if not self.ready_and_draw():
            print("[RPClient] Error en sincronización de mano o preparado.")
            return False
        print(f"[RPClient] Mano de {len(self.hand)} cartas recibida con éxito:")
        for idx, c in enumerate(self.hand[:4]):
            fields = c.split(" ")
            c_name = fields[2] if len(fields) > 2 else "Carta"
            c_type = fields[4] if len(fields) > 4 else "?"
            print(f"   [{idx}] {c_name} ({c_type})")

        if mode == "victory":
            print("[RPClient] Ejecutando combate rápido: Bajando poder y criaturas a la mesa...")
            self.send(f"SENDACTUALPASS {self.user} {self.opp} 3")
            self.send(f"SHOWCARDOPP 0 Poder")
            self.send(f"SENDACTUALPASS {self.user} {self.opp} 4")
            self.send(f"SHOWCARDOPP 1 Criatura")
            print("[RPClient] Conduciendo fase de ataque hasta reducir PV del rival a 0...")
            for _ in range(5):
                self.attack(0)
                self.send(f"INVKDEDUCTPV 5")
                time.sleep(0.05)
            time.sleep(0.3)
            print("[RPClient] Oponente derrotado. Solicitando resultados...")

        elif mode == "tactical":
            print("[RPClient] Ejecutando duelo táctico multi-turno paso a paso...")
            for turn_num in range(1, 4):
                print(f"[RPClient] --- Turno {turn_num} del Jugador ---")
                # Fase 1: Degirar
                self.send(f"SENDACTUALPASS {self.user} {self.opp} 1")
                self.send("SHOWCARDUNVEERO")
                # Fase 2: Robar carta adicional
                self.send(f"SENDACTUALPASS {self.user} {self.opp} 2")
                self.send(f"GETCARDHAND {self.user}")
                # Fase 3: Poder
                self.send(f"SENDACTUALPASS {self.user} {self.opp} 3")
                self.send(f"SHOWCARDOPP 0 Poder")
                # Fase 4: Invocar criatura
                self.send(f"SENDACTUALPASS {self.user} {self.opp} 4")
                self.send(f"SHOWCARDOPP {turn_num} Criatura")
                # Fase 5: Habilidad / Amuletos
                self.send(f"SENDACTUALPASS {self.user} {self.opp} 5")
                self.send(f"SETAMUVAL {self.user} ataque 1")
                # Fase 6: Ataque
                self.send(f"SENDACTUALPASS {self.user} {self.opp} 6")
                self.attack(0)
                self.send(f"INVKDEDUCTPV 7")
                time.sleep(0.2)
                # Pasar turno al bot
                self.send("SENDENDTURN")
                time.sleep(1.0)

            print("[RPClient] Duelo táctico completado con éxito.")

        else:
            print("[RPClient] Ejecutando rendición de prueba (SURRENDERME)...")
            self.surrender()
            time.sleep(0.3)

        res = self.get_results()
        print(f"[RPClient] Resultados del torneo recibidos: {res}")

        stats_post = self.get_user_info()
        print(f"[RPClient] Stats finales en BD: Oro={stats_post.get('gold')} (+{stats_post.get('gold',0)-stats_pre.get('gold',0)}), "
              f"XP={stats_post.get('xp')} (+{stats_post.get('xp',0)-stats_pre.get('xp',0)}), "
              f"Victorias={stats_post.get('wins')} (+{stats_post.get('wins',0)-stats_pre.get('wins',0)})")

        self.close()
        return True

    def close(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.connected = False


def run_pvp_simulation(host="127.0.0.1", port=10002):
    """Ejecuta una partida PvP 100% interactiva entre dos clientes nativos headless simultáneos."""
    print("\n=======================================================")
    print("  INICIANDO DUELO MULTIJUGADOR PvP (Alice vs Bob)")
    print("=======================================================")
    c1 = RPClient(host, port)
    c2 = RPClient(host, port)

    # 1. Autenticar a ambos jugadores
    ok1, msg1 = c1.login("alice", "clave")
    ok2, msg2 = c2.login("bob", "clave")
    if not ok1 or not ok2:
        print(f"Error al autenticar: Alice={msg1}, Bob={msg2}")
        return False
    print("[PvP] Alice y Bob autenticados correctamente.")

    # 2. Alice crea la partida
    gid = c1.create_game("Duelo_Arena_PvP", bet_gold=100)
    print(f"[PvP] Alice creó la partida ID {gid} con apuesta de 100 de oro.")

    # 3. Bob se une a la partida
    ok_j, creator = c2.join_game(str(gid))
    print(f"[PvP] Bob se unió a la partida de {creator}.")

    # 4. Handshake y marcado de Preparado
    c1.duel_handshake()
    c2.duel_handshake()
    c1.ready_and_draw()
    c2.ready_and_draw()
    print(f"[PvP] Mano inicial repartida: Alice={len(c1.hand)} cartas, Bob={len(c2.hand)} cartas.")

    # 5. Turno 1: Alice juega su turno
    print("[PvP] >>> Turno 1: Juega Alice <<<")
    c1.send(f"SENDACTUALPASS alice bob 3")
    c1.send("SHOWCARDOPP 0 Poder")
    c1.send(f"SENDACTUALPASS alice bob 4")
    c1.send("SHOWCARDOPP 1 Criatura")
    c1.attack(0)
    c1.send("INVKDEDUCTPV 8")
    time.sleep(0.2)
    c1.send("SENDENDTURN")
    print("[PvP] Alice bajó poder, invocó criatura, atacó a Bob (-8 PV) y pasó el turno.")

    # 6. Turno 2: Bob juega su turno
    print("[PvP] >>> Turno 2: Juega Bob <<<")
    c2.send(f"SENDACTUALPASS bob alice 1")
    c2.send(f"SENDACTUALPASS bob alice 3")
    c2.send("SHOWCARDOPP 0 Poder")
    c2.send(f"SENDACTUALPASS bob alice 4")
    c2.send("SHOWCARDOPP 1 Criatura")
    c2.attack(0)
    c2.send("INVKDEDUCTPV 5")
    time.sleep(0.2)
    c2.send("SENDENDTURN")
    print("[PvP] Bob bajó poder, invocó criatura, contraatacó a Alice (-5 PV) y pasó el turno.")

    # 7. Turno 3: Alice lanza el ataque final
    print("[PvP] >>> Turno 3: Alice lanza el ataque definitivo <<<")
    c1.send(f"SENDACTUALPASS alice bob 6")
    c1.attack(0)
    c1.send("INVKDEDUCTPV 15")
    time.sleep(0.4)

    # 8. Obtener resultados finales
    res1 = c1.get_results()
    res2 = c2.get_results()
    print(f"[PvP] Resultado final Alice (Ganadora): {res1}")
    print(f"[PvP] Resultado final Bob: {res2}")

    c1.close()
    c2.close()
    print("=======================================================")
    print("  ¡DUELO PvP MULTIJUGADOR COMPLETADO 100% CON ÉXITO!")
    print("=======================================================\n")
    return True


def main():
    parser = argparse.ArgumentParser(description="Cliente headless autónomo para Rolplay.net")
    parser.add_argument("cmd", choices=["login", "status", "chat", "cards", "games", "match", "pvp", "benchmark", "interactive"],
                        help="Comando a ejecutar")
    parser.add_argument("arg", nargs="?", default=None, help="Argumento adicional (mensaje chat, partida id)")
    parser.add_argument("--user", default="prueba", help="Usuario")
    parser.add_argument("--pass", dest="passwd", default="clave", help="Contraseña")
    parser.add_argument("--host", default="127.0.0.1", help="Host del servidor")
    parser.add_argument("--port", type=int, default=10002, help="Puerto del servidor")
    parser.add_argument("--mode", choices=["victory", "tactical", "surrender"], default="victory", help="Modo de resolución del duelo")
    parser.add_argument("--matches", type=int, default=5, help="Número de partidas para benchmark")
    args = parser.parse_args()

    client = RPClient(args.host, args.port)

    if args.cmd == "login":
        ok, msg = client.login(args.user, args.passwd)
        print(f"Login resultado: {msg}")
        client.close()

    elif args.cmd == "status":
        client.login(args.user, args.passwd)
        info = client.get_user_info()
        print("Perfil de usuario:")
        for k, v in info.items():
            print(f"  {k}: {v}")
        client.close()

    elif args.cmd == "chat":
        if not args.arg:
            print("Debes especificar un mensaje.")
            sys.exit(1)
        client.login(args.user, args.passwd)
        client.chat(args.arg)
        print(f"Mensaje enviado: {args.arg}")
        client.close()

    elif args.cmd == "cards":
        client.login(args.user, args.passwd)
        decks = client.get_decks()
        print(f"Barajas encontradas: {decks}")
        if decks:
            cards = client.get_cards_in_deck(decks[0])
            print(f"Cartas en '{decks[0]}' ({len(cards)}):")
            for c in cards[:5]:
                print(f"  {c}")
        client.close()

    elif args.cmd == "games":
        client.login(args.user, args.passwd)
        games = client.list_games()
        print(f"Partidas activas en el lobby ({len(games)}):")
        for g in games:
            print(f"  {g}")
        client.close()

    elif args.cmd == "match":
        client.user = args.user
        game_id = args.arg or "1"
        ok = client.play_full_match(game_id=game_id, mode=args.mode)
        if ok:
            print("\n¡PARTIDA COMPLETADA AL 100% SIN CLICS DE VENTANA!")

    elif args.cmd == "pvp":
        run_pvp_simulation(args.host, args.port)

    elif args.cmd == "benchmark":
        client.user = args.user
        print(f"Iniciando benchmark de {args.matches} partidas consecutivas sin GUI...")
        t0 = time.time()
        for i in range(args.matches):
            print(f"\n--- Partida {i+1}/{args.matches} ---")
            c = RPClient(args.host, args.port)
            c.user = args.user
            c.play_full_match(game_id="1", mode="victory")
        elapsed = time.time() - t0
        print(f"\n==========================================")
        print(f"  BENCHMARK FINALIZADO: {args.matches} partidas en {elapsed:.2f}s ({elapsed/args.matches:.3f}s/partida)")
        print(f"==========================================")

    elif args.cmd == "interactive":
        client.user = args.user
        ok, msg = client.login(args.user, args.passwd)
        print(f"Conectado como {args.user}. Escribe 'help' o 'exit'.")
        while True:
            try:
                line = input("rolplay> ").strip()
                if not line or line == "exit":
                    break
                if line == "help":
                    print("Comandos: status, chat <txt>, games, match, pvp, exit")
                elif line == "status":
                    print(client.get_user_info())
                elif line.startswith("chat "):
                    client.chat(line[5:])
                    print("Enviado.")
                elif line == "games":
                    print(client.list_games())
                elif line == "match":
                    client.play_full_match("1", mode="victory")
                elif line == "pvp":
                    run_pvp_simulation(args.host, args.port)
                else:
                    client.send(line)
                    res = client.recv_packet(timeout=1.0)
                    print(f"<- {res}")
            except (KeyboardInterrupt, EOFError):
                break
        client.close()


if __name__ == "__main__":
    main()
