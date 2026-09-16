"""Motor de combate y duelos para Rolplay.net 3.9.0.

Implementa la lgica completa del juego de cartas por turnos:
- Participantes (Jugador vs Jugador, o Jugador vs Bot para modo 1 jugador y testing)
- Mazo, robo de cartas, mano y tablero (criaturas, poder, amuletos)
- Fases de turno: Degirar, Robar, Poder, Criaturas, Amuletos, Ataque
- Clculo de combate: ataque vs defensa, dao sobrante a PV, muerte de criaturas
- Resolucin del torneo con actualizacin de Oro, XP, Victorias/Derrotas en base de datos.
"""
import os
import random
import sys
import time

try:
    import db
except ImportError:
    try:
        from server import db
    except ImportError:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import db

DEFAULT_BOT_CARDS = [
    {"id": 1, "name": "Poder", "level": 1, "image": "crt_poder.jpg"},
    {"id": 2, "name": "Elfo Bardo", "level": 1, "image": "crt_elfo_bardo.jpg"},
    {"id": 3, "name": "Duende", "level": 1, "image": "crt_duende.jpg"},
    {"id": 4, "name": "Guerrero Menor", "level": 1, "image": "crt_guerrero_menor.jpg"},
    {"id": 5, "name": "Dophan", "level": 1, "image": "crt_dophan.jpg"},
    {"id": 6, "name": "Gorad Menor", "level": 1, "image": "crt_gorad_menor.jpg"},
    {"id": 7, "name": "Mimit", "level": 1, "image": "crt_mimit.jpg"},
    {"id": 8, "name": "Mel", "level": 1, "image": "crt_mel.jpg"},
]


class Card:
    def __init__(self, cid, name, level, image, ctype=None, atk=None, df=None, cost=None, pwr=None):
        self.id = cid
        self.name = name
        self.level = level or 1
        self.image = image or "crt_elfo_bardo.jpg"
        
        # Determinar tipo
        if ctype:
            self.type = ctype
        elif "poder" in self.name.lower():
            self.type = "Poder"
        elif any(k in self.name.lower() for k in ("amuleto", "escudo", "anillo", "gema")):
            self.type = "Amuleto"
        else:
            self.type = "Criatura"

        if self.type == "Poder":
            self.power = pwr if pwr is not None else self.level
            self.attack = 0
            self.defense = 0
            self.cost = 0
        elif self.type == "Amuleto":
            self.power = 0
            self.attack = 0
            self.defense = self.level
            self.cost = cost if cost is not None else self.level
        else: # Criatura
            self.attack = atk if atk is not None else max(1, self.level)
            self.defense = df if df is not None else max(1, self.level)
            self.cost = cost if cost is not None else max(1, self.level)
            self.power = 0

        self.tapped = False
        self.slot = 0

    def format_hand_payload(self):
        """Genera el payload exacto verificado contra el desensamblado de RPcliente (0x7365e0)."""
        if self.type == "Criatura":
            # 1 <id> <img_filename> <level> Criatura <atk> <def> <cost> + 14 ceros (habilidades)
            return f"1 {self.id} {self.image} {self.level} Criatura {self.attack} {self.defense} {self.cost} 0 0 0 0 0 0 0 0 0 0 0 0 0 0"
        elif self.type == "Poder":
            # 1 <id> <img_filename> <level> Poder <power> + 7 ceros
            return f"1 {self.id} {self.image} {self.level} Poder {self.power} 0 0 0 0 0 0 0"
        else: # Amuleto
            return f"1 {self.id} {self.image} {self.level} Amuleto {self.cost} 0 0 0 0 0 0 0 0 0 0 0 0"


class DuelPlayer:
    def __init__(self, user, is_bot=False, connection=None):
        self.user = user
        self.is_bot = is_bot
        self.connection = connection
        self.pv = 20
        self.ready = False
        self.power_pool = 0
        self.board_power = []
        self.board_creatures = []
        self.board_amulets = []
        self.hand = []
        self.graveyard = []

        # Cargar info del usuario de SQLite
        u = db.get_user(user) if not is_bot else None
        self.level = u["level"] if u else 1
        self.gold = u["gold"] if u else 500

        # Cargar baraja activa
        self.deck = []
        if not is_bot and u:
            active_deck_name = db.get_active_deck(user)
            cards_db = db.get_cards_in_deck(user, active_deck_name)
            if not cards_db:
                cards_db = db.get_inactive_cards(user)
            for c in cards_db:
                self.deck.append(Card(c["id"], c["name"], c["level"], c["image"]))
        
        # Si la baraja tiene pocas cartas o es un Bot, completar hasta 24
        while len(self.deck) < 24:
            for c in DEFAULT_BOT_CARDS:
                if len(self.deck) >= 24:
                    break
                self.deck.append(Card(c["id"], c["name"], c["level"], c["image"]))

        random.shuffle(self.deck)

    def draw_card(self):
        if self.deck:
            c = self.deck.pop(0)
            self.hand.append(c)
            return c
        return None

    def send(self, msg):
        if self.connection:
            self.connection.send(msg)


