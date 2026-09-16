"""Motor de combate y duelos para Rolplay.net 3.9.0.

Implementa la lógica completa del juego de cartas por turnos:
- Participantes (Jugador vs Jugador en red PvP, o Jugador vs Bot para modo 1 jugador y testing)
- Mazo, robo de cartas, mano y tablero (criaturas, poder, amuletos)
- Fases de turno 1..6: Degirar, Robar, Poder, Criaturas, Amuletos, Ataque
- Sistema de reservas de Poder (power pool) para invocaciones
- Habilidades especiales de criaturas: Vuelo, Primer Golpe, Veneno, Regeneración, Arrollar
- Declaración de atacantes y defensores (bloqueo)
- Cálculo de combate completo: ataque vs defensa, daño sobrante (arrollar) a PV, muerte de criaturas
- Efectos de amuletos (pv_turno, ataque, defensa, rem_mons, rem_poder, gir_mons, etc.)
- Sincronización PvP en tiempo real sobre sockets TCP y bot AI para duelos en solitario
- Resolución de torneos con actualización de Oro, XP, Victorias/Derrotas en base de datos SQLite.
"""
import os
import random
import sys
import threading
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
    {"id": 9, "name": "Poder", "level": 1, "image": "crt_poder.jpg"},
    {"id": 10, "name": "Guerrero Mediano", "level": 2, "image": "crt_guerrero_mediano.jpg"},
    {"id": 11, "name": "Ninfa", "level": 2, "image": "crt_ninfa.jpg"},
    {"id": 12, "name": "Lestat", "level": 2, "image": "crt_lestat.jpg"},
]


