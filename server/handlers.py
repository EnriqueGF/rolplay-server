"""Handlers del protocolo Rolplay.net (versión completa y persistente).

Integra SQLite para persistencia real de cuentas, oro, nivel, cartas y barajas.
Se recarga en caliente en cada segmento recibido en rpserver.py.
"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
import duel

SESSION_ID = "7369694132202740228"
WELCOME = "Bienvenido a Rolplay.net (Servidor Reconstruido)"

CHANNELS = [
    "Principiantes 1(n1-n5)",
    "Principiantes 2(n1-n5)",
    "Intermedios 1(n6-n15)",
    "Avanzados 1(n16+)",
    "Torneos",
    "Libre",
]


def _lst(items):
    """Lista con coma final requerida por el cliente VB6."""
    return "".join(f"{x}," for x in items)


def _card_item(c):
    # nombre:id:rarity:imagen.jpg:level:str
    cid = c.get("user_card_id", c.get("id", 1))
    return f"{c['name']}:{cid}:{c.get('rarity', 1)}:{c['image']}:{c.get('level', 1)}:1"


# --- Login y sesión ----------------------------------------------------------
def h_LOGINUSERADV(cn, a, S):
    # LOGINUSERADV user pass 3.9.0 <PC> <ip> <puerto> WindowsNT ...
    user = a[0] if a else "prueba"
    passwd = a[1] if len(a) > 1 else "clave"

    # Verificar o auto-crear usuario
    u = db.authenticate_user(user, passwd)
    if not u:
        # Si no existe, crear cuenta automáticamente para facilitar acceso
        db.create_user(user, passwd)
        u = db.get_user(user)

    cn.user = user
    cn.channel = u.get("channel", CHANNELS[0])
    S["users"][cn.user] = cn
    return [f"LOGINUSERRPS OK-{SESSION_ID}"]


h_LOGINUSER = h_LOGINUSERADV
h_LOGIN = h_LOGINUSERADV


def h_ADDUSER(cn, a, S):
    # ADDUSER user pass email
    if len(a) < 2:
        return ["ADDUSERRPS ERROR"]
    ok, res = db.create_user(a[0], a[1], a[2] if len(a) > 2 else "")
    return [f"ADDUSERRPS {res}"]


def h_LOGOUT(cn, a, S):
    if cn.user:
        S["users"].pop(cn.user, None)
    return []


def h_GETMSGJOIN(cn, a, S):
    return [f"GETMSGJOINRPS {WELCOME}"]


def h_GETUSERCHANNEL(cn, a, S):
    u = db.get_user(cn.user or "prueba")
    ch = u["channel"] if u else CHANNELS[0]
    return [f"GETUSERCHANNELRPS {ch}"]


def h_GETUSERPRIV(cn, a, S):
    return ["GETUSERPRIVRPS 1"]


def h_GETCOUNTCONN(cn, a, S):
    return [f"GETCOUNTCONNRPS {len(S['users'])} 0"]


def h_GETUSERINF(cn, a, S):
    u = db.get_user(cn.user or "prueba")
    if not u:
        return ["GETUSERINFRPS 1 0 0 0 0 0 20"]
    # Formato original: nivel xp ? ? ? ? pv
    return [f"GETUSERINFRPS {u['level']} {u['xp']} 0 0 0 0 {u['pv']}"]


def h_GETUSERLEVEL(cn, a, S):
    u = db.get_user(a[0] if a else cn.user)
    return [f"GETUSERLEVELRPS {u['level'] if u else 1}"]


def h_GETUSERXP(cn, a, S):
    u = db.get_user(a[0] if a else cn.user)
    return [f"GETUSERXPRPS {u['xp'] if u else 0}"]


def h_GETUSERAWAY(cn, a, S):
    return ["GETUSERAWAYRPS 0"]


# --- Usuarios conectados y salas --------------------------------------------
def h_LSTCONNCNT(cn, a, S):
    # LSTCONNCNT user sala
    target_ch = a[1].replace("=", " ") if len(a) > 1 else getattr(cn, "channel", CHANNELS[0])
    in_channel = [u for u, c in S["users"].items() if getattr(c, "channel", CHANNELS[0]) == target_ch]
    return [f"LSTCONNCNTRPS {len(in_channel) or 1}"]


def h_LSTCONN(cn, a, S):
    # LSTCONN user sala 0 35
    target_ch = a[1].replace("=", " ") if len(a) > 1 else getattr(cn, "channel", CHANNELS[0])
    in_channel = [u for u, c in S["users"].items() if getattr(c, "channel", CHANNELS[0]) == target_ch]
    if not in_channel and cn.user:
        in_channel = [cn.user]
    items = " ".join(f"{u}(1) ," for u in in_channel)
    return [f"LSTCONNRPS  {items}"]


def h_PINGUSR(cn, a, S):
    return ["PINGRPS OK"]


def h_GETLSTCHANNELS(cn, a, S):
    # GETLSTCHANNELS <sid>
    return [f"GETLSTCHANNELSRPS {_lst(CHANNELS)}"]


def h_SETUSERCHANNEL(cn, a, S):
    # SETUSERCHANNEL <sid> <channel>
    new_ch = " ".join(a[1:]).replace("=", " ") if len(a) > 1 else CHANNELS[0]
    cn.channel = new_ch
    if cn.user:
        db.update_user(cn.user, channel=new_ch)
        # Difundir a la nueva sala
        for u, other in S["users"].items():
            if getattr(other, "channel", None) == new_ch and other != cn:
                other.send(f"MSGADD {cn.user}(1)  se ha unido a {new_ch} @ADD@")
    return [f"SETUSERCHANNELRPS {new_ch}"]


def h_JOINCHANEL(cn, a, S):
    new_ch = " ".join(a[1:]).replace("=", " ") if len(a) > 1 else CHANNELS[0]
    cn.channel = new_ch
    return []


# --- Chat y mensajería -------------------------------------------------------
def h_MSG(cn, a, S):
    # MSG <sid> <text_with_=> <channel>
    if not a:
        return []
    if len(a) >= 3:
        raw_text = a[1].replace("=", " ")
        cur_ch = a[2].replace("=", " ")
    elif len(a) == 2:
        raw_text = a[0].replace("=", " ")
        cur_ch = getattr(cn, "channel", CHANNELS[0])
    else:
        raw_text = " ".join(a).replace("=", " ")
        cur_ch = getattr(cn, "channel", CHANNELS[0])

    msg_out = f"MSG {cn.user} {raw_text}"
    for u, other in list(S["users"].items()):
        if getattr(other, "channel", CHANNELS[0]) == cur_ch:
            other.send(msg_out)
    return []


def h_MSGPRIV(cn, a, S):
    # MSGPRIV <destinatario> <texto>
    if len(a) >= 2:
        target, text = a[0], " ".join(a[1:])
        other = S["users"].get(target)
        if other:
            other.send(f"MSGPRIV {cn.user} {text}")
    return []


def _noop(cn, a, S):
    return []


h_SETUSERPRIV = h_SETUSERNOPRIV = h_SETUSERAWAY = h_SETUSERNOAWAY = _noop


# --- Ventana Cartas y Barajas ------------------------------------------------
def h_GETUSERGOLD(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    u = db.get_user(user)
    gold = u["gold"] if u else 500
    return [f"GETUSERGOLDRPS {gold}"]


def h_GETLSTDECKS(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    which = a[1] if len(a) > 1 else "0"
    decks = db.get_user_decks(user, which)
    return [f"GETLSTDECKSRPS {_lst(decks)} {which}"]


def h_GETDECKACT(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    which = a[1] if len(a) > 1 else "1"
    deck = db.get_active_deck(user)
    return [f"GETDECKACTRPS {deck} {which}"]


def h_SETDECKACT(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    deck = a[1] if len(a) > 1 else "Inicial"
    db.set_active_deck(user, deck)
    return [f"SETDECKACTRPS {deck}"]


def h_CREATEDECK(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    name = a[1] if len(a) > 1 else f"Baraja{random.randint(10, 99)}"
    db.create_deck(user, name)
    return [f"CREATEDECKRPS {name}"]


def h_DELETEDECK(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    name = a[1] if len(a) > 1 else "Segunda"
    db.delete_deck(user, name)
    return [f"DELETEDECKRPS {name}"]


def h_GETACTCARDLISTCNT(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    deck = a[1] if len(a) > 1 else db.get_active_deck(user)
    cards = db.get_cards_in_deck(user, deck)
    return [f"GETACTCARDLISTCNTRPS {len(cards)} 0"]


def h_GETINACTCARDLISTCNT(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    cards = db.get_inactive_cards(user)
    return [f"GETINACTCARDLISTCNTRPS {len(cards)} 0"]


def h_GETACTCARDLIST(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    start = int(a[1]) if len(a) > 1 and a[1].isdigit() else 0
    deck = db.get_active_deck(user)
    cards = db.get_cards_in_deck(user, deck)
    page = cards[start:start + 20]
    items = [_card_item(c) for c in page]
    col = start + len(page)
    return [f"GETACTCARDLISTRPS {_lst(items)} COL:{col}"]


def h_GETINACTCARDLIST(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    start = int(a[1]) if len(a) > 1 and a[1].isdigit() else 0
    cards = db.get_inactive_cards(user)
    page = cards[start:start + 20]
    items = [_card_item(c) for c in page]
    col = start + len(page)
    return [f"GETINACTCARDLISTRPS {_lst(items)} COL:{col}"]


# --- Partidas y Retos --------------------------------------------------------
def h_GETGAMELIST(cn, a, S):
    cur_ch = getattr(cn, "channel", CHANNELS[0])
    games = db.get_active_games(cur_ch)
    if not games:
        return ["GETGAMELISTRPS Sin partidas activas"]
    # Formato: nombre@id/creador/apuesta,
    items = [f"{g['name']}@{g['id']}/{g['creator']}/{g['bet_gold']}" for g in games]
    return [f"GETGAMELISTRPS {_lst(items)}"]


def h_CREATEGAME(cn, a, S):
    name = a[0] if a else f"Partida_{cn.user}"
    cur_ch = getattr(cn, "channel", CHANNELS[0])
    gid = db.create_game(name, cn.user or "anon", cur_ch)
    d = duel.duel_manager.create_duel(cn.user or "anon", opponent="BotRival", channel=cur_ch)
    d.p1.connection = cn
    return [f"CREATEGAMERPS OK {gid}"]


def h_JOINGAME(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    gid = int(a[1]) if len(a) > 1 and a[1].isdigit() else 1
    games = db.get_active_games(getattr(cn, "channel", CHANNELS[0]))
    target_game = next((g for g in games if g["id"] == gid), None)
    creator = target_game["creator"] if target_game else "BotRival"

    d = duel.duel_manager.get_user_duel(user)
    if not d:
        d = duel.duel_manager.create_duel(creator, opponent=user, channel=getattr(cn, "channel", CHANNELS[0]))
    p = d.get_player(user)
    if p:
        p.connection = cn
    return [f"JOINGAMERPS OK{creator}"]


def h_UNJOINGAME(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    d = duel.duel_manager.get_user_duel(user)
    if d:
        d.status = "finished"
    return ["UNJOINGAMERPS OK"]


# --- Handlers de combate y Torneo --------------------------------------------
def h_GETUSERLEVEL(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    u = db.get_user(user)
    lvl = u["level"] if u else 1
    return [f"GETUSERLEVELRPS {lvl}"]


def h_GETDUELNUMCARDS(cn, a, S):
    return ["GETDUELNUMCARDSRPS 8"]


def h_GETDUELBEGINGUS(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    d = duel.duel_manager.get_user_duel(user)
    start_turn = 1 if (d and d.turn == 1) else 2
    return [f"GETDUELBEGINGUSRPS {start_turn}"]


def h_GETGAMEOPP(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    d = duel.duel_manager.get_user_duel(user)
    opp = d.get_opponent(user) if d else None
    opp_name = opp.user if opp else "BotRival"
    return [f"GETGAMEOPPRPS {opp_name}"]


def h_GETGAMEOPPLEVEL(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    d = duel.duel_manager.get_user_duel(user)
    opp = d.get_opponent(user) if d else None
    lvl = opp.level if opp else 1
    return [f"GETGAMEOPPLEVELRPS {lvl}"]


def h_GETGAMEOPPPV(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    d = duel.duel_manager.get_user_duel(user)
    opp = d.get_opponent(user) if d else None
    pv = opp.pv if opp else 20
    return [f"GETGAMEOPPPVRPS {pv}"]


def h_MSGDUEL(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    d = duel.duel_manager.get_user_duel(user)
    if d:
        opp = d.get_opponent(user)
        if opp and opp.connection:
            opp.send(f"MSGGAME {user}: {' '.join(a[1:])}")
    return []


def h_SETPINGGAME(cn, a, S):
    return ["PINGRPS OK"]


def h_SETPLAYERREADY(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    d = duel.duel_manager.get_user_duel(user)
    if not d:
        d = duel.duel_manager.create_duel("BotRival", opponent=user)
    p = d.get_player(user)
    if p:
        p.connection = cn

    both_ready = d.set_ready(user)
    return ["SETGAMEREADY OK"]


def h_SETPLAYERUNREADY(cn, a, S):
    return []


def h_GETCARDCOUNT(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    d = duel.duel_manager.get_user_duel(user)
    p = d.get_player(user) if d else None
    cnt = len(p.deck) if p else 20
    replies = [f"GETCARDCOUNTRPS {cnt}"]
    if d and d.is_ready() and not getattr(d, "started", False):
        d.started = True
        d.status = "playing"
        if d.is_active_turn(user):
            replies.append("BEGINTURN OK")
        else:
            opp = d.get_opponent(user)
            if opp and opp.is_bot:
                import threading
                threading.Thread(target=d.bot_play_turn, daemon=True).start()
    return replies


def h_GETCARDCOUNTOPP(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    d = duel.duel_manager.get_user_duel(user)
    opp = d.get_opponent(user) if d else None
    cnt = len(opp.deck) if opp else 20
    return [f"GETCARDCOUNTOPPRPS {cnt}"]


def h_GETCARDHAND(cn, a, S):
    user = a[0] if a else (cn.user or "prueba")
    d = duel.duel_manager.get_user_duel(user)
    p = d.get_player(user) if d else None
    card = p.draw_card() if p else None
    if not card:
        card = duel.Card(1, "Poder", 1, "crt_poder.jpg")

    payload = card.format_hand_payload()
    return [f"GETCARDHANDRPS {payload}"]


def h_SENDACTUALPASS(cn, a, S):
    user = cn.user or "prueba"
    phase = a[-1] if a else "1"
    d = duel.duel_manager.get_user_duel(user)
    if d:
        try:
            d.phase = int(phase)
        except ValueError:
            pass
        opp = d.get_opponent(user)
        if opp and opp.connection:
            opp.send(f"SENDACTUALPASS {phase}")
    return []


def h_SHOWCARDOPP(cn, a, S):
    user = cn.user or "prueba"
    d = duel.duel_manager.get_user_duel(user)
    if d:
        p = d.get_player(user)
        if p:
            slot = a[0] if a else "0"
            ctype = a[1] if len(a) > 1 else "Criatura"
            card = p.hand.pop(0) if p.hand else duel.Card(2, "Elfo Bardo", 1, "crt_elfo_bardo.jpg")
            if "poder" in ctype.lower():
                card.type = "Poder"
                card.power = max(1, card.power)
                p.board_power.append(card)
                p.power_pool += card.power
            elif "amuleto" in ctype.lower():
                card.type = "Amuleto"
                p.board_amulets.append(card)
            else:
                card.type = "Criatura"
                p.board_creatures.append(card)

        opp = d.get_opponent(user)
        if opp and opp.connection:
            opp.send(f"SHOWCARDOPPACT {' '.join(a)}")
    return []


def h_SHOWCARDVEER(cn, a, S):
    user = cn.user or "prueba"
    d = duel.duel_manager.get_user_duel(user)
    slot = a[0] if a else "0"
    if d:
        opp = d.get_opponent(user)
        if opp and opp.connection:
            opp.send(f"SHOWCARDVEERACT {slot}")
    return [f"SHOWCARDVEERACT {slot}"]


def h_SHOWCARDUNVEERO(cn, a, S):
    user = cn.user or "prueba"
    d = duel.duel_manager.get_user_duel(user)
    if d:
        opp = d.get_opponent(user)
        if opp and opp.connection:
            opp.send("SHOWCARDUNVEEROACT OK")
    return ["SHOWCARDUNVEERACT OK"]


def h_SENDATTACK(cn, a, S):
    user = cn.user or "prueba"
    slot = a[0] if a else "0"
    d = duel.duel_manager.get_user_duel(user)
    if d:
        d.player_attack(user, slot)
    return []


def h_SENDATTACKRPS(cn, a, S):
    return []


def h_SETCATTACK(cn, a, S):
    return ["SETCATTACKRPS OK"]


def h_SETCDEFEND(cn, a, S):
    return ["SETCDEFENDRPS OK"]


def h_KILLCARD(cn, a, S):
    cid = a[0] if a else "0"
    return [f"KILLCARD {cid}"]


def h_INVKDEDUCTPV(cn, a, S):
    user = cn.user or "prueba"
    dmg = int(a[0]) if a and a[0].isdigit() else 1
    d = duel.duel_manager.get_user_duel(user)
    if d:
        opp = d.get_opponent(user)
        if opp:
            opp.pv = max(0, opp.pv - dmg)
            if opp.connection:
                opp.send(f"DEDUCTPV {dmg}")
            if opp.pv <= 0:
                d.finish_duel(user)
    return [f"DEDUCTPVOPP {dmg}"]


def h_INVKADDPV(cn, a, S):
    heal = int(a[0]) if a and a[0].isdigit() else 1
    return [f"ADDPV {heal}"]


def h_INVKGIRMONSOK(cn, a, S):
    slot = a[0] if a else "0"
    return [f"GIRMONS {slot}"]


def h_INVKREMPOD(cn, a, S):
    slot = a[0] if a else "0"
    return [f"REMPOD {slot}"]


def h_INVKREMMONS(cn, a, S):
    slot = a[0] if a else "0"
    return [f"REMMONS {slot}"]


def h_INVKREMAMU(cn, a, S):
    slot = a[0] if a else "0"
    return [f"REMAMU {slot}"]


def h_SETAMUVAL(cn, a, S):
    return ["SETAMUVALRPS OK"]


def h_REMAMUVAL(cn, a, S):
    return []


def h_DEADME(cn, a, S):
    user = cn.user or "prueba"
    d = duel.duel_manager.get_user_duel(user)
    if d:
        opp = d.get_opponent(user)
        d.finish_duel(opp.user if opp else "Rival")
    return []


def h_SURRENDERME(cn, a, S):
    user = cn.user or "prueba"
    d = duel.duel_manager.get_user_duel(user)
    if d:
        opp = d.get_opponent(user)
        d.finish_duel(opp.user if opp else "Rival", surrender=True)
    return []


def h_SENDENDTURN(cn, a, S):
    user = cn.user or "prueba"
    d = duel.duel_manager.get_user_duel(user)
    if d:
        d.next_turn()
    return []


def h_GETDUELRES(cn, a, S):
    user = cn.user or (a[0] if a else "prueba")
    d = duel.duel_manager.get_user_duel(user)
    import time
    elapsed_mins = max(1, int((time.time() - d.start_time) / 60)) if (d and getattr(d, 'start_time', None)) else 1
    gold_reward = (d.bet_gold * 2 if d.bet_gold > 0 else 50) if d else 50
    if d and d.winner == user:
        opp_name = d.get_opponent(user).user if (d and d.get_opponent(user)) else "Rival"
        return [f"GETDUELRESRPS {elapsed_mins} {opp_name} 100 {gold_reward}"]
    else:
        opp_name = d.winner if (d and d.winner) else "BotRival"
        return [f"GETDUELRESRPS {elapsed_mins} {opp_name} 20 0"]


# --- Intercambios, Clanes y Estadísticas -------------------------------------
def h_GETDEALLIST(cn, a, S):
    return ["GETDEALLISTRPS Sin intercambios activos"]


def h_GETLSTCLANES(cn, a, S):
    return ["GETLSTCLANESRPS Sin clanes activos"]


def h_EST(cn, a, S):
    return ["ESTRPS 0"]


def h_GETCARDIMAGEMAIN(cn, a, S):
    return ["GETCARDIMAGEMAINRPS crt_elfo_bardo.jpg"]