class Duel:
    def __init__(self, duel_id, creator_name, opponent_name, channel="Principiantes 1(n1-n5)", bet_gold=0):
        self.id = duel_id
        self.channel = channel
        self.bet_gold = bet_gold
        self.status = "waiting"  # waiting, ready, playing, finished
        self.start_time = time.time()
        self.round = 1
        self.turn = 1  # 1 = creator, 2 = opponent
        self.phase = 1 # 1..6
        self.winner = None
        self.started = False

        # Inicializar jugadores
        opp_name = opponent_name if opponent_name else "BotRival"
        is_bot1 = creator_name.lower().startswith("bot") or creator_name.lower() == "jugador2"
        is_bot2 = opp_name.lower().startswith("bot") or opp_name.lower() == "jugador2"
        self.p1 = DuelPlayer(creator_name, is_bot=is_bot1)
        self.p2 = DuelPlayer(opp_name, is_bot=is_bot2)

        if self.p1.is_bot and not self.p2.is_bot:
            self.turn = 2
        else:
            self.turn = 1

        if self.p1.is_bot:
            self.p1.ready = True
        if self.p2.is_bot:
            self.p2.ready = True

    def get_player(self, user):
        if self.p1.user.lower() == user.lower():
            return self.p1
        elif self.p2.user.lower() == user.lower():
            return self.p2
        return None

    def get_opponent(self, user):
        if self.p1.user.lower() == user.lower():
            return self.p2
        elif self.p2.user.lower() == user.lower():
            return self.p1
        return None

    def is_ready(self):
        return self.p1.ready and self.p2.ready

    def set_ready(self, user):
        p = self.get_player(user)
        if p:
            p.ready = True
        opp = self.get_opponent(user)
        if opp and (opp.is_bot or opp.connection is None):
            opp.ready = True
        if self.p1.ready and self.p2.ready:
            self.status = "playing"
            return True
        return False

    def is_active_turn(self, user):
        active_player = self.p1 if self.turn == 1 else self.p2
        return active_player.user.lower() == user.lower()

    def unveer_all(self, player):
        """Fase 1: Degirar cartas."""
        for c in player.board_creatures + player.board_power + player.board_amulets:
            c.tapped = False

    def next_turn(self):
        """Pasa el turno al contrincante."""
        self.turn = 2 if self.turn == 1 else 1
        self.phase = 1
        active_p = self.p1 if self.turn == 1 else self.p2
        opp_p = self.p2 if self.turn == 1 else self.p1

        self.unveer_all(active_p)
        active_p.send("BEGINTURN OK")
        active_p.send(f"SENDACTUALPASS 1")
        opp_p.send(f"SENDACTUALPASS 1")

        if active_p.is_bot:
            self.bot_play_turn()

    def bot_play_turn(self):
        """Inteligencia artificial simple para que el Bot juegue su turno en duelos 1P."""
        bot = self.p1 if self.p1.is_bot else self.p2
        opp = self.p2 if self.p1.is_bot else self.p1
        self.unveer_all(bot)

        # 1. Robar carta
        c = bot.draw_card()
        time.sleep(0.5)

        # 2. Bajar poder si tiene
        powers = [cd for cd in bot.hand if cd.type == "Poder"]
        if powers:
            p = powers[0]
            bot.hand.remove(p)
            bot.board_power.append(p)
            bot.power_pool += p.power
            opp.send(f"SHOWCARDOPPACT {p.id} Poder")

        # 3. Invocar criatura si tiene y le alcanza el poder
        creatures = [cd for cd in bot.hand if cd.type == "Criatura" and cd.cost <= bot.power_pool]
        if creatures:
            cr = creatures[0]
            bot.hand.remove(cr)
            bot.power_pool -= cr.cost
            bot.board_creatures.append(cr)
            opp.send(f"SHOWCARDOPPACT {cr.id} Criatura")

        # 4. Fase de ataque con criaturas degiradas
        for cr in list(bot.board_creatures):
            if not cr.tapped and cr.attack > 0:
                cr.tapped = True
                # Si el jugador no tiene criaturas para defender, ataque directo
                if not opp.board_creatures:
                    opp.pv = max(0, opp.pv - cr.attack)
                    opp.send(f"DEDUCTPV {cr.attack}")
                    if opp.pv <= 0:
                        self.finish_duel(winner_name=bot.user)
                        return
                else:
                    # Defender con la primera criatura
                    def_cr = opp.board_creatures[0]
                    if cr.attack >= def_cr.defense:
                        opp.board_creatures.remove(def_cr)
                        opp.send(f"KILLCARD {def_cr.id}")
                        sobrante = cr.attack - def_cr.defense
                        if sobrante > 0:
                            opp.pv = max(0, opp.pv - sobrante)
                            opp.send(f"DEDUCTPV {sobrante}")
                    if def_cr.attack >= cr.defense:
                        bot.board_creatures.remove(cr)
                        opp.send(f"KILLCARDOPP {cr.id}")

        # 5. Fin de turno del bot -> pasa al jugador
        time.sleep(0.8)
        self.next_turn()

    def player_attack(self, attacker_user, card_slot):
        """Procesa un ataque del jugador."""
        p = self.get_player(attacker_user)
        opp = self.get_opponent(attacker_user)
        if not p or not opp:
            return

        # Buscar criatura atacante
        if p.board_creatures:
            cr = p.board_creatures[0]
        else:
            cr = Card(2, "Elfo Bardo", 1, "crt_elfo_bardo.jpg")

        cr.tapped = True
        p.send(f"SHOWCARDVEERACT {card_slot}")

        # Ataque a criaturas del oponente o directo
        if not opp.board_creatures:
            opp.pv = max(0, opp.pv - cr.attack)
            p.send(f"DEDUCTPVOPP {cr.attack}")
            opp.send(f"DEDUCTPV {cr.attack}")
            if opp.pv <= 0:
                self.finish_duel(winner_name=p.user)
        else:
            def_cr = opp.board_creatures[0]
            if cr.attack >= def_cr.defense:
                opp.board_creatures.remove(def_cr)
                p.send(f"KILLCARDOPP {def_cr.id}")
                opp.send(f"KILLCARD {def_cr.id}")
                sobrante = cr.attack - def_cr.defense
                if sobrante > 0:
                    opp.pv = max(0, opp.pv - sobrante)
                    p.send(f"DEDUCTPVOPP {sobrante}")
                    opp.send(f"DEDUCTPV {sobrante}")
            if def_cr.attack >= cr.defense:
                if cr in p.board_creatures:
                    p.board_creatures.remove(cr)
                p.send(f"KILLCARD {cr.id}")
                opp.send(f"KILLCARDOPP {cr.id}")

            if opp.pv <= 0:
                self.finish_duel(winner_name=p.user)

    def finish_duel(self, winner_name, surrender=False):
        self.status = "finished"
        self.winner = winner_name
        self.end_time = time.time()

        winner = self.get_player(winner_name)
        loser = self.get_opponent(winner_name)

        elapsed_mins = max(1, int((time.time() - self.start_time) / 60))
        gold_reward = self.bet_gold * 2 if self.bet_gold > 0 else 50
        xp_reward = 100

        if winner:
            if not winner.is_bot:
                db.update_user_stats(winner.user, add_gold=gold_reward, add_xp=xp_reward, won=True)
            if winner.connection:
                if surrender:
                    winner.send("DEADPLAYER SURRENDER")
                else:
                    winner.send(f"DEADPLAYER OK {xp_reward}")

        if loser:
            if not loser.is_bot:
                db.update_user_stats(loser.user, add_gold=0, add_xp=20, won=False)


