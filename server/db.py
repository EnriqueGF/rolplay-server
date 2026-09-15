"""Base de datos y persistencia SQLite para el servidor de Rolplay.net.

Gestiona:
- Usuarios, credenciales, niveles, experiencia, oro, vida, victorias y derrotas.
- Catálogo oficial de cartas (285 cartas cargadas desde cards.csv con sus imágenes).
- Barajas de usuario (activas y de reserva).
- Colección de cartas de cada jugador (en baraja y en reserva/álbum).
- Partidas y salas activas.
"""
import csv
import os
import re
import sqlite3
import threading

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rolplay.db")
CARDS_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "cards.csv"))
IMG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "game", "imagenes"))

_lock = threading.Lock()


def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize(name):
    s = name.lower().strip()
    s = s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    s = re.sub(r"[^\w\s]", "", s)
    return s


def _find_image(card_name, all_imgs, img_lower_map):
    norm = _normalize(card_name)
    cand = f"crt_{norm.replace(' ', '_')}.jpg"
    if cand in img_lower_map:
        return img_lower_map[cand]

    m = re.search(r"(\w+)\s+x\s+(\d+)", card_name.lower())
    if m:
        base, num = m.group(1), m.group(2)
        base_slug = _normalize(base).replace(" ", "_")
        cand1 = f"crt_{base_slug}{num}.jpg"
        if cand1 in img_lower_map:
            return img_lower_map[cand1]
        cand2 = f"crt_{base_slug}_{num}.jpg"
        if cand2 in img_lower_map:
            return img_lower_map[cand2]

    words = [w for w in norm.split() if len(w) > 2 and w not in ["menor", "mayor", "mediano"]]
    if words:
        for f in all_imgs:
            fl = f.lower()
            if all(w in fl for w in words):
                return f

    for f in all_imgs:
        if norm.split()[0] in f.lower():
            return f

    return "crt_elfo_bardo.jpg"


