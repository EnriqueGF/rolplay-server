"""Handlers del protocolo Rolplay.net.

Cada función `h_<COMANDO>(cn, args, S)` recibe la conexión, los argumentos del
comando (ya separados por espacio) y el estado global `S`, y devuelve una lista
de respuestas (cadenas en claro, sin '#' ni terminador).

Reglas verificadas contra el cliente:
- Toda respuesta necesita al menos un argumento (p. ej. 'PINGRPS OK').
- Las listas terminan siempre en coma.
- Los nombres de baraja no pueden llevar espacios.
"""
import time

SESSION_ID = "7369694132202740228"
CHANNEL = "Principiantes 1(n1-n5)"
WELCOME = "Bienvenido al servidor privado de Rolplay.net (reconstruido)"

# --- datos de ejemplo (sustituir por persistencia real) ---------------------
# nivel xp ? ? ? ? ?   (valores del log original: '1 0 0 0 0 0 2')
USER_INFO = "1 0 0 0 0 0 2"
USER_GOLD = 500
DECKS = {"0": ["Inicial", "Segunda"], "1": ["Inicial"]}   # 0 = reserva, 1 = activa
ACTIVE_DECK = "Inicial"
# ítem de carta: nombre:id:int:imagen.jpg:int:str  (id numérico único; imagen en imagenes\)
CARDS = ["Elfo Bardo:1:1:crt_elfo_bardo.jpg:1:1"]


def _lst(items):
    """Lista con coma final, como espera el cliente."""
    return "".join(f"{x}," for x in items)


def _once(S, key, secs=3):
    """Evita reenviar la misma respuesta en bucle si el cliente la rechaza."""
    g = S.setdefault("once", {})
    now = time.time()
    if now - g.get(key, 0) < secs:
        return False
    g[key] = now
    return True


# --- login y lobby -----------------------------------------------------------
def h_LOGINUSERADV(cn, a, S):
    # LOGINUSERADV user pass 3.9.0 <PC> <ip> <puerto> WindowsNT 6.2 9200
    cn.user = a[0] if a else "anon"
    S["users"][cn.user] = cn
    return [f"LOGINUSERRPS OK-{SESSION_ID}"]


h_LOGINUSER = h_LOGINUSERADV


def h_LOGOUT(cn, a, S):
    S["users"].pop(cn.user, None)
    return []


def h_GETMSGJOIN(cn, a, S):
    return [f"GETMSGJOINRPS {WELCOME}"]


def h_GETUSERCHANNEL(cn, a, S):
    return [f"GETUSERCHANNELRPS {CHANNEL}"]


def h_GETUSERPRIV(cn, a, S):
    return ["GETUSERPRIVRPS 1"]


def h_GETCOUNTCONN(cn, a, S):
    return [f"GETCOUNTCONNRPS {len(S['users'])} 0"]


def h_GETUSERINF(cn, a, S):
    return [f"GETUSERINFRPS {USER_INFO}"]


def h_GETUSERAWAY(cn, a, S):
    return ["GETUSERAWAYRPS 0"]


def h_LSTCONNCNT(cn, a, S):
    return [f"LSTCONNCNTRPS {len(S['users'])}"]


def h_LSTCONN(cn, a, S):
    return ["LSTCONNRPS  " + " ".join(f"{u}(1) ," for u in S["users"])]


def h_PINGUSR(cn, a, S):
    return ["PINGRPS OK"]


def _noop(cn, a, S):
    return []


h_JOINCHANEL = h_SETUSERPRIV = h_SETUSERNOPRIV = h_SETUSERAWAY = h_SETUSERNOAWAY = _noop


def h_MSG(cn, a, S):
    # Chat de sala: reenviar a todos (formato exacto de MSG pendiente de verificar).
    text = " ".join(a[1:]) if len(a) > 1 else ""
    for other in list(S["users"].values()):
        other.send(f"MSG {cn.user} {text}")
    return []


# --- ventana Cartas ----------------------------------------------------------
def h_GETUSERGOLD(cn, a, S):
    return [f"GETUSERGOLDRPS {USER_GOLD}"]


def h_GETLSTDECKS(cn, a, S):
    # GETLSTDECKS user N  ->  GETLSTDECKSRPS baraja1,baraja2, N
    which = a[1] if len(a) > 1 else "0"
    return [f"GETLSTDECKSRPS {_lst(DECKS.get(which, []))} {which}"]


def h_GETDECKACT(cn, a, S):
    # GETDECKACT user N  ->  GETDECKACTRPS <baraja> N
    which = a[1] if len(a) > 1 else "1"
    return [f"GETDECKACTRPS {ACTIVE_DECK} {which}"]


def h_GETACTCARDLISTCNT(cn, a, S):
    return [f"GETACTCARDLISTCNTRPS {len(CARDS)} 0"]


def h_GETINACTCARDLISTCNT(cn, a, S):
    return [f"GETINACTCARDLISTCNTRPS {len(CARDS)} 0"]


def _card_page(a):
    # GET(IN)ACTCARDLIST user <from> <from> 20
    start = int(a[1]) if len(a) > 1 and a[1].isdigit() else 0
    page = CARDS[start:start + 20]
    return f"{_lst(page)} COL:{start + len(page)}"


def h_GETACTCARDLIST(cn, a, S):
    return [f"GETACTCARDLISTRPS {_card_page(a)}"] if _once(S, "act") else []


def h_GETINACTCARDLIST(cn, a, S):
    return [f"GETINACTCARDLISTRPS {_card_page(a)}"] if _once(S, "inact") else []