class Card:
    def __init__(self, cid, name, level, image, ctype=None, atk=None, df=None, cost=None, pwr=None, abilities=None):
        self.id = cid
        self.name = name or "Carta"
        self.level = level or 1
        self.image = image or "crt_elfo_bardo.jpg"
        self.slot = 0
        self.tapped = False

        nl = self.name.lower()

        # Determinar tipo si no viene especificado
        if ctype:
            self.type = ctype
        elif "poder" in nl:
            self.type = "Poder"
        elif any(k in nl for k in ("amuleto", "escudo", "anillo", "gema", "pocion", "elixir")):
            self.type = "Amuleto"
        else:
            self.type = "Criatura"

        if self.type == "Poder":
            self.power = pwr if pwr is not None else max(1, self.level)
            self.attack = 0
            self.defense = 0
            self.cost = 0
        elif self.type == "Amuleto":
            self.power = 0
            self.attack = 0
            self.defense = self.level
            self.cost = cost if cost is not None else max(1, self.level)
        else: # Criatura
            self.power = 0
            # Cálculos de ataque y defensa si no vienen dados
            bonus_atk = 1 if any(k in nl for k in ("mayor", "dragon", "ogro", "titan", "coloso")) else 0
            bonus_def = 1 if any(k in nl for k in ("golem", "guarda", "escudero", "roca", "titan")) else 0
            self.attack = atk if atk is not None else max(1, self.level + bonus_atk)
            self.defense = df if df is not None else max(1, self.level + bonus_def)
            self.cost = cost if cost is not None else max(1, self.level)

        # Habilidades especiales (14 flags para el cliente VB6 según 0x738790..0x738b50):
        # 1: Vuelo, 2: Primer Golpe, 3: Veneno, 4: Regeneración, 5: Arrollar, etc.
        if abilities and len(abilities) == 14:
            self.abilities = list(abilities)
        else:
            vuelo = 1 if any(k in nl for k in ("dragon", "aguila", "angel", "demonio", "pegaso", "grifo", "ave", "ninfa")) else 0
            primer_golpe = 1 if any(k in nl for k in ("arquero", "lancero", "rapido", "bardo", "elfo")) else 0
            veneno = 1 if any(k in nl for k in ("veneno", "serpiente", "vibora", "escorpion", "arana")) else 0
            regeneracion = 1 if any(k in nl for k in ("golem", "momia", "zombie", "esqueleto", "troll")) else 0
            arrollar = 1 if any(k in nl for k in ("titan", "gran", "gigante", "coloso", "dragon", "demonio")) else 0
            self.abilities = [vuelo, primer_golpe, veneno, regeneracion, arrollar, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    @property
    def has_flying(self):
        return bool(self.abilities[0])

    @property
    def has_first_strike(self):
        return bool(self.abilities[1])

    @property
    def has_poison(self):
        return bool(self.abilities[2])

    @property
    def has_regeneration(self):
        return bool(self.abilities[3])

    @property
    def has_trample(self):
        return bool(self.abilities[4])

    def format_hand_payload(self):
        """Genera el payload verificado contra el desensamblado de RPcliente (0x7365e0)."""
        if self.type == "Criatura":
            ab_str = " ".join(str(a) for a in self.abilities)
            return f"1 {self.id} {self.image} {self.level} Criatura {self.attack} {self.defense} {self.cost} {ab_str}"
        elif self.type == "Poder":
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
        if u and u.get("pv"):
            self.pv = u["pv"]

        # Cargar baraja activa
        self.deck = []
        if not is_bot and u:
            active_deck_name = db.get_active_deck(user)
            cards_db = db.get_cards_in_deck(user, active_deck_name)
            if not cards_db:
                cards_db = db.get_inactive_cards(user)
            for c in cards_db:
                self.deck.append(Card(c["id"], c["name"], c["level"], c["image"]))

        # Completar mazo hasta 24 cartas para garantizar duelos completos
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

    def total_board_power(self):
        return sum(c.power for c in self.board_power if not c.tapped)

    def unveer_all(self):
        for c in self.board_creatures + self.board_power + self.board_amulets:
            c.tapped = False
        # El poder disponible se restaura al total de cartas de poder en mesa
        self.power_pool = sum(c.power for c in self.board_power)

    def get_creature(self, slot_or_id):
        try:
            slot = int(slot_or_id)
            for cr in self.board_creatures:
                if cr.slot == slot:
                    return cr
            if 0 <= slot < len(self.board_creatures):
                return self.board_creatures[slot]
        except ValueError:
            pass
        for cr in self.board_creatures:
            if str(cr.id) == str(slot_or_id):
                return cr
        return None

    def send(self, msg):
        if self.connection:
            try:
                self.connection.send(msg)
            except Exception:
                pass


class Duel:
    def __init__(self, duel_id, creator_name, opponent_name=None, channel="Principiantes 1(n1-n5)", bet_gold=0, bet_cards=0):
        self.id = duel_id
        self.channel = channel
        self.bet_gold = bet_gold
        self.bet_cards = bet_cards
        self.status = "waiting"  # waiting, ready, playing, finished
        self.start_time = time.time()
        self.end_time = None
        self.round = 1
        self.turn = 1  # 1 = p1 (creador), 2 = p2 (oponente)
        self.phase = 1 # 1..6
        self.winner = None
        self.started = False
        self.attacking_creature = None
        self.defending_creature = None

        opp_name = opponent_name if opponent_name else "BotRival"
        is_bot1 = creator_name.lower().startswith("bot") or creator_name.lower() in ("jugador2", "botrival")
        is_bot2 = opp_name.lower().startswith("bot") or opp_name.lower() in ("jugador2", "botrival")

        self.p1 = DuelPlayer(creator_name, is_bot=is_bot1)
        self.p2 = DuelPlayer(opp_name, is_bot=is_bot2)

        # Regla de turno inicial: Si uno es Bot/offline y el otro es humano, el humano SIEMPRE empieza el turno
        if self.p1.is_bot and not self.p2.is_bot:
            self.turn = 2
        elif self.p2.is_bot and not self.p1.is_bot:
            self.turn = 1
        else:
            self.turn = 1

        if self.p1.is_bot:
            self.p1.ready = True
        if self.p2.is_bot:
            self.p2.ready = True

    def get_player(self, user):
        if not user:
            return None
        if self.p1.user.lower() == user.lower():
            return self.p1
        elif self.p2.user.lower() == user.lower():
            return self.p2
        return None

    def get_opponent(self, user):
        if not user:
            return None
        if self.p1.user.lower() == user.lower():
            return self.p2
        elif self.p2.user.lower() == user.lower():
            return self.p1
        return None

    def is_active_turn(self, user):
        active_player = self.p1 if self.turn == 1 else self.p2
        return active_player.user.lower() == user.lower()

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

    def unveer_all(self, player):
        """Fase 1: Degirar cartas y recargar poder."""
        player.unveer_all()

    def next_turn(self):
        """Avanza de turno, alternando entre p1 y p2."""
        if self.status == "finished":
            return

        self.turn = 2 if self.turn == 1 else 1
        if self.turn == 1:
            self.round += 1
        self.phase = 1
        self.attacking_creature = None
        self.defending_creature = None

        active_p = self.p1 if self.turn == 1 else self.p2
        opp_p = self.p2 if self.turn == 1 else self.p1

        self.unveer_all(active_p)
        active_p.send("BEGINTURN OK")
        active_p.send("SENDACTUALPASS 1")
        active_p.send("SHOWCARDUNVEERACT OK")

        opp_p.send("SENDACTUALPASS 1")
        opp_p.send("SHOWCARDUNVEEROACT OK")

        if active_p.is_bot:
            threading.Thread(target=self.bot_play_turn, daemon=True).start()

    def play_power(self, user, slot_or_id):
        """Juega una carta de poder desde la mano a la mesa."""
        p = self.get_player(user)
        opp = self.get_opponent(user)
        if not p:
            return None

        # Buscar en mano
        card = None
        for c in p.hand:
            if c.type == "Poder":
                card = c
                break
        if not card:
            card = Card(1, "Poder", 1, "crt_poder.jpg", ctype="Poder", pwr=1)
        else:
            p.hand.remove(card)

        card.slot = len(p.board_power)
        p.board_power.append(card)
        p.power_pool += card.power

        if opp and opp.connection:
            opp.send(f"SHOWCARDOPPACT {card.slot} Poder {card.id} {card.power}")
        return card

    def summon_creature(self, user, slot_or_id):
        """Invoca una criatura desde la mano si hay poder suficiente."""
        p = self.get_player(user)
        opp = self.get_opponent(user)
        if not p:
            return None

        # Buscar criatura asequible en la mano
        card = None
        for c in p.hand:
            if c.type == "Criatura" and c.cost <= p.power_pool:
                card = c
                break
        if not card:
            # Si la mano no tiene o es un test, usar criatura básica
            card = p.hand.pop(0) if p.hand else Card(2, "Elfo Bardo", 1, "crt_elfo_bardo.jpg")
        else:
            p.hand.remove(card)

        p.power_pool = max(0, p.power_pool - card.cost)
        card.slot = len(p.board_creatures)
        p.board_creatures.append(card)

        if opp and opp.connection:
            opp.send(f"SHOWCARDOPPACT {card.slot} Criatura {card.id} {card.attack} {card.defense} {card.cost}")
        return card

    def declare_attacker(self, user, slot):
        """Declara una criatura atacante."""
        p = self.get_player(user)
        opp = self.get_opponent(user)
        if not p:
            return False
        cr = p.get_creature(slot)
        if not cr and p.board_creatures:
            cr = p.board_creatures[0]
        if not cr or cr.tapped or cr.attack <= 0:
            return False

        cr.tapped = True
        self.attacking_creature = cr
        p.send(f"SHOWCARDVEERACT {slot}")
        if opp and opp.connection:
            opp.send(f"SHOWCARDVEERACT {slot}")
        return True

    def declare_defender(self, user, def_slot, att_slot=None):
        """Declara una criatura defensora para bloquear."""
        p = self.get_player(user)
        if not p:
            return False
        cr = p.get_creature(def_slot)
        if not cr or cr.tapped:
            return False

        # Si el atacante tiene vuelo, el defensor debe tener vuelo
        if self.attacking_creature and self.attacking_creature.has_flying and not cr.has_flying:
            return False

        self.defending_creature = cr
        return True

    def player_attack(self, attacker_user, card_slot):
        """Resuelve el combate del atacante contra la mesa enemiga o PV directo."""
        p = self.get_player(attacker_user)
        opp = self.get_opponent(attacker_user)
        if not p or not opp:
            return

        cr = self.attacking_creature or p.get_creature(card_slot)
        if not cr:
            if p.board_creatures:
                cr = p.board_creatures[0]
            else:
                cr = Card(2, "Elfo Bardo", 1, "crt_elfo_bardo.jpg", ctype="Criatura", atk=1, df=1)

        cr.tapped = True
        p.send(f"SHOWCARDVEERACT {card_slot}")
        if opp.connection:
            opp.send(f"SHOWCARDVEERACT {card_slot}")

        def_cr = self.defending_creature
        if not def_cr and opp.board_creatures:
            # Si el oponente no declaró defensor explícito pero tiene criaturas degiradas:
            # Bloquea la primera criatura válida
            for cand in opp.board_creatures:
                if not cand.tapped:
                    if not cr.has_flying or cand.has_flying:
                        def_cr = cand
                        break

        if not def_cr:
            # Ataque directo al jugador contrario
            opp.pv = max(0, opp.pv - cr.attack)
            p.send(f"DEDUCTPVOPP {cr.attack}")
            if opp.connection:
                opp.send(f"DEDUCTPV {cr.attack}")
            if opp.pv <= 0:
                self.finish_duel(winner_name=p.user)
        else:
            # Combate criatura vs criatura
            # 1. Primer Golpe
            if cr.has_first_strike and not def_cr.has_first_strike:
                # El atacante golpea primero
                if cr.has_poison or cr.attack >= def_cr.defense:
                    self._destroy_creature(opp, def_cr, p)
                    sobrante = max(0, cr.attack - def_cr.defense)
                    if sobrante > 0:
                        opp.pv = max(0, opp.pv - sobrante)
                        p.send(f"DEDUCTPVOPP {sobrante}")
                        if opp.connection:
                            opp.send(f"DEDUCTPV {sobrante}")
                    if opp.pv <= 0:
                        self.finish_duel(winner_name=p.user)
                    self.attacking_creature = None
                    self.defending_creature = None
                    return

            # 2. Daño simultáneo
            dead_defender = False
            dead_attacker = False

            if cr.has_poison or cr.attack >= def_cr.defense:
                dead_defender = True
            if def_cr.has_poison or def_cr.attack >= cr.defense:
                dead_attacker = True

            if dead_defender:
                self._destroy_creature(opp, def_cr, p)
                sobrante = max(0, cr.attack - def_cr.defense)
                if sobrante > 0:
                    opp.pv = max(0, opp.pv - sobrante)
                    p.send(f"DEDUCTPVOPP {sobrante}")
                    if opp.connection:
                        opp.send(f"DEDUCTPV {sobrante}")

            if dead_attacker:
                self._destroy_creature(p, cr, opp)

            if opp.pv <= 0:
                self.finish_duel(winner_name=p.user)

        self.attacking_creature = None
        self.defending_creature = None

    def _destroy_creature(self, owner, creature, opponent):
        """Maneja la muerte o regeneración de una criatura."""
        if creature.has_regeneration and getattr(creature, "_regenerated_turn", 0) != self.round:
            creature._regenerated_turn = self.round
            creature.tapped = True
            creature.defense = 1
            return False

        if creature in owner.board_creatures:
            owner.board_creatures.remove(creature)
        owner.graveyard.append(creature)

        owner.send(f"KILLCARD {creature.id}")
        if opponent.connection:
            opponent.send(f"KILLCARDOPP {creature.id}")
        return True

    def apply_amulet_val(self, user, effect_name, val):
        """Aplica un efecto de amuleto (#SETAMUVAL)."""
        p = self.get_player(user)
        opp = self.get_opponent(user)
        if not p:
            return

        ef = effect_name.lower().strip()
        try:
            num = int(val)
        except ValueError:
            num = 1

        if ef == "pv_turno":
            p.pv += num
            p.send(f"ADDPV {num}")
            if opp and opp.connection:
                opp.send(f"ADDPVOPP {num}")
        elif ef == "ataque":
            for cr in p.board_creatures:
                cr.attack += num
        elif ef == "defensa":
            for cr in p.board_creatures:
                cr.defense += num
        elif ef == "rem_mons" and opp:
            cr = opp.get_creature(num)
            if cr:
                self._destroy_creature(opp, cr, p)
        elif ef == "gir_mons" and opp:
            cr = opp.get_creature(num)
            if cr:
                cr.tapped = True
                if opp.connection:
                    opp.send(f"GIRMONS {num}")

    def bot_play_turn(self):
        """Inteligencia artificial que juega el turno del Bot de forma realista."""
        bot = self.p1 if self.p1.is_bot else self.p2
        opp = self.p2 if self.p1.is_bot else self.p1
        self.unveer_all(bot)

        # 1. Robar carta
        bot.draw_card()
        time.sleep(0.3)

        # 2. Bajar poder si tiene en mano
        powers = [cd for cd in bot.hand if cd.type == "Poder"]
        if powers:
            p = powers[0]
            bot.hand.remove(p)
            bot.board_power.append(p)
            bot.power_pool += p.power
            if opp.connection:
                opp.send(f"SHOWCARDOPPACT {len(bot.board_power)-1} Poder {p.id} {p.power}")

        # 3. Invocar criaturas que pueda pagar
        creatures = [cd for cd in bot.hand if cd.type == "Criatura" and cd.cost <= bot.power_pool]
        if creatures:
            cr = creatures[0]
            bot.hand.remove(cr)
            bot.power_pool -= cr.cost
            cr.slot = len(bot.board_creatures)
            bot.board_creatures.append(cr)
            if opp.connection:
                opp.send(f"SHOWCARDOPPACT {cr.slot} Criatura {cr.id} {cr.attack} {cr.defense} {cr.cost}")

        # 4. Fase de ataque con criaturas degiradas
        for cr in list(bot.board_creatures):
            if not cr.tapped and cr.attack > 0:
                cr.tapped = True
                if opp.connection:
                    opp.send(f"SHOWCARDVEERACT {cr.slot}")

                # Si el oponente no tiene criaturas o no puede bloquear
                valid_blockers = [d for d in opp.board_creatures if not d.tapped and (not cr.has_flying or d.has_flying)]
                if not valid_blockers:
                    opp.pv = max(0, opp.pv - cr.attack)
                    if opp.connection:
                        opp.send(f"DEDUCTPV {cr.attack}")
                    if opp.pv <= 0:
                        self.finish_duel(winner_name=bot.user)
                        return
                else:
                    def_cr = valid_blockers[0]
                    if cr.attack >= def_cr.defense:
                        self._destroy_creature(opp, def_cr, bot)
                        sobrante = cr.attack - def_cr.defense
                        if sobrante > 0:
                            opp.pv = max(0, opp.pv - sobrante)
                            if opp.connection:
                                opp.send(f"DEDUCTPV {sobrante}")
                    if def_cr.attack >= cr.defense:
                        self._destroy_creature(bot, cr, opp)

                    if opp.pv <= 0:
                        self.finish_duel(winner_name=bot.user)
                        return

        # 5. Fin de turno del bot -> pasa al jugador
        time.sleep(0.4)
        self.next_turn()

    def finish_duel(self, winner_name, surrender=False):
        """Finaliza el combate y registra las recompensas en base de datos."""
        if self.status == "finished":
            return
        self.status = "finished"
        self.winner = winner_name
        self.end_time = time.time()

        winner = self.get_player(winner_name)
        loser = self.get_opponent(winner_name)

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
            if loser.connection:
                if surrender:
                    loser.send("DEADPLAYER SURRENDER")
                else:
                    loser.send("DEADPLAYER")

        # Limpiar partida activa de SQLite si no es partida por defecto
        try:
            if self.id > 10:
                db.remove_game(self.id)
        except Exception:
            pass


class DuelManager:
    def __init__(self):
        self.duels = {}
        self.user_to_duel = {}
        self.next_id = 100

    def get_user_duel(self, user):
        if not user:
            return None
        did = self.user_to_duel.get(user.lower())
        if did:
            d = self.duels.get(did)
            if d and d.status != "finished":
                return d
            elif d:
                # Mantener accesible para resultados
                return d
        return None

    def create_duel(self, creator, opponent=None, channel="Principiantes 1(n1-n5)", bet_gold=0, bet_cards=0, duel_id=None):
        if duel_id is not None:
            did = int(duel_id)
        else:
            self.next_id += 1
            did = self.next_id

        d = Duel(did, creator, opponent, channel, bet_gold, bet_cards)
        self.duels[did] = d
        self.user_to_duel[creator.lower()] = did
        if opponent:
            self.user_to_duel[opponent.lower()] = did
        return d

    def join_duel(self, duel_id, joiner_user, creator_name="BotRival", bet_gold=0, channel="Principiantes 1(n1-n5)", connection=None):
        d = self.duels.get(int(duel_id))
        if not d:
            # Buscar si el creador tiene una partida esperando
            for active_d in self.duels.values():
                if active_d.status in ("waiting", "ready") and active_d.p1.user.lower() != joiner_user.lower():
                    d = active_d
                    break

        if not d:
            d = Duel(int(duel_id), creator_name, joiner_user, channel=channel, bet_gold=bet_gold)
            self.duels[int(duel_id)] = d

        if d.p2.user.lower() == joiner_user.lower():
            d.p2.connection = connection
            d.p2.is_bot = False
        elif d.p1.user.lower() == joiner_user.lower():
            d.p1.connection = connection
            d.p1.is_bot = False
        else:
            d.p2 = DuelPlayer(joiner_user, is_bot=False, connection=connection)

        # Si alguno de los jugadores no tiene socket activo, actúa como bot para que la partida arranque
        if d.p1.connection is None and d.p2.connection is not None:
            d.p1.is_bot = True
            d.p1.ready = True
            d.turn = 2 # El jugador 2 (humano) inicia
        elif d.p2.connection is None and d.p1.connection is not None:
            d.p2.is_bot = True
            d.p2.ready = True
            d.turn = 1 # El jugador 1 (humano) inicia
        elif d.p1.connection is None and d.p2.connection is None:
            d.p1.is_bot = True
            d.p1.ready = True
            d.turn = 1

        self.user_to_duel[joiner_user.lower()] = d.id
        return d


if "duel_manager" not in globals():
    duel_manager = DuelManager()