def init_db():
    """Inicializa tablas y precarga el catálogo de cartas si está vacío."""
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT DEFAULT '',
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 500,
                pv INTEGER DEFAULT 20,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                channel TEXT DEFAULT 'Principiantes 1(n1-n5)',
                priv INTEGER DEFAULT 1,
                away INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS cards_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                rarity INTEGER DEFAULT 1,
                quantity INTEGER DEFAULT 12,
                level INTEGER DEFAULT 1,
                image TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS user_decks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                deck_name TEXT NOT NULL,
                is_active INTEGER DEFAULT 0,
                UNIQUE(username, deck_name)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS user_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                card_id INTEGER NOT NULL,
                deck_name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (card_id) REFERENCES cards_catalog(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                creator TEXT NOT NULL,
                opponent TEXT DEFAULT '',
                password TEXT DEFAULT '',
                bet_gold INTEGER DEFAULT 0,
                bet_cards INTEGER DEFAULT 0,
                channel TEXT DEFAULT 'Principiantes 1(n1-n5)',
                status TEXT DEFAULT 'waiting',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Cargar catálogo si está vacío
        c.execute("SELECT COUNT(*) FROM cards_catalog")
        if c.fetchone()[0] == 0 and os.path.exists(CARDS_CSV) and os.path.exists(IMG_DIR):
            all_imgs = [f for f in os.listdir(IMG_DIR) if f.startswith("crt_") and not f.endswith("_g.jpg") and not f.endswith("_h.jpg")]
            img_lower_map = {f.lower(): f for f in all_imgs}
            with open(CARDS_CSV, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    img = _find_image(row["name"], all_imgs, img_lower_map)
                    c.execute("""
                        INSERT OR IGNORE INTO cards_catalog (name, rarity, quantity, level, image)
                        VALUES (?, ?, ?, ?, ?)
                    """, (row["name"].strip(), int(row.get("rarity", 1)), int(row.get("quantity", 12)), int(row.get("level", 1)), img))

        # Crear usuario por defecto 'prueba'
        c.execute("SELECT COUNT(*) FROM users WHERE username = 'prueba'")
        if c.fetchone()[0] == 0:
            _create_user_with_starter(c, "prueba", "clave", "prueba@rolplay.net")

        conn.commit()


def _create_user_with_starter(cursor, username, password, email):
    cursor.execute("""
        INSERT INTO users (username, password, email, level, xp, gold, pv, wins, losses, channel)
        VALUES (?, ?, ?, 1, 0, 500, 20, 0, 0, 'Principiantes 1(n1-n5)')
    """, (username, password, email))

    # Barajas
    cursor.execute("INSERT INTO user_decks (username, deck_name, is_active) VALUES (?, 'Inicial', 1)", (username,))
    cursor.execute("INSERT INTO user_decks (username, deck_name, is_active) VALUES (?, 'Segunda', 0)", (username,))

    # Asignar 20 cartas nivel 1 a la baraja 'Inicial'
    cursor.execute("SELECT id FROM cards_catalog WHERE level = 1 LIMIT 20")
    starter_cards = cursor.fetchall()
    for row in starter_cards:
        cursor.execute("""
            INSERT INTO user_cards (username, card_id, deck_name, is_active)
            VALUES (?, ?, 'Inicial', 1)
        """, (username, row[0]))

    # Asignar 10 cartas a la baraja de reserva 'Segunda'
    cursor.execute("SELECT id FROM cards_catalog LIMIT 10 OFFSET 20")
    reserve_cards = cursor.fetchall()
    for row in reserve_cards:
        cursor.execute("""
            INSERT INTO user_cards (username, card_id, deck_name, is_active)
            VALUES (?, ?, 'Segunda', 0)
        """, (username, row[0]))


# --- Métodos de usuario ------------------------------------------------------
def get_user(username):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        return dict(row) if row else None


def authenticate_user(username, password):
    user = get_user(username)
    if user and user["password"] == password:
        return user
    return None


def create_user(username, password, email=""):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        if c.fetchone():
            return False, "USEREXIST"
        _create_user_with_starter(c, username, password, email)
        conn.commit()
        return True, "OK"


def update_user(username, **kwargs):
    if not kwargs:
        return
    keys = list(kwargs.keys())
    vals = [kwargs[k] for k in keys] + [username]
    set_expr = ", ".join(f"{k} = ?" for k in keys)
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute(f"UPDATE users SET {set_expr} WHERE username = ?", vals)
        conn.commit()


def update_user_stats(username, add_gold=0, add_xp=0, won=None):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT gold, xp, wins, losses, level FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        if not row:
            return
        gold, xp, wins, losses, level = row
        new_gold = max(0, gold + add_gold)
        new_xp = xp + add_xp
        new_wins = wins + (1 if won is True else 0)
        new_losses = losses + (1 if won is False else 0)
        XP_LEVELS = [(15, 9000), (14, 8000), (13, 7000), (12, 6000), (11, 5100),
                     (10, 4400), (9, 3700), (8, 3100), (7, 2500), (6, 1900),
                     (5, 1400), (4, 900), (3, 500), (2, 200)]
        new_level = 1
        for lvl, req in XP_LEVELS:
            if new_xp >= req:
                new_level = lvl
                break
        new_level = max(level, new_level)
        c.execute("""
            UPDATE users SET gold = ?, xp = ?, wins = ?, losses = ?, level = ?
            WHERE username = ?
        """, (new_gold, new_xp, new_wins, new_losses, new_level, username))
        conn.commit()


# --- Métodos de barajas y cartas ---------------------------------------------
def get_user_decks(username, which="0"):
    """Devuelve nombres de barajas. which: '1' para activa, '0' para reserva/todas."""
    with _lock, get_conn() as conn:
        c = conn.cursor()
        if str(which) == "1":
            c.execute("SELECT deck_name FROM user_decks WHERE username = ? AND is_active = 1", (username,))
        else:
            c.execute("SELECT deck_name FROM user_decks WHERE username = ?", (username,))
        rows = c.fetchall()
        return [r[0] for r in rows] or ["Inicial"]


def get_active_deck(username):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT deck_name FROM user_decks WHERE username = ? AND is_active = 1", (username,))
        row = c.fetchone()
        return row[0] if row else "Inicial"


def set_active_deck(username, deck_name):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE user_decks SET is_active = 0 WHERE username = ?", (username,))
        c.execute("UPDATE user_decks SET is_active = 1 WHERE username = ? AND deck_name = ?", (username, deck_name))
        c.execute("UPDATE user_cards SET is_active = CASE WHEN deck_name = ? THEN 1 ELSE 0 END WHERE username = ?", (deck_name, username))
        conn.commit()


def create_deck(username, deck_name):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO user_decks (username, deck_name, is_active) VALUES (?, ?, 0)", (username, deck_name))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def delete_deck(username, deck_name):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM user_decks WHERE username = ? AND deck_name = ?", (username, deck_name))
        c.execute("UPDATE user_cards SET deck_name = 'Inicial' WHERE username = ? AND deck_name = ?", (username, deck_name))
        conn.commit()
        return True


def get_cards_in_deck(username, deck_name):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT c.id, c.name, c.level, c.image, c.rarity, uc.id as user_card_id
            FROM user_cards uc
            JOIN cards_catalog c ON uc.card_id = c.id
            WHERE uc.username = ? AND uc.deck_name = ?
            ORDER BY uc.id
        """, (username, deck_name))
        return [dict(r) for r in c.fetchall()]


def get_inactive_cards(username):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT c.id, c.name, c.level, c.image, c.rarity, uc.id as user_card_id
            FROM user_cards uc
            JOIN cards_catalog c ON uc.card_id = c.id
            WHERE uc.username = ? AND uc.is_active = 0
            ORDER BY uc.id
        """, (username,))
        return [dict(r) for r in c.fetchall()]


# --- Partidas (Games) --------------------------------------------------------
def get_active_games(channel):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM games WHERE channel = ? AND status = 'waiting' ORDER BY id DESC", (channel,))
        return [dict(r) for r in c.fetchall()]


def create_game(name, creator, channel, password="", bet_gold=0, bet_cards=0):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO games (name, creator, channel, password, bet_gold, bet_cards, status)
            VALUES (?, ?, ?, ?, ?, ?, 'waiting')
        """, (name, creator, channel, password, bet_gold, bet_cards))
        conn.commit()
        return c.lastrowid


def remove_game(game_id):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM games WHERE id = ?", (game_id,))
        conn.commit()


# Inicializar DB al importar
init_db()
