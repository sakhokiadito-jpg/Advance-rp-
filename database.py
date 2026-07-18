import sqlite3
import random
import string
import time
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")

ORG_DISPLAY = {
    "ф1":     ("🏎️", "Формула-1"),
    "футбол": ("⚽", "Футбол"),
    "семья":  ("👨‍👩‍👧‍👦", "Семья"),
}

import config as _cfg


def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            uid INTEGER PRIMARY KEY,
            username TEXT,
            spm_id TEXT,
            game_name TEXT,
            balance REAL DEFAULT 150000,
            bank REAL DEFAULT 0,
            btc REAL DEFAULT 0,
            job TEXT DEFAULT '',
            last_salary INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0,
            license INTEGER DEFAULT 0,
            garage_slots INTEGER DEFAULT 8,
            x2 INTEGER DEFAULT 0,
            credit REAL DEFAULT 0,
            bank_last_updated INTEGER DEFAULT 0,
            biz_income_time INTEGER DEFAULT 0,
            appearance TEXT DEFAULT '',
            source TEXT DEFAULT '',
            biz_slots INTEGER DEFAULT 3,
            apt_slots INTEGER DEFAULT 6
        );

        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER,
            car_id INTEGER,
            name TEXT,
            token TEXT UNIQUE,
            plate TEXT DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER,
            biz_id INTEGER,
            name TEXT,
            income REAL,
            token TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS apartments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER,
            apt_id INTEGER,
            name TEXT,
            token TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS casino_plays (
            uid INTEGER,
            date TEXT,
            plays INTEGER DEFAULT 0,
            PRIMARY KEY (uid, date)
        );

        CREATE TABLE IF NOT EXISTS org_members (
            uid INTEGER,
            org_key TEXT,
            is_owner INTEGER DEFAULT 0,
            PRIMARY KEY (uid, org_key)
        );

        CREATE TABLE IF NOT EXISTS org_names (
            org_key TEXT PRIMARY KEY,
            name TEXT
        );

        CREATE TABLE IF NOT EXISTS crypto_portfolio (
            uid INTEGER,
            symbol TEXT,
            amount REAL DEFAULT 0,
            avg_buy_price REAL DEFAULT 0,
            PRIMARY KEY (uid, symbol)
        );

        CREATE TABLE IF NOT EXISTS catalog_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            game_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            income REAL DEFAULT 0,
            description TEXT DEFAULT '',
            specs TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            added_by INTEGER DEFAULT 0,
            added_at INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            amount REAL NOT NULL,
            max_uses INTEGER DEFAULT 1,
            used_count INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            added_by INTEGER DEFAULT 0,
            added_at INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS promo_uses (
            uid INTEGER,
            code TEXT,
            used_at INTEGER DEFAULT 0,
            PRIMARY KEY (uid, code)
        );

        CREATE TABLE IF NOT EXISTS admins (
            uid INTEGER PRIMARY KEY,
            granted_by INTEGER DEFAULT 0,
            granted_at INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS transaction_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            uid INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            amount REAL DEFAULT 0,
            admin_uid INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS fines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER NOT NULL,
            amount REAL NOT NULL,
            reason TEXT DEFAULT '',
            article TEXT DEFAULT '',
            issued_by INTEGER DEFAULT 0,
            issued_at INTEGER DEFAULT 0,
            paid INTEGER DEFAULT 0,
            paid_at INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS government_treasury (
            id INTEGER PRIMARY KEY DEFAULT 1,
            balance REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS treasury_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            action TEXT NOT NULL,
            amount REAL DEFAULT 0,
            uid INTEGER DEFAULT 0,
            details TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS crypto_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            uid INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL,
            amount REAL DEFAULT 0,
            price REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS tax_debt (
            uid INTEGER PRIMARY KEY,
            amount REAL DEFAULT 0,
            last_charged INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS player_orgs (
            org_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL UNIQUE,
            icon     TEXT    DEFAULT '🏛️',
            owner_uid INTEGER NOT NULL,
            created_at INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS player_org_members (
            org_id    INTEGER NOT NULL,
            uid       INTEGER NOT NULL,
            joined_at INTEGER DEFAULT 0,
            PRIMARY KEY (org_id, uid)
        );

        CREATE TABLE IF NOT EXISTS government_employees (
            uid INTEGER PRIMARY KEY,
            role TEXT DEFAULT 'Сотрудник правительства',
            assigned_by INTEGER DEFAULT 0,
            assigned_at INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS mvd_employees (
            uid INTEGER PRIMARY KEY,
            role TEXT DEFAULT 'Сотрудник МВД',
            assigned_by INTEGER DEFAULT 0,
            assigned_at INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS plates (
            plate TEXT PRIMARY KEY,
            car_id INTEGER,
            uid INTEGER,
            assigned_at INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS daily_bonus_rewards (
            day INTEGER PRIMARY KEY,
            reward_type TEXT DEFAULT 'money',
            reward_value TEXT DEFAULT '0',
            description TEXT DEFAULT '',
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS daily_bonus_claims (
            uid INTEGER PRIMARY KEY,
            current_day INTEGER DEFAULT 1,
            last_claimed INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            total_claims INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS toto_matches (
            match_id    TEXT PRIMARY KEY,
            league      TEXT,
            league_flag TEXT,
            home_team   TEXT,
            away_team   TEXT,
            match_time  INTEGER,
            status      TEXT DEFAULT 'pending',
            home_score  INTEGER DEFAULT -1,
            away_score  INTEGER DEFAULT -1,
            odds_home   REAL,
            odds_draw   REAL,
            odds_away   REAL,
            created_at  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS toto_bets (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            match_id      TEXT    NOT NULL,
            bet_type      TEXT    NOT NULL,
            amount        REAL    NOT NULL,
            potential_win REAL    NOT NULL,
            status        TEXT    DEFAULT 'pending',
            created_at    INTEGER DEFAULT 0
        );
        """)
        # Migrate existing DB: add missing columns
        _migrate(c)


def _migrate(c):
    """Add new columns to existing tables safely."""
    migrations = [
        ("users", "appearance", "TEXT DEFAULT ''"),
        ("users", "source", "TEXT DEFAULT ''"),
        ("users", "biz_slots", "INTEGER DEFAULT 3"),
        ("users", "apt_slots", "INTEGER DEFAULT 6"),
        ("fines", "article", "TEXT DEFAULT ''"),
    ]
    for table, col, definition in migrations:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
        except Exception:
            pass


def _gen_token(length=6):
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


# ===== РУССКИЕ НОМЕРА =====

RU_PLATE_LETTERS = list("АВЕКМНОРСТУХ")  # Кириллические буквы, используемые на номерах
RU_PLATE_REGIONS = [61, 161, 761]


def gen_ru_plate() -> str:
    """Генерирует российский номер формата А000АА 61"""
    def _make():
        l1 = random.choice(RU_PLATE_LETTERS)
        digits = "".join(random.choices(string.digits, k=3))
        l2 = random.choice(RU_PLATE_LETTERS)
        l3 = random.choice(RU_PLATE_LETTERS)
        region = random.choice(RU_PLATE_REGIONS)
        return f"{l1}{digits}{l2}{l3} {region}"

    plate = _make()
    with _conn() as c:
        for _ in range(50):
            exists = c.execute("SELECT 1 FROM cars WHERE plate=?", (plate,)).fetchone()
            if not exists:
                return plate
            plate = _make()
    return _make()


def _unique_token(table: str, col: str = "token") -> str:
    with _conn() as c:
        for _ in range(100):
            t = _gen_token()
            row = c.execute(f"SELECT 1 FROM {table} WHERE {col}=?", (t,)).fetchone()
            if not row:
                return t
    return _gen_token(10)


# ========== USERS ==========

def register_user(uid, username, spm_id, game_name, appearance='', source=''):
    with _conn() as c:
        c.execute("""
            INSERT OR REPLACE INTO users
              (uid, username, spm_id, game_name, balance, bank, btc, job,
               last_salary, banned, license, garage_slots, x2, credit,
               bank_last_updated, biz_income_time, appearance, source, biz_slots, apt_slots)
            VALUES (?,?,?,?,?,0,0,'',0,0,0,8,0,0,?,0,?,?,3,6)
        """, (uid, username, spm_id, game_name, _cfg.START_BALANCE, int(time.time()), appearance, source))


def get_user(uid):
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()
        return tuple(row) if row else None


def get_user_by_username(username):
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM users WHERE LOWER(username)=LOWER(?)", (username,)
        ).fetchone()
        return tuple(row) if row else None


def get_all_users():
    with _conn() as c:
        rows = c.execute("SELECT uid FROM users").fetchall()
        return [r[0] for r in rows]


def get_all_users_info():
    with _conn() as c:
        rows = c.execute("SELECT uid, username, game_name FROM users").fetchall()
        return [tuple(r) for r in rows]


def get_top(n=10):
    with _conn() as c:
        rows = c.execute(
            "SELECT username, game_name, balance FROM users WHERE banned=0 ORDER BY balance DESC LIMIT ?",
            (n,)
        ).fetchall()
        return [tuple(r) for r in rows]


def update_balance(uid, delta):
    with _conn() as c:
        c.execute("UPDATE users SET balance=balance+? WHERE uid=?", (delta, uid))


def set_balance(uid, amount):
    with _conn() as c:
        c.execute("UPDATE users SET balance=? WHERE uid=?", (amount, uid))


def update_btc(uid, delta):
    with _conn() as c:
        c.execute("UPDATE users SET btc=btc+? WHERE uid=?", (delta, uid))


def update_salary_time(uid):
    with _conn() as c:
        c.execute("UPDATE users SET last_salary=? WHERE uid=?", (int(time.time()), uid))


def set_job(uid, job):
    with _conn() as c:
        c.execute("UPDATE users SET job=? WHERE uid=?", (job, uid))


def ban_user(uid):
    with _conn() as c:
        c.execute("UPDATE users SET banned=1 WHERE uid=?", (uid,))


def unban_user(uid):
    with _conn() as c:
        c.execute("UPDATE users SET banned=0 WHERE uid=?", (uid,))


def has_x2(uid):
    with _conn() as c:
        row = c.execute("SELECT x2 FROM users WHERE uid=?", (uid,)).fetchone()
        return bool(row[0]) if row else False


def set_x2(uid, value: bool):
    with _conn() as c:
        c.execute("UPDATE users SET x2=? WHERE uid=?", (int(value), uid))


def delete_user(uid):
    with _conn() as c:
        for tbl in ["users", "cars", "businesses", "apartments", "casino_plays",
                    "org_members", "crypto_portfolio", "fines", "tax_debt",
                    "government_employees", "mvd_employees"]:
            c.execute(f"DELETE FROM {tbl} WHERE uid=?", (uid,))


def reset_user(uid):
    with _conn() as c:
        c.execute("""UPDATE users SET
            balance=150000, bank=0, btc=0, job='', last_salary=0,
            license=0, garage_slots=8, x2=0, credit=0,
            bank_last_updated=?, biz_income_time=0,
            biz_slots=3, apt_slots=6
            WHERE uid=?""", (int(time.time()), uid))
        c.execute("DELETE FROM cars WHERE uid=?", (uid,))
        c.execute("DELETE FROM businesses WHERE uid=?", (uid,))
        c.execute("DELETE FROM apartments WHERE uid=?", (uid,))
        c.execute("DELETE FROM casino_plays WHERE uid=?", (uid,))
        c.execute("DELETE FROM org_members WHERE uid=?", (uid,))
        c.execute("DELETE FROM crypto_portfolio WHERE uid=?", (uid,))
        c.execute("DELETE FROM fines WHERE uid=?", (uid,))
        c.execute("UPDATE tax_debt SET amount=0 WHERE uid=?", (uid,))


# ========== LICENSE ==========

def has_license(uid):
    with _conn() as c:
        row = c.execute("SELECT license FROM users WHERE uid=?", (uid,)).fetchone()
        return bool(row[0]) if row else False


def set_license(uid, value: bool):
    with _conn() as c:
        c.execute("UPDATE users SET license=? WHERE uid=?", (int(value), uid))


# ========== GARAGE ==========

def get_garage_slots(uid):
    with _conn() as c:
        row = c.execute("SELECT garage_slots FROM users WHERE uid=?", (uid,)).fetchone()
        return row[0] if row else 8


def update_garage_slots(uid, slots):
    with _conn() as c:
        c.execute("UPDATE users SET garage_slots=? WHERE uid=?", (slots, uid))


def get_biz_slots(uid):
    with _conn() as c:
        row = c.execute("SELECT biz_slots FROM users WHERE uid=?", (uid,)).fetchone()
        return row[0] if row else 3


def update_biz_slots(uid, slots):
    with _conn() as c:
        c.execute("UPDATE users SET biz_slots=? WHERE uid=?", (slots, uid))


def get_apt_slots(uid):
    with _conn() as c:
        row = c.execute("SELECT apt_slots FROM users WHERE uid=?", (uid,)).fetchone()
        return row[0] if row else 6


def update_apt_slots(uid, slots):
    with _conn() as c:
        c.execute("UPDATE users SET apt_slots=? WHERE uid=?", (slots, uid))


# ========== CARS ==========

def add_car(uid, car_id, car_name):
    token = _unique_token("cars")
    with _conn() as c:
        c.execute(
            "INSERT INTO cars (uid, car_id, name, token) VALUES (?,?,?,?)",
            (uid, car_id, car_name, token)
        )
    return token


def get_cars(uid):
    with _conn() as c:
        rows = c.execute("SELECT id, name FROM cars WHERE uid=?", (uid,)).fetchall()
        return [tuple(r) for r in rows]


def get_cars_full(uid):
    with _conn() as c:
        rows = c.execute(
            "SELECT id, name, token, plate FROM cars WHERE uid=?", (uid,)
        ).fetchall()
        return [tuple(r) for r in rows]


def get_car_ids(uid):
    with _conn() as c:
        rows = c.execute("SELECT car_id FROM cars WHERE uid=?", (uid,)).fetchall()
        return [r[0] for r in rows]


def get_car_by_token(token):
    with _conn() as c:
        row = c.execute(
            "SELECT id, uid, car_id, name, token, plate FROM cars WHERE token=?", (token,)
        ).fetchone()
        return tuple(row) if row else None


def get_car_by_dbid(db_id):
    with _conn() as c:
        row = c.execute(
            "SELECT id, uid, car_id, name, token, plate FROM cars WHERE id=?", (db_id,)
        ).fetchone()
        return tuple(row) if row else None


def remove_car_db(db_id):
    with _conn() as c:
        c.execute("DELETE FROM cars WHERE id=?", (db_id,))


def transfer_car(db_id, new_uid):
    with _conn() as c:
        c.execute("UPDATE cars SET uid=? WHERE id=?", (new_uid, db_id))


def update_car_plate(db_id, plate):
    with _conn() as c:
        c.execute("UPDATE cars SET plate=? WHERE id=?", (plate, db_id))


def get_last_car(uid):
    with _conn() as c:
        row = c.execute(
            "SELECT id, uid, car_id, name, token, plate FROM cars WHERE uid=? ORDER BY id DESC LIMIT 1", (uid,)
        ).fetchone()
        return tuple(row) if row else None


# ========== BUSINESSES ==========

def add_business(uid, biz_id, biz_name, income):
    token = _unique_token("businesses")
    with _conn() as c:
        c.execute(
            "INSERT INTO businesses (uid, biz_id, name, income, token) VALUES (?,?,?,?,?)",
            (uid, biz_id, biz_name, income, token)
        )
    return token


def get_businesses(uid):
    with _conn() as c:
        rows = c.execute(
            "SELECT name, income FROM businesses WHERE uid=?", (uid,)
        ).fetchall()
        return [tuple(r) for r in rows]


def get_businesses_full(uid):
    with _conn() as c:
        rows = c.execute(
            "SELECT id, name, income, token FROM businesses WHERE uid=?", (uid,)
        ).fetchall()
        return [tuple(r) for r in rows]


def get_biz_ids(uid):
    with _conn() as c:
        rows = c.execute("SELECT biz_id FROM businesses WHERE uid=?", (uid,)).fetchall()
        return [r[0] for r in rows]


def get_business_by_token(token):
    with _conn() as c:
        row = c.execute(
            "SELECT id, uid, biz_id, name, income, token FROM businesses WHERE token=?",
            (token,)
        ).fetchone()
        return tuple(row) if row else None


def remove_business_db(db_id):
    with _conn() as c:
        c.execute("DELETE FROM businesses WHERE id=?", (db_id,))


def transfer_business(db_id, new_uid):
    with _conn() as c:
        c.execute("UPDATE businesses SET uid=? WHERE id=?", (new_uid, db_id))


def get_biz_owner(biz_id):
    with _conn() as c:
        row = c.execute("SELECT uid FROM businesses WHERE biz_id=?", (biz_id,)).fetchone()
        return row[0] if row else None


def get_biz_income_time(uid):
    with _conn() as c:
        row = c.execute("SELECT biz_income_time FROM users WHERE uid=?", (uid,)).fetchone()
        return row[0] if row else 0


def update_biz_income_time(uid):
    with _conn() as c:
        c.execute("UPDATE users SET biz_income_time=? WHERE uid=?", (int(time.time()), uid))


# ========== APARTMENTS ==========

def add_apartment(uid, apt_id, apt_name):
    token = _unique_token("apartments")
    with _conn() as c:
        c.execute(
            "INSERT INTO apartments (uid, apt_id, name, token) VALUES (?,?,?,?)",
            (uid, apt_id, apt_name, token)
        )
    return token


def get_apartments_full(uid):
    with _conn() as c:
        rows = c.execute(
            "SELECT id, name, token FROM apartments WHERE uid=?", (uid,)
        ).fetchall()
        return [tuple(r) for r in rows]


def get_apt_ids(uid):
    with _conn() as c:
        rows = c.execute("SELECT apt_id FROM apartments WHERE uid=?", (uid,)).fetchall()
        return [r[0] for r in rows]


def get_apartment_by_token(token):
    with _conn() as c:
        row = c.execute(
            "SELECT id, uid, apt_id, name, token FROM apartments WHERE token=?", (token,)
        ).fetchone()
        return tuple(row) if row else None


def remove_apartment_db(db_id):
    with _conn() as c:
        c.execute("DELETE FROM apartments WHERE id=?", (db_id,))


def transfer_apartment(db_id, new_uid):
    with _conn() as c:
        c.execute("UPDATE apartments SET uid=? WHERE id=?", (new_uid, db_id))


# ========== BANK ==========

def apply_bank_interest(uid):
    with _conn() as c:
        row = c.execute(
            "SELECT bank, credit, bank_last_updated FROM users WHERE uid=?", (uid,)
        ).fetchone()
        if not row:
            return
        bank, credit, last_updated = row
        now = int(time.time())
        if last_updated == 0:
            c.execute("UPDATE users SET bank_last_updated=? WHERE uid=?", (now, uid))
            return
        hours = (now - last_updated) / 3600.0
        if hours < 0.01:
            return
        new_bank = bank * ((1 + _cfg.BANK_DEPOSIT_RATE_PER_HOUR) ** hours)
        new_credit = credit * ((1 + _cfg.BANK_CREDIT_RATE_PER_HOUR) ** hours) if credit > 0 else 0
        c.execute(
            "UPDATE users SET bank=?, credit=?, bank_last_updated=? WHERE uid=?",
            (new_bank, new_credit, now, uid)
        )


def bank_deposit(uid, amount):
    with _conn() as c:
        c.execute(
            "UPDATE users SET balance=balance-?, bank=bank+? WHERE uid=?",
            (amount, amount, uid)
        )


def bank_withdraw(uid, amount):
    with _conn() as c:
        c.execute(
            "UPDATE users SET bank=bank-?, balance=balance+? WHERE uid=?",
            (amount, amount, uid)
        )


def get_credit(uid):
    with _conn() as c:
        row = c.execute("SELECT credit FROM users WHERE uid=?", (uid,)).fetchone()
        return row[0] if row else 0


def take_credit(uid, amount):
    with _conn() as c:
        c.execute(
            "UPDATE users SET credit=credit+?, balance=balance+? WHERE uid=?",
            (amount, amount, uid)
        )


def repay_credit(uid, amount):
    with _conn() as c:
        c.execute(
            "UPDATE users SET credit=MAX(0, credit-?), balance=balance-? WHERE uid=?",
            (amount, amount, uid)
        )


# ========== CASINO ==========

def get_casino_plays(uid, date):
    with _conn() as c:
        row = c.execute(
            "SELECT plays FROM casino_plays WHERE uid=? AND date=?", (uid, date)
        ).fetchone()
        return row[0] if row else 0


def increment_casino_plays(uid, date):
    with _conn() as c:
        c.execute("""
            INSERT INTO casino_plays (uid, date, plays) VALUES (?,?,1)
            ON CONFLICT(uid, date) DO UPDATE SET plays=plays+1
        """, (uid, date))


# ========== ORGANISATIONS ==========

def add_org_member(uid, org_key, is_owner):
    with _conn() as c:
        c.execute("""
            INSERT INTO org_members (uid, org_key, is_owner) VALUES (?,?,?)
            ON CONFLICT(uid, org_key) DO UPDATE SET is_owner=excluded.is_owner
        """, (uid, org_key, int(is_owner)))


def remove_org_member(uid, org_key):
    with _conn() as c:
        c.execute("DELETE FROM org_members WHERE uid=? AND org_key=?", (uid, org_key))


def get_user_orgs(uid):
    with _conn() as c:
        rows = c.execute(
            "SELECT org_key, is_owner FROM org_members WHERE uid=?", (uid,)
        ).fetchall()
        return [(r[0], bool(r[1])) for r in rows]


def get_org_members(org_key):
    with _conn() as c:
        rows = c.execute(
            "SELECT uid, is_owner FROM org_members WHERE org_key=?", (org_key,)
        ).fetchall()
        return [(r[0], bool(r[1])) for r in rows]


def set_org_name(org_key, name):
    with _conn() as c:
        c.execute("""
            INSERT INTO org_names (org_key, name) VALUES (?,?)
            ON CONFLICT(org_key) DO UPDATE SET name=excluded.name
        """, (org_key, name))


def get_org_name(org_key):
    with _conn() as c:
        row = c.execute(
            "SELECT name FROM org_names WHERE org_key=?", (org_key,)
        ).fetchone()
        if row:
            return row[0]
        _, default = ORG_DISPLAY.get(org_key, ("", org_key))
        return default


# ========== CATALOG ITEMS ==========

def add_catalog_item(item_type, game_id, name, price, income=0, description='', specs='', added_by=0):
    with _conn() as c:
        c.execute(
            "INSERT INTO catalog_items (item_type, game_id, name, price, income, description, specs, added_by, added_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (item_type, game_id, name, price, income, description, specs, added_by, int(time.time()))
        )


def get_catalog_items(item_type):
    with _conn() as c:
        rows = c.execute(
            "SELECT id, item_type, game_id, name, price, income, description, specs FROM catalog_items WHERE item_type=? AND active=1",
            (item_type,)
        ).fetchall()
        return [tuple(r) for r in rows]


def deactivate_catalog_item(game_id, item_type):
    with _conn() as c:
        c.execute("UPDATE catalog_items SET active=0 WHERE game_id=? AND item_type=?", (game_id, item_type))


# ========== PROMO CODES ==========

def add_promo_code(code, amount, max_uses, added_by):
    with _conn() as c:
        try:
            c.execute(
                "INSERT INTO promo_codes (code, amount, max_uses, added_by, added_at) VALUES (?,?,?,?,?)",
                (code.upper(), float(amount), int(max_uses), added_by, int(time.time()))
            )
            return True
        except Exception:
            return False


def disable_promo_code(code):
    with _conn() as c:
        c.execute("UPDATE promo_codes SET active=0 WHERE code=?", (code.upper(),))
        return c.execute("SELECT changes()").fetchone()[0] > 0


def get_active_promos():
    with _conn() as c:
        rows = c.execute(
            "SELECT code, amount, max_uses, used_count, added_at FROM promo_codes WHERE active=1 ORDER BY added_at DESC"
        ).fetchall()
        return [tuple(r) for r in rows]


def use_promo_code(uid, code):
    code = code.upper()
    with _conn() as c:
        promo = c.execute(
            "SELECT code, amount, max_uses, used_count, active FROM promo_codes WHERE code=?",
            (code,)
        ).fetchone()
        if not promo:
            return False, 0.0, "not_found"
        if not promo[4]:
            return False, 0.0, "disabled"
        if promo[2] > 0 and promo[3] >= promo[2]:
            return False, 0.0, "exhausted"
        already = c.execute(
            "SELECT 1 FROM promo_uses WHERE uid=? AND code=?", (uid, code)
        ).fetchone()
        if already:
            return False, 0.0, "already_used"
        c.execute(
            "INSERT INTO promo_uses (uid, code, used_at) VALUES (?,?,?)",
            (uid, code, int(time.time()))
        )
        c.execute("UPDATE promo_codes SET used_count = used_count + 1 WHERE code=?", (code,))
        return True, float(promo[1]), "ok"


# ========== CRYPTO ==========

def get_crypto_portfolio(uid):
    with _conn() as c:
        rows = c.execute(
            "SELECT symbol, amount, avg_buy_price FROM crypto_portfolio WHERE uid=? AND amount > 0",
            (uid,)
        ).fetchall()
        return [(r[0], r[1], r[2]) for r in rows]


def get_crypto_holding(uid, symbol):
    with _conn() as c:
        row = c.execute(
            "SELECT amount, avg_buy_price FROM crypto_portfolio WHERE uid=? AND symbol=?",
            (uid, symbol)
        ).fetchone()
        return (row[0], row[1]) if row else (0.0, 0.0)


def buy_crypto(uid, symbol, amount, price):
    with _conn() as c:
        row = c.execute(
            "SELECT amount, avg_buy_price FROM crypto_portfolio WHERE uid=? AND symbol=?",
            (uid, symbol)
        ).fetchone()
        if row:
            old_amount, old_avg = row[0], row[1]
            new_amount = old_amount + amount
            new_avg = (old_amount * old_avg + amount * price) / new_amount if new_amount > 0 else price
            c.execute(
                "UPDATE crypto_portfolio SET amount=?, avg_buy_price=? WHERE uid=? AND symbol=?",
                (new_amount, new_avg, uid, symbol)
            )
        else:
            c.execute(
                "INSERT INTO crypto_portfolio (uid, symbol, amount, avg_buy_price) VALUES (?,?,?,?)",
                (uid, symbol, amount, price)
            )


def sell_crypto(uid, symbol, amount):
    with _conn() as c:
        row = c.execute(
            "SELECT amount, avg_buy_price FROM crypto_portfolio WHERE uid=? AND symbol=?",
            (uid, symbol)
        ).fetchone()
        if not row:
            return False
        old_amount = row[0]
        if old_amount < amount - 1e-9:
            return False
        new_amount = max(0.0, old_amount - amount)
        c.execute(
            "UPDATE crypto_portfolio SET amount=? WHERE uid=? AND symbol=?",
            (new_amount, uid, symbol)
        )
        return True


def add_crypto_history(uid, symbol, action, amount, price):
    with _conn() as c:
        c.execute(
            "INSERT INTO crypto_history (ts, uid, symbol, action, amount, price) VALUES (?,?,?,?,?,?)",
            (int(time.time()), uid, symbol, action, amount, price)
        )


def get_crypto_history(uid, limit=20):
    with _conn() as c:
        rows = c.execute(
            "SELECT ts, symbol, action, amount, price FROM crypto_history "
            "WHERE uid=? ORDER BY ts DESC LIMIT ?",
            (uid, limit)
        ).fetchall()
        return [(r[0], r[1], r[2], r[3], r[4]) for r in rows]


# ========== ADMINS ==========

def is_db_admin(uid):
    with _conn() as c:
        row = c.execute("SELECT 1 FROM admins WHERE uid=? AND active=1", (uid,)).fetchone()
        return bool(row)


def grant_admin(uid, granted_by):
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO admins (uid, granted_by, granted_at, active) VALUES (?,?,?,1)",
            (uid, granted_by, int(time.time()))
        )


def revoke_admin(uid):
    with _conn() as c:
        c.execute("UPDATE admins SET active=0 WHERE uid=? AND active=1", (uid,))
        row = c.execute("SELECT changes()").fetchone()
        return bool(row and row[0])


def get_admins():
    with _conn() as c:
        rows = c.execute(
            "SELECT uid, granted_by, granted_at FROM admins WHERE active=1"
        ).fetchall()
        return [tuple(r) for r in rows]


# ========== LOGS ==========

def add_log(uid, action, details='', amount=0, admin_uid=0):
    with _conn() as c:
        c.execute(
            "INSERT INTO transaction_logs (ts, uid, action, details, amount, admin_uid) VALUES (?,?,?,?,?,?)",
            (int(time.time()), uid, action, details, float(amount), admin_uid)
        )


# ========== FINES ==========

def add_fine(uid, amount, reason, article, admin_uid):
    with _conn() as c:
        c.execute(
            "INSERT INTO fines (uid, amount, reason, article, issued_by, issued_at) VALUES (?,?,?,?,?,?)",
            (uid, amount, reason, article, admin_uid, int(time.time()))
        )


def get_fines(uid, unpaid_only=False):
    with _conn() as c:
        if unpaid_only:
            rows = c.execute(
                "SELECT id, amount, reason, article, issued_at, paid FROM fines WHERE uid=? AND paid=0 ORDER BY issued_at DESC", (uid,)
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT id, amount, reason, article, issued_at, paid FROM fines WHERE uid=? ORDER BY issued_at DESC", (uid,)
            ).fetchall()
        return [tuple(r) for r in rows]


def pay_fine(fine_id, uid):
    with _conn() as c:
        fine = c.execute("SELECT amount, paid FROM fines WHERE id=? AND uid=?", (fine_id, uid)).fetchone()
        if not fine or fine[1]:
            return None
        c.execute("UPDATE fines SET paid=1, paid_at=? WHERE id=?", (int(time.time()), fine_id))
        return fine[0]


# ========== TREASURY ==========

def get_treasury():
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO government_treasury (id, balance) VALUES (1, 0)")
        row = c.execute("SELECT balance FROM government_treasury WHERE id=1").fetchone()
        return row[0] if row else 0.0


def update_treasury(amount, action, uid=0, details=''):
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO government_treasury (id, balance) VALUES (1, 0)")
        c.execute("UPDATE government_treasury SET balance = balance + ? WHERE id=1", (amount,))
        c.execute(
            "INSERT INTO treasury_logs (ts, action, amount, uid, details) VALUES (?,?,?,?,?)",
            (int(time.time()), action, amount, uid, details)
        )


def get_treasury_logs(limit=20):
    with _conn() as c:
        rows = c.execute(
            "SELECT ts, action, amount, uid, details FROM treasury_logs ORDER BY ts DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [tuple(r) for r in rows]


# ========== TAX ==========

TAX_RATE = 0.35


def get_tax_debt(uid):
    with _conn() as c:
        row = c.execute("SELECT amount, last_charged FROM tax_debt WHERE uid=?", (uid,)).fetchone()
        return (row[0], row[1]) if row else (0.0, 0)


def add_tax_debt(uid, amount):
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO tax_debt (uid, amount, last_charged) VALUES (?,0,0)", (uid,))
        c.execute("UPDATE tax_debt SET amount=amount+?, last_charged=? WHERE uid=?",
                  (amount, int(time.time()), uid))


def pay_tax_debt(uid, amount):
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO tax_debt (uid, amount, last_charged) VALUES (?,0,0)", (uid,))
        row = c.execute("SELECT amount FROM tax_debt WHERE uid=?", (uid,)).fetchone()
        if not row or row[0] <= 0:
            return 0.0
        actual = min(amount, row[0])
        c.execute("UPDATE tax_debt SET amount=amount-? WHERE uid=?", (actual, uid))
        return actual


# ========== PLAYER ORGS ==========

def create_player_org(owner_uid, name, icon='🏛️'):
    with _conn() as c:
        try:
            c.execute(
                "INSERT INTO player_orgs (name, icon, owner_uid, created_at) VALUES (?,?,?,?)",
                (name, icon, owner_uid, int(time.time()))
            )
            org_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.execute(
                "INSERT INTO player_org_members (org_id, uid, joined_at) VALUES (?,?,?)",
                (org_id, owner_uid, int(time.time()))
            )
            return org_id
        except Exception:
            return None


def get_player_org_by_name(name):
    with _conn() as c:
        row = c.execute(
            "SELECT org_id, name, icon, owner_uid, created_at FROM player_orgs WHERE LOWER(name)=LOWER(?)",
            (name,)
        ).fetchone()
        return dict(row) if row else None


def get_player_org_by_id(org_id):
    with _conn() as c:
        row = c.execute(
            "SELECT org_id, name, icon, owner_uid, created_at FROM player_orgs WHERE org_id=?",
            (org_id,)
        ).fetchone()
        return dict(row) if row else None


def get_player_orgs_for_user(uid):
    with _conn() as c:
        rows = c.execute("""
            SELECT po.org_id, po.name, po.icon, po.owner_uid
            FROM player_orgs po
            JOIN player_org_members pom ON po.org_id = pom.org_id
            WHERE pom.uid=?
            ORDER BY po.created_at
        """, (uid,)).fetchall()
        return [dict(r) for r in rows]


def get_orgs_owned_by(uid):
    with _conn() as c:
        rows = c.execute(
            "SELECT org_id, name, icon FROM player_orgs WHERE owner_uid=?", (uid,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_player_org_members(org_id):
    with _conn() as c:
        rows = c.execute(
            "SELECT uid, joined_at FROM player_org_members WHERE org_id=?", (org_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def add_player_org_member(org_id, uid):
    with _conn() as c:
        try:
            c.execute(
                "INSERT OR IGNORE INTO player_org_members (org_id, uid, joined_at) VALUES (?,?,?)",
                (org_id, uid, int(time.time()))
            )
            return True
        except Exception:
            return False


def remove_player_org_member(org_id, uid):
    with _conn() as c:
        c.execute("DELETE FROM player_org_members WHERE org_id=? AND uid=?", (org_id, uid))


def delete_player_org(org_id):
    with _conn() as c:
        c.execute("DELETE FROM player_org_members WHERE org_id=?", (org_id,))
        c.execute("DELETE FROM player_orgs WHERE org_id=?", (org_id,))


def delete_all_player_orgs_by_owner(uid):
    with _conn() as c:
        org_ids = [r[0] for r in c.execute(
            "SELECT org_id FROM player_orgs WHERE owner_uid=?", (uid,)
        ).fetchall()]
        for oid in org_ids:
            c.execute("DELETE FROM player_org_members WHERE org_id=?", (oid,))
        c.execute("DELETE FROM player_orgs WHERE owner_uid=?", (uid,))
        return len(org_ids)


def is_player_org_member(org_id, uid):
    with _conn() as c:
        row = c.execute(
            "SELECT 1 FROM player_org_members WHERE org_id=? AND uid=?", (org_id, uid)
        ).fetchone()
        return row is not None


# ========== GOVERNMENT EMPLOYEES ==========

def set_gov_employee(uid, role, assigned_by):
    with _conn() as c:
        c.execute("""
            INSERT OR REPLACE INTO government_employees (uid, role, assigned_by, assigned_at)
            VALUES (?,?,?,?)
        """, (uid, role, assigned_by, int(time.time())))


def remove_gov_employee(uid):
    with _conn() as c:
        c.execute("DELETE FROM government_employees WHERE uid=?", (uid,))


def is_gov_employee(uid):
    with _conn() as c:
        row = c.execute("SELECT 1 FROM government_employees WHERE uid=?", (uid,)).fetchone()
        return bool(row)


def get_gov_employee(uid):
    with _conn() as c:
        row = c.execute("SELECT uid, role FROM government_employees WHERE uid=?", (uid,)).fetchone()
        return dict(row) if row else None


# ========== MVD EMPLOYEES ==========

def set_mvd_employee(uid, role, assigned_by):
    with _conn() as c:
        c.execute("""
            INSERT OR REPLACE INTO mvd_employees (uid, role, assigned_by, assigned_at)
            VALUES (?,?,?,?)
        """, (uid, role, assigned_by, int(time.time())))


def remove_mvd_employee(uid):
    with _conn() as c:
        c.execute("DELETE FROM mvd_employees WHERE uid=?", (uid,))


def is_mvd_employee(uid):
    with _conn() as c:
        row = c.execute("SELECT 1 FROM mvd_employees WHERE uid=?", (uid,)).fetchone()
        return bool(row)


def get_mvd_employee(uid):
    with _conn() as c:
        row = c.execute("SELECT uid, role FROM mvd_employees WHERE uid=?", (uid,)).fetchone()
        return dict(row) if row else None


# ========== OWNERSHIP UTILS ==========

def remove_all_cars(uid):
    with _conn() as c:
        count = c.execute("SELECT COUNT(*) FROM cars WHERE uid=?", (uid,)).fetchone()[0]
        c.execute("DELETE FROM cars WHERE uid=?", (uid,))
        return count


def remove_all_businesses(uid):
    with _conn() as c:
        count = c.execute("SELECT COUNT(*) FROM businesses WHERE uid=?", (uid,)).fetchone()[0]
        c.execute("DELETE FROM businesses WHERE uid=?", (uid,))
        return count


def remove_all_apartments(uid):
    with _conn() as c:
        count = c.execute("SELECT COUNT(*) FROM apartments WHERE uid=?", (uid,)).fetchone()[0]
        c.execute("DELETE FROM apartments WHERE uid=?", (uid,))
        return count


def set_custom_plate(car_db_id, plate_str):
    with _conn() as c:
        c.execute("UPDATE cars SET plate=? WHERE id=?", (plate_str, car_db_id))


# ========== DAILY BONUS ==========

DAILY_BONUS_DEFAULTS = [
    (1,  'money', '10000',  '💵 10 000 ₽'),
    (2,  'money', '20000',  '💵 20 000 ₽'),
    (3,  'car',   '0',      '🚗 ВАЗ-2170 «Приора»'),
    (4,  'money', '40000',  '💵 40 000 ₽'),
    (5,  'money', '50000',  '💵 50 000 ₽'),
    (6,  'money', '60000',  '💵 60 000 ₽'),
    (7,  'money', '70000',  '💵 70 000 ₽'),
    (8,  'money', '80000',  '💵 80 000 ₽'),
    (9,  'money', '90000',  '💵 90 000 ₽'),
    (10, 'money', '100000', '💵 100 000 ₽'),
    (11, 'money', '110000', '💵 110 000 ₽'),
    (12, 'money', '120000', '💵 120 000 ₽'),
    (13, 'money', '130000', '💵 130 000 ₽'),
    (14, 'car',   '42',     '🚗 BMW M5 F10'),
    (50, 'biz',   '0',      '🏢 Бизнес'),
]


def init_daily_bonus_defaults():
    """Populate daily_bonus_rewards with defaults if the table is empty."""
    with _conn() as c:
        count = c.execute("SELECT COUNT(*) FROM daily_bonus_rewards").fetchone()[0]
        if count == 0:
            c.executemany(
                "INSERT OR IGNORE INTO daily_bonus_rewards "
                "(day, reward_type, reward_value, description) VALUES (?,?,?,?)",
                [(d, rt, rv, desc) for d, rt, rv, desc in DAILY_BONUS_DEFAULTS],
            )


def get_all_daily_bonus_rewards():
    with _conn() as c:
        rows = c.execute(
            "SELECT day, reward_type, reward_value, description, active "
            "FROM daily_bonus_rewards ORDER BY day"
        ).fetchall()
        return [tuple(r) for r in rows]


def get_active_daily_bonus_rewards():
    with _conn() as c:
        rows = c.execute(
            "SELECT day, reward_type, reward_value, description, active "
            "FROM daily_bonus_rewards WHERE active=1 ORDER BY day"
        ).fetchall()
        return [tuple(r) for r in rows]


def get_daily_bonus_reward(day: int):
    with _conn() as c:
        row = c.execute(
            "SELECT day, reward_type, reward_value, description, active "
            "FROM daily_bonus_rewards WHERE day=?", (day,)
        ).fetchone()
        return tuple(row) if row else None


def get_max_bonus_day():
    with _conn() as c:
        row = c.execute(
            "SELECT MAX(day) FROM daily_bonus_rewards WHERE active=1"
        ).fetchone()
        return row[0] or 14


def get_user_bonus_state(uid: int) -> dict:
    with _conn() as c:
        row = c.execute(
            "SELECT uid, current_day, last_claimed, streak, total_claims "
            "FROM daily_bonus_claims WHERE uid=?", (uid,)
        ).fetchone()
        if row:
            return dict(row)
        return {
            "uid": uid, "current_day": 1,
            "last_claimed": 0, "streak": 0, "total_claims": 0,
        }


def upsert_daily_bonus_reward(day: int, reward_type: str, reward_value: str, description: str):
    with _conn() as c:
        c.execute("""
            INSERT OR REPLACE INTO daily_bonus_rewards
              (day, reward_type, reward_value, description, active)
            VALUES (?, ?, ?, ?, 1)
        """, (day, reward_type, reward_value, description))


def toggle_daily_bonus_reward(day: int, active: int):
    with _conn() as c:
        c.execute(
            "UPDATE daily_bonus_rewards SET active=? WHERE day=?", (active, day)
        )


def delete_daily_bonus_reward(day: int):
    with _conn() as c:
        c.execute("DELETE FROM daily_bonus_rewards WHERE day=?", (day,))


def _find_reward_for_day(current_day: int):
    """Return (reward_row, actual_day_claimed). Falls back to looping."""
    with _conn() as c:
        # Try exact day first
        row = c.execute(
            "SELECT day, reward_type, reward_value, description, active "
            "FROM daily_bonus_rewards WHERE day=? AND active=1", (current_day,)
        ).fetchone()
        if row:
            return tuple(row), current_day
        # Find nearest higher day
        row = c.execute(
            "SELECT day, reward_type, reward_value, description, active "
            "FROM daily_bonus_rewards WHERE day>=? AND active=1 ORDER BY day LIMIT 1",
            (current_day,)
        ).fetchone()
        if row:
            return tuple(row), tuple(row)[0]
        # Loop: take first available day
        row = c.execute(
            "SELECT day, reward_type, reward_value, description, active "
            "FROM daily_bonus_rewards WHERE active=1 ORDER BY day LIMIT 1"
        ).fetchone()
        if row:
            return tuple(row), tuple(row)[0]
    # Absolute fallback
    return (current_day, 'money', '10000', '💵 10 000 ₽', 1), current_day


def claim_daily_bonus(uid: int):
    """
    Attempt to claim the daily bonus for uid.

    Returns dict:
      success  bool   — False if cooldown not yet met
      reset    bool   — True if streak was reset (>48 h gap)
      day      int    — day that was actually claimed
      reward   tuple  — (day, reward_type, reward_value, description, active)
      next_day int    — day queued for tomorrow
    """
    now = int(time.time())
    state = get_user_bonus_state(uid)
    last         = state["last_claimed"]
    current_day  = state["current_day"]
    streak       = state["streak"]
    total        = state["total_claims"]
    reset        = False

    # Streak reset if missed >48 h (and had claimed at least once before)
    if last > 0 and (now - last) > 48 * 3600:
        current_day = 1
        streak      = 0
        reset       = True

    # Cooldown check
    if last > 0 and (now - last) < 24 * 3600:
        return {"success": False, "reset": False, "day": current_day,
                "reward": None, "next_day": current_day}

    reward_row, claimed_day = _find_reward_for_day(current_day)

    # Advance to next day
    max_day  = get_max_bonus_day()
    next_day = current_day + 1
    if next_day > max_day:
        next_day = 1

    streak += 1
    total  += 1

    with _conn() as c:
        c.execute("""
            INSERT OR REPLACE INTO daily_bonus_claims
              (uid, current_day, last_claimed, streak, total_claims)
            VALUES (?, ?, ?, ?, ?)
        """, (uid, next_day, now, streak, total))

    return {
        "success":  True,
        "reset":    reset,
        "day":      claimed_day,
        "reward":   reward_row,
        "next_day": next_day,
    }


# ========== ТОТАЛИЗАТОР ==========

def toto_upsert_matches(matches: list):
    """Upsert upcoming matches; never overwrite scores/status of finished ones."""
    now = int(time.time())
    with _conn() as c:
        for m in matches:
            c.execute("""
                INSERT INTO toto_matches
                    (match_id, league, league_flag, home_team, away_team,
                     match_time, odds_home, odds_draw, odds_away, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    home_team  = excluded.home_team,
                    away_team  = excluded.away_team,
                    match_time = excluded.match_time
                WHERE toto_matches.status = 'pending'
            """, (
                m["match_id"], m["league"], m["league_flag"],
                m["home_team"], m["away_team"], m["match_time"],
                m["odds_home"], m["odds_draw"], m["odds_away"], now,
            ))


def toto_get_upcoming_matches() -> list:
    """Return pending matches that haven't started more than 2 h ago."""
    cutoff = int(time.time()) - 2 * 3600
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM toto_matches "
            "WHERE status='pending' AND match_time >= ? "
            "ORDER BY match_time ASC LIMIT 30",
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]


def toto_get_match(match_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM toto_matches WHERE match_id=?", (match_id,)
        ).fetchone()
        return dict(row) if row else None


def toto_place_bet(user_id: int, match_id: str, bet_type: str,
                   amount: float, potential_win: float) -> int:
    now = int(time.time())
    with _conn() as c:
        c.execute("UPDATE users SET balance = balance - ? WHERE uid = ?",
                  (amount, user_id))
        c.execute(
            "INSERT INTO toto_bets "
            "(user_id, match_id, bet_type, amount, potential_win, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (user_id, match_id, bet_type, amount, potential_win, now),
        )
        return c.lastrowid


def toto_get_user_bets(user_id: int, status: str | None = None) -> list:
    with _conn() as c:
        if status:
            rows = c.execute(
                "SELECT b.*, m.home_team, m.away_team, m.league, m.league_flag, "
                "       m.match_time, m.home_score, m.away_score "
                "FROM toto_bets b JOIN toto_matches m ON b.match_id = m.match_id "
                "WHERE b.user_id = ? AND b.status = ? "
                "ORDER BY b.created_at DESC LIMIT 20",
                (user_id, status),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT b.*, m.home_team, m.away_team, m.league, m.league_flag, "
                "       m.match_time, m.home_score, m.away_score "
                "FROM toto_bets b JOIN toto_matches m ON b.match_id = m.match_id "
                "WHERE b.user_id = ? "
                "ORDER BY b.created_at DESC LIMIT 20",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]


def toto_get_pending_for_resolution() -> list:
    """Match IDs that are still 'pending' but started > 2 h ago (likely finished)."""
    cutoff = int(time.time()) - 2 * 3600
    with _conn() as c:
        rows = c.execute(
            "SELECT match_id FROM toto_matches "
            "WHERE status = 'pending' AND match_time < ?",
            (cutoff,),
        ).fetchall()
        return [r["match_id"] for r in rows]


def toto_resolve_match(match_id: str, home_score: int, away_score: int) -> tuple:
    """Set result, pay winners, return (outcome, home_score, away_score, [(uid, win_amount)])."""
    if home_score > away_score:
        outcome = "1"
    elif home_score == away_score:
        outcome = "X"
    else:
        outcome = "2"
    winners = []
    with _conn() as c:
        c.execute(
            "UPDATE toto_matches SET status='finished', home_score=?, away_score=? "
            "WHERE match_id=? AND status='pending'",
            (home_score, away_score, match_id),
        )
        bets = c.execute(
            "SELECT id, user_id, bet_type, amount, potential_win "
            "FROM toto_bets WHERE match_id=? AND status='pending'",
            (match_id,),
        ).fetchall()
        for bet in bets:
            if bet["bet_type"] == outcome:
                c.execute("UPDATE toto_bets SET status='won'  WHERE id=?", (bet["id"],))
                c.execute("UPDATE users SET balance = balance + ? WHERE uid=?",
                          (bet["potential_win"], bet["user_id"]))
                winners.append((bet["user_id"], bet["potential_win"]))
            else:
                c.execute("UPDATE toto_bets SET status='lost' WHERE id=?", (bet["id"],))
    return outcome, home_score, away_score, winners


def toto_cancel_match(match_id: str):
    """Cancel match and refund all pending bets."""
    with _conn() as c:
        c.execute("UPDATE toto_matches SET status='cancelled' WHERE match_id=?", (match_id,))
        bets = c.execute(
            "SELECT id, user_id, amount FROM toto_bets WHERE match_id=? AND status='pending'",
            (match_id,),
        ).fetchall()
        for bet in bets:
            c.execute("UPDATE toto_bets SET status='refunded' WHERE id=?", (bet["id"],))
            c.execute("UPDATE users SET balance = balance + ? WHERE uid=?",
                      (bet["amount"], bet["user_id"]))


# ========== INIT ==========

init_db()
