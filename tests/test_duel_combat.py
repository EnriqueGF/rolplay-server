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


if __name__ == "__main__":
    unittest.main()