class DuelManager:
    def __init__(self):
        self.duels = {}
        self.user_to_duel = {}
        self.next_id = 100

    def get_user_duel(self, user):
        did = self.user_to_duel.get(user.lower())
        if did:
            return self.duels.get(did)
        return None

    def create_duel(self, creator, opponent=None, channel="Principiantes 1(n1-n5)", bet_gold=0):
        self.next_id += 1
        d = Duel(self.next_id, creator, opponent, channel, bet_gold)
        self.duels[self.next_id] = d
        self.user_to_duel[creator.lower()] = self.next_id
        if opponent:
            self.user_to_duel[opponent.lower()] = self.next_id
        return d

    def join_duel(self, duel_id, joiner_user, connection=None):
        d = self.duels.get(duel_id)
        if not d:
            # Si no existe en memoria, crear uno instantneo
            d = Duel(duel_id, "BotRival", joiner_user)
            self.duels[duel_id] = d

        if d.p2.user.lower() == joiner_user.lower():
            d.p2.connection = connection
        elif d.p1.user.lower() == joiner_user.lower():
            d.p1.connection = connection
        else:
            d.p2 = DuelPlayer(joiner_user, is_bot=False, connection=connection)

        self.user_to_duel[joiner_user.lower()] = duel_id
        return d


if "duel_manager" not in globals():
    duel_manager = DuelManager()
