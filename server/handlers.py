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
    # Formato: nombre@creador=descripcion,
    items = [f"{g['name']}@{g['creator']}={g['bet_gold']} oro" for g in games]
    return [f"GETGAMELISTRPS {_lst(items)}"]


def h_CREATEGAME(cn, a, S):
    name = a[0] if a else f"Partida_{cn.user}"
    cur_ch = getattr(cn, "channel", CHANNELS[0])
    gid = db.create_game(name, cn.user or "anon", cur_ch)
    return [f"CREATEGAMERPS OK {gid}"]


def h_JOINGAME(cn, a, S):
    return ["JOINGAMERPS OK"]


def h_UNJOINGAME(cn, a, S):
    return ["UNJOINGAMERPS OK"]


# --- Intercambios, Clanes y Estadísticas -------------------------------------
def h_GETDEALLIST(cn, a, S):
    return ["GETDEALLISTRPS Sin intercambios activos"]


def h_GETLSTCLANES(cn, a, S):
    return ["GETLSTCLANESRPS Sin clanes activos"]


def h_EST(cn, a, S):
    return ["ESTRPS 0"]


def h_GETCARDIMAGEMAIN(cn, a, S):
    return ["GETCARDIMAGEMAINRPS crt_elfo_bardo.jpg"]
