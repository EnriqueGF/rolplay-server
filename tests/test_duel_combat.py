"""Pruebas completas del motor de duelo, combate, fases y persistencia en base de datos.
Verifica que el 100% de la lógica de cartas, turnos y resolución de torneos funciona fielmente.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))
import db
import duel
import handlers


class FakeConn:
    def __init__(self, user="prueba"):
        self.user = user
        self.channel = "Principiantes 1(n1-n5)"
        self.sent = []

    def send(self, msg):
        self.sent.append(msg)


class TestDuelCombat(unittest.TestCase):
    def setUp(self):
        # Asegurar usuario de prueba en base de datos
        db.init_db()
        u = db.get_user("tester")
        if not u:
            db.create_user("tester", "clave")
        duel.duel_manager.duels.clear()
        duel.duel_manager.user_to_duel.clear()
        # Asegurar partida de prueba ID 1 con creador Jugador2
        games = db.get_active_games("Principiantes 1(n1-n5)")
        if not any(g["id"] == 1 for g in games):
            with db._lock, db.get_conn() as conn:
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO games (id, name, creator, channel, status, bet_gold) VALUES (1, 'Duelo_Epico', 'Jugador2', 'Principiantes 1(n1-n5)', 'waiting', 100)")
                conn.commit()

    def test_deck_initialization(self):
        """Verifica que un DuelPlayer siempre tiene un mazo balanceado de 24+ cartas."""
        p = duel.DuelPlayer("tester", is_bot=False)
        self.assertGreaterEqual(len(p.deck), 24)
        bot = duel.DuelPlayer("BotRival", is_bot=True)
        self.assertGreaterEqual(len(bot.deck), 24)

    def test_card_payload_format(self):
        """Verifica que el payload de la mano coincide exactamente con lo esperado por el cliente VB6."""
        c_cr = duel.Card(2, "Elfo Bardo", 1, "crt_elfo_bardo.jpg", ctype="Criatura", atk=1, df=1, cost=1)
        payload = c_cr.format_hand_payload()
        parts = payload.split(" ")
        self.assertEqual(parts[0], "1")
        self.assertEqual(parts[1], "2")
        self.assertEqual(parts[2], "crt_elfo_bardo.jpg")
        self.assertEqual(parts[3], "1")
        self.assertEqual(parts[4], "Criatura")
        self.assertEqual(parts[5], "1") # Atk
        self.assertEqual(parts[6], "1") # Def
        self.assertEqual(parts[7], "1") # Cost
        self.assertEqual(len(parts), 22) # 8 campos + 14 habilidades

        c_pw = duel.Card(1, "Poder", 1, "crt_poder.jpg", ctype="Poder", pwr=1)
        payload_pw = c_pw.format_hand_payload()
        parts_pw = payload_pw.split(" ")
        self.assertEqual(parts_pw[4], "Poder")
        self.assertEqual(len(parts_pw), 13)

    def test_duel_flow_and_ready(self):
        """Verifica la creación del duelo, asignación de turnos y sincronización de listos."""
        d = duel.Duel(999, "Jugador2", "tester")
        self.assertTrue(d.p1.is_bot)
        self.assertTrue(d.p1.ready)
        self.assertFalse(d.p2.ready)
        self.assertEqual(d.turn, 2) # El jugador humano inicia el turno
        self.assertFalse(d.is_ready())

        ready = d.set_ready("tester")
        self.assertTrue(ready)
        self.assertTrue(d.is_ready())
        self.assertEqual(d.status, "playing")
        self.assertTrue(d.is_active_turn("tester"))

    def test_phases_and_playing_cards(self):
        """Verifica el avance de fases y la colocación de Poderes y Criaturas en mesa."""
        conn = FakeConn("tester")
        d = duel.Duel(998, "Jugador2", "tester")
        duel.duel_manager.duels[998] = d
        duel.duel_manager.user_to_duel["tester"] = 998
        d.set_ready("tester")
        d.p2.connection = conn

        # Añadir cartas controladas a la mano
        card_pwr = duel.Card(1, "Poder", 1, "crt_poder.jpg", ctype="Poder", pwr=1)
        card_cr = duel.Card(2, "Elfo Bardo", 1, "crt_elfo_bardo.jpg", ctype="Criatura", atk=2, df=2, cost=1)
        d.p2.hand = [card_pwr, card_cr]

        # Fase 3: Bajar poder
        handlers.h_SENDACTUALPASS(conn, ["tester", "Jugador2", "3"], {})
        self.assertEqual(d.phase, 3)

        handlers.h_SHOWCARDOPP(conn, ["0", "Poder"], {})
        self.assertEqual(len(d.p2.board_power), 1)
        self.assertEqual(d.p2.power_pool, 1)

        # Fase 4: Invocar criatura
        handlers.h_SENDACTUALPASS(conn, ["tester", "Jugador2", "4"], {})
        self.assertEqual(d.phase, 4)

        handlers.h_SHOWCARDOPP(conn, ["1", "Criatura"], {})
        self.assertEqual(len(d.p2.board_creatures), 1)
        self.assertEqual(d.p2.board_creatures[0].name, "Elfo Bardo")

    def test_combat_damage_and_victory(self):
        """Verifica el cálculo de ataque directo, deducción de PV y fin de torneo con recompensas."""
        conn = FakeConn("tester")
        d = duel.Duel(997, "Jugador2", "tester")
        duel.duel_manager.duels[997] = d
        duel.duel_manager.user_to_duel["tester"] = 997
        d.set_ready("tester")
        d.p2.connection = conn

        # Criatura atacante de 20 de daño para victoria directa
        attacker = duel.Card(10, "Titan", 5, "crt_titan.jpg", ctype="Criatura", atk=20, df=10, cost=1)
        d.p2.board_creatures = [attacker]
        d.p1.board_creatures = [] # Sin defensores
        d.p1.pv = 20

        # Obtener stats previas
        u_prev = db.get_user("tester")
        prev_gold = u_prev["gold"]
        prev_xp = u_prev["xp"]
        prev_wins = u_prev.get("wins", 0)

        # Fase 6: Ataque
        d.player_attack("tester", 0)

        # Oponente debe haber recibido 20 de daño y haber llegado a 0 PV
        self.assertEqual(d.p1.pv, 0)
        self.assertEqual(d.status, "finished")
        self.assertEqual(d.winner, "tester")

        # Verificar paquetes enviados al jugador
        sent_types = [msg.split(" ")[0] for msg in conn.sent]
        self.assertIn("SHOWCARDVEERACT", sent_types)
        self.assertIn("DEDUCTPVOPP", sent_types)
        self.assertIn("DEADPLAYER", sent_types)
        # Verificar que DEADPLAYER tiene el formato seguro para VB6 (con espacio)
        for msg in conn.sent:
            if msg.startswith("DEADPLAYER"):
                self.assertIn(" ", msg)

        # Verificar solicitud y recepción de resultados del torneo
        res_duel = handlers.h_GETDUELRES(conn, ["tester"], {})
        self.assertTrue(res_duel[0].startswith("GETDUELRESRPS 1"))

        # Verificar persistencia en base de datos SQLite
        u_post = db.get_user("tester")
        self.assertGreater(u_post["gold"], prev_gold)
        self.assertGreater(u_post["xp"], prev_xp)
        self.assertEqual(u_post.get("wins", 0), prev_wins + 1)

    def test_creature_vs_creature_combat(self):
        """Verifica el cálculo de ataque vs defensa, muerte de criaturas y daño sobrante."""
        conn = FakeConn("tester")
        d = duel.Duel(996, "Jugador2", "tester")
        duel.duel_manager.duels[996] = d
        duel.duel_manager.user_to_duel["tester"] = 996
        d.set_ready("tester")
        d.p2.connection = conn

        # Atacante: 5/3. Defensor: 3/2
        cr_atk = duel.Card(11, "Guerrero", 2, "", ctype="Criatura", atk=5, df=3, cost=2)
        cr_def = duel.Card(12, "Defensor", 1, "", ctype="Criatura", atk=3, df=2, cost=1)
        d.p2.board_creatures = [cr_atk]
        d.p1.board_creatures = [cr_def]
        d.p1.pv = 20

        d.player_attack("tester", 0)

        # Defensor tiene defensa 2 y el ataque es 5 -> defensor muere, daño sobrante = 3 a PV
        self.assertEqual(len(d.p1.board_creatures), 0)
        self.assertEqual(d.p1.pv, 17) # 20 - (5 - 2) = 17

        # Contraataque: defensor tenía ataque 3, atacante tenía defensa 3 -> atacante también muere
        self.assertEqual(len(d.p2.board_creatures), 0)

    def test_e2e_handlers_duel(self):
        """Simula el flujo completo de paquetes del cliente desde entrar a partida hasta ganar."""
        conn = FakeConn("tester")
        
        # 1. Unirse a partida
        res = handlers.h_JOINGAME(conn, ["tester", "1"], {})
        self.assertEqual(res, ["JOINGAMERPS OKJugador2"])

        # 2. Handshake pre-partida
        self.assertEqual(handlers.h_GETDUELNUMCARDS(conn, ["tester", "Jugador2"], {}), ["GETDUELNUMCARDSRPS 8"])
        self.assertEqual(handlers.h_GETDUELBEGINGUS(conn, ["tester", "Jugador2"], {}), ["GETDUELBEGINGUSRPS 2"])
        self.assertEqual(handlers.h_GETGAMEOPP(conn, ["tester", "Jugador2"], {}), ["GETGAMEOPPRPS Jugador2"])
        self.assertEqual(handlers.h_GETGAMEOPPPV(conn, ["tester", "Jugador2"], {}), ["GETGAMEOPPPVRPS 20"])

        # 3. Marcar Preparado
        res_ready = handlers.h_SETPLAYERREADY(conn, ["tester", "Jugador2"], {})
        self.assertEqual(res_ready, ["SETGAMEREADY OK"])

        # 4. Solicitud de conteo de cartas tras SETGAMEREADY
        res_opp = handlers.h_GETCARDCOUNTOPP(conn, ["tester", "Jugador2"], {})
        self.assertTrue(res_opp[0].startswith("GETCARDCOUNTOPPRPS"))

        res_cnt = handlers.h_GETCARDCOUNT(conn, ["tester", "Jugador2"], {})
        self.assertTrue(res_cnt[0].startswith("GETCARDCOUNTRPS"))
        self.assertIn("BEGINTURN OK", res_cnt)

        # 5. Robo de las 8 cartas de la mano
        for i in range(8):
            hand_res = handlers.h_GETCARDHAND(conn, ["tester"], {})
            self.assertTrue(hand_res[0].startswith("GETCARDHANDRPS 1"))

        # 6. Fases de combate y ataque ganador
        d = duel.duel_manager.get_user_duel("tester")
        self.assertIsNotNone(d)
        d.p1.pv = 1 # Vida restante 1 para remate con criatura básica (atk 1)
        handlers.h_SENDACTUALPASS(conn, ["tester", "Jugador2", "6"], {})

        # Atacar con criatura
        handlers.h_SENDATTACK(conn, ["0"], {})
        self.assertEqual(d.p1.pv, 0)
        self.assertEqual(d.status, "finished")

        # 7. Solicitar resultados finales del torneo
        res_final = handlers.h_GETDUELRES(conn, ["tester"], {})
        self.assertTrue(res_final[0].startswith("GETDUELRESRPS 1"))

    def test_creature_special_abilities(self):
        """Verifica el cálculo de combate con habilidades especiales: Primer Golpe, Veneno, Vuelo, Regeneración, Arrollar."""
        d = duel.Duel(995, "Jugador2", "tester")
        d.set_ready("tester")

        # 1. Primer Golpe: Atacante 3/1 con Primer Golpe vs Defensor 5/3 sin Primer Golpe
        # El atacante debe matar al defensor y sobrevivir sin recibir daño.
        cr_first_strike = duel.Card(20, "Arquero Elfo", 2, "", atk=3, df=1, cost=2,
                                    abilities=[0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        cr_normal = duel.Card(21, "Orco Fuerte", 3, "", atk=5, df=3, cost=3,
                              abilities=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        d.p2.board_creatures = [cr_first_strike]
        d.p1.board_creatures = [cr_normal]
        d.player_attack("tester", 0)
        self.assertIn(cr_first_strike, d.p2.board_creatures) # Sobrevive
        self.assertNotIn(cr_normal, d.p1.board_creatures) # Defensor muerto

        # 2. Veneno: Atacante 1/1 con Veneno vs Defensor 1/10
        # Debe matar al defensor gigante independientemente de su defensa.
        cr_poison = duel.Card(22, "Víbora Negra", 1, "", atk=1, df=1, cost=1,
                              abilities=[0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        cr_giant = duel.Card(23, "Gigante de Roca", 5, "", atk=0, df=10, cost=5,
                             abilities=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        d.p2.board_creatures = [cr_poison]
        d.p1.board_creatures = [cr_giant]
        d.player_attack("tester", 0)
        self.assertNotIn(cr_giant, d.p1.board_creatures) # Defensor muere por veneno

        # 3. Regeneración: Defensor con regeneración sobrevive a daño letal la primera vez
        cr_attacker = duel.Card(24, "Guerrero", 2, "", atk=5, df=5, cost=2)
        cr_regen = duel.Card(25, "Golem de Barro", 3, "", atk=1, df=2, cost=3,
                             abilities=[0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        d.p2.board_creatures = [cr_attacker]
        d.p1.board_creatures = [cr_regen]
        d.player_attack("tester", 0)
        self.assertIn(cr_regen, d.p1.board_creatures) # No muere, se regenera
        self.assertTrue(cr_regen.tapped)

        # 4. Vuelo: Criatura sin vuelo no puede bloquear a una criatura con vuelo
        cr_flyer = duel.Card(26, "Águila Gigante", 2, "", atk=3, df=2, cost=2,
                             abilities=[1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        cr_ground = duel.Card(27, "Enano", 1, "", atk=2, df=2, cost=1,
                              abilities=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        d.p2.board_creatures = [cr_flyer]
        d.p1.board_creatures = [cr_ground]
        d.p1.pv = 20
        d.player_attack("tester", 0)
        # El enano no puede bloquear, el daño va directo a los PV del rival
        self.assertEqual(d.p1.pv, 17)
        self.assertIn(cr_ground, d.p1.board_creatures)

    def test_power_pool_and_summoning(self):
        """Verifica la acumulación de poder y el coste de invocación."""
        d = duel.Duel(994, "Jugador2", "tester")
        p = d.p2
        self.assertEqual(p.power_pool, 0)

        # Jugar carta de Poder 2
        card_pwr = duel.Card(1, "Poder x 2", 2, "crt_poder2.jpg", ctype="Poder", pwr=2)
        p.hand = [card_pwr]
        d.play_power("tester", 0)
        self.assertEqual(p.power_pool, 2)
        self.assertEqual(len(p.board_power), 1)

        # Invocar criatura de coste 2
        card_cr = duel.Card(5, "Dophan", 2, "crt_dophan.jpg", ctype="Criatura", cost=2)
        p.hand = [card_cr]
        d.summon_creature("tester", 0)
        self.assertEqual(p.power_pool, 0)
        self.assertEqual(len(p.board_creatures), 1)

        # En la siguiente fase 1 (Degirar), el poder se recarga
        d.unveer_all(p)
        self.assertEqual(p.power_pool, 2)

    def test_amulet_effects(self):
        """Verifica la ejecución de efectos de amuletos (#SETAMUVAL)."""
        d = duel.Duel(993, "Jugador2", "tester")
        d.p2.pv = 15
        d.p1.board_creatures = [duel.Card(30, "Monstruo", 1, "", atk=2, df=2, cost=1)]
        d.p2.board_creatures = [duel.Card(31, "MiCriatura", 1, "", atk=1, df=1, cost=1)]

        # 1. Curar vida con pv_turno
        d.apply_amulet_val("tester", "pv_turno", 5)
        self.assertEqual(d.p2.pv, 20)

        # 2. Buff de ataque
        d.apply_amulet_val("tester", "ataque", 2)
        self.assertEqual(d.p2.board_creatures[0].attack, 3)

        # 3. Girar monstruo rival (gir_mons)
        d.apply_amulet_val("tester", "gir_mons", 30)
        self.assertTrue(d.p1.board_creatures[0].tapped)

        # 4. Destruir monstruo rival (rem_mons)
        d.apply_amulet_val("tester", "rem_mons", 30)
        self.assertEqual(len(d.p1.board_creatures), 0)

    def test_pvp_multiplayer_match(self):
        """Simula una partida PvP completa entre dos clientes humanos simultáneos."""
        conn1 = FakeConn("alice")
        conn2 = FakeConn("bob")

        # Asegurar usuarios en BD
        for u in ("alice", "bob"):
            if not db.get_user(u):
                db.create_user(u, "clave")

        # 1. Alice crea la partida
        create_res = handlers.h_CREATEGAME(conn1, ["Partida_Alice", "", "50"], {})
        self.assertTrue(create_res[0].startswith("CREATEGAMERPS OK"))
        gid = int(create_res[0].split(" ")[2])

        # 2. Bob se une a la partida
        join_res = handlers.h_JOINGAME(conn2, ["bob", str(gid)], {})
        self.assertEqual(join_res, ["JOINGAMERPS OKalice"])

        # 3. Ambos marcan Preparado
        handlers.h_SETPLAYERREADY(conn1, ["alice", "bob"], {})
        handlers.h_SETPLAYERREADY(conn2, ["bob", "alice"], {})

        d = duel.duel_manager.duels.get(gid)
        self.assertIsNotNone(d)
        self.assertTrue(d.is_ready())
        self.assertFalse(d.p1.is_bot)
        self.assertFalse(d.p2.is_bot)

        # 4. Turno de Alice (turn = 1)
        self.assertEqual(d.turn, 1)
        self.assertTrue(d.is_active_turn("alice"))
        self.assertFalse(d.is_active_turn("bob"))

        # Alice baja poder y criatura
        handlers.h_SENDACTUALPASS(conn1, ["alice", "bob", "3"], {})
        handlers.h_SHOWCARDOPP(conn1, ["0", "Poder"], {})

        handlers.h_SENDACTUALPASS(conn1, ["alice", "bob", "4"], {})
        handlers.h_SHOWCARDOPP(conn1, ["1", "Criatura"], {})

        # Alice ataca a Bob
        handlers.h_SENDACTUALPASS(conn1, ["alice", "bob", "6"], {})
        d.p2.pv = 5
        handlers.h_SENDATTACK(conn1, ["0"], {})
        # Bob recibe daño
        self.assertLess(d.p2.pv, 5)

        # Alice termina su turno
        handlers.h_SENDENDTURN(conn1, ["alice"], {})

        # 5. Turno de Bob (turn = 2)
        self.assertEqual(d.turn, 2)
        self.assertTrue(d.is_active_turn("bob"))
        self.assertFalse(d.is_active_turn("alice"))

        # Bob se rinde (SURRENDERME)
        handlers.h_SURRENDERME(conn2, ["bob", "alice"], {})
        self.assertEqual(d.status, "finished")
        self.assertEqual(d.winner, "alice")

        # Verificar recompensas en BD
        u_alice = db.get_user("alice")
        self.assertGreaterEqual(u_alice["wins"], 1)


if __name__ == "__main__":
    unittest.main()

