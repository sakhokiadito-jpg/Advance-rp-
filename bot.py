import asyncio
import hashlib
import random
import time
from datetime import datetime, timezone, timedelta
import aiohttp

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
import database as db

bot = Bot(token=config.TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== АВТОСАЛОН (цены в USD, конвертируются по курсу) ====================
# Цены в USD — умножаются на config.USD_RUB_RATE при покупке/отображении

CARS_USD = {
    1:   ("Honda Civic Mk6 — 175 л.с.", 52),
    2:   ("Smart Fortwo — 100 л.с.", 45),
    3:   ("Peugeot 406 — 207 л.с.", 54),
    4:   ("BMW E28 — 286 л.с.", 55),
    5:   ("BMW M135i — 326 л.с.", 62),
    6:   ("Ford Transit — 220 л.с.", 50),
    7:   ("Peugeot 308 — 180 л.с.", 55),
    8:   ("Mercedes W140 — 390 л.с.", 62),
    9:   ("BMW M5 E34 — 340 л.с.", 65),
    10:  ("Mazda RX-8 — 210 л.с.", 62),
    11:  ("Honda S2000 — 240 л.с.", 64),
    12:  ("Mercedes-Benz 190 (W201) — 220 л.с.", 54),
    13:  ("BMW 5 Series (E39) — 400 л.с.", 112),
    14:  ("Dodge Diplomat — 140 л.с.", 36),
    15:  ("Ford Crown Vic — 240 л.с.", 62),
    16:  ("Audi Quattro Sport — 306 л.с.", 168),
    17:  ("Toyota AE86 Trueno — 140 л.с.", 280),
    18:  ("Honda Del Sol — 160 л.с.", 168),
    19:  ("Volkswagen Golf II GTI — 112 л.с.", 168),
    20:  ("Mazda MX-5 — 190 л.с.", 139),
    21:  ("Volkswagen Scirocco — 250 л.с.", 61),
    22:  ("BMW M3 E36 — 320 л.с.", 134),
    23:  ("Audi RS 4 Avant — 450 л.с.", 448),
    24:  ("Ford Mustang VI — 310 л.с.", 504),
    25:  ("Mercedes-Benz W210 — 354 л.с.", 168),
    26:  ("Dodge Charger — 420 л.с.", 280),
    27:  ("Chevrolet Camaro — 490 л.с.", 426),
    28:  ("Toyota Camry 70 — 280 л.с.", 314),
    29:  ("Volkswagen Passat B8 — 190 л.с.", 336),
    30:  ("BMW M5 E60 — 507 л.с.", 426),
    31:  ("Kia Stinger GT — 361 л.с.", 381),
    32:  ("BMW M3 E92 — 420 л.с.", 336),
    33:  ("Cadillac Escalade — 400 л.с.", 314),
    34:  ("Mercedes-AMG C 63 Coupe — 487 л.с.", 336),
    35:  ("Cadillac CTS — 320 л.с.", 370),
    36:  ("Subaru BRZ — 220 л.с.", 179),
    37:  ("Mercedes G 65 — 575 л.с.", 526),
    38:  ("BMW X5 E70 — 555 л.с.", 392),
    39:  ("Alfa Romeo Giulia Quadrifoglio — 505 л.с.", 504),
    40:  ("Subaru WRX STI — 300 л.с.", 415),
    41:  ("BMW M2 F87 — 450 л.с.", 560),
    42:  ("BMW M5 F10 — 560 л.с.", 426),
    43:  ("Toyota Land Cruiser 200 — 362 л.с.", 426),
    44:  ("Mercedes-Benz GLE — 435 л.с.", 426),
    45:  ("Audi RS2 Avant — 315 л.с.", 392),
    46:  ("Nissan Skyline R34 — 270 л.с.", 403),
    47:  ("Nissan Skyline R32 — 220 л.с.", 314),
    48:  ("Toyota Crown — 315 л.с.", 280),
    49:  ("Toyota Supra A80 — 280 л.с.", 415),
    50:  ("Mercedes-Benz CL 65 AMG — 630 л.с.", 560),
    51:  ("Mercedes-Benz S-Klasse W221 — 650 л.с.", 448),
    52:  ("Chevrolet Tahoe — 420 л.с.", 415),
    53:  ("Mitsubishi Lancer Evolution X — 295 л.с.", 616),
    54:  ("Subaru Impreza WRX STI GVB — 300 л.с.", 504),
    55:  ("Subaru WRX STI VA — 300 л.с.", 526),
    56:  ("Mercedes-Benz Actros — 625 л.с.", 1232),
    57:  ("Scania R730 — 600 л.с.", 1512),
    58:  ("Nissan 240SX S13 — 240 л.с.", 392),
    59:  ("Skoda Octavia A8 Combi — 190 л.с.", 358),
    60:  ("Mazda RX-7 FD3S — 280 л.с.", 616),
    61:  ("Toyota Mark II JZX100 — 280 л.с.", 448),
    62:  ("Ford Focus RS — 350 л.с.", 392),
    63:  ("Toyota Altezza RS200 — 210 л.с.", 140),
    64:  ("Dacia Logan — 90 л.с.", 67),
    65:  ("Fiat Doblo — 105 л.с.", 162),
    66:  ("Honda Civic Type R FK8 — 320 л.с.", 470),
    67:  ("Chevrolet C10 Silverado — 165 л.с.", 246),
    68:  ("Volkswagen Golf VII R — 300 л.с.", 448),
    69:  ("BMW M4 F82 — 431 л.с.", 896),
    70:  ("Volkswagen Polo Sedan — 110 л.с.", 157),
    71:  ("Ford Fiesta — 120 л.с.", 102),
    72:  ("Renault Logan — 82 л.с.", 78),
    73:  ("LADA Vesta — 106 л.с.", 123),
    74:  ("LADA Granta — 87 л.с.", 90),
    75:  ("KIA Rio — 123 л.с.", 168),
    76:  ("Hyundai Solaris — 123 л.с.", 162),
    77:  ("Skoda Octavia — 150 л.с.", 246),
    78:  ("Renault Duster — 135 л.с.", 213),
    79:  ("Toyota RAV4 — 203 л.с.", 392),
    80:  ("Kia Sportage — 177 л.с.", 336),
    81:  ("Nissan X-Trail — 163 л.с.", 302),
    82:  ("Hyundai Tucson — 184 л.с.", 358),
    83:  ("Mitsubishi Outlander — 167 л.с.", 314),
    84:  ("Toyota Corolla — 122 л.с.", 280),
    85:  ("Mazda 6 — 194 л.с.", 336),
    86:  ("Honda Accord — 201 л.с.", 358),
    87:  ("Ford Explorer — 300 л.с.", 504),
    88:  ("Jeep Grand Cherokee — 296 л.с.", 560),
    89:  ("Audi A6 — 249 л.с.", 560),
    90:  ("BMW 7 Series — 440 л.с.", 840),
    91:  ("Mercedes S-Class — 469 л.с.", 1120),
    92:  ("Range Rover — 525 л.с.", 1232),
    93:  ("Porsche Cayenne — 340 л.с.", 784),
    94:  ("Porsche 911 — 450 л.с.", 1120),
    95:  ("Lamborghini Huracan — 610 л.с.", 2800),
    96:  ("Ferrari 488 GTB — 660 л.с.", 3360),
    97:  ("McLaren 570S — 562 л.с.", 2240),
    98:  ("Aston Martin DB11 — 503 л.с.", 2352),
    99:  ("Bentley Continental GT — 626 л.с.", 2800),
    100: ("Rolls-Royce Ghost — 563 л.с.", 3920),
    101: ("Lamborghini Urus — 641 л.с.", 2576),
    102: ("Ferrari Portofino — 591 л.с.", 2800),
    103: ("Bugatti Chiron — 1500 л.с.", 47040),
    104: ("Koenigsegg Agera RS — 1115 л.с.", 33600),
    105: ("McLaren P1 — 920 л.с.", 16800),
    106: ("Ferrari LaFerrari — 949 л.с.", 40320),
    107: ("Pagani Zonda Cinque — 764 л.с.", 106400),
    108: ("Lamborghini Veneno — 750 л.с.", 39200),
    109: ("Bugatti Veyron — 1001 л.с.", 21280),
    110: ("Rolls-Royce Dawn — 570 л.с.", 13440),
    111: ("Koenigsegg Jesko Attack — 1280 л.с.", 61600),
    112: ("Mercedes G-Class 6x6 — 544 л.с.", 10640),
}


def car_price_rub(car_id: int) -> int:
    """Возвращает цену авто в рублях по текущему курсу USD/RUB."""
    usd = CARS_USD.get(car_id, (None, 0))[1]
    return round(usd * config.USD_RUB_RATE / 1000) * 1000  # округление до тысячи


def get_car(car_id: int):
    """Возвращает (name, price_rub) или None."""
    data = CARS_USD.get(car_id)
    if not data:
        return None
    name, usd = data
    return name, car_price_rub(car_id)


# Для обратной совместимости (топ имущество)
CARS = {cid: (n, car_price_rub(cid)) for cid, (n, _) in CARS_USD.items()}

# ==================== РАБОТЫ ====================

JOBS = {
    "Заправщик":            60_000,
    "Работник фаст-фуда":   56_000,
    "Кассир":               50_000,
    "Таксист":              80_000,
    "Водитель автобуса":    80_000,
    "Эвакуаторщик":         90_000,
    "Автомеханик":          75_000,
    "Дальнобойщик":         95_000,
    "Инкассатор":          105_000,
    "Строитель":            85_000,
    "Фермер":               75_000,
    "Курьер":               80_000,
}

_MVD_RANKS = [
    ("Сержант",             65_000),
    ("Старшина",            75_000),
    ("Прапорщик",           85_000),
    ("Мл. лейтенант",       95_000),
    ("Лейтенант МВД",      105_000),
    ("Ст. лейтенант МВД",  115_000),
    ("Капитан МВД",        125_000),
    ("Майор МВД",          140_000),
    ("Подполковник МВД",   155_000),
    ("Полковник МВД",      170_000),
    ("Генерал МВД",        200_000),
]
_MVD_UNITS = ["СОБР", "ОМОН", "ППС", "ДПС"]

GOV_JOBS = {}
# МВД — все подразделения × все звания
for _unit in _MVD_UNITS:
    for _rank, _sal in _MVD_RANKS:
        GOV_JOBS[f"{_unit} — {_rank}"] = _sal

# ФСБ
GOV_JOBS.update({
    "ФСБ — Мл. лейтенант":   100_000,
    "ФСБ — Лейтенант":        110_000,
    "ФСБ — Ст. лейтенант":    120_000,
    "ФСБ — Капитан":          130_000,
    "ФСБ — Майор":            145_000,
    "ФСБ — Подполковник":     160_000,
    "ФСБ — Полковник":        180_000,
    "ФСБ — Генерал":          220_000,
})

# Прокуратура
GOV_JOBS.update({
    "Помощник прокурора":     90_000,
    "Прокурор":              105_000,
    "Старший прокурор":      120_000,
    "Прокурор района":       135_000,
    "Прокурор города":       150_000,
    "Прокурор области":      170_000,
    "Генеральный прокурор":  210_000,
})

# Правительство
GOV_JOBS.update({
    "Охранник прав-ва":       70_000,
    "Водитель прав-ва":       75_000,
    "Секретарь прав-ва":      85_000,
    "Депутат":               110_000,
    "Министр":               135_000,
    "Зам. губернатора":      165_000,
    "Губернатор":            200_000,
})

# ЦОДД
GOV_JOBS.update({
    "ЦОДД — Инспектор":           70_000,
    "ЦОДД — Ст. инспектор":       85_000,
    "ЦОДД — Нач. смены":         105_000,
    "ЦОДД — Рук. подразделения":  140_000,
})

ALL_JOBS = {**JOBS, **GOV_JOBS}

# ==================== БИЗНЕСЫ (₽) ====================

BUSINESSES = {
    1:  ("Мотель Grand Rock (Москва)", 22_500_000, 315_000),
    2:  ("Центральная АЗС", 25_200_000, 342_000),
    3:  ("Центральный Автосервис (СТО+Мойка)", 27_000_000, 360_000),
    4:  ("Центральный Супермаркет", 135_000_000, 945_000),
    5:  ("McDonald's", 45_000_000, 585_000),
    6:  ("Ресторан быстрого питания (Питер)", 67_500_000, 675_000),
    7:  ("АЗС WAVERIK", 85_500_000, 855_000),
    8:  ("Карго Порт", 405_000_000, 1_620_000),
    9:  ("Автосервис CPM (тюнинг)", 63_000_000, 720_000),
    10: ("Рекламная вывеска Тип 1", 3_780_000, 72_000),
    11: ("Вендинговый аппарат Тип 1", 1_350_000, 27_000),
    12: ("Тележка с напитками Тип 1", 1_665_000, 31_500),
    13: ("Тележка с напитками Тип 2", 1_665_000, 31_500),
    14: ("Рекламная вывеска Тип 2", 3_780_000, 72_000),
    15: ("Рекламная вывеска Тип 3", 3_780_000, 72_000),
    16: ("Рекламная вывеска Тип 4", 3_780_000, 72_000),
    17: ("Вендинговый аппарат Тип 2", 1_350_000, 27_000),
    18: ("Рекламный баннер (остановка)", 1_665_000, 27_000),
    19: ("Мини-маркет Small Way", 9_000_000, 225_000),
    20: ("Парковка Berlin Safe-Stop", 27_000_000, 315_000),
    21: ("Отель & Resort", 162_000_000, 1_035_000),
    22: ("Кофейня Central Kaffe", 81_000_000, 765_000),
    23: ("ТРЦ Schuppig Center", 135_000_000, 945_000),
    24: ("Частная парковка", 36_000_000, 405_000),
    25: ("Автозапчасти", 62_100_000, 585_000),
    26: ("Автозаправка-мойка", 36_000_000, 360_000),
    27: ("Mechanis PRO (СТО)", 40_500_000, 450_000),
    28: ("Супермаркет", 29_160_000, 342_000),
    29: ("Рекламный баннер Тип 2", 27_000, 9_000),
    30: ("Рекламный баннер Тип 3", 27_000, 9_000),
    31: ("Автосервис TASSIMOV", 67_500_000, 810_000),
    32: ("Заправка (пригород)", 22_500_000, 342_000),
    33: ("Заправка (магистраль)", 34_200_000, 405_000),
    34: ("Заправка (элитный посёлок)", 36_900_000, 450_000),
    35: ("Рекламная вывеска (регион)", 2_340_000, 27_000),
    36: ("Уличное кафе STREETFOOD", 30_600_000, 315_000),
    37: ("Мотель RTT", 52_200_000, 540_000),
    38: ("АЗС (пригород)", 33_300_000, 405_000),
    39: ("Паркинг GROUND", 76_500_000, 765_000),
    40: ("McDonald's (Центр)", 43_200_000, 585_000),
    41: ("СТО (малое)", 22_500_000, 315_000),
    42: ("Заправка", 35_550_000, 450_000),
    43: ("Шиномонтаж на колёсах Тип 1", 5_850_000, 108_000),
    44: ("Шиномонтаж на колёсах Тип 2", 5_850_000, 108_000),
    45: ("Шиномонтаж на колёсах Тип 3", 5_850_000, 108_000),
    46: ("Шиномонтаж на колёсах Тип 4", 5_850_000, 108_000),
    47: ("СТО", 41_400_000, 540_000),
    48: ("АЗС", 40_500_000, 585_000),
}

# ==================== НЕДВИЖИМОСТЬ (₽) ====================

APARTMENTS = {
    1:  ("Хостел / комната", 675_000),
    2:  ("1-комнатная квартира", 2_250_000),
    3:  ("Дом / апартаменты", 4_500_000),
    4:  ("Luxury Studio (элитный небоскрёб)", 9_000_000),
    5:  ("Посёлок с частными домами", 4_050_000),
    6:  ("Современный многоквартирный дом", 6_750_000),
    7:  ("Квартира старого фонда", 1_107_000),
    8:  ("Посёлок (бюджетный район)", 3_150_000),
    9:  ("Luxury Studio Санкт-Петербург", 13_500_000),
    10: ("Апартаменты Среднего класса", 9_000_000),
    11: ("Апартаменты Business класса Москва", 80_100_000),
    12: ("Апартаменты Среднего класса (Север)", 16_200_000),
    13: ("Апартаменты Business класса Регион", 40_500_000),
    14: ("Апартаменты Среднего класса (город)", 17_100_000),
    15: ("Апартаменты ELITE класса", 162_000_000),
    16: ("Апартаменты Среднего класса (окраина)", 7_200_000),
    17: ("Квартирный дом эконом класса", 3_600_000),
    18: ("Квартирный дом с кофейней", 3_600_000),
    19: ("Элитные дома (пригород Москвы)", 162_000_000),
}

# ==================== КРИПТО БИРЖА ====================
# Данные и хендлеры вынесены в отдельный модуль crypto_exchange.py
# Здесь импортируем только то, что нужно для rates_updater и совместимости

import crypto_exchange as _cx
from crypto_exchange import router as crypto_router

# Псевдонимы для обратной совместимости (используются в логах/командах)
CRYPTO_PRICES = _cx.CRYPTO_PRICES   # mutable dict — изменения видны везде

# ==================== ФОНОВЫЕ ЗАДАЧИ ====================

# ==================== ТОТАЛИЗАТОР — константы и фоновый апдейтер ====================

TOTO_LEAGUES = [
    ("4328", "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "АПЛ"),
    ("4480", "🇷🇺",       "РПЛ"),
    ("4335", "🇪🇸",       "Ла Лига"),
    ("4331", "🇩🇪",       "Бундеслига"),
    ("4332", "🇮🇹",       "Серия А"),
    ("4334", "🇫🇷",       "Лига 1"),
]
TOTO_API = "https://www.thesportsdb.com/api/v1/json/3"
_TOTO_BET_AMOUNTS = [1_000, 5_000, 10_000, 25_000, 50_000, 100_000]
_TOTO_BET_LABELS  = {"1": "П1 (хозяева)", "X": "Х (ничья)", "2": "П2 (гости)"}
_TOTO_STATUS_ICON = {"pending": "⏳", "won": "✅", "lost": "❌", "refunded": "↩️"}


def _toto_odds(match_id: str) -> tuple[float, float, float]:
    """Deterministic odds seeded by match ID so they never change between fetches."""
    seed = int(hashlib.md5(str(match_id).encode()).hexdigest()[:8], 16)
    rng  = random.Random(seed)
    return (
        round(rng.uniform(1.40, 2.70), 2),
        round(rng.uniform(2.80, 3.80), 2),
        round(rng.uniform(1.50, 2.90), 2),
    )


def _toto_parse_time(date_s: str, time_s) -> int:
    ts = (time_s or "20:00:00")[:8]
    try:
        dt = datetime.strptime(f"{date_s} {ts}", "%Y-%m-%d %H:%M:%S")
        return int(dt.replace(tzinfo=timezone.utc).timestamp())
    except Exception:
        try:
            return int(datetime.strptime(date_s, "%Y-%m-%d")
                       .replace(tzinfo=timezone.utc, hour=20).timestamp())
        except Exception:
            return int(time.time()) + 86400


async def _toto_fetch_matches(session: aiohttp.ClientSession) -> list:
    result = []
    for lid, flag, name in TOTO_LEAGUES:
        try:
            url = f"{TOTO_API}/eventsnextleague.php?id={lid}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
            for ev in (data.get("events") or []):
                mid  = str(ev.get("idEvent") or "")
                home = ev.get("strHomeTeam") or ""
                away = ev.get("strAwayTeam") or ""
                date = ev.get("dateEvent") or ""
                if not (mid and home and away and date):
                    continue
                oh, od, oa = _toto_odds(mid)
                result.append({
                    "match_id": mid, "league": name, "league_flag": flag,
                    "home_team": home, "away_team": away,
                    "match_time": _toto_parse_time(date, ev.get("strTime")),
                    "odds_home": oh, "odds_draw": od, "odds_away": oa,
                })
        except Exception:
            pass
    return result


async def _toto_resolve_finished(session: aiohttp.ClientSession):
    pending = set(db.toto_get_pending_for_resolution())
    if not pending:
        return
    for lid, _flag, _name in TOTO_LEAGUES:
        try:
            url = f"{TOTO_API}/eventspastleague.php?id={lid}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
            for ev in (data.get("events") or []):
                mid = str(ev.get("idEvent") or "")
                if mid not in pending:
                    continue
                hs_raw = ev.get("intHomeScore")
                as_raw = ev.get("intAwayScore")
                if hs_raw is None or as_raw is None:
                    continue
                try:
                    db.toto_resolve_match(mid, int(hs_raw), int(as_raw))
                    pending.discard(mid)
                except Exception:
                    pass
        except Exception:
            pass


async def totalizator_updater():
    """Каждые 15 минут: тянем новые матчи + проверяем результаты сыгранных."""
    await asyncio.sleep(20)          # дать боту инициализироваться
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                matches = await _toto_fetch_matches(session)
                if matches:
                    db.toto_upsert_matches(matches)
                await _toto_resolve_finished(session)
        except Exception:
            pass
        await asyncio.sleep(900)     # 15 минут


async def rates_updater():
    """Обновляет USD/RUB каждые 5 мин, крипту через CoinGecko каждые 60 сек."""
    usd_rub_tick = 0
    while True:
        await asyncio.sleep(60)
        try:
            async with aiohttp.ClientSession() as session:
                # === Крипто: каждые 60 сек через CoinGecko ===
                await _cx.update_crypto_rates(session)

                # === USD/RUB: каждые 5 мин (каждый 5-й тик) ===
                usd_rub_tick += 1
                if usd_rub_tick >= 5:
                    usd_rub_tick = 0
                    try:
                        async with session.get(
                            "https://api.exchangerate-api.com/v4/latest/USD",
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as resp:
                            data = await resp.json()
                            rub = float(data["rates"]["RUB"])
                            if 50 < rub < 200:
                                config.USD_RUB_RATE = rub
                                global CARS
                                CARS = {cid: (n, car_price_rub(cid))
                                        for cid, (n, _) in CARS_USD.items()}
                    except Exception:
                        pass
        except Exception:
            pass


# ==================== ВСПОМОГАТЕЛЬНЫЕ СЛОВАРИ ====================

PENDING_REGISTRATIONS: dict = {}
PENDING_SALES: dict = {}


# ==================== FSM ====================

class Registration(StatesGroup):
    rp_name    = State()
    cpm_id     = State()
    appearance = State()
    source     = State()

class AddCarFSM(StatesGroup):
    name    = State()
    price   = State()
    description = State()
    specs   = State()
    confirm = State()

class AddBizFSM(StatesGroup):
    name    = State()
    price   = State()
    income  = State()
    description = State()
    confirm = State()

class AddAptFSM(StatesGroup):
    name    = State()
    price   = State()
    description = State()
    confirm = State()

class AddPromoFSM(StatesGroup):
    code     = State()
    amount   = State()
    max_uses = State()
    confirm  = State()

class DisablePromoFSM(StatesGroup):
    code = State()

class FineIssueFSM(StatesGroup):
    amount = State()
    article = State()
    reason  = State()

class DailyBonusAdminFSM(StatesGroup):
    choose_action = State()   # unused, kept for future extension
    enter_day     = State()   # waiting for day number
    enter_type    = State()   # waiting for reward type selection
    enter_value   = State()   # waiting for reward value
    enter_desc    = State()   # waiting for description
    confirm_del   = State()   # confirm deletion


# ==================== ХЕЛПЕРЫ ====================

def fmt(n):
    """Форматирует сумму в рублях."""
    return f"{int(n):,}".replace(",", " ") + " ₽"


def is_admin(uid):
    return uid in config.ADMIN_IDS or db.is_db_admin(uid)


def is_founder(uid):
    return uid in config.ADMIN_IDS


def is_mvd(uid):
    return is_admin(uid) or db.is_mvd_employee(uid)


def is_gov(uid):
    return is_admin(uid) or db.is_gov_employee(uid)


GARAGE_SLOT_PRICES = {
    3: 100_000,
    4: 150_000,
    5: 200_000,
    6: 250_000,
    7: 300_000,
    8: 400_000,
}

LICENSE_PRICE = 18_000  # 200 € → ₽

PLATE_PRICE = 18_000    # 200 € → ₽


def info_keyboard(uid: int):
    u = str(uid)
    rows = [
        [
            InlineKeyboardButton(text="🚗 Гараж", callback_data=f"list_cars|{u}"),
            InlineKeyboardButton(text="💼 Работа", callback_data=f"list_jobs|{u}"),
        ],
        [
            InlineKeyboardButton(text="🏢 Бизнесы", callback_data=f"list_biz|{u}"),
            InlineKeyboardButton(text="🏠 Недвижимость", callback_data=f"list_apts|{u}"),
        ],
        [
            InlineKeyboardButton(text="🏛️ Организации", callback_data=f"list_orgs|{u}"),
            InlineKeyboardButton(text="🏦 Банк", callback_data=f"bank_menu|{u}"),
        ],
        [
            InlineKeyboardButton(text="📋 Штрафы", callback_data=f"my_fines|{u}"),
            InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data=f"daily_bonus|{u}"),
        ],
        [
            InlineKeyboardButton(text="💱 Крипто Биржа", callback_data=f"cx_menu|{u}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_keyboard(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_info|{uid}")]
    ])


def _parse_menu_owner(data: str):
    if "|" in data:
        try:
            return int(data.split("|", 1)[1])
        except Exception:
            return None
    return None


async def _assert_owner(callback: types.CallbackQuery):
    owner_uid = _parse_menu_owner(callback.data)
    if owner_uid is not None and callback.from_user.id != owner_uid:
        await callback.answer("⛔ Это меню принадлежит другому игроку.", show_alert=True)
        return None
    return owner_uid if owner_uid is not None else callback.from_user.id


def check_user(user):
    if not user:
        return "not_registered"
    if user[9]:
        return "banned"
    return "ok"


def parse_mentioned_username(text: str) -> str | None:
    parts = text.split()
    for part in parts:
        if part.startswith("@") and len(part) > 1:
            return part[1:]
    return None


def _resolve_user_by_nick(nick: str):
    nick = nick.lstrip("@")
    if nick.isdigit():
        return db.get_user(int(nick))
    return db.get_user_by_username(nick)


# ==================== РЕГИСТРАЦИЯ ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user = db.get_user(message.from_user.id)
    if user:
        await message.answer("✅ Вы уже зарегистрированы!\n\nНапишите <b>инфо</b> для просмотра профиля.", parse_mode="HTML")
        return
    await message.answer(
        "🎮 <b>Добро пожаловать в Advance RP!</b>\n\n"
        "Начнём регистрацию.\n\n"
        "1️⃣ Введи своё RP имя и фамилию:\n"
        "<i>Пример: Иван Петров</i>",
        parse_mode="HTML"
    )
    await state.set_state(Registration.rp_name)


@dp.message(Registration.rp_name)
async def reg_rp_name(message: types.Message, state: FSMContext):
    await state.update_data(rp_name=message.text.strip())
    await message.answer(
        "2️⃣ Введи свой ID в Car Parking Multiplayer:\n"
        "<i>(цифровой игровой ID)</i>",
        parse_mode="HTML"
    )
    await state.set_state(Registration.cpm_id)


@dp.message(Registration.cpm_id)
async def reg_cpm_id(message: types.Message, state: FSMContext):
    await state.update_data(cpm_id=message.text.strip())
    await message.answer(
        "3️⃣ Опиши свою внешность:\n\n"
        "<i>Пример:\nРост: 180 см\nТелосложение: спортивное\nОсобые приметы: tattoo на шее</i>",
        parse_mode="HTML"
    )
    await state.set_state(Registration.appearance)


@dp.message(Registration.appearance)
async def reg_appearance(message: types.Message, state: FSMContext):
    await state.update_data(appearance=message.text.strip())
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="TikTok", callback_data="reg_source_tiktok"),
            InlineKeyboardButton(text="Telegram", callback_data="reg_source_telegram"),
        ],
        [
            InlineKeyboardButton(text="Рекомендация друга", callback_data="reg_source_friend"),
            InlineKeyboardButton(text="Другое", callback_data="reg_source_other"),
        ],
    ])
    await message.answer("4️⃣ Откуда ты узнал о нас?", reply_markup=kb)
    await state.set_state(Registration.source)


@dp.callback_query(Registration.source, F.data.startswith("reg_source_"))
async def reg_source(callback: types.CallbackQuery, state: FSMContext):
    source_map = {
        "reg_source_tiktok":   "TikTok",
        "reg_source_telegram": "Telegram",
        "reg_source_friend":   "Рекомендация друга",
        "reg_source_other":    "Другое",
    }
    source = source_map.get(callback.data, "Другое")
    data = await state.get_data()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)

    rp_name    = data["rp_name"]
    cpm_id     = data["cpm_id"]
    appearance = data["appearance"]
    uid        = callback.from_user.id
    username   = callback.from_user.username or callback.from_user.first_name

    if not config.REGISTRATION_CHAT_ID:
        db.register_user(uid, username, cpm_id, rp_name, appearance, source)
        await callback.message.answer(
            f"✅ <b>Регистрация завершена!</b>\n\n"
            f"👤 RP имя: {rp_name}\n"
            f"🆔 CPM ID: {cpm_id}\n"
            f"🌐 Источник: {source}\n"
            f"💰 Стартовый баланс: {fmt(config.START_BALANCE)}\n\n"
            f"Напишите <b>инфо</b> для просмотра профиля.",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    PENDING_REGISTRATIONS[uid] = {
        "rp_name": rp_name, "cpm_id": cpm_id,
        "appearance": appearance, "source": source, "username": username,
    }

    text = (
        f"📋 <b>Advance RP — Новая анкета</b>\n\n"
        f"👤 TG: @{username} (ID: {uid})\n"
        f"🎮 RP имя: {rp_name}\n"
        f"🆔 CPM ID: {cpm_id}\n"
        f"🪞 Внешность:\n{appearance}\n"
        f"🌐 Источник: {source}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_reg_{uid}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_reg_{uid}"),
    ]])
    try:
        send_kwargs = dict(chat_id=config.REGISTRATION_CHAT_ID, text=text, reply_markup=kb, parse_mode="HTML")
        if config.REGISTRATION_TOPIC_ID:
            send_kwargs["message_thread_id"] = config.REGISTRATION_TOPIC_ID
        await bot.send_message(**send_kwargs)
    except Exception:
        db.register_user(uid, username, cpm_id, rp_name, appearance, source)
        await callback.message.answer(
            f"✅ <b>Регистрация завершена!</b>\n\n"
            f"👤 RP имя: {rp_name}\n"
            f"💰 Стартовый баланс: {fmt(config.START_BALANCE)}",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await callback.message.answer(
        f"📋 Анкета отправлена на рассмотрение!\n\n"
        f"🎮 RP имя: {rp_name}\n"
        f"🆔 CPM ID: {cpm_id}\n\n"
        f"⏳ Ожидайте одобрения от администратора."
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("approve_reg_"))
async def cb_approve_reg(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    uid = int(callback.data.split("_")[2])
    pending = PENDING_REGISTRATIONS.pop(uid, None)
    if not pending:
        if db.get_user(uid):
            await callback.answer("✅ Уже одобрено", show_alert=True)
        else:
            await callback.answer("❌ Анкета не найдена (устарела)", show_alert=True)
        return
    db.register_user(uid, pending["username"], pending["cpm_id"], pending["rp_name"],
                     pending["appearance"], pending["source"])
    try:
        await bot.send_message(
            uid,
            f"✅ <b>Advance RP — Анкета одобрена!</b>\n\n"
            f"🎮 RP имя: {pending['rp_name']}\n"
            f"🆔 CPM ID: {pending['cpm_id']}\n"
            f"💰 Стартовый баланс: {fmt(config.START_BALANCE)}\n\n"
            f"Напишите <b>инфо</b> для просмотра профиля.",
            parse_mode="HTML"
        )
    except Exception:
        pass
    admin_name = callback.from_user.username or callback.from_user.first_name
    await callback.message.edit_text(callback.message.text + f"\n\n✅ Одобрено: @{admin_name}")
    await callback.answer("✅ Игрок зарегистрирован!")


@dp.callback_query(F.data.startswith("reject_reg_"))
async def cb_reject_reg(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    uid = int(callback.data.split("_")[2])
    pending = PENDING_REGISTRATIONS.pop(uid, None)
    if not pending:
        await callback.answer("❌ Анкета не найдена", show_alert=True)
        return
    try:
        await bot.send_message(uid, "❌ Advance RP — Анкета отклонена.\n\nОбратитесь к администратору.")
    except Exception:
        pass
    admin_name = callback.from_user.username or callback.from_user.first_name
    await callback.message.edit_text(callback.message.text + f"\n\n❌ Отклонено: @{admin_name}")
    await callback.answer("❌ Анкета отклонена")


# ==================== ПРОВЕРКА ИГРОВОГО ЧАТА ====================

async def _require_game_chat(message: types.Message) -> bool:
    if is_admin(message.from_user.id):
        return True
    if message.chat.type == "private" or (config.GAME_CHAT_ID and message.chat.id != config.GAME_CHAT_ID):
        await message.answer("⛔ Эта команда доступна только в игровом чате.")
        return False
    return True


# ==================== ПРОФИЛЬ ====================

def build_profile_text(user):
    uid, username, spm_id, game_name, balance, bank, btc, job, last_salary, banned, license_, garage_slots, x2, credit, bank_last_updated, biz_income_time, *extra = user
    appearance = extra[0] if len(extra) > 0 else ""

    gov_emp = db.get_gov_employee(uid)
    mvd_emp = db.get_mvd_employee(uid)

    gov_badge = ""
    if gov_emp:
        gov_badge = f"\n🏛️ Правительство: {gov_emp['role']}"
    mvd_badge = ""
    if mvd_emp:
        mvd_badge = f"\n👮 МВД: {mvd_emp['role']}"

    text = (
        f"🎮 <b>Advance RP</b> — Профиль\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 RP имя: <b>{game_name}</b>\n"
        f"🆔 CPM ID: {spm_id}\n"
        f"📱 TG: @{username}\n"
    )
    if appearance:
        text += f"🪞 Внешность: {appearance}\n"

    text += (
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Баланс: <b>{fmt(balance)}</b>\n"
        f"🏦 Банк: {fmt(bank)}\n"
        f"💼 Работа: {job if job else '— Безработный'}"
    )

    text += gov_badge + mvd_badge

    orgs = db.get_user_orgs(uid)
    player_orgs = db.get_player_orgs_for_user(uid)
    if orgs or player_orgs:
        text += "\n━━━━━━━━━━━━━━━━━━━"
        for org_type, is_owner in orgs:
            info = db.ORG_DISPLAY.get(org_type)
            if info:
                icon, _ = info
                org_name = db.get_org_name(org_type)
                role = "👑 Владелец" if is_owner else "👤 Участник"
                text += f"\n{icon} {org_name} — {role}"
        for po in player_orgs:
            role = "👑 Лидер" if po["owner_uid"] == uid else "👤 Участник"
            text += f"\n{po['icon']} {po['name']} — {role}"
        text += "\n━━━━━━━━━━━━━━━━━━━"

    credit = db.get_credit(uid)
    if credit > 0:
        text += f"\n\n📉 Кредит: {fmt(credit)}"

    fines = db.get_fines(uid, unpaid_only=True)
    if fines:
        total_fines = sum(f[1] for f in fines)
        text += f"\n⚠️ Неоплаченные штрафы: {fmt(total_fines)}"

    return text


@dp.message(lambda m: m.text and m.text.lower() == "инфо")
async def info_cmd(message: types.Message):
    if not await _require_game_chat(message):
        return
    user = db.get_user(message.from_user.id)
    status = check_user(user)
    if status == "not_registered":
        await message.answer("❌ Вы не зарегистрированы. Напишите /start")
        return
    if status == "banned":
        await message.answer("⛔ Вы заблокированы.")
        return
    await message.answer(build_profile_text(user), parse_mode="HTML", reply_markup=info_keyboard(message.from_user.id))


# ==================== БАЛАНС ====================

@dp.message(lambda m: m.text and m.text.lower() in ["б", "баланс"])
async def balance_cmd(message: types.Message):
    if not await _require_game_chat(message):
        return
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Напишите /start")
        return
    await message.answer(
        f"💰 Баланс: <b>{fmt(user[4])}</b>\n"
        f"🏦 Банк: {fmt(user[5])}",
        parse_mode="HTML"
    )


# ==================== ЗАРПЛАТА ====================

@dp.message(lambda m: m.text and m.text.lower() in ["зп", "зарплата"])
async def salary_cmd(message: types.Message):
    if message.chat.type == "private":
        await message.answer("⛔ Зарплату можно получить только в игровом чате.")
        return
    if config.GAME_CHAT_ID and message.chat.id != config.GAME_CHAT_ID:
        await message.answer("⛔ Зарплату можно получить только в игровом чате.")
        return
    user = db.get_user(message.from_user.id)
    status = check_user(user)
    if status == "not_registered":
        await message.answer("❌ Вы не зарегистрированы. Напишите /start")
        return
    if status == "banned":
        await message.answer("⛔ Вы заблокированы.")
        return

    uid, username, cpm_id, game_name, balance, bank, btc, job, last_salary, banned, *_ = user

    if not job:
        await message.answer("❌ У вас нет работы. Обратитесь к администратору.")
        return

    now = int(time.time())
    if now - last_salary < config.SALARY_COOLDOWN:
        remaining = config.SALARY_COOLDOWN - (now - last_salary)
        mins = remaining // 60
        secs = remaining % 60
        await message.answer(f"⏰ Зарплата будет доступна через {mins} мин. {secs} сек.")
        return

    salary = ALL_JOBS.get(job, 0)
    if salary == 0:
        await message.answer("❌ Работа не найдена. Обратитесь к администратору.")
        return

    multiplier = 2 if db.has_x2(uid) else 1
    final_salary = salary * multiplier

    db.update_balance(uid, final_salary)
    db.update_salary_time(uid)

    x2_text = " (×2 бонус! 🔥)" if multiplier == 2 else ""
    await message.answer(
        f"💵 Вы получили зарплату: <b>+{fmt(final_salary)}</b>{x2_text}\n"
        f"💰 Новый баланс: {fmt(balance + final_salary)}",
        parse_mode="HTML"
    )


@dp.message(lambda m: (
    m.text and
    m.text.lower().startswith("зп ") and
    "@" in m.text and
    not m.text.lower().startswith("зп бизнес")
))
async def salary_mention_cmd(message: types.Message):
    target_username = parse_mentioned_username(message.text)
    if not target_username:
        await message.answer("❌ Формат: зп @никнейм")
        return

    target = db.get_user_by_username(target_username)
    if not target:
        return

    status = check_user(target)
    if status == "banned":
        await message.answer(f"⛔ Игрок @{target_username} заблокирован.")
        return

    uid, username, spm_id, game_name, balance, bank, btc, job, last_salary, banned, *_ = target

    if not job:
        await message.answer(f"❌ У @{target_username} нет работы.")
        return

    now = int(time.time())
    if now - last_salary < config.SALARY_COOLDOWN:
        remaining = config.SALARY_COOLDOWN - (now - last_salary)
        mins = remaining // 60
        secs = remaining % 60
        await message.answer(f"⏰ @{target_username}, зарплата будет доступна через {mins} мин. {secs} сек.")
        return

    salary = ALL_JOBS.get(job, 0)
    if salary == 0:
        await message.answer(f"❌ Работа игрока @{target_username} не найдена.")
        return

    multiplier = 2 if db.has_x2(uid) else 1
    final_salary = salary * multiplier

    db.update_balance(uid, final_salary)
    db.update_salary_time(uid)

    x2_text = " (×2 бонус! 🔥)" if multiplier == 2 else ""
    await message.answer(
        f"💵 @{target_username} получил зарплату: <b>+{fmt(final_salary)}</b>{x2_text}\n"
        f"💼 Должность: {job}\n"
        f"💰 Новый баланс: {fmt(balance + final_salary)}",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            uid,
            f"💵 Вам выдали зарплату: <b>+{fmt(final_salary)}</b>{x2_text}\n"
            f"💼 Должность: {job}\n"
            f"💰 Новый баланс: {fmt(balance + final_salary)}",
            parse_mode="HTML"
        )
    except Exception:
        pass


@dp.message(lambda m: (
    m.text and
    m.text.lower().startswith("зп бизнес") and
    "@" in m.text
))
async def salary_and_biz_cmd(message: types.Message):
    target_username = parse_mentioned_username(message.text)
    if not target_username:
        await message.answer("❌ Формат: зп бизнес @никнейм")
        return

    target = db.get_user_by_username(target_username)
    if not target:
        return

    status = check_user(target)
    if status == "banned":
        await message.answer(f"⛔ Игрок @{target_username} заблокирован.")
        return

    uid, username, spm_id, game_name, balance, bank, btc, job, last_salary, banned, *_ = target
    multiplier = 2 if db.has_x2(uid) else 1
    x2_text = " (×2 бонус! 🔥)" if multiplier == 2 else ""
    now = int(time.time())
    lines = []
    total_earned = 0

    if job:
        salary = ALL_JOBS.get(job, 0)
        if salary > 0:
            if now - last_salary < config.SALARY_COOLDOWN:
                rem = config.SALARY_COOLDOWN - (now - last_salary)
                lines.append(f"⏰ Зарплата: ещё {rem // 60} мин. {rem % 60} сек.")
            else:
                final_sal = salary * multiplier
                db.update_balance(uid, final_sal)
                db.update_salary_time(uid)
                total_earned += final_sal
                lines.append(f"💵 Зарплата ({job}): +{fmt(final_sal)}")
    else:
        lines.append("💼 Работа: нет")

    bizs = db.get_businesses(uid)
    if bizs:
        last_biz_time = db.get_biz_income_time(uid)
        if now - last_biz_time < config.BIZ_COOLDOWN:
            rem = config.BIZ_COOLDOWN - (now - last_biz_time)
            lines.append(f"⏰ Бизнес: ещё {rem // 60} мин. {rem % 60} сек.")
        else:
            total_inc = sum(inc for _, inc in bizs)
            final_inc = total_inc * multiplier
            tax_amount = round(final_inc * db.TAX_RATE)
            db.update_balance(uid, final_inc)
            db.update_biz_income_time(uid)
            db.add_tax_debt(uid, tax_amount)
            total_earned += final_inc
            biz_lines = "\n".join(f"  • {name}: +{fmt(inc * multiplier)}" for name, inc in bizs)
            lines.append(f"🏢 Бизнесы:\n{biz_lines}\n  📈 Итого бизнес: +{fmt(final_inc)}\n  🏛 Налог (35%): {fmt(tax_amount)} добавлен в долг")
    else:
        lines.append("🏢 Бизнесов нет")

    new_balance = balance + total_earned
    report = "\n".join(lines)
    await message.answer(
        f"💰 <b>Advance RP — Выплата @{target_username}</b>{x2_text}\n\n"
        f"{report}\n\n"
        f"{'📊 Итого получено: +' + fmt(total_earned) if total_earned else '⚠️ Ничего не выдано'}\n"
        f"💵 Баланс: {fmt(new_balance)}",
        parse_mode="HTML"
    )

    if total_earned:
        try:
            await bot.send_message(uid,
                f"💰 <b>Advance RP — Вам выплачено</b>{x2_text}\n\n{report}\n\n"
                f"📊 Итого: +{fmt(total_earned)}\n💵 Баланс: {fmt(new_balance)}",
                parse_mode="HTML"
            )
        except Exception:
            pass


@dp.message(lambda m: (
    m.text and
    m.text.lower().startswith("бизнес ") and
    "@" in m.text
))
async def business_only_cmd(message: types.Message):
    target_username = parse_mentioned_username(message.text)
    if not target_username:
        await message.answer("❌ Формат: бизнес @никнейм")
        return

    target = db.get_user_by_username(target_username)
    if not target:
        return

    status = check_user(target)
    if status == "banned":
        await message.answer(f"⛔ Игрок @{target_username} заблокирован.")
        return

    uid, username, spm_id, game_name, balance, bank, btc, job, last_salary, banned, *_ = target
    multiplier = 2 if db.has_x2(uid) else 1
    x2_text = " (×2 бонус! 🔥)" if multiplier == 2 else ""
    now = int(time.time())

    bizs = db.get_businesses(uid)
    if not bizs:
        await message.answer(f"🏢 У @{target_username} нет бизнесов.")
        return

    last_biz_time = db.get_biz_income_time(uid)
    if now - last_biz_time < config.BIZ_COOLDOWN:
        rem = config.BIZ_COOLDOWN - (now - last_biz_time)
        await message.answer(f"⏰ @{target_username}, бизнес-доход будет доступен через {rem // 60} мин. {rem % 60} сек.")
        return

    total_income = sum(inc for _, inc in bizs)
    final_income = total_income * multiplier
    tax_amount = round(final_income * db.TAX_RATE)
    db.update_balance(uid, final_income)
    db.update_biz_income_time(uid)
    db.add_tax_debt(uid, tax_amount)

    biz_lines = "\n".join(f"  • {name}: +{fmt(inc * multiplier)}" for name, inc in bizs)
    await message.answer(
        f"🏢 @{target_username} получил доход от бизнесов{x2_text}:\n\n"
        f"{biz_lines}\n\n"
        f"📈 Итого: +{fmt(final_income)}\n"
        f"🏛 Налог (35%): {fmt(tax_amount)} добавлен в долг\n"
        f"💰 Новый баланс: {fmt(balance + final_income)}",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(uid,
            f"🏢 <b>Advance RP</b> — Доход от бизнесов{x2_text}:\n\n{biz_lines}\n\n"
            f"📈 Итого: +{fmt(final_income)}\n💰 Новый баланс: {fmt(balance + final_income)}",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ==================== ПЕРЕВОДЫ ====================

@dp.message(lambda m: m.text and m.text.lower().startswith("дать ") and "@" in m.text and m.reply_to_message is None and (m.from_user is None or not is_admin(m.from_user.id)))
async def player_give_cmd(message: types.Message):
    user = db.get_user(message.from_user.id)
    status = check_user(user)
    if status == "not_registered":
        await message.answer("❌ Вы не зарегистрированы. Напишите /start")
        return
    if status == "banned":
        await message.answer("⛔ Вы заблокированы.")
        return
    parts = message.text.strip().split()
    try:
        amount = int(parts[1])
        username = next(p for p in parts if p.startswith("@"))[1:]
    except Exception:
        await message.answer("❌ Формат: дать [сумма] @никнейм")
        return
    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше 0")
        return
    balance = user[4]
    if balance < amount:
        await message.answer(f"❌ Недостаточно средств. Ваш баланс: {fmt(balance)}")
        return
    if username.lower() == (message.from_user.username or "").lower():
        await message.answer("❌ Нельзя переводить самому себе")
        return
    target = db.get_user_by_username(username)
    if not target:
        return
    db.update_balance(message.from_user.id, -amount)
    db.update_balance(target[0], amount)
    db.add_log(message.from_user.id, 'transfer', f'→ @{username}', amount)
    sender = message.from_user.username or message.from_user.first_name
    await message.answer(f"✅ Переведено {fmt(amount)} → @{username}")
    try:
        await bot.send_message(target[0], f"💸 Вам перевели {fmt(amount)} от @{sender}")
    except Exception:
        pass


@dp.message(lambda m: m.text and m.text.startswith("+") and len(m.text.split()) >= 2 and m.text[1:].split()[0].isdigit())
async def transfer_cmd(message: types.Message):
    user = db.get_user(message.from_user.id)
    status = check_user(user)
    if status == "not_registered":
        await message.answer("❌ Вы не зарегистрированы. Напишите /start")
        return
    if status == "banned":
        await message.answer("⛔ Вы заблокированы.")
        return
    try:
        parts = message.text.split()
        amount = int(parts[0][1:])
        target_username = parts[1].replace("@", "")
    except Exception:
        await message.answer("❌ Формат: +сумма @никнейм")
        return
    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше 0")
        return
    balance = user[4]
    if balance < amount:
        await message.answer(f"❌ Недостаточно средств. Ваш баланс: {fmt(balance)}")
        return
    target = db.get_user_by_username(target_username)
    if not target:
        return
    if target[0] == message.from_user.id:
        await message.answer("❌ Нельзя переводить самому себе")
        return
    db.update_balance(message.from_user.id, -amount)
    db.update_balance(target[0], amount)
    db.add_log(message.from_user.id, 'transfer', f'→ @{target_username}', amount)
    await message.answer(f"✅ Переведено {fmt(amount)} → @{target_username}")
    try:
        sender = message.from_user.username or message.from_user.first_name
        await bot.send_message(target[0], f"💸 Вам перевели {fmt(amount)} от @{sender}")
    except Exception:
        pass


# ==================== КАЗИНО ====================

CASINO_DAILY_LIMIT = 1000
CASINO_BETS = [500, 1_000, 5_000, 10_000, 20_000, 30_000, 40_000, 50_000]


def _casino_bet_kb():
    rows = []
    for i in range(0, len(CASINO_BETS), 4):
        chunk = CASINO_BETS[i:i+4]
        rows.append([
            InlineKeyboardButton(text=f"{fmt(b)}", callback_data=f"cas_bet|{b}")
            for b in chunk
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _casino_game_kb(bet: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎰 Слоты", callback_data=f"cas_slot|{bet}"),
            InlineKeyboardButton(text="🎲 Кубик", callback_data=f"cas_dice|{bet}"),
        ],
        [InlineKeyboardButton(text="🔙 Изменить ставку", callback_data="cas_back")],
    ])


def _casino_bet_text(user, plays_today: int) -> str:
    balance = user[4]
    remaining = CASINO_DAILY_LIMIT - plays_today
    return (
        f"🎰 <b>КАЗИНО — Advance RP</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Баланс: <b>{fmt(balance)}</b>\n"
        f"🎟 Осталось игр сегодня: <b>{remaining}</b>\n\n"
        f"Выберите ставку:"
    )


def _casino_game_text(user, plays_today: int, bet: int) -> str:
    balance = user[4]
    remaining = CASINO_DAILY_LIMIT - plays_today
    prize = bet * 2
    return (
        f"🎰 <b>КАЗИНО — Advance RP</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Баланс: <b>{fmt(balance)}</b>\n"
        f"🎟 Осталось игр сегодня: <b>{remaining}</b>\n\n"
        f"💰 Ставка: <b>{fmt(bet)}</b>\n"
        f"🎁 Выигрыш: <b>{fmt(prize)}</b>\n\n"
        f"Выберите игру:"
    )


@dp.message(lambda m: m.text and m.text.lower().strip() == "казино")
async def casino_cmd(message: types.Message):
    user = db.get_user(message.from_user.id)
    status = check_user(user)
    if status == "not_registered":
        await message.answer("❌ Вы не зарегистрированы. Напишите /start")
        return
    if status == "banned":
        await message.answer("⛔ Вы заблокированы.")
        return
    today = time.strftime("%Y-%m-%d")
    plays_today = db.get_casino_plays(message.from_user.id, today)
    await message.answer(_casino_bet_text(user, plays_today), parse_mode="HTML", reply_markup=_casino_bet_kb())


@dp.callback_query(F.data == "cas_back")
async def cb_cas_back(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    today = time.strftime("%Y-%m-%d")
    plays_today = db.get_casino_plays(callback.from_user.id, today)
    await callback.message.edit_text(_casino_bet_text(user, plays_today), parse_mode="HTML", reply_markup=_casino_bet_kb())
    await callback.answer()


@dp.callback_query(F.data.startswith("cas_bet|"))
async def cb_cas_bet(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    try:
        bet = int(callback.data.split("|")[1])
    except Exception:
        await callback.answer("❌ Ошибка")
        return
    today = time.strftime("%Y-%m-%d")
    plays_today = db.get_casino_plays(callback.from_user.id, today)
    if plays_today >= CASINO_DAILY_LIMIT:
        await callback.answer("⛔ Лимит игр на сегодня исчерпан", show_alert=True)
        return
    if user[4] < bet:
        await callback.answer(f"❌ Нужно {fmt(bet)}, у вас {fmt(user[4])}", show_alert=True)
        return
    await callback.message.edit_text(_casino_game_text(user, plays_today, bet), parse_mode="HTML", reply_markup=_casino_game_kb(bet))
    await callback.answer()


async def _play_casino(callback: types.CallbackQuery, game: str, bet: int):
    uid = callback.from_user.id
    user = db.get_user(uid)
    if not user:
        await callback.answer("❌ Не зарегистрированы", show_alert=True)
        return
    today = time.strftime("%Y-%m-%d")
    plays_today = db.get_casino_plays(uid, today)
    if plays_today >= CASINO_DAILY_LIMIT:
        await callback.answer("⛔ Лимит игр на сегодня исчерпан", show_alert=True)
        return
    balance = user[4]
    if balance < bet:
        await callback.answer(f"❌ Нужно {fmt(bet)}, у вас {fmt(balance)}", show_alert=True)
        return

    db.increment_casino_plays(uid, today)
    prize = bet * 2

    if game == "slot":
        symbols = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
        reels = [random.choice(symbols) for _ in range(3)]
        win = (reels[0] == reels[1] == reels[2])
        animation = f"{reels[0]} | {reels[1]} | {reels[2]}"
        title = "🎰 СЛОТЫ"
    else:
        roll = random.randint(1, 6)
        dice_emoji = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"][roll - 1]
        win = roll >= 4
        animation = f"{dice_emoji}  ({roll})"
        title = "🎲 КУБИК"

    if win:
        net = prize - bet
        db.update_balance(uid, net)
        new_bal = balance + net
        result = f"🎉 <b>ВЫИГРЫШ!</b>\n💰 +{fmt(prize)}"
    else:
        db.update_balance(uid, -bet)
        new_bal = balance - bet
        result = f"💀 <b>Проигрыш</b>\n💸 −{fmt(bet)}"

    plays_today += 1
    text = (
        f"{title}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"   {animation}\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"{result}\n"
        f"💵 Баланс: <b>{fmt(new_bal)}</b>\n"
        f"🎟 Осталось игр: <b>{CASINO_DAILY_LIMIT - plays_today}</b>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_casino_game_kb(bet))
    await callback.answer("🎉 Победа!" if win else "💀 Не повезло")


@dp.callback_query(F.data.startswith("cas_slot|"))
async def cb_cas_slot(callback: types.CallbackQuery):
    try:
        bet = int(callback.data.split("|")[1])
    except Exception:
        await callback.answer("❌ Ошибка")
        return
    await _play_casino(callback, "slot", bet)


@dp.callback_query(F.data.startswith("cas_dice|"))
async def cb_cas_dice(callback: types.CallbackQuery):
    try:
        bet = int(callback.data.split("|")[1])
    except Exception:
        await callback.answer("❌ Ошибка")
        return
    await _play_casino(callback, "dice", bet)


# ==================== ТОП ====================

@dp.message(lambda m: m.text and m.text.lower() in ["топ", "топ баланс"])
async def top_cmd(message: types.Message):
    players = db.get_top(10)
    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 <b>ТОП ИГРОКОВ ПО БАЛАНСУ</b>\n\n"
    for i, (username, game_name, balance) in enumerate(players, 1):
        icon = medals[i - 1] if i <= 3 else f"{i}."
        text += f"{icon} {game_name} (@{username})\n   💰 {fmt(balance)}\n\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(lambda m: m.text and m.text.lower() == "топ имущество")
async def top_wealth_cmd(message: types.Message):
    all_users = db.get_all_users_info()
    wealth = []
    for uid, username, game_name in all_users:
        car_ids = db.get_car_ids(uid)
        biz_ids = db.get_biz_ids(uid)
        apt_ids = db.get_apt_ids(uid)
        car_val = sum(CARS.get(c, (None, 0))[1] for c in car_ids)
        biz_val = sum(BUSINESSES.get(b, (None, 0, 0))[1] for b in biz_ids)
        apt_val = sum(APARTMENTS.get(a, (None, 0))[1] for a in apt_ids)
        total = car_val + biz_val + apt_val
        wealth.append((username, game_name, total))
    wealth.sort(key=lambda x: x[2], reverse=True)
    top = wealth[:10]
    medals = ["🥇", "🥈", "🥉"]
    text = "🏠 <b>ТОП ИГРОКОВ ПО ИМУЩЕСТВУ</b>\n\n"
    for i, (username, game_name, total) in enumerate(top, 1):
        if total == 0:
            continue
        icon = medals[i - 1] if i <= 3 else f"{i}."
        text += f"{icon} {game_name} (@{username})\n   💎 {fmt(total)}\n\n"
    if text.strip() == "🏠 <b>ТОП ИГРОКОВ ПО ИМУЩЕСТВУ</b>":
        text += "Пока нет игроков с имуществом."
    await message.answer(text, parse_mode="HTML")


# ==================== КУПИТЬ АВТО (РЕАЛЬНЫЙ КУРС) ====================

@dp.message(lambda m: m.text and m.text.lower().startswith("купить авто"))
async def buy_car(message: types.Message):
    user = db.get_user(message.from_user.id)
    status = check_user(user)
    if status != "ok":
        await message.answer("❌ Вы не зарегистрированы." if status == "not_registered" else "⛔ Вы заблокированы.")
        return
    try:
        car_id = int(message.text.split()[2])
    except Exception:
        await message.answer("❌ Формат: купить авто [номер]")
        return
    car = get_car(car_id)
    if not car:
        await message.answer(f"❌ Авто №{car_id} не найдено. Доступны: 1–{max(CARS_USD.keys())}")
        return
    car_name, car_price = car
    balance = user[4]
    garage_slots = db.get_garage_slots(message.from_user.id)
    current_cars = db.get_cars(message.from_user.id)
    if balance < car_price:
        await message.answer(
            f"🚗 <b>{car_name}</b>\n"
            f"💰 Цена: {fmt(car_price)} (курс: {config.USD_RUB_RATE:.1f} ₽/USD)\n\n"
            f"❌ Недостаточно средств. Баланс: {fmt(balance)}",
            parse_mode="HTML"
        )
        return
    if len(current_cars) >= garage_slots:
        await message.answer(
            f"🚗 <b>{car_name}</b>\n\n"
            f"❌ Гараж заполнен ({len(current_cars)}/{garage_slots} мест).\n"
            f"Для покупки дополнительного слота обратитесь к администратору.",
            parse_mode="HTML"
        )
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Купить", callback_data=f"bc_{car_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cbuy_cancel"),
    ]])
    await message.answer(
        f"🚗 <b>{car_name}</b>\n\n"
        f"💰 Цена: <b>{fmt(car_price)}</b>\n"
        f"📈 Курс USD/RUB: {config.USD_RUB_RATE:.2f} ₽\n"
        f"💵 Ваш баланс: {fmt(balance)}\n\n"
        f"Подтвердить покупку?",
        parse_mode="HTML",
        reply_markup=kb
    )


@dp.callback_query(F.data.startswith("bc_"))
async def confirm_buy_car(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    car_id = int(callback.data.split("_")[1])
    car = get_car(car_id)
    if not car:
        await callback.answer("❌ Авто не найдено")
        return
    car_name, car_price = car
    balance = user[4]
    if balance < car_price:
        await callback.answer(f"❌ Недостаточно средств. Нужно {fmt(car_price)}", show_alert=True)
        return
    garage_slots = db.get_garage_slots(callback.from_user.id)
    current_cars = db.get_cars(callback.from_user.id)
    if len(current_cars) >= garage_slots:
        await callback.answer(f"❌ Гараж заполнен ({len(current_cars)}/{garage_slots})", show_alert=True)
        return
    db.update_balance(callback.from_user.id, -car_price)
    db.add_car(callback.from_user.id, car_id, car_name)
    db.add_log(callback.from_user.id, 'buy_car', car_name, car_price)
    await callback.message.edit_text(
        f"🚗 <b>Поздравляем!</b>\n\n"
        f"Вы купили: <b>{car_name}</b>\n"
        f"Потрачено: {fmt(car_price)}\n"
        f"Остаток: {fmt(balance - car_price)}",
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== КУПИТЬ БИЗНЕС ====================

@dp.message(lambda m: m.text and m.text.lower().startswith("купить бизнес"))
async def buy_business(message: types.Message):
    user = db.get_user(message.from_user.id)
    status = check_user(user)
    if status != "ok":
        await message.answer("❌ Вы не зарегистрированы." if status == "not_registered" else "⛔ Вы заблокированы.")
        return
    try:
        biz_id = int(message.text.split()[2])
    except Exception:
        await message.answer("❌ Формат: купить бизнес [номер]")
        return
    if biz_id not in BUSINESSES:
        await message.answer(f"❌ Бизнес №{biz_id} не найден.")
        return
    biz_name, biz_price, biz_income = BUSINESSES[biz_id]
    balance = user[4]
    owner = db.get_biz_owner(biz_id)
    if owner:
        msg = "Вы уже владеете этим бизнесом." if owner == message.from_user.id else "Этот бизнес уже принадлежит другому игроку."
        await message.answer(f"❌ {msg}")
        return
    owned_biz = db.get_businesses(message.from_user.id)
    biz_slots = db.get_biz_slots(message.from_user.id)
    if len(owned_biz) >= biz_slots:
        await message.answer(f"❌ Лимит бизнесов ({len(owned_biz)}/{biz_slots}).")
        return
    if balance < biz_price:
        await message.answer(
            f"🏢 <b>{biz_name}</b>\n💰 Цена: {fmt(biz_price)}\n\n❌ Недостаточно средств. Баланс: {fmt(balance)}",
            parse_mode="HTML"
        )
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Купить", callback_data=f"bb_{biz_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cbuy_cancel"),
    ]])
    await message.answer(
        f"🏢 <b>{biz_name}</b>\n\n"
        f"💰 Цена: <b>{fmt(biz_price)}</b>\n"
        f"📈 Доход: {fmt(biz_income)}/3ч\n"
        f"💵 Ваш баланс: {fmt(balance)}\n\n"
        f"Подтвердить покупку?",
        parse_mode="HTML",
        reply_markup=kb
    )


@dp.callback_query(F.data.startswith("bb_"))
async def confirm_buy_biz(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    biz_id = int(callback.data.split("_")[1])
    if biz_id not in BUSINESSES:
        await callback.answer("❌ Бизнес не найден")
        return
    biz_name, biz_price, biz_income = BUSINESSES[biz_id]
    owner = db.get_biz_owner(biz_id)
    if owner:
        err = "Вы уже владеете этим бизнесом." if owner == callback.from_user.id else "Бизнес уже занят."
        await callback.answer(f"❌ {err}", show_alert=True)
        return
    owned_biz = db.get_businesses(callback.from_user.id)
    biz_slots = db.get_biz_slots(callback.from_user.id)
    if len(owned_biz) >= biz_slots:
        await callback.answer(f"❌ Лимит бизнесов ({len(owned_biz)}/{biz_slots})", show_alert=True)
        return
    balance = user[4]
    if balance < biz_price:
        await callback.answer(f"❌ Недостаточно средств. Нужно {fmt(biz_price)}", show_alert=True)
        return
    db.update_balance(callback.from_user.id, -biz_price)
    db.add_business(callback.from_user.id, biz_id, biz_name, biz_income)
    db.add_log(callback.from_user.id, 'buy_biz', biz_name, biz_price)
    await callback.message.edit_text(
        f"🏢 <b>Поздравляем!</b>\n\n"
        f"Вы купили: <b>{biz_name}</b>\n"
        f"Потрачено: {fmt(biz_price)}\n"
        f"Доход: {fmt(biz_income)}/3ч\n"
        f"Остаток: {fmt(balance - biz_price)}",
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== КУПИТЬ НЕДВИЖИМОСТЬ ====================

@dp.message(lambda m: m.text and m.text.lower().startswith("купить недвижимость"))
async def buy_apartment(message: types.Message):
    user = db.get_user(message.from_user.id)
    status = check_user(user)
    if status != "ok":
        await message.answer("❌ Вы не зарегистрированы." if status == "not_registered" else "⛔ Вы заблокированы.")
        return
    try:
        apt_id = int(message.text.split()[2])
    except Exception:
        await message.answer("❌ Формат: купить недвижимость [номер]")
        return
    if apt_id not in APARTMENTS:
        await message.answer(f"❌ Объект №{apt_id} не найден.")
        return
    apt_name, apt_price = APARTMENTS[apt_id]
    balance = user[4]
    owned_apt = db.get_apartments_full(message.from_user.id)
    apt_slots = db.get_apt_slots(message.from_user.id)
    if len(owned_apt) >= apt_slots:
        await message.answer(f"❌ Лимит недвижимости ({len(owned_apt)}/{apt_slots}).")
        return
    if balance < apt_price:
        await message.answer(
            f"🏠 <b>{apt_name}</b>\n💰 Цена: {fmt(apt_price)}\n\n❌ Недостаточно средств. Баланс: {fmt(balance)}",
            parse_mode="HTML"
        )
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Купить", callback_data=f"ba_{apt_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cbuy_cancel"),
    ]])
    await message.answer(
        f"🏠 <b>{apt_name}</b>\n\n"
        f"💰 Цена: <b>{fmt(apt_price)}</b>\n"
        f"💵 Ваш баланс: {fmt(balance)}\n\n"
        f"Подтвердить покупку?",
        parse_mode="HTML",
        reply_markup=kb
    )


@dp.callback_query(F.data.startswith("ba_"))
async def confirm_buy_apt(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    apt_id = int(callback.data.split("_")[1])
    if apt_id not in APARTMENTS:
        await callback.answer("❌ Квартира не найдена")
        return
    apt_name, apt_price = APARTMENTS[apt_id]
    owned_apt = db.get_apartments_full(callback.from_user.id)
    apt_slots = db.get_apt_slots(callback.from_user.id)
    if len(owned_apt) >= apt_slots:
        await callback.answer(f"❌ Лимит недвижимости ({len(owned_apt)}/{apt_slots})", show_alert=True)
        return
    balance = user[4]
    if balance < apt_price:
        await callback.answer(f"❌ Недостаточно средств. Нужно {fmt(apt_price)}", show_alert=True)
        return
    db.update_balance(callback.from_user.id, -apt_price)
    db.add_apartment(callback.from_user.id, apt_id, apt_name)
    db.add_log(callback.from_user.id, 'buy_apt', apt_name, apt_price)
    await callback.message.edit_text(
        f"🏠 <b>Поздравляем!</b>\n\n"
        f"Вы купили: <b>{apt_name}</b>\n"
        f"Потрачено: {fmt(apt_price)}\n"
        f"Остаток: {fmt(balance - apt_price)}",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "cbuy_cancel")
async def cancel_buy(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Покупка отменена.")
    await callback.answer()


# ==================== БАНК ====================

def _bank_kb(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Внести", callback_data="bank_help_dep"),
            InlineKeyboardButton(text="💸 Вывести", callback_data="bank_help_wd"),
        ],
        [
            InlineKeyboardButton(text="📈 Взять кредит", callback_data="bank_help_cr"),
            InlineKeyboardButton(text="✅ Погасить", callback_data="bank_help_rp"),
        ],
        [InlineKeyboardButton(text="🏛 Налоги", callback_data=f"tax_menu|{uid}")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"bank_menu|{uid}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_info|{uid}")],
    ])


def _bank_text(uid: int) -> str:
    db.apply_bank_interest(uid)
    user = db.get_user(uid)
    balance = user[4]
    bank = user[5]
    credit = db.get_credit(uid)
    dep_day = config.BANK_DEPOSIT_RATE_PER_HOUR * 24 * 100
    cr_day = config.BANK_CREDIT_RATE_PER_HOUR * 24 * 100
    return (
        f"🏦 <b>БАНК — Advance RP</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Наличные: <b>{fmt(balance)}</b>\n"
        f"🏦 На счёте: <b>{fmt(bank)}</b>\n"
        f"📉 Кредит:   <b>{fmt(credit)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📈 Доход по вкладу: <b>+{dep_day:.1f}%</b>/сутки\n"
        f"💢 Кредит растёт: <b>+{cr_day:.1f}%</b>/сутки\n\n"
        f"<b>Команды:</b>\n"
        f"<code>внести [сумма]</code> | <code>вывести [сумма]</code>\n"
        f"<code>кредит [сумма]</code> | <code>погасить [сумма]</code>"
    )


@dp.message(lambda m: m.text and m.text.lower().strip() == "банк")
async def bank_cmd(message: types.Message):
    if not await _require_game_chat(message):
        return
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы.")
        return
    await message.answer(_bank_text(message.from_user.id), parse_mode="HTML", reply_markup=_bank_kb(message.from_user.id))


@dp.callback_query(F.data.startswith("bank_menu"))
async def cb_bank_menu(callback: types.CallbackQuery):
    uid = await _assert_owner(callback)
    if uid is None:
        return
    await callback.message.edit_text(_bank_text(uid), parse_mode="HTML", reply_markup=_bank_kb(uid))
    await callback.answer()


def _tax_menu_kb(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить всё", callback_data=f"tax_pay_all|{uid}")],
        [InlineKeyboardButton(text="🔙 Назад в банк", callback_data=f"bank_menu|{uid}")],
    ])


def _tax_text(uid: int) -> str:
    debt, last_ts = db.get_tax_debt(uid)
    debt_str = fmt(debt) if debt > 0 else "0 ₽"
    last_str = datetime.fromtimestamp(last_ts).strftime("%d.%m %H:%M") if last_ts else "—"
    return (
        f"🏛 <b>Налоги — Advance RP</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📋 Налоговая ставка: <b>35%</b> от дохода бизнеса\n"
        f"💸 Текущий долг: <b>{debt_str}</b>\n"
        f"🕐 Последнее начисление: <b>{last_str}</b>"
    )


@dp.callback_query(F.data.startswith("tax_menu"))
async def cb_tax_menu(callback: types.CallbackQuery):
    uid = await _assert_owner(callback)
    if uid is None:
        return
    await callback.message.edit_text(_tax_text(uid), parse_mode="HTML", reply_markup=_tax_menu_kb(uid))
    await callback.answer()


@dp.callback_query(F.data.startswith("tax_pay_all"))
async def cb_tax_pay_all(callback: types.CallbackQuery):
    uid = await _assert_owner(callback)
    if uid is None:
        return
    debt, _ = db.get_tax_debt(uid)
    if debt <= 0:
        await callback.answer("✅ Долгов нет!", show_alert=True)
        return
    user = db.get_user(uid)
    balance = user[4]
    if balance < debt:
        await callback.answer(f"❌ Недостаточно средств!\nДолг: {fmt(debt)}\nНаличные: {fmt(balance)}", show_alert=True)
        return
    paid = db.pay_tax_debt(uid, debt)
    db.update_balance(uid, -paid)
    db.update_treasury(paid, "tax_payment", uid, f"Налог от uid={uid}")
    await callback.message.edit_text(
        f"✅ Налог оплачен: {fmt(paid)}\n"
        f"💸 Переведено в государственную казну.\n"
        f"💰 Остаток: {fmt(balance - paid)}",
        reply_markup=_tax_menu_kb(uid)
    )
    await callback.answer("✅ Оплачено!")


_BANK_HELP = {
    "bank_help_dep": "💰 Чтобы внести: напишите внести [сумма]",
    "bank_help_wd":  "💸 Чтобы вывести: напишите вывести [сумма]",
    "bank_help_cr":  "📈 Чтобы взять кредит: напишите кредит [сумма]",
    "bank_help_rp":  "✅ Чтобы погасить: напишите погасить [сумма]",
}


@dp.callback_query(lambda c: c.data in _BANK_HELP)
async def cb_bank_help(callback: types.CallbackQuery):
    await callback.answer(_BANK_HELP[callback.data], show_alert=True)


@dp.message(lambda m: m.text and m.text.lower().startswith("внести "))
async def bank_deposit_cmd(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        return
    try:
        amount = int(message.text.split()[1])
        if amount <= 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Формат: внести [сумма]")
        return
    db.apply_bank_interest(message.from_user.id)
    user = db.get_user(message.from_user.id)
    if user[4] < amount:
        await message.answer(f"❌ Недостаточно наличных. У вас: {fmt(user[4])}")
        return
    db.bank_deposit(message.from_user.id, amount)
    await message.answer(_bank_text(message.from_user.id), parse_mode="HTML", reply_markup=_bank_kb(message.from_user.id))


@dp.message(lambda m: m.text and m.text.lower().startswith("вывести "))
async def bank_withdraw_cmd(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        return
    try:
        amount = int(message.text.split()[1])
        if amount <= 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Формат: вывести [сумма]")
        return
    db.apply_bank_interest(message.from_user.id)
    user = db.get_user(message.from_user.id)
    if user[5] < amount:
        await message.answer(f"❌ Недостаточно на счёте. На счёте: {fmt(user[5])}")
        return
    db.bank_withdraw(message.from_user.id, amount)
    await message.answer(_bank_text(message.from_user.id), parse_mode="HTML", reply_markup=_bank_kb(message.from_user.id))


@dp.message(lambda m: m.text and m.text.lower().startswith("кредит "))
async def bank_credit_cmd(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        return
    try:
        amount = int(message.text.split()[1])
        if amount <= 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Формат: кредит [сумма]")
        return
    db.apply_bank_interest(message.from_user.id)
    user = db.get_user(message.from_user.id)
    current_credit = db.get_credit(message.from_user.id)
    max_credit = max(5_000_000, user[4] * config.CREDIT_LIMIT_MULT)
    if current_credit + amount > max_credit:
        await message.answer(
            f"❌ Превышен лимит кредита.\n"
            f"Макс: {fmt(max_credit)}\n"
            f"Уже взято: {fmt(current_credit)}"
        )
        return
    db.take_credit(message.from_user.id, amount)
    await message.answer(
        f"📈 Кредит выдан: <b>+{fmt(amount)}</b>\n⚠️ Не забывайте о процентах!\n\n" + _bank_text(message.from_user.id),
        parse_mode="HTML", reply_markup=_bank_kb(message.from_user.id)
    )


@dp.message(lambda m: m.text and m.text.lower().startswith("погасить "))
async def bank_repay_cmd(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        return
    try:
        amount = int(message.text.split()[1])
        if amount <= 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Формат: погасить [сумма]")
        return
    db.apply_bank_interest(message.from_user.id)
    user = db.get_user(message.from_user.id)
    credit = db.get_credit(message.from_user.id)
    if credit <= 0:
        await message.answer("ℹ️ У вас нет долга.")
        return
    if amount > credit:
        amount = int(credit)
    if user[4] < amount:
        await message.answer(f"❌ Не хватает наличных. У вас: {fmt(user[4])}")
        return
    db.repay_credit(message.from_user.id, amount)
    await message.answer(
        f"✅ Погашено: <b>−{fmt(amount)}</b>\n\n" + _bank_text(message.from_user.id),
        parse_mode="HTML", reply_markup=_bank_kb(message.from_user.id)
    )


# ==================== МОИ АКТИВЫ ====================

@dp.message(lambda m: m.text and m.text.lower() in ["мои авто", "гараж"])
async def my_cars(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы.")
        return
    cars = db.get_cars_full(message.from_user.id)
    has_lic = db.has_license(message.from_user.id)
    lic_text = "✅ Права есть" if has_lic else "❌ Прав нет"
    if not cars:
        await message.answer(f"🚗 У вас нет автомобилей\n{lic_text}\nКупить: купить авто [номер]")
        return
    text = f"🚗 <b>Ваши автомобили:</b>\n🪪 {lic_text}\n\n"
    for i, (db_id, name, token, plate) in enumerate(cars, 1):
        plate_str = plate if plate else "нет номеров"
        text += f"{i}. {name}\n   🔑 {token} | 🔢 {plate_str}\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(lambda m: m.text and m.text.lower() in ["мои бизнесы", "бизнесы"])
async def my_businesses(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы.")
        return
    bizs = db.get_businesses_full(message.from_user.id)
    if not bizs:
        await message.answer("🏢 У вас нет бизнесов\nКупить: купить бизнес [номер]")
        return
    text = "🏢 <b>Ваши бизнесы:</b>\n\n"
    for i, (bid, name, income, token) in enumerate(bizs, 1):
        text += f"{i}. {name}\n   💵 {fmt(income)}/3ч | 🔑 {token}\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(lambda m: m.text and m.text.lower() in ["мои объекты", "недвижимость", "мои квартиры"])
async def my_apts(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы.")
        return
    apts = db.get_apartments_full(message.from_user.id)
    if not apts:
        await message.answer("🏠 У вас нет недвижимости\nКупить: купить недвижимость [номер]")
        return
    text = "🏠 <b>Ваша недвижимость:</b>\n\n"
    for i, (aid, name, token) in enumerate(apts, 1):
        text += f"{i}. {name} | 🔑 {token}\n"
    await message.answer(text, parse_mode="HTML")


# ==================== ИНЛАЙН КНОПКИ ГАРАЖ ====================

def build_garage_kb(uid, cars_full, garage_slots, has_lic):
    buttons = []
    if not has_lic:
        buttons.append([InlineKeyboardButton(
            text=f"🪪 Купить права — {fmt(LICENSE_PRICE)}",
            callback_data="buy_license"
        )])
    for db_id, car_name, token, plate in cars_full:
        buttons.append([InlineKeyboardButton(
            text=f"🚗 {car_name}",
            callback_data=f"car_det_{db_id}"
        )])
    next_slot = garage_slots + 1
    if next_slot in GARAGE_SLOT_PRICES:
        price = GARAGE_SLOT_PRICES[next_slot]
        buttons.append([InlineKeyboardButton(
            text=f"🔓 Доп. место в гараже — {fmt(price)}",
            callback_data=f"buy_slot_{next_slot}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_info|{uid}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.callback_query(F.data.startswith("back_to_info"))
async def cb_back_to_info(callback: types.CallbackQuery):
    uid = await _assert_owner(callback)
    if uid is None:
        return
    user = db.get_user(uid)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    await callback.message.edit_text(build_profile_text(user), parse_mode="HTML", reply_markup=info_keyboard(uid))
    await callback.answer()


async def _show_garage(callback: types.CallbackQuery):
    uid = callback.from_user.id
    cars_full = db.get_cars_full(uid)
    garage_slots = db.get_garage_slots(uid)
    has_lic = db.has_license(uid)
    lic_icon = "✅" if has_lic else "❌"
    text = (
        f"🚗 <b>Ваш гараж ({len(cars_full)}/{garage_slots} мест)</b>\n\n"
        f"🪪 Права: {lic_icon} {'Есть' if has_lic else 'Нет'}\n\n"
    )
    if not cars_full:
        text += "Гараж пустой\n📝 Купить авто: купить авто [номер]"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=build_garage_kb(uid, cars_full, garage_slots, has_lic))


@dp.callback_query(F.data.startswith("list_cars"))
async def cb_cars(callback: types.CallbackQuery):
    uid = await _assert_owner(callback)
    if uid is None:
        return
    user = db.get_user(uid)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    await _show_garage(callback)
    await callback.answer()


@dp.callback_query(F.data == "buy_license")
async def cb_buy_license(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    uid = user[0]
    if db.has_license(uid):
        await callback.answer("✅ У вас уже есть права!", show_alert=True)
        return
    if user[4] < LICENSE_PRICE:
        await callback.answer(f"❌ Недостаточно денег. Нужно {fmt(LICENSE_PRICE)}", show_alert=True)
        return
    db.update_balance(uid, -LICENSE_PRICE)
    db.set_license(uid, True)
    await callback.answer("✅ Права получены!", show_alert=True)
    await _show_garage(callback)


@dp.callback_query(F.data.startswith("car_det_"))
async def cb_car_detail(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    try:
        db_id = int(callback.data.split("_")[2])
    except Exception:
        await callback.answer("❌ Ошибка")
        return
    car = db.get_car_by_dbid(db_id)
    if not car or car[1] != callback.from_user.id:
        await callback.answer("❌ Авто не найдено", show_alert=True)
        return
    cdb_id, uid, car_id, car_name, token, plate = car
    plate_text = f"✅ {plate}" if plate else "❌ Нет номеров"
    text = (
        f"🚗 <b>{car_name}</b>\n\n"
        f"🔑 Токен: {token}\n"
        f"🔢 Номера: {plate_text}"
    )
    buttons = []
    if not plate:
        buttons.append([InlineKeyboardButton(
            text=f"🔢 Купить номера — {fmt(PLATE_PRICE)}",
            callback_data=f"buy_plate_{db_id}"
        )])
    else:
        buttons.append([InlineKeyboardButton(
            text=f"🔄 Перебить номера — {fmt(PLATE_PRICE)}",
            callback_data=f"reroll_plate_{db_id}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="list_cars")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@dp.callback_query(lambda c: c.data and (c.data.startswith("buy_plate_") or c.data.startswith("reroll_plate_")))
async def cb_plate_action(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    parts = callback.data.split("_")
    db_id = int(parts[2])
    car = db.get_car_by_dbid(db_id)
    if not car or car[1] != callback.from_user.id:
        await callback.answer("❌ Авто не найдено", show_alert=True)
        return
    if user[4] < PLATE_PRICE:
        await callback.answer(f"❌ Недостаточно денег. Нужно {fmt(PLATE_PRICE)}", show_alert=True)
        return
    db.update_balance(user[0], -PLATE_PRICE)
    plate = db.gen_ru_plate()
    db.update_car_plate(db_id, plate)
    cdb_id, uid, car_id, car_name, token, _ = car
    text = (
        f"🚗 <b>{car_name}</b>\n\n"
        f"🔑 Токен: {token}\n"
        f"🔢 Номера: ✅ {plate}"
    )
    buttons = [[InlineKeyboardButton(
        text=f"🔄 Перебить номера — {fmt(PLATE_PRICE)}",
        callback_data=f"reroll_plate_{db_id}"
    )], [InlineKeyboardButton(text="🔙 Назад", callback_data="list_cars")]]
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer(f"✅ Номера: {plate}")


@dp.callback_query(F.data.startswith("buy_slot_"))
async def cb_buy_garage_slot(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    uid = user[0]
    balance = user[4]
    slot_num = int(callback.data.split("_")[2])
    price = GARAGE_SLOT_PRICES.get(slot_num)
    if not price:
        await callback.answer("❌ Место не найдено")
        return
    current_slots = db.get_garage_slots(uid)
    if current_slots >= slot_num:
        await callback.answer("✅ Место уже куплено")
        return
    if balance < price:
        await callback.answer(f"❌ Недостаточно денег. Нужно {fmt(price)}", show_alert=True)
        return
    db.update_balance(uid, -price)
    db.update_garage_slots(uid, slot_num)
    await callback.answer(f"✅ Куплено {slot_num}-е место в гараже!")
    await _show_garage(callback)


# ==================== МОИ ШТРАФЫ (Callback) ====================

@dp.callback_query(F.data.startswith("my_fines|"))
async def cb_my_fines(callback: types.CallbackQuery):
    uid = await _assert_owner(callback)
    if uid is None:
        return
    fines = db.get_fines(uid)
    if not fines:
        await callback.message.edit_text(
            "📋 <b>Ваши штрафы</b>\n\nШтрафов нет ✅",
            parse_mode="HTML",
            reply_markup=back_keyboard(uid)
        )
        await callback.answer()
        return
    text = "📋 <b>Ваши штрафы:</b>\n\n"
    for fine_id, amount, reason, article, issued_at, paid in fines:
        status_icon = "✅" if paid else "❌"
        dt = datetime.fromtimestamp(issued_at).strftime("%d.%m.%Y %H:%M")
        article_str = f" | Ст. {article}" if article else ""
        text += (
            f"{status_icon} #{fine_id} — <b>{fmt(amount)}</b>\n"
            f"   Причина: {reason}{article_str}\n"
            f"   Дата: {dt}\n\n"
        )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_keyboard(uid))
    await callback.answer()


# ==================== МОИ БИЗНЕСЫ (Callback) ====================

@dp.callback_query(F.data.startswith("list_biz|"))
async def cb_list_biz(callback: types.CallbackQuery):
    uid = await _assert_owner(callback)
    if uid is None:
        return
    user = db.get_user(uid)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    bizs = db.get_businesses_full(uid)
    biz_slots = db.get_biz_slots(uid)
    if not bizs:
        text = (
            f"🏢 <b>Ваши бизнесы ({len(bizs)}/{biz_slots} мест)</b>\n\n"
            f"<i>Бизнесов нет.</i>\n"
            f"📝 Купить: <code>купить бизнес [номер]</code>"
        )
    else:
        text = f"🏢 <b>Ваши бизнесы ({len(bizs)}/{biz_slots} мест)</b>\n\n"
        for i, (bid, name, income, token) in enumerate(bizs, 1):
            text += f"{i}. {name}\n   💵 {fmt(income)}/3ч | 🔑 {token}\n\n"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_keyboard(uid))
    await callback.answer()


# ==================== МОЯ НЕДВИЖИМОСТЬ (Callback) ====================

@dp.callback_query(F.data.startswith("list_apts|"))
async def cb_list_apts(callback: types.CallbackQuery):
    uid = await _assert_owner(callback)
    if uid is None:
        return
    user = db.get_user(uid)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    apts = db.get_apartments_full(uid)
    apt_slots = db.get_apt_slots(uid)
    if not apts:
        text = (
            f"🏠 <b>Ваша недвижимость ({len(apts)}/{apt_slots} мест)</b>\n\n"
            f"<i>Недвижимости нет.</i>\n"
            f"📝 Купить: <code>купить недвижимость [номер]</code>"
        )
    else:
        text = f"🏠 <b>Ваша недвижимость ({len(apts)}/{apt_slots} мест)</b>\n\n"
        for i, (aid, name, token) in enumerate(apts, 1):
            text += f"{i}. {name} | 🔑 {token}\n"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_keyboard(uid))
    await callback.answer()


# ==================== РАБОТА ====================

JOBS_LIST = list(JOBS.items())
GOV_JOBS_LIST = list(GOV_JOBS.items())
JOBS_PER_PAGE = 5

GOV_JOB_CATEGORIES = [
    ("🛡️ МВД — СОБР",  [f"СОБР — {r}" for r, _ in _MVD_RANKS]),
    ("🚨 МВД — ОМОН",  [f"ОМОН — {r}" for r, _ in _MVD_RANKS]),
    ("👮‍♂️ МВД — ППС", [f"ППС — {r}"  for r, _ in _MVD_RANKS]),
    ("🚔 МВД — ДПС",  [f"ДПС — {r}"  for r, _ in _MVD_RANKS]),
    ("🔵 ФСБ", [
        "ФСБ — Мл. лейтенант", "ФСБ — Лейтенант", "ФСБ — Ст. лейтенант",
        "ФСБ — Капитан", "ФСБ — Майор", "ФСБ — Подполковник",
        "ФСБ — Полковник", "ФСБ — Генерал",
    ]),
    ("⚖️ Прокуратура", [
        "Помощник прокурора", "Прокурор", "Старший прокурор",
        "Прокурор района", "Прокурор города", "Прокурор области",
        "Генеральный прокурор",
    ]),
    ("🏛️ Правительство", [
        "Охранник прав-ва", "Водитель прав-ва", "Секретарь прав-ва",
        "Депутат", "Министр", "Зам. губернатора", "Губернатор",
    ]),
    ("🚦 ЦОДД", [
        "ЦОДД — Инспектор", "ЦОДД — Ст. инспектор",
        "ЦОДД — Нач. смены", "ЦОДД — Рук. подразделения",
    ]),
]


def _main_jobs_kb(uid: int, has_job: bool):
    rows = [
        [InlineKeyboardButton(text="💼 Гражданские работы", callback_data="jobs_civ_0")],
        [InlineKeyboardButton(text="🏛 Гос. должности", callback_data="jobs_gov_cats")],
    ]
    if has_job:
        rows.append([InlineKeyboardButton(text="🚪 Уволиться", callback_data="quit_job")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_info|{uid}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _civ_jobs_kb(page: int, has_job: bool):
    total = len(JOBS_LIST)
    total_pages = (total + JOBS_PER_PAGE - 1) // JOBS_PER_PAGE
    start = page * JOBS_PER_PAGE
    chunk = JOBS_LIST[start:start + JOBS_PER_PAGE]
    rows = []
    for i, (job_name, salary) in enumerate(chunk):
        rows.append([InlineKeyboardButton(
            text=f"💼 {job_name} — {fmt(salary)}",
            callback_data=f"apj_{start + i}"
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"jobs_civ_{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if start + JOBS_PER_PAGE < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"jobs_civ_{page + 1}"))
    rows.append(nav)
    if has_job:
        rows.append([InlineKeyboardButton(text="🚪 Уволиться", callback_data="quit_job")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="list_jobs")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _gov_cats_kb():
    rows = [[InlineKeyboardButton(text=cat, callback_data=f"jobs_gov_{i}")]
            for i, (cat, _) in enumerate(GOV_JOB_CATEGORIES)]
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="list_jobs")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _gov_jobs_kb(cat_idx: int):
    _, job_names = GOV_JOB_CATEGORIES[cat_idx]
    rows = []
    for job_name in job_names:
        salary = GOV_JOBS.get(job_name, 0)
        rows.append([InlineKeyboardButton(
            text=f"🏛 {job_name} — {fmt(salary)}",
            callback_data=f"agj_{cat_idx}_{job_name}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="jobs_gov_cats")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data.startswith("list_jobs"))
async def cb_jobs(callback: types.CallbackQuery):
    uid = await _assert_owner(callback)
    if uid is None:
        return
    user = db.get_user(uid)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    has_job = bool(user[7])
    text = (
        f"💼 <b>Работа</b>\n\n"
        f"Текущая: <b>{user[7] if has_job else 'Безработный'}</b>\n\n"
        f"Выберите категорию:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_main_jobs_kb(uid, has_job))
    await callback.answer()


@dp.callback_query(F.data.startswith("jobs_civ_"))
async def cb_civ_jobs(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[2])
    user = db.get_user(callback.from_user.id)
    has_job = bool(user[7]) if user else False
    await callback.message.edit_text(
        f"💼 <b>Гражданские работы</b>\n<i>Страница {page + 1}</i>",
        parse_mode="HTML",
        reply_markup=_civ_jobs_kb(page, has_job)
    )
    await callback.answer()


@dp.callback_query(F.data == "jobs_gov_cats")
async def cb_gov_cats(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🏛 <b>Государственные должности</b>\n\nВыберите ведомство:",
        parse_mode="HTML",
        reply_markup=_gov_cats_kb()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("jobs_gov_") & (F.data != "jobs_gov_cats"))
async def cb_gov_jobs(callback: types.CallbackQuery):
    try:
        cat_idx = int(callback.data.split("_")[2])
    except Exception:
        await callback.answer("❌ Ошибка")
        return
    cat_name, _ = GOV_JOB_CATEGORIES[cat_idx]
    await callback.message.edit_text(
        f"🏛 <b>{cat_name}</b>",
        parse_mode="HTML",
        reply_markup=_gov_jobs_kb(cat_idx)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("apj_"))
async def cb_apply_civ_job(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Работу выдаёт только администратор", show_alert=True)
        return
    idx = int(callback.data.split("_")[1])
    job_name, salary = JOBS_LIST[idx]
    uid = callback.from_user.id
    db.set_job(uid, job_name)
    db.add_log(uid, 'set_job', job_name, salary)
    await callback.answer(f"✅ Назначена: {job_name}", show_alert=True)


@dp.callback_query(F.data.startswith("agj_"))
async def cb_apply_gov_job(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Работу выдаёт только администратор", show_alert=True)
        return
    parts = callback.data.split("_", 2)
    job_name = parts[2]
    salary = GOV_JOBS.get(job_name, 0)
    uid = callback.from_user.id
    db.set_job(uid, job_name)
    db.add_log(uid, 'set_job', job_name, salary)
    await callback.answer(f"✅ Назначена: {job_name}", show_alert=True)


@dp.callback_query(F.data == "quit_job")
async def cb_quit_job(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user or not user[7]:
        await callback.answer("❌ У вас нет работы", show_alert=True)
        return
    old_job = user[7]
    db.set_job(callback.from_user.id, "")
    db.add_log(callback.from_user.id, 'quit_job', old_job)
    await callback.answer(f"✅ Вы уволились с должности: {old_job}", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=_main_jobs_kb(callback.from_user.id, False))


@dp.callback_query(F.data == "noop")
async def cb_noop(callback: types.CallbackQuery):
    await callback.answer()


# ==================== СПИСОК АКТИВОВ ====================

@dp.message(lambda m: m.text and m.text.lower() in ["каталог авто", "список авто"])
async def catalog_cars(message: types.Message):
    rate = config.USD_RUB_RATE
    lines = [f"🚗 <b>Каталог автомобилей</b> (курс USD/RUB: {rate:.1f} ₽)\n"]
    for cid in sorted(CARS_USD.keys()):
        name, usd = CARS_USD[cid]
        price = car_price_rub(cid)
        lines.append(f"{cid}. {name} — {fmt(price)}")
    text = "\n".join(lines)
    for i in range(0, len(text), 4000):
        await message.answer(text[i:i+4000], parse_mode="HTML")


@dp.message(lambda m: m.text and m.text.lower() in ["каталог бизнесов", "список бизнесов"])
async def catalog_biz(message: types.Message):
    lines = ["🏢 <b>Каталог бизнесов</b>\n"]
    for bid, (name, price, income) in BUSINESSES.items():
        lines.append(f"{bid}. {name}\n   💰 {fmt(price)} | 📈 {fmt(income)}/3ч")
    text = "\n".join(lines)
    for i in range(0, len(text), 4000):
        await message.answer(text[i:i+4000], parse_mode="HTML")


@dp.message(lambda m: m.text and m.text.lower() in ["каталог недвижимости", "список недвижимости"])
async def catalog_apt(message: types.Message):
    lines = ["🏠 <b>Каталог недвижимости</b>\n"]
    for aid, (name, price) in APARTMENTS.items():
        lines.append(f"{aid}. {name} — {fmt(price)}")
    text = "\n".join(lines)
    for i in range(0, len(text), 4000):
        await message.answer(text[i:i+4000], parse_mode="HTML")


# ==================== ОРГАНИЗАЦИИ ====================

ORG_KEYWORDS = {"ф1": "ф1", "футбол": "футбол", "семья": "семья"}


def _parse_org_cmd(text: str):
    parts = text.strip().split()
    if len(parts) < 2:
        return None
    key = parts[0].lower()
    if key not in ORG_KEYWORDS:
        return None
    target = parts[1]
    is_owner = False
    name = None
    if len(parts) >= 3:
        if parts[2].lower() == "владелец":
            is_owner = True
            if len(parts) >= 4:
                name = " ".join(parts[3:])
        else:
            name = " ".join(parts[2:])
    return ORG_KEYWORDS[key], target, is_owner, name


@dp.message(lambda m: m.text and m.text.strip().split()[0].lower() in ORG_KEYWORDS and m.from_user and m.from_user.id in config.ADMIN_IDS)
async def org_add_cmd(message: types.Message):
    parsed = _parse_org_cmd(message.text)
    if not parsed:
        await message.answer("❌ Формат: ф1 @юз [владелец]")
        return
    org_key, target_str, is_owner, custom_name = parsed
    target_user = None
    if target_str.startswith("@"):
        target_user = db.get_user_by_username(target_str[1:])
    else:
        try:
            target_user = db.get_user(int(target_str))
        except Exception:
            pass
    if not target_user:
        return
    target_uid = target_user[0]
    target_name = f"@{target_user[1]}" if target_user[1] else str(target_uid)
    db.add_org_member(target_uid, org_key, is_owner)
    if custom_name:
        db.set_org_name(org_key, custom_name)
    icon, _default = db.ORG_DISPLAY[org_key]
    org_name = db.get_org_name(org_key)
    role = "👑 Владелец" if is_owner else "👤 Участник"
    await message.answer(f"✅ {icon} {org_name}\n\n{target_name} добавлен как {role}")
    try:
        await bot.send_message(target_uid,
            f"🎉 Вас добавили в организацию!\n\n{icon} <b>{org_name}</b>\nСтатус: {role}",
            parse_mode="HTML"
        )
    except Exception:
        pass


@dp.message(lambda m: m.text and m.text.lower().startswith("убрать ") and m.from_user and m.from_user.id in config.ADMIN_IDS)
async def org_remove_cmd(message: types.Message):
    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.answer("❌ Формат: убрать ф1 @юз")
        return
    org_key = parts[1].lower()
    if org_key not in ORG_KEYWORDS:
        return
    target_str = parts[2]
    target_user = None
    if target_str.startswith("@"):
        target_user = db.get_user_by_username(target_str[1:])
    else:
        try:
            target_user = db.get_user(int(target_str))
        except Exception:
            pass
    if not target_user:
        return
    target_uid = target_user[0]
    target_name = f"@{target_user[1]}" if target_user[1] else str(target_uid)
    db.remove_org_member(target_uid, org_key)
    icon, org_name = db.ORG_DISPLAY[org_key]
    await message.answer(f"✅ {target_name} убран из «{icon} {org_name}»")


def _render_org_card(org_key: str) -> str:
    icon, _ = db.ORG_DISPLAY[org_key]
    org_name = db.get_org_name(org_key)
    members = db.get_org_members(org_key)
    text = f"{icon} <b>{org_name}</b>\n"
    if not members:
        text += "\n<i>Пусто.</i>"
        return text
    owners = []
    participants = []
    for uid, is_owner in members:
        u = db.get_user(uid)
        name = f"@{u[1]}" if u and u[1] else str(uid)
        game = f" — {u[3]}" if u and u[3] else ""
        if is_owner:
            owners.append(f"  👑 {name}{game}")
        else:
            participants.append(f"  • {name}{game}")
    if owners:
        text += "\n👑 <b>Владелец:</b>\n" + "\n".join(owners)
    if participants:
        text += f"\n\n👥 <b>Участники ({len(participants)}):</b>\n" + "\n".join(participants)
    return text


@dp.callback_query(F.data.startswith("list_orgs"))
async def cb_list_orgs(callback: types.CallbackQuery):
    uid = await _assert_owner(callback)
    if uid is None:
        return
    orgs = db.get_user_orgs(uid)
    player_orgs = db.get_player_orgs_for_user(uid)
    if not orgs and not player_orgs:
        await callback.message.edit_text(
            "🏛️ <b>Организации</b>\n\n<i>Вы ни в одной организации не состоите.</i>",
            parse_mode="HTML", reply_markup=back_keyboard(uid)
        )
        await callback.answer()
        return
    parts = []
    for org_key, _ in orgs:
        parts.append(_render_org_card(org_key))
    for po in player_orgs:
        parts.append(_render_player_org_card(po["org_id"]))
    text = "🏛️ <b>Ваши организации</b>\n\n" + "\n\n━━━━━━━━━━━━━━━━\n\n".join(parts)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_keyboard(uid))
    await callback.answer()


# ==================== ПОЛЬЗОВАТЕЛЬСКИЕ ОРГАНИЗАЦИИ ====================

def _render_player_org_card(org_id: int) -> str:
    org = db.get_player_org_by_id(org_id)
    if not org:
        return "<i>Организация не найдена.</i>"
    icon = org["icon"]
    name = org["name"]
    owner_uid = org["owner_uid"]
    owner = db.get_user(owner_uid)
    owner_name = f"@{owner[1]}" if owner and owner[1] else str(owner_uid)
    members = db.get_player_org_members(org_id)
    text = f"{icon} <b>{name}</b>\n"
    text += f"👑 Лидер: {owner_name}\n"
    text += f"👥 Участников: {len(members)}\n"
    non_owners = [m for m in members if m["uid"] != owner_uid]
    if non_owners:
        lines = []
        for m in non_owners:
            u = db.get_user(m["uid"])
            uname = f"@{u[1]}" if u and u[1] else str(m["uid"])
            game = f" — {u[3]}" if u and u[3] else ""
            lines.append(f"  • {uname}{game}")
        text += "\n" + "\n".join(lines)
    return text


@dp.message(lambda m: m.text and m.text.lower().startswith("создать орг "))
async def player_create_org(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы.")
        return
    name = message.text.strip()[len("создать орг "):].strip()
    if not name or len(name) > 32:
        await message.answer("❌ Формат: создать орг [название] (не более 32 символов)")
        return
    owned = db.get_orgs_owned_by(message.from_user.id)
    if len(owned) >= 1:
        await message.answer(f"❌ Вы уже лидер «{owned[0]['name']}». Расформируйте: расформировать [название]")
        return
    org_id = db.create_player_org(message.from_user.id, name)
    if org_id is None:
        await message.answer(f"❌ Организация «{name}» уже существует.")
        return
    await message.answer(
        f"🎉 Организация создана!\n\n🏛️ <b>{name}</b>\n👑 Вы — лидер.\n\n"
        f"Приглашайте: <code>пригласить @ник {name}</code>",
        parse_mode="HTML"
    )


@dp.message(lambda m: m.text and m.text.lower().startswith("пригласить "))
async def player_invite_to_org(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы.")
        return
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Формат: пригласить @ник [название орги]")
        return
    target_str, org_name_raw = parts[1], parts[2].strip()
    target = db.get_user_by_username(target_str.lstrip("@")) if target_str.startswith("@") else db.get_user_by_username(target_str)
    if not target:
        await message.answer("❌ Игрок не найден.")
        return
    org = db.get_player_org_by_name(org_name_raw)
    if not org:
        await message.answer(f"❌ Организация «{org_name_raw}» не найдена.")
        return
    if org["owner_uid"] != message.from_user.id:
        await message.answer("❌ Только лидер может приглашать.")
        return
    if db.is_player_org_member(org["org_id"], target[0]):
        await message.answer(f"❌ Игрок уже состоит в «{org['name']}».")
        return
    db.add_player_org_member(org["org_id"], target[0])
    t_name = f"@{target[1]}" if target[1] else str(target[0])
    await message.answer(f"✅ {t_name} добавлен(а) в «{org['icon']} {org['name']}»")
    try:
        await bot.send_message(target[0],
            f"🎉 Вас пригласили в организацию!\n\n{org['icon']} <b>{org['name']}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass


@dp.message(lambda m: m.text and m.text.lower().startswith("расформировать "))
async def player_disband_org(message: types.Message):
    user = db.get_user(message.from_user.id)
    if not user:
        return
    org_name_raw = message.text.strip()[len("расформировать "):].strip()
    org = db.get_player_org_by_name(org_name_raw)
    if not org:
        await message.answer(f"❌ Организация «{org_name_raw}» не найдена.")
        return
    if org["owner_uid"] != message.from_user.id and message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ Только лидер может расформировать.")
        return
    db.delete_player_org(org["org_id"])
    await message.answer(f"✅ Организация «{org_name_raw}» расформирована.")


@dp.message(lambda m: m.text and m.text.lower().startswith("орг "))
async def player_org_info(message: types.Message):
    org_name_raw = message.text.strip()[4:].strip()
    org = db.get_player_org_by_name(org_name_raw)
    if not org:
        await message.answer(f"❌ Организация «{org_name_raw}» не найдена.")
        return
    await message.answer(_render_player_org_card(org["org_id"]), parse_mode="HTML")


# ==================== ПРОДАЖА ИМУЩЕСТВА ====================

def _parse_sell_cmd(text: str):
    parts = text.strip().split()
    if len(parts) < 3:
        return None
    asset_map = {"авто": "car", "машину": "car", "машина": "car", "бизнес": "biz", "квартиру": "apt", "недвижимость": "apt", "объект": "apt"}
    asset_raw = parts[1].lower()
    asset_type = asset_map.get(asset_raw)
    if not asset_type:
        return None
    token = parts[2].upper()
    if len(parts) >= 5:
        nick = next((p for p in parts[3:] if p.startswith("@")), None)
        price_str = next((p for p in parts[3:] if p.isdigit()), None)
        if nick and price_str:
            return {"type": asset_type, "token": token, "nick": nick[1:], "price": int(price_str)}
    return {"type": asset_type, "token": token, "nick": None, "price": None}


def _get_asset_price(asset_type: str, asset_id: int) -> int:
    if asset_type == "car":
        data = CARS.get(asset_id)
        return data[1] if data else 0
    elif asset_type == "biz":
        data = BUSINESSES.get(asset_id)
        return data[1] if data else 0
    elif asset_type == "apt":
        data = APARTMENTS.get(asset_id)
        return data[1] if data else 0
    return 0


@dp.message(lambda m: m.text and m.text.lower().startswith("продать ") and not (len(m.text.split()) >= 3 and m.text.lower().split()[1] in _cx.CRYPTO_INFO))
async def sell_asset_cmd(message: types.Message):
    user = db.get_user(message.from_user.id)
    status = check_user(user)
    if status != "ok":
        await message.answer("❌ Вы не зарегистрированы." if status == "not_registered" else "⛔ Вы заблокированы.")
        return

    parsed = _parse_sell_cmd(message.text)
    if not parsed:
        await message.answer("❌ Формат: продать авто/бизнес/недвижимость [токен] [@ник цена]")
        return

    atype = parsed["type"]
    token = parsed["token"]
    uid = user[0]

    if atype == "car":
        asset = db.get_car_by_token(token)
    elif atype == "biz":
        asset = db.get_business_by_token(token)
    else:
        asset = db.get_apartment_by_token(token)

    if not asset or asset[1] != uid:
        await message.answer("❌ Актив не найден или не является вашим.")
        return

    db_id = asset[0]
    asset_name = asset[3]
    asset_id = asset[2]
    full_price = _get_asset_price(atype, asset_id)
    state_price = full_price // 2

    type_names = {"car": "Автомобиль", "biz": "Бизнес", "apt": "Недвижимость"}
    type_name = type_names[atype]

    if parsed["nick"] and parsed["price"]:
        target_nick = parsed["nick"]
        sale_price = parsed["price"]
        target = db.get_user_by_username(target_nick)
        if not target:
            await message.answer(f"❌ Игрок @{target_nick} не найден.")
            return
        if target[0] == uid:
            await message.answer("❌ Нельзя продавать самому себе.")
            return
        import secrets as _secrets
        sale_token = _secrets.token_hex(4).upper()
        PENDING_SALES[sale_token] = {
            "type": atype, "db_id": db_id, "seller_uid": uid,
            "buyer_uid": target[0], "price": sale_price, "name": asset_name
        }
        seller_nick = message.from_user.username or message.from_user.first_name
        offer_text = (
            f"💼 Предложение о покупке от @{seller_nick}\n\n"
            f"📋 {type_name}: {asset_name}\n"
            f"🔑 Токен: {sale_token}\n"
            f"💰 Цена: {fmt(sale_price)}\n\n"
            f"Ваш баланс: {fmt(target[4])}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Принять", callback_data=f"asale_{sale_token}"),
            InlineKeyboardButton(text="❌ Отказать", callback_data=f"rsale_{sale_token}"),
        ]])
        try:
            await bot.send_message(target[0], offer_text, reply_markup=kb)
        except Exception:
            PENDING_SALES.pop(sale_token, None)
            await message.answer(f"❌ Не удалось отправить предложение @{target_nick}.")
            return
        await message.answer(f"✅ Предложение отправлено @{target_nick}!\n📋 {asset_name} | {fmt(sale_price)}")
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=f"✅ Продать за {fmt(state_price)}", callback_data=f"csell_{atype}_{token}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"xsell_{token}"),
        ]])
        await message.answer(
            f"🏛 Продажа государству (50% от стоимости)\n\n"
            f"📋 {type_name}: {asset_name}\n"
            f"💰 Получите: {fmt(state_price)}\n\n"
            f"Или: продать авто {token} @ник [цена]",
            reply_markup=kb
        )


@dp.callback_query(lambda c: c.data and c.data.startswith("csell_"))
async def cb_confirm_sell_state(callback: types.CallbackQuery):
    user = db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрированы")
        return
    parts = callback.data.split("_")
    atype = parts[1]
    token = "_".join(parts[2:])
    uid = user[0]
    if atype == "car":
        asset = db.get_car_by_token(token)
    elif atype == "biz":
        asset = db.get_business_by_token(token)
    else:
        asset = db.get_apartment_by_token(token)
    if not asset or asset[1] != uid:
        await callback.answer("❌ Актив не найден", show_alert=True)
        return
    db_id = asset[0]
    asset_name = asset[3]
    asset_id = asset[2]
    full_price = _get_asset_price(atype, asset_id)
    state_price = full_price // 2
    if atype == "car":
        db.remove_car_db(db_id)
    elif atype == "biz":
        db.remove_business_db(db_id)
    else:
        db.remove_apartment_db(db_id)
    db.update_balance(uid, state_price)
    type_names = {"car": "Автомобиль", "biz": "Бизнес", "apt": "Недвижимость"}
    await callback.message.edit_text(
        f"✅ {type_names[atype]} продан государству!\n\n"
        f"📋 {asset_name}\n"
        f"💰 Получено: +{fmt(state_price)}\n"
        f"💵 Баланс: {fmt(user[4] + state_price)}"
    )
    await callback.answer("✅ Продано!")


@dp.callback_query(lambda c: c.data and c.data.startswith("xsell_"))
async def cb_cancel_sell(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Продажа отменена.")
    await callback.answer("Отменено")


@dp.callback_query(lambda c: c.data and c.data.startswith("asale_"))
async def cb_accept_sale(callback: types.CallbackQuery):
    token = callback.data[6:]
    sale = PENDING_SALES.get(token)
    if not sale:
        await callback.answer("❌ Предложение устарело", show_alert=True)
        await callback.message.edit_reply_markup()
        return
    if callback.from_user.id != sale["buyer_uid"]:
        await callback.answer("❌ Это предложение не для вас", show_alert=True)
        return
    buyer = db.get_user(sale["buyer_uid"])
    if not buyer or buyer[4] < sale["price"]:
        await callback.answer("❌ Недостаточно средств", show_alert=True)
        return
    db.update_balance(sale["buyer_uid"], -sale["price"])
    db.update_balance(sale["seller_uid"], sale["price"])
    atype = sale["type"]
    db_id = sale["db_id"]
    if atype == "car":
        db.transfer_car(db_id, sale["buyer_uid"])
    elif atype == "biz":
        db.transfer_business(db_id, sale["buyer_uid"])
    else:
        db.transfer_apartment(db_id, sale["buyer_uid"])
    db.add_log(sale["buyer_uid"], 'p2p_buy', sale["name"], sale["price"])
    db.add_log(sale["seller_uid"], 'p2p_sell', sale["name"], sale["price"])
    PENDING_SALES.pop(token, None)
    type_names = {"car": "Автомобиль", "biz": "Бизнес", "apt": "Недвижимость"}
    tn = type_names.get(atype, "Актив")
    await callback.message.edit_text(
        f"✅ Покупка совершена!\n\n"
        f"📋 {tn}: {sale['name']}\n"
        f"💰 Оплачено: {fmt(sale['price'])}\n"
        f"💵 Баланс: {fmt(buyer[4] - sale['price'])}"
    )
    await callback.answer("✅ Сделка совершена!")
    try:
        buyer_nick = buyer[1] or "Покупатель"
        await bot.send_message(sale["seller_uid"],
            f"✅ <b>Advance RP</b> — Сделка совершена!\n\n"
            f"📋 {tn}: {sale['name']}\n"
            f"👤 Покупатель: @{buyer_nick}\n"
            f"💰 Получено: +{fmt(sale['price'])}",
            parse_mode="HTML"
        )
    except Exception:
        pass


@dp.callback_query(lambda c: c.data and c.data.startswith("rsale_"))
async def cb_reject_sale(callback: types.CallbackQuery):
    token = callback.data[6:]
    sale = PENDING_SALES.get(token)
    if not sale:
        await callback.answer("❌ Предложение не найдено", show_alert=True)
        return
    if callback.from_user.id != sale["buyer_uid"]:
        await callback.answer("❌ Это предложение не для вас", show_alert=True)
        return
    PENDING_SALES.pop(token, None)
    await callback.message.edit_text("❌ Вы отказались от покупки.")
    await callback.answer("Отказано")


# ==================== ПРАВИТЕЛЬСТВО ====================

@dp.message(lambda m: m.text and m.text.lower().startswith("govemployee ") and "@" in m.text and m.from_user and is_admin(m.from_user.id))
async def gov_employee_cmd(message: types.Message):
    parts = message.text.strip().split(maxsplit=2)
    username = next((p[1:] for p in parts if p.startswith("@")), None)
    if not username:
        await message.answer("❌ Формат: govemployee @никнейм [роль]")
        return
    role = parts[2].strip() if len(parts) >= 3 and not parts[2].startswith("@") else "Сотрудник правительства"
    target = db.get_user_by_username(username)
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    db.set_gov_employee(target[0], role, message.from_user.id)
    db.add_log(target[0], 'gov_employee_set', role, 0, message.from_user.id)
    await message.answer(
        f"🏛️ <b>Назначение в Правительство</b>\n\n"
        f"👤 Игрок: @{username}\n"
        f"💼 Роль: {role}",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            target[0],
            f"🏛️ <b>Advance RP — Назначение</b>\n\n"
            f"Вы назначены сотрудником Правительства!\n"
            f"💼 Роль: <b>{role}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass


@dp.message(lambda m: m.text and m.text.lower().startswith("mvdemployee ") and "@" in m.text and m.from_user and is_admin(m.from_user.id))
async def mvd_employee_cmd(message: types.Message):
    parts = message.text.strip().split(maxsplit=2)
    username = next((p[1:] for p in parts if p.startswith("@")), None)
    if not username:
        await message.answer("❌ Формат: mvdemployee @никнейм [роль]")
        return
    role = parts[2].strip() if len(parts) >= 3 and not parts[2].startswith("@") else "Сотрудник МВД"
    target = db.get_user_by_username(username)
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    db.set_mvd_employee(target[0], role, message.from_user.id)
    db.add_log(target[0], 'mvd_employee_set', role, 0, message.from_user.id)
    await message.answer(
        f"👮 <b>Назначение в МВД</b>\n\n"
        f"👤 Игрок: @{username}\n"
        f"💼 Роль: {role}",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            target[0],
            f"👮 <b>Advance RP — Назначение</b>\n\n"
            f"Вы назначены сотрудником МВД!\n"
            f"💼 Роль: <b>{role}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ==================== КАЗНА (ПРАВИТЕЛЬСТВО) ====================

@dp.message(lambda m: m.text and m.text.lower().strip() in ["казна", "казна правительства"] and m.from_user and is_gov(m.from_user.id))
async def treasury_cmd(message: types.Message):
    balance = db.get_treasury()
    logs = db.get_treasury_logs(10)
    text = (
        f"🏛️ <b>Государственная казна — Advance RP</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Баланс: <b>{fmt(balance)}</b>\n\n"
        f"<b>Последние операции:</b>\n"
    )
    for ts, action, amount, uid, details in logs:
        dt = datetime.fromtimestamp(ts).strftime("%d.%m %H:%M")
        sign = "+" if amount >= 0 else ""
        text += f"  {dt} | {action} | {sign}{fmt(amount)}\n"
    await message.answer(text, parse_mode="HTML")


# ==================== ШТРАФЫ МВД ====================

@dp.message(lambda m: m.text and m.text.lower().startswith("штраф ") and "@" in m.text)
async def fine_cmd(message: types.Message):
    if not is_mvd(message.from_user.id):
        await message.answer("⛔ Только сотрудники МВД могут выписывать штрафы.")
        return

    # Парсим команду
    # Формат: штраф @username
    # Затем бот спрашивает сумму, статью и причину через FSM
    username = parse_mentioned_username(message.text)
    if not username:
        await message.answer("❌ Формат: штраф @никнейм")
        return
    target = db.get_user_by_username(username)
    if not target:
        await message.answer(f"❌ Игрок @{username} не найден.")
        return

    status = check_user(target)
    if status == "banned":
        await message.answer(f"⛔ Игрок @{username} заблокирован.")
        return

    # Парсим дополнительные параметры если указаны в строке
    # штраф @username СУММА СТАТЬЯ ПРИЧИНА
    parts = message.text.strip().split()
    amount = None
    article = ""
    reason = ""

    # Ищем число (сумму)
    for p in parts[2:]:
        if p.replace("₽", "").replace(" ", "").isdigit():
            amount = int(p.replace("₽", ""))
            break

    # Ищем статью
    for i, p in enumerate(parts):
        if p.lower() in ["статья", "ст."] and i + 1 < len(parts):
            article = parts[i + 1]

    # Причина — всё остальное
    reason_parts = [p for p in parts[2:] if not p.startswith("@") and p != str(amount) and p not in [article, "статья", "ст."]]
    reason = " ".join(reason_parts) if reason_parts else "Нарушение ПДД"

    if not amount:
        await message.answer(
            "❌ Формат: штраф @никнейм [сумма] [статья XX] [причина]\n\n"
            "Пример:\nштраф @username 5000 статья 12 Превышение скорости"
        )
        return

    # Выполняем штраф
    target_uid = target[0]
    target_balance = target[4]

    # Списываем деньги
    actual_fine = min(amount, target_balance)
    if actual_fine > 0:
        db.update_balance(target_uid, -actual_fine)
        db.update_treasury(actual_fine, "fine", target_uid, f"Штраф: {reason}")

    # Записываем штраф
    db.add_fine(target_uid, amount, reason, article, message.from_user.id)
    db.add_log(target_uid, 'fine', f'article:{article} reason:{reason}', amount, message.from_user.id)

    officer_name = message.from_user.username or message.from_user.first_name
    article_str = f"Статья: {article}\n" if article else ""

    await message.answer(
        f"🚔 <b>ШТРАФ ВЫПИСАН</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Игрок: @{username}\n"
        f"💸 Сумма: <b>{fmt(amount)}</b>\n"
        f"{article_str}"
        f"📋 Причина: {reason}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Списано: {fmt(actual_fine)}\n"
        f"🏛️ Переведено в казну: {fmt(actual_fine)}\n"
        f"👮 Офицер: @{officer_name}",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            target_uid,
            f"🚔 <b>Advance RP — ШТРАФ</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💸 Сумма: <b>{fmt(amount)}</b>\n"
            f"{article_str}"
            f"📋 Причина: {reason}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Списано с баланса: {fmt(actual_fine)}",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ==================== ПРОМОКОДЫ ====================

@dp.message(lambda m: m.text and m.text.lower().startswith("createpromo "))
async def createpromo_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 4:
        await message.answer(
            "❌ Формат: createpromo НАЗВАНИЕ СУММА ЛИМИТ\n"
            "Пример: createpromo DIAMOND 100000 500\n"
            "(ЛИМИТ=0 → без ограничений)"
        )
        return
    code = parts[1].upper()
    try:
        amount = float(parts[2].replace(",", "."))
        limit = int(parts[3])
        if amount <= 0 or limit < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ СУММА > 0, ЛИМИТ ≥ 0")
        return
    success = db.add_promo_code(code, amount, limit, message.from_user.id)
    db.add_log(message.from_user.id, 'createpromo', code, amount)
    if success:
        limit_str = "∞" if limit == 0 else str(limit)
        await message.answer(
            f"✅ <b>Промокод создан!</b>\n"
            f"Код: <code>{code}</code>\n"
            f"Сумма: {fmt(amount)}\n"
            f"Лимит: {limit_str}",
            parse_mode="HTML"
        )
    else:
        await message.answer(f"❌ Промокод <code>{code}</code> уже существует.", parse_mode="HTML")


@dp.message(lambda m: m.text and m.text.lower().strip() == "промокоды")
async def list_promos_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    promos = db.get_active_promos()
    if not promos:
        await message.answer("📋 Нет активных промокодов.")
        return
    lines = ["🎟 <b>Активные промокоды:</b>\n"]
    for code, amount, max_uses, used_count, added_at in promos:
        uses_str = f"{used_count}/{max_uses}" if max_uses > 0 else f"{used_count}/∞"
        lines.append(f"• <code>{code}</code> — {fmt(amount)} | {uses_str}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(lambda m: m.text and m.text.lower().startswith("promo "))
async def promo_cmd(message: types.Message):
    user = db.get_user(message.from_user.id)
    status = check_user(user)
    if status == "not_registered":
        await message.answer("❌ Вы не зарегистрированы. Напишите /start")
        return
    if status == "banned":
        await message.answer("⛔ Вы заблокированы.")
        return
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Формат: promo КОД")
        return
    code = parts[1].strip().upper()
    success, amount, reason = db.use_promo_code(message.from_user.id, code)
    if success:
        db.update_balance(message.from_user.id, amount)
        db.add_log(message.from_user.id, 'promo', code, amount)
        balance = db.get_user(message.from_user.id)[4]
        await message.answer(
            f"✅ Промокод <b>{code}</b> активирован!\n"
            f"💰 Начислено: <b>+{fmt(amount)}</b>\n"
            f"💵 Баланс: <b>{fmt(balance)}</b>",
            parse_mode="HTML"
        )
    else:
        msgs = {
            "not_found": f"❌ Промокод <b>{code}</b> не найден.",
            "disabled": f"❌ Промокод <b>{code}</b> отключён.",
            "exhausted": f"❌ Промокод <b>{code}</b> исчерпан.",
            "already_used": f"❌ Вы уже использовали промокод <b>{code}</b>.",
        }
        await message.answer(msgs.get(reason, "❌ Ошибка активации."), parse_mode="HTML")


@dp.message(lambda m: m.text and m.text.lower().startswith("активировать "))
async def activate_promo_cmd(message: types.Message):
    user = db.get_user(message.from_user.id)
    status = check_user(user)
    if status == "not_registered":
        await message.answer("❌ Вы не зарегистрированы. Напишите /start")
        return
    if status == "banned":
        await message.answer("⛔ Вы заблокированы.")
        return
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Формат: активировать [КОД]")
        return
    code = parts[1].strip().upper()
    success, amount, reason = db.use_promo_code(message.from_user.id, code)
    if success:
        db.update_balance(message.from_user.id, amount)
        db.add_log(message.from_user.id, 'promo', code, amount)
        balance = db.get_user(message.from_user.id)[4]
        await message.answer(
            f"✅ Промокод <b>{code}</b> активирован!\n"
            f"💰 Начислено: <b>+{fmt(amount)}</b>\n"
            f"💵 Баланс: <b>{fmt(balance)}</b>",
            parse_mode="HTML"
        )
    else:
        msgs = {
            "not_found": f"❌ Промокод <b>{code}</b> не найден.",
            "disabled": f"❌ Промокод <b>{code}</b> отключён.",
            "exhausted": f"❌ Промокод <b>{code}</b> исчерпан.",
            "already_used": f"❌ Вы уже использовали промокод <b>{code}</b>.",
        }
        await message.answer(msgs.get(reason, "❌ Ошибка активации."), parse_mode="HTML")


# ==================== SPECIAL SYSTEM ====================

@dp.message(lambda m: m.text and m.text.lower().startswith("specialcar ") and "@" in m.text and m.from_user and is_admin(m.from_user.id))
async def specialcar_cmd(message: types.Message):
    """specialcar @username vehicle_name"""
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Формат: specialcar @никнейм [название авто]\nПример: specialcar @username BMW_M5_GSG9")
        return
    username = parts[1].lstrip("@")
    car_name = parts[2].replace("_", " ")
    target = db.get_user_by_username(username)
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    db.add_car(target[0], 0, car_name)
    db.add_log(message.from_user.id, 'specialcar', f"{username}:{car_name}", 0)
    await message.answer(
        f"✅ <b>Спецтранспорт выдан</b>\n\n"
        f"👤 Игрок: @{username}\n"
        f"🚗 Авто: {car_name}",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(target[0],
            f"🚗 <b>Advance RP — Специальный транспорт</b>\n\nВам выдан автомобиль: <b>{car_name}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass


@dp.message(lambda m: m.text and m.text.lower().startswith("specialplate ") and "@" in m.text and m.from_user and is_admin(m.from_user.id))
async def specialplate_cmd(message: types.Message):
    """specialplate @username plate"""
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Формат: specialplate @никнейм [номер]\nПример: specialplate @username B-GOV-001")
        return
    username = parts[1].lstrip("@")
    plate_str = parts[2].strip()
    target = db.get_user_by_username(username)
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    car = db.get_last_car(target[0])
    if not car:
        await message.answer(f"❌ У @{username} нет автомобилей. Сначала выдайте авто.")
        return
    db.set_custom_plate(car[0], plate_str)
    db.add_log(message.from_user.id, 'specialplate', f"{username}:{plate_str}", 0)
    await message.answer(
        f"✅ <b>Спецномер установлен</b>\n\n"
        f"👤 Игрок: @{username}\n"
        f"🚗 Авто: {car[3]}\n"
        f"🔢 Номер: <code>{plate_str}</code>",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(target[0],
            f"🔢 <b>Advance RP</b> — Вам установлен специальный номер: <code>{plate_str}</code>\n"
            f"Автомобиль: {car[3]}",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ==================== РУССКИЕ НОМЕРА ====================

@dp.message(lambda m: m.text and m.text.lower() == "курс")
async def rate_cmd(message: types.Message):
    await message.answer(
        f"💱 <b>Текущий курс</b>\n\n"
        f"🇺🇸 USD/RUB: <b>{config.USD_RUB_RATE:.2f} ₽</b>\n"
        f"📈 Обновляется каждые 5 минут\n\n"
        f"Используется для расчёта цен в Автосалоне.",
        parse_mode="HTML"
    )


# ==================== ПОМОЩЬ ====================

@dp.message(lambda m: m.text and m.text.lower() in ["помощь", "команды", "/help"])
async def help_cmd(message: types.Message):
    await message.answer(
        "🎮 <b>Advance RP — Команды</b>\n\n"
        "━━━━ 👤 Профиль ━━━━\n"
        "<code>инфо</code> — профиль\n"
        "<code>б</code> / <code>баланс</code> — текущий баланс\n"
        "<code>курс</code> — курс USD/RUB\n\n"
        "━━━━ 💼 Работа и зарплата ━━━━\n"
        "<code>зп</code> — получить зарплату\n"
        "<code>зп @ник</code> — зарплата игроку\n"
        "<code>зп бизнес @ник</code> — зарплата + бизнес\n"
        "<code>бизнес @ник</code> — только доход от бизнесов\n\n"
        "━━━━ 💰 Покупки ━━━━\n"
        "<code>купить авто [id]</code> — автосалон (реальный курс)\n"
        "<code>купить бизнес [id]</code>\n"
        "<code>купить недвижимость [id]</code>\n\n"
        "━━━━ 📋 Каталоги ━━━━\n"
        "<code>каталог авто</code> / <code>каталог бизнесов</code> / <code>каталог недвижимости</code>\n\n"
        "━━━━ 💸 Переводы ━━━━\n"
        "<code>дать [сумма] @ник</code>\n"
        "<code>+[сумма] @ник</code>\n\n"
        "━━━━ 💰 Продажа ━━━━\n"
        "<code>продать авто [токен]</code> — государству (50%)\n"
        "<code>продать авто [токен] @ник [цена]</code> — игроку\n\n"
        "━━━━ 🏆 Рейтинги ━━━━\n"
        "<code>топ</code> / <code>топ имущество</code>\n\n"
        "━━━━ 🏦 Банк ━━━━\n"
        "<code>банк</code> | <code>внести / вывести [сумма]</code>\n"
        "<code>кредит / погасить [сумма]</code>\n\n"
        "━━━━ 💹 Крипто ━━━━\n"
        "<code>крипто</code> — портфель\n"
        "<code>купить BTC 0.001</code> / <code>продать ETH 1</code>\n\n"
        "━━━━ 🎰 Казино ━━━━\n"
        "<code>казино</code>\n\n"
        "━━━━ 🎟 Промокоды ━━━━\n"
        "<code>promo КОД</code> / <code>активировать КОД</code>\n\n"
        "━━━━ 🏛️ Организации ━━━━\n"
        "<code>создать орг [название]</code>\n"
        "<code>пригласить @ник [орг]</code>\n"
        "<code>расформировать [орг]</code>\n\n"
        "━━━━ 🚔 МВД (штрафы) ━━━━\n"
        "<code>штраф @ник [сумма] [статья XX] [причина]</code>\n\n"
        "━━━━ 🏛️ Правительство ━━━━\n"
        "<code>казна</code> — государственная казна",
        parse_mode="HTML"
    )


# ==================== ADMIN КОМАНДЫ ====================

@dp.message(lambda m: m.text and m.text.startswith("/setbalance"))
async def admin_setbalance(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        parts = message.text.split()
        amount = int(parts[2])
    except Exception:
        await message.answer("❌ Формат: /setbalance @ник [сумма]")
        return
    target = _resolve_user_by_nick(parts[1])
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    db.set_balance(target[0], amount)
    db.add_log(target[0], 'setbalance', f'admin {message.from_user.id}', amount, message.from_user.id)
    await message.answer(f"✅ Баланс @{target[1]} → {fmt(amount)}")


@dp.message(lambda m: m.text and m.text.startswith("/ban") and not m.text.startswith("/bank"))
async def admin_ban(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Формат: /ban @ник")
        return
    target = _resolve_user_by_nick(parts[1])
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    db.ban_user(target[0])
    await message.answer(f"✅ Игрок @{target[1]} заблокирован")


@dp.message(lambda m: m.text and m.text.startswith("/unban"))
async def admin_unban(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Формат: /unban @ник")
        return
    target = _resolve_user_by_nick(parts[1])
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    db.unban_user(target[0])
    await message.answer(f"✅ Игрок @{target[1]} разблокирован")


@dp.message(lambda m: m.text and (
    m.text.lower().startswith("/reset") or
    (m.text.lower().startswith("reset ") and "@" in m.text)
))
async def admin_reset_user(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("❌ Формат: /reset @ник")
        return
    target = _resolve_user_by_nick(parts[1])
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    target_id = target[0]
    name = f"@{target[1]}" if target[1] else str(target_id)
    db.reset_user(target_id)
    db.add_log(target_id, 'reset', f'admin {message.from_user.id}', 0, message.from_user.id)
    await message.answer(
        f"♻️ Аккаунт {name} сброшен.\n"
        f"Баланс, банк, крипта, транспорт, бизнесы, квартиры, работа — обнулено."
    )
    try:
        await bot.send_message(target_id,
            "♻️ <b>Advance RP</b> — Ваш аккаунт был сброшен администратором.\n"
            "Все игровые данные обнулены. Напишите «инфо».",
            parse_mode="HTML"
        )
    except Exception:
        pass


@dp.message(lambda m: m.text and m.text.lower().startswith("/setjob"))
async def admin_setjob(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        parts = message.text.split(maxsplit=2)
        job = parts[2]
    except Exception:
        await message.answer("❌ Формат: /setjob @ник [работа]")
        return
    target = _resolve_user_by_nick(parts[1])
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    if job not in ALL_JOBS:
        await message.answer(f"❌ Работа не найдена.")
        return
    db.set_job(target[0], job)
    await message.answer(f"✅ Работа @{target[1]}: {job}")


@dp.message(lambda m: m.text and m.text.startswith("/addcar"))
async def admin_addcar(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        parts = message.text.split()
        car_id = int(parts[2])
    except Exception:
        await message.answer("❌ Формат: /addcar @ник [номер авто]")
        return
    target = _resolve_user_by_nick(parts[1])
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    car = get_car(car_id)
    if not car:
        await message.answer(f"❌ Авто #{car_id} не найдено")
        return
    car_name, _ = car
    db.add_car(target[0], car_id, car_name)
    db.add_log(message.from_user.id, 'admin_addcar', f"{target[1]}:{car_name}", 0)
    await message.answer(f"✅ Авто {car_name} → @{target[1]}")


@dp.message(lambda m: m.text and m.text.startswith("/setx2"))
async def admin_setx2(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        parts = message.text.split()
        value = int(parts[2])
        assert value in (0, 1)
    except Exception:
        await message.answer("❌ Формат: /setx2 @ник [1 или 0]")
        return
    target = _resolve_user_by_nick(parts[1])
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    db.set_x2(target[0], bool(value))
    status = "включён 🔥" if value else "выключен"
    await message.answer(f"✅ Х2 бонус для @{target[1]}: {status}")


@dp.message(lambda m: m.text and m.text.startswith("/userinfo"))
async def admin_userinfo(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Формат: /userinfo @ник")
        return
    target = _resolve_user_by_nick(parts[1])
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    uid, username, spm_id, game_name, balance, bank, btc, job, last_salary, banned, *_ = target
    x2 = db.has_x2(uid)
    gov_emp = db.get_gov_employee(uid)
    mvd_emp = db.get_mvd_employee(uid)
    text = (
        f"👤 <b>Информация об игроке</b>\n\n"
        f"🆔 ID: {uid}\n"
        f"📱 Username: @{username}\n"
        f"🎮 RP имя: {game_name}\n"
        f"🆔 CPM ID: {spm_id}\n"
        f"💰 Баланс: {fmt(balance)}\n"
        f"🏦 Банк: {fmt(bank)}\n"
        f"💼 Работа: {job if job else 'Безработный'}\n"
        f"🔥 Х2 бонус: {'Да' if x2 else 'Нет'}\n"
        f"⛔ Бан: {'Да' if banned else 'Нет'}\n"
        f"🏛️ Правительство: {gov_emp['role'] if gov_emp else 'Нет'}\n"
        f"👮 МВД: {mvd_emp['role'] if mvd_emp else 'Нет'}"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(lambda m: m.text and m.text.startswith("/broadcast"))
async def admin_broadcast(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    try:
        text = message.text.split(maxsplit=1)[1]
    except Exception:
        await message.answer("❌ Формат: /broadcast [текст]")
        return
    users = db.get_all_users()
    sent = 0
    for uid in users:
        try:
            await bot.send_message(uid, f"📢 <b>Объявление Advance RP:</b>\n\n{text}", parse_mode="HTML")
            sent += 1
        except Exception:
            pass
    await message.answer(f"✅ Отправлено {sent}/{len(users)} игрокам")


@dp.message(lambda m: m.text and m.text.lower().startswith("добавить администратора") and m.from_user and is_founder(m.from_user.id))
async def add_admin_cmd(message: types.Message):
    username = next((p[1:] for p in message.text.split() if p.startswith("@")), None)
    if not username:
        await message.answer("❌ Формат: добавить администратора @никнейм")
        return
    target = db.get_user_by_username(username)
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    db.grant_admin(target[0], message.from_user.id)
    db.add_log(target[0], 'admin_grant', f'выдал {message.from_user.id}', 0, message.from_user.id)
    await message.answer(f"✅ @{username} назначен администратором.")
    try:
        await bot.send_message(target[0], "✅ Вам выданы права администратора в <b>Advance RP</b>.", parse_mode="HTML")
    except Exception:
        pass


@dp.message(lambda m: m.text and m.text.lower().startswith("снять администратора") and m.from_user and is_founder(m.from_user.id))
async def remove_admin_cmd(message: types.Message):
    username = next((p[1:] for p in message.text.split() if p.startswith("@")), None)
    if not username:
        await message.answer("❌ Формат: снять администратора @никнейм")
        return
    target = db.get_user_by_username(username)
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    if is_founder(target[0]):
        await message.answer("❌ Нельзя снять основателя.")
        return
    success = db.revoke_admin(target[0])
    if success:
        db.add_log(target[0], 'admin_revoke', f'снял {message.from_user.id}', 0, message.from_user.id)
        await message.answer(f"✅ Права администратора у @{username} сняты.")
    else:
        await message.answer(f"❌ @{username} не является администратором.")


# ==================== ADMIN ВЫДАЧА ПО ЮЗЕРНЕЙМУ ====================

@dp.message(lambda m: (
    m.text and m.from_user and is_admin(m.from_user.id) and
    m.reply_to_message is None and
    m.text.lower().startswith("выдать авто ") and "@" in m.text
))
async def admin_give_car_username(message: types.Message):
    parts = message.text.strip().split()
    try:
        username = next(p for p in parts if p.startswith("@"))[1:]
        car_id = int(parts[-1])
    except Exception:
        await message.answer("❌ Формат: выдать авто @ник [номер авто]")
        return
    target = db.get_user_by_username(username)
    if not target:
        return
    car = get_car(car_id)
    if not car:
        await message.answer(f"❌ Авто #{car_id} не найдено.")
        return
    car_name, _ = car
    db.add_car(target[0], car_id, car_name)
    db.add_log(message.from_user.id, 'give_car', f"{username}:{car_name}", 0)
    await message.answer(f"✅ @{username} получил авто: {car_name}")
    try:
        await bot.send_message(target[0], f"🚗 Вам выдали автомобиль: {car_name}")
    except Exception:
        pass


@dp.message(lambda m: (
    m.text and m.from_user and is_admin(m.from_user.id) and
    m.reply_to_message is None and
    m.text.lower().startswith("выдать бизнес ") and "@" in m.text
))
async def admin_give_biz_username(message: types.Message):
    parts = message.text.strip().split()
    try:
        username = next(p for p in parts if p.startswith("@"))[1:]
        biz_id = int(parts[-1])
    except Exception:
        await message.answer("❌ Формат: выдать бизнес @ник [номер]")
        return
    target = db.get_user_by_username(username)
    if not target:
        return
    if biz_id not in BUSINESSES:
        await message.answer(f"❌ Бизнес #{biz_id} не найден.")
        return
    biz_name, _, biz_income = BUSINESSES[biz_id]
    db.add_business(target[0], biz_id, biz_name, biz_income)
    db.add_log(message.from_user.id, 'give_biz', f"{username}:{biz_name}", 0)
    await message.answer(f"✅ @{username} получил бизнес: {biz_name}")
    try:
        await bot.send_message(target[0], f"🏢 Вам выдали бизнес: {biz_name}\n💰 Доход: {fmt(biz_income)}/3ч")
    except Exception:
        pass


@dp.message(lambda m: (
    m.text and m.from_user and is_admin(m.from_user.id) and
    m.reply_to_message is None and
    m.text.lower().startswith("выдать работу ") and "@" in m.text
))
async def admin_give_job_username(message: types.Message):
    parts = message.text.strip().split()
    try:
        at_idx = next(i for i, p in enumerate(parts) if p.startswith("@"))
        username = parts[at_idx][1:]
        job_name = " ".join(parts[at_idx + 1:])
    except Exception:
        await message.answer("❌ Формат: выдать работу @ник [название работы]")
        return
    if not job_name:
        await message.answer("❌ Укажи название работы.")
        return
    target = db.get_user_by_username(username)
    if not target:
        return
    matched = next((j for j in ALL_JOBS.keys() if j.lower() == job_name.lower()), None)
    if not matched:
        await message.answer(f"❌ Работа не найдена: {job_name}")
        return
    salary = ALL_JOBS[matched]
    db.set_job(target[0], matched)
    db.add_log(message.from_user.id, 'give_job', f"{username}:{matched}", salary)
    await message.answer(f"✅ @{username} назначена работа: {matched} ({fmt(salary)}/зп)")
    try:
        await bot.send_message(target[0], f"💼 Вам назначена работа: {matched}\n💵 Зарплата: {fmt(salary)}")
    except Exception:
        pass


@dp.message(lambda m: m.text and m.text.lower().startswith("дать ") and m.from_user and is_admin(m.from_user.id) and m.reply_to_message is None and "@" in m.text)
async def admin_dat_cmd(message: types.Message):
    parts = message.text.strip().split()
    try:
        amount = int(parts[1])
        username = parts[2].lstrip("@")
    except Exception:
        await message.answer("❌ Формат: дать [сумма] @никнейм")
        return
    target = db.get_user_by_username(username)
    if not target:
        return
    db.update_balance(target[0], amount)
    db.add_log(target[0], 'admin_give_money', f'admin {message.from_user.id}', amount, message.from_user.id)
    await message.answer(f"✅ Выдано {fmt(amount)} → @{username}")
    try:
        await bot.send_message(target[0], f"💰 Вам выдано {fmt(amount)} администратором.")
    except Exception:
        pass


@dp.message(lambda m: m.text and m.text.lower().startswith("снять ") and m.from_user and is_admin(m.from_user.id) and "@" in m.text and m.reply_to_message is None)
async def admin_take_money_cmd(message: types.Message):
    parts = message.text.strip().split()
    try:
        amount = int(parts[1])
        username = next(p[1:] for p in parts if p.startswith("@"))
    except Exception:
        await message.answer("❌ Формат: снять [сумма] @никнейм")
        return
    target = db.get_user_by_username(username)
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    db.update_balance(target[0], -amount)
    db.add_log(target[0], 'admin_take_money', f'admin {message.from_user.id}', amount, message.from_user.id)
    await message.answer(f"✅ Снято {fmt(amount)} у @{username}")


@dp.message(lambda m: m.text and m.text.lower().startswith("забрать авто") and m.from_user and is_admin(m.from_user.id) and m.reply_to_message is None)
async def seize_cars_cmd(message: types.Message):
    username = next((p[1:] for p in message.text.split() if p.startswith("@")), None)
    if not username:
        await message.answer("❌ Формат: забрать авто @никнейм")
        return
    target = db.get_user_by_username(username)
    if not target:
        await message.answer("❌ Игрок не найден")
        return
    count = db.remove_all_cars(target[0])
    db.add_log(target[0], 'seize_cars', f'{count} авто', 0, message.from_user.id)
    await message.answer(f"✅ У @{username} изъято авто: {count} шт.")


@dp.message(lambda m: m.text and m.text.lower().strip() == "администраторы" and m.from_user and is_admin(m.from_user.id))
async def list_admins_cmd(message: types.Message):
    import datetime as _dt
    lines = ["👑 <b>Администраторы Advance RP:</b>\n"]
    lines.append("<b>🔑 Основатели:</b>")
    for uid in config.ADMIN_IDS:
        u = db.get_user(uid)
        name = f"@{u[1]}" if u and u[1] else f"ID:{uid}"
        lines.append(f"  • {name}")
    db_admins = db.get_admins()
    if db_admins:
        lines.append("\n<b>👮 Администраторы (DB):</b>")
        for uid, granted_by, granted_at in db_admins:
            u = db.get_user(uid)
            name = f"@{u[1]}" if u and u[1] else f"ID:{uid}"
            dt = _dt.datetime.fromtimestamp(granted_at).strftime('%d.%m.%Y')
            lines.append(f"  • {name} (с {dt})")
    await message.answer("\n".join(lines), parse_mode="HTML")


# ==================== ОТВЕТ НА СООБЩЕНИЕ (ADMIN) ====================

@dp.message(lambda m: (
    m.reply_to_message is not None and
    m.text is not None and
    m.from_user is not None and
    is_admin(m.from_user.id)
))
async def admin_reply_cmd(message: types.Message):
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    text = message.text.lower().strip()
    parts = message.text.strip().split()

    if not db.get_user(target_id):
        return

    if text.startswith("выдать работу") or text.startswith("дать работу"):
        if len(parts) < 3:
            await message.answer("❌ Формат: выдать работу [название]")
            return
        job_name = " ".join(parts[2:])
        matched = next((j for j in ALL_JOBS.keys() if j.lower() == job_name.lower()), None)
        if not matched:
            await message.answer(f"❌ Работа не найдена: {job_name}")
            return
        salary = ALL_JOBS[matched]
        db.set_job(target_id, matched)
        await message.answer(f"✅ Назначена работа [{matched}] → @{target_user.username or target_id}")
        try:
            await bot.send_message(target_id, f"💼 Вам назначена работа: {matched}\n💵 Зарплата: {fmt(salary)}")
        except Exception:
            pass

    elif text.startswith("выдать авто"):
        try:
            car_id = int(parts[-1])
        except Exception:
            await message.answer("❌ Формат: выдать авто [номер]")
            return
        car = get_car(car_id)
        if not car:
            await message.answer(f"❌ Авто #{car_id} не найдено.")
            return
        car_name, _ = car
        db.add_car(target_id, car_id, car_name)
        await message.answer(f"✅ @{target_user.username or target_id} получил авто: {car_name}")
        try:
            await bot.send_message(target_id, f"🚗 Вам выдали автомобиль: {car_name}")
        except Exception:
            pass

    elif text.startswith("выдать бизнес"):
        try:
            biz_id = int(parts[-1])
        except Exception:
            await message.answer("❌ Формат: выдать бизнес [номер]")
            return
        if biz_id not in BUSINESSES:
            await message.answer(f"❌ Бизнес #{biz_id} не найден.")
            return
        biz_name, _, biz_income = BUSINESSES[biz_id]
        db.add_business(target_id, biz_id, biz_name, biz_income)
        await message.answer(f"✅ @{target_user.username or target_id} получил бизнес: {biz_name}")
        try:
            await bot.send_message(target_id, f"🏢 Вам выдали бизнес: {biz_name}\n💰 Доход: {fmt(biz_income)}/3ч")
        except Exception:
            pass

    elif text.startswith("х2 вкл"):
        db.set_x2(target_id, True)
        await message.answer(f"✅ Х2 бонус ВКЛЮЧЁН для @{target_user.username or target_id} 🔥")

    elif text.startswith("х2 выкл"):
        db.set_x2(target_id, False)
        await message.answer(f"✅ Х2 бонус ВЫКЛЮЧЕН для @{target_user.username or target_id}")

    elif text.startswith("забрать авто"):
        count = db.remove_all_cars(target_id)
        db.add_log(target_id, 'seize_cars', f'{count} авто', 0, message.from_user.id)
        await message.answer(f"✅ У @{target_user.username or target_id} изъято авто: {count} шт.")

    elif text.startswith("забрать бизнес"):
        count = db.remove_all_businesses(target_id)
        db.add_log(target_id, 'seize_businesses', f'{count} бизнесов', 0, message.from_user.id)
        await message.answer(f"✅ У @{target_user.username or target_id} изъято бизнесов: {count} шт.")

    elif text.startswith("забрать недвижимость") or text.startswith("забрать квартиру"):
        count = db.remove_all_apartments(target_id)
        db.add_log(target_id, 'seize_apartments', f'{count} объектов', 0, message.from_user.id)
        await message.answer(f"✅ У @{target_user.username or target_id} изъято недвижимости: {count} шт.")

    elif text.startswith("выдать") or text.startswith("дать"):
        try:
            amount = int(parts[1])
        except Exception:
            await message.answer("❌ Формат: выдать [сумма]")
            return
        db.update_balance(target_id, amount)
        db.add_log(target_id, 'admin_give_money', f'admin {message.from_user.id}', amount, message.from_user.id)
        await message.answer(f"✅ Выдано {fmt(amount)} → @{target_user.username or target_id}")
        try:
            await bot.send_message(target_id, f"💰 Вам выдано {fmt(amount)} администратором.")
        except Exception:
            pass

    elif text.startswith("снять"):
        try:
            amount = int(parts[1])
        except Exception:
            await message.answer("❌ Формат: снять [сумма]")
            return
        db.update_balance(target_id, -amount)
        db.add_log(target_id, 'admin_take_money', f'admin {message.from_user.id}', amount, message.from_user.id)
        await message.answer(f"✅ Снято {fmt(amount)} у @{target_user.username or target_id}")

    elif text.startswith("бан"):
        db.ban_user(target_id)
        await message.answer(f"✅ Игрок @{target_user.username or target_id} заблокирован")

    elif text.startswith("разбан"):
        db.unban_user(target_id)
        await message.answer(f"✅ Игрок @{target_user.username or target_id} разблокирован")


# ==================== ПЕРЕВОД ОТВЕТОМ ====================

@dp.message(lambda m: (
    m.text and m.text.lower().startswith("дать ") and
    m.reply_to_message is not None and
    m.from_user is not None and
    not is_admin(m.from_user.id)
))
async def player_give_reply_cmd(message: types.Message):
    user = db.get_user(message.from_user.id)
    status = check_user(user)
    if status == "not_registered":
        await message.answer("❌ Вы не зарегистрированы. Напишите /start")
        return
    if status == "banned":
        await message.answer("⛔ Вы заблокированы.")
        return
    target_user = message.reply_to_message.from_user
    if target_user.id == message.from_user.id:
        await message.answer("❌ Нельзя переводить самому себе")
        return
    target = db.get_user(target_user.id)
    if not target:
        return
    try:
        amount = int(message.text.strip().split()[1])
    except Exception:
        await message.answer("❌ Формат: дать [сумма]")
        return
    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше 0")
        return
    balance = user[4]
    if balance < amount:
        await message.answer(f"❌ Недостаточно средств. Ваш баланс: {fmt(balance)}")
        return
    db.update_balance(message.from_user.id, -amount)
    db.update_balance(target_user.id, amount)
    db.add_log(message.from_user.id, 'transfer', f'→ {target_user.id}', amount)
    sender = message.from_user.username or message.from_user.first_name
    name = target_user.username or target_user.first_name
    await message.answer(f"✅ Переведено {fmt(amount)} → {name}")
    try:
        await bot.send_message(target_user.id, f"💸 Вам перевели {fmt(amount)} от @{sender}")
    except Exception:
        pass


# ==================== ДОБАВЛЕНИЕ В КАТАЛОГ (ADMIN FSM) ====================

def _next_cat_id(current_dict: dict, item_type: str) -> int:
    db_ids = {r[2] for r in db.get_catalog_items(item_type)}
    all_ids = set(current_dict.keys()) | db_ids
    return max(all_ids) + 1 if all_ids else 1


def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="catalog_cancel")]
    ])


@dp.callback_query(F.data == "catalog_cancel")
async def cb_catalog_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text("❌ Операция отменена.")
    except Exception:
        await callback.message.answer("❌ Отменено.")
    await callback.answer()


# ========== ADD CAR FSM ==========

@dp.message(lambda m: m.text and m.from_user and is_admin(m.from_user.id) and
            m.text.lower().strip() in ["добавить машину", "добавить авто", "добавить автомобиль"])
async def admin_addcar_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🚗 <b>Добавление автомобиля в каталог</b>\n\n"
        "Шаг 1/4 — Введи <b>название</b>:\n"
        "<i>Пример: Lada Vesta Sport — 145 л.с.</i>",
        parse_mode="HTML", reply_markup=_cancel_kb()
    )
    await state.set_state(AddCarFSM.name)


@dp.message(AddCarFSM.name)
async def addcar_fsm_name(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(car_name=message.text.strip())
    await message.answer(
        "💰 Шаг 2/4 — Введи <b>цену</b> в ₽ (только цифры):\n"
        "<i>Пример: 1500000</i>",
        parse_mode="HTML", reply_markup=_cancel_kb()
    )
    await state.set_state(AddCarFSM.price)


@dp.message(AddCarFSM.price)
async def addcar_fsm_price(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        price = int(message.text.strip().replace(" ", "").replace("₽", ""))
        assert price > 0
    except Exception:
        await message.answer("❌ Введи корректную сумму (только цифры):", reply_markup=_cancel_kb())
        return
    await state.update_data(car_price=price)
    await message.answer(
        "📝 Шаг 3/4 — Введи <b>описание</b> (или «—» чтобы пропустить):",
        parse_mode="HTML", reply_markup=_cancel_kb()
    )
    await state.set_state(AddCarFSM.description)


@dp.message(AddCarFSM.description)
async def addcar_fsm_desc(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    skip_vals = {"—", "-", "нет", "пропустить", "skip"}
    desc = "" if message.text.strip().lower() in skip_vals else message.text.strip()
    await state.update_data(car_desc=desc)
    await message.answer(
        "⚙️ Шаг 4/4 — Введи <b>характеристики</b> (или «—» пропустить):\n"
        "<i>Пример: Мощность: 145 л.с. | КПП: автомат</i>",
        parse_mode="HTML", reply_markup=_cancel_kb()
    )
    await state.set_state(AddCarFSM.specs)


@dp.message(AddCarFSM.specs)
async def addcar_fsm_specs(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    skip_vals = {"—", "-", "нет", "пропустить", "skip"}
    specs = "" if message.text.strip().lower() in skip_vals else message.text.strip()
    data  = await state.get_data()
    name  = data["car_name"]
    price = data["car_price"]
    desc  = data.get("car_desc", "")
    gid   = _next_cat_id(CARS, 'car')
    await state.update_data(car_specs=specs, car_game_id=gid)

    preview = (
        f"🚗 <b>Предпросмотр</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <b>{gid}</b>\n"
        f"📌 Название: <b>{name}</b>\n"
        f"💰 Цена: <b>{fmt(price)}</b>\n"
    )
    if desc:  preview += f"📝 Описание: {desc}\n"
    if specs: preview += f"⚙️ Характеристики: {specs}\n"
    preview += "\nПодтвердить добавление в каталог?"

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Добавить",  callback_data="addcar_confirm"),
        InlineKeyboardButton(text="❌ Отмена",    callback_data="catalog_cancel"),
    ]])
    await message.answer(preview, parse_mode="HTML", reply_markup=kb)
    await state.set_state(AddCarFSM.confirm)


@dp.callback_query(AddCarFSM.confirm, F.data == "addcar_confirm")
async def addcar_fsm_confirm(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    data  = await state.get_data()
    name  = data["car_name"]
    price = data["car_price"]
    desc  = data.get("car_desc", "")
    specs = data.get("car_specs", "")
    gid   = data["car_game_id"]
    await state.clear()

    db.add_catalog_item('car', gid, name, price, 0, desc, specs, callback.from_user.id)
    CARS[gid] = (name, price)
    db.add_log(callback.from_user.id, 'admin_addcatalog_car', f"#{gid}: {name}", price)

    await callback.message.edit_text(
        f"✅ <b>Автомобиль добавлен!</b>\n\n"
        f"🆔 ID: {gid} | 📌 {name}\n"
        f"💰 Цена: {fmt(price)}\n\n"
        f"Игроки могут купить:\n<code>купить авто {gid}</code>",
        parse_mode="HTML"
    )
    await callback.answer("✅ Добавлено!")


# ========== ADD BUSINESS FSM ==========

@dp.message(lambda m: m.text and m.from_user and is_admin(m.from_user.id) and
            m.text.lower().strip() in ["добавить бизнес", "добавить бизнес в каталог"])
async def admin_addbiz_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏢 <b>Добавление бизнеса в каталог</b>\n\n"
        "Шаг 1/4 — Введи <b>название</b>:",
        parse_mode="HTML", reply_markup=_cancel_kb()
    )
    await state.set_state(AddBizFSM.name)


@dp.message(AddBizFSM.name)
async def addbiz_fsm_name(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(biz_name=message.text.strip())
    await message.answer(
        "💰 Шаг 2/4 — Введи <b>цену</b> в ₽ (только цифры):",
        parse_mode="HTML", reply_markup=_cancel_kb()
    )
    await state.set_state(AddBizFSM.price)


@dp.message(AddBizFSM.price)
async def addbiz_fsm_price(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        price = int(message.text.strip().replace(" ", "").replace("₽", ""))
        assert price > 0
    except Exception:
        await message.answer("❌ Введи корректную сумму:", reply_markup=_cancel_kb())
        return
    await state.update_data(biz_price=price)
    await message.answer(
        "📈 Шаг 3/4 — Введи <b>доход за 3 часа</b> в ₽:",
        parse_mode="HTML", reply_markup=_cancel_kb()
    )
    await state.set_state(AddBizFSM.income)


@dp.message(AddBizFSM.income)
async def addbiz_fsm_income(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        income = int(message.text.strip().replace(" ", "").replace("₽", ""))
        assert income >= 0
    except Exception:
        await message.answer("❌ Введи корректный доход:", reply_markup=_cancel_kb())
        return
    await state.update_data(biz_income=income)
    await message.answer(
        "📝 Шаг 4/4 — Введи <b>описание</b> (или «—» чтобы пропустить):",
        parse_mode="HTML", reply_markup=_cancel_kb()
    )
    await state.set_state(AddBizFSM.description)


@dp.message(AddBizFSM.description)
async def addbiz_fsm_desc(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    skip_vals = {"—", "-", "нет", "пропустить", "skip"}
    desc   = "" if message.text.strip().lower() in skip_vals else message.text.strip()
    data   = await state.get_data()
    name   = data["biz_name"]
    price  = data["biz_price"]
    income = data["biz_income"]
    gid    = _next_cat_id(BUSINESSES, 'biz')
    await state.update_data(biz_desc=desc, biz_game_id=gid)

    preview = (
        f"🏢 <b>Предпросмотр</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <b>{gid}</b>\n"
        f"📌 Название: <b>{name}</b>\n"
        f"💰 Цена: <b>{fmt(price)}</b>\n"
        f"📈 Доход: <b>{fmt(income)}/3ч</b>\n"
    )
    if desc: preview += f"📝 Описание: {desc}\n"
    preview += "\nПодтвердить добавление?"

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Добавить",  callback_data="addbiz_confirm"),
        InlineKeyboardButton(text="❌ Отмена",    callback_data="catalog_cancel"),
    ]])
    await message.answer(preview, parse_mode="HTML", reply_markup=kb)
    await state.set_state(AddBizFSM.confirm)


@dp.callback_query(AddBizFSM.confirm, F.data == "addbiz_confirm")
async def addbiz_fsm_confirm(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    data   = await state.get_data()
    name   = data["biz_name"]
    price  = data["biz_price"]
    income = data["biz_income"]
    desc   = data.get("biz_desc", "")
    gid    = data["biz_game_id"]
    await state.clear()

    db.add_catalog_item('biz', gid, name, price, income, desc, '', callback.from_user.id)
    BUSINESSES[gid] = (name, price, income)
    db.add_log(callback.from_user.id, 'admin_addcatalog_biz', f"#{gid}: {name}", price)

    await callback.message.edit_text(
        f"✅ <b>Бизнес добавлен!</b>\n\n"
        f"🆔 ID: {gid} | 📌 {name}\n"
        f"💰 Цена: {fmt(price)}\n"
        f"📈 Доход: {fmt(income)}/3ч\n\n"
        f"Игроки могут купить:\n<code>купить бизнес {gid}</code>",
        parse_mode="HTML"
    )
    await callback.answer("✅ Добавлено!")


# ========== ADD APARTMENT FSM ==========

@dp.message(lambda m: m.text and m.from_user and is_admin(m.from_user.id) and
            m.text.lower().strip() in ["добавить недвижимость", "добавить квартиру", "добавить дом"])
async def admin_addapt_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏠 <b>Добавление недвижимости в каталог</b>\n\n"
        "Шаг 1/3 — Введи <b>название</b>:",
        parse_mode="HTML", reply_markup=_cancel_kb()
    )
    await state.set_state(AddAptFSM.name)


@dp.message(AddAptFSM.name)
async def addapt_fsm_name(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(apt_name=message.text.strip())
    await message.answer(
        "💰 Шаг 2/3 — Введи <b>цену</b> в ₽ (только цифры):",
        parse_mode="HTML", reply_markup=_cancel_kb()
    )
    await state.set_state(AddAptFSM.price)


@dp.message(AddAptFSM.price)
async def addapt_fsm_price(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        price = int(message.text.strip().replace(" ", "").replace("₽", ""))
        assert price > 0
    except Exception:
        await message.answer("❌ Введи корректную сумму:", reply_markup=_cancel_kb())
        return
    await state.update_data(apt_price=price)
    await message.answer(
        "📝 Шаг 3/3 — Введи <b>описание</b> (или «—» чтобы пропустить):",
        parse_mode="HTML", reply_markup=_cancel_kb()
    )
    await state.set_state(AddAptFSM.description)


@dp.message(AddAptFSM.description)
async def addapt_fsm_desc(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    skip_vals = {"—", "-", "нет", "пропустить", "skip"}
    desc  = "" if message.text.strip().lower() in skip_vals else message.text.strip()
    data  = await state.get_data()
    name  = data["apt_name"]
    price = data["apt_price"]
    gid   = _next_cat_id(APARTMENTS, 'apt')
    await state.update_data(apt_desc=desc, apt_game_id=gid)

    preview = (
        f"🏠 <b>Предпросмотр</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <b>{gid}</b>\n"
        f"📌 Название: <b>{name}</b>\n"
        f"💰 Цена: <b>{fmt(price)}</b>\n"
    )
    if desc: preview += f"📝 Описание: {desc}\n"
    preview += "\nПодтвердить добавление?"

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Добавить",  callback_data="addapt_confirm"),
        InlineKeyboardButton(text="❌ Отмена",    callback_data="catalog_cancel"),
    ]])
    await message.answer(preview, parse_mode="HTML", reply_markup=kb)
    await state.set_state(AddAptFSM.confirm)


@dp.callback_query(AddAptFSM.confirm, F.data == "addapt_confirm")
async def addapt_fsm_confirm(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    data  = await state.get_data()
    name  = data["apt_name"]
    price = data["apt_price"]
    desc  = data.get("apt_desc", "")
    gid   = data["apt_game_id"]
    await state.clear()

    db.add_catalog_item('apt', gid, name, price, 0, desc, '', callback.from_user.id)
    APARTMENTS[gid] = (name, price)
    db.add_log(callback.from_user.id, 'admin_addcatalog_apt', f"#{gid}: {name}", price)

    await callback.message.edit_text(
        f"✅ <b>Недвижимость добавлена!</b>\n\n"
        f"🆔 ID: {gid} | 📌 {name}\n"
        f"💰 Цена: {fmt(price)}\n\n"
        f"Игроки могут купить:\n<code>купить недвижимость {gid}</code>",
        parse_mode="HTML"
    )
    await callback.answer("✅ Добавлено!")


# ==================== ЕЖЕДНЕВНЫЙ БОНУС ====================

_BONUS_TYPE_EMOJI = {
    'money': '💵',
    'car':   '🚗',
    'biz':   '🏢',
    'vip':   '⭐',
    'case':  '📦',
    'item':  '🎁',
}

_BONUS_TYPE_LABEL = {
    'money': 'Деньги',
    'car':   'Автомобиль',
    'biz':   'Бизнес',
    'vip':   'VIP (x2 зарплата)',
    'case':  'Кейс',
    'item':  'Предмет',
}


def _bonus_display(reward_row) -> str:
    """Return a one-line display string for a reward row."""
    _, rtype, rvalue, desc, *_ = reward_row
    emoji = _BONUS_TYPE_EMOJI.get(rtype, '🎁')
    if desc:
        return f"{emoji} {desc}"
    if rtype == 'money':
        try:
            return f"{emoji} {fmt(int(rvalue))}"
        except Exception:
            pass
    return f"{emoji} {_BONUS_TYPE_LABEL.get(rtype, rtype)}"


def _seconds_to_hm(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    if h > 0:
        return f"{h}ч {m:02d}м"
    return f"{m}м {sec % 60:02d}с"


def _build_bonus_menu_text(uid: int) -> tuple[str, bool]:
    """Returns (text, can_claim)."""
    import time as _time
    state   = db.get_user_bonus_state(uid)
    rewards = db.get_active_daily_bonus_rewards()
    now     = int(_time.time())
    last    = state["last_claimed"]
    cday    = state["current_day"]
    streak  = state["streak"]

    # Detect pending reset (>48h gap)
    reset_warning = last > 0 and (now - last) > 48 * 3600

    # Cooldown
    can_claim    = (last == 0) or (now - last >= 24 * 3600)
    secs_left    = max(0, 24 * 3600 - (now - last)) if last > 0 else 0

    # Next reward for display
    next_reward = db.get_daily_bonus_reward(cday)
    if not next_reward or not next_reward[4]:
        next_reward = rewards[0] if rewards else None

    next_str = _bonus_display(next_reward) if next_reward else "—"
    max_day  = db.get_max_bonus_day()

    timer_line = (
        f"✅ Готово к получению!" if can_claim
        else f"⏳ Следующий бонус через: <b>{_seconds_to_hm(secs_left)}</b>"
    )
    reset_line = (
        "\n⚠️ <b>Серия будет сброшена — забери бонус!</b>"
        if reset_warning else ""
    )

    text = (
        f"🎁 <b>Ежедневный бонус</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📅 День серии: <b>{cday}</b> / {max_day}\n"
        f"🔥 Дней подряд: <b>{streak}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🎀 Следующая награда:\n<b>{next_str}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{timer_line}{reset_line}"
    )
    return text, can_claim


def _bonus_menu_kb(uid: int, can_claim: bool, is_adm: bool) -> InlineKeyboardMarkup:
    u = str(uid)
    rows = []
    if can_claim:
        rows.append([InlineKeyboardButton(text="🎁 Забрать бонус!", callback_data=f"db_claim|{u}")])
    else:
        rows.append([InlineKeyboardButton(text="🔒 Бонус уже получен", callback_data="db_noop")])
    rows.append([InlineKeyboardButton(text="📅 Все награды", callback_data=f"db_all|{u}|0")])
    if is_adm:
        rows.append([InlineKeyboardButton(text="⚙️ Управление бонусами", callback_data=f"db_admin|{u}")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_info|{u}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _all_rewards_kb(uid: int, rewards: list, page: int) -> InlineKeyboardMarkup:
    u        = str(uid)
    per_page = 7
    total    = len(rewards)
    pages    = max(1, (total + per_page - 1) // per_page)
    page     = max(0, min(page, pages - 1))
    chunk    = rewards[page * per_page:(page + 1) * per_page]

    rows = []
    for r in chunk:
        day, rtype, rvalue, desc, active = r
        label   = _bonus_display(r)
        status  = "" if active else " 🔴"
        rows.append([InlineKeyboardButton(
            text=f"День {day}: {label}{status}",
            callback_data="db_noop"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"db_all|{u}|{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{pages}", callback_data="db_noop"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"db_all|{u}|{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"daily_bonus|{u}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _admin_bonus_main_kb(uid: int) -> InlineKeyboardMarkup:
    u = str(uid)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список наград", callback_data=f"dba_list|{u}|0")],
        [
            InlineKeyboardButton(text="➕ Добавить / Изменить день", callback_data=f"dba_add|{u}"),
            InlineKeyboardButton(text="🗑 Удалить день", callback_data=f"dba_del|{u}"),
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"daily_bonus|{u}")],
    ])


def _admin_reward_list_kb(uid: int, rewards: list, page: int) -> InlineKeyboardMarkup:
    u        = str(uid)
    per_page = 6
    total    = len(rewards)
    pages    = max(1, (total + per_page - 1) // per_page)
    page     = max(0, min(page, pages - 1))
    chunk    = rewards[page * per_page:(page + 1) * per_page]

    rows = []
    for r in chunk:
        day, rtype, rvalue, desc, active = r
        label  = _bonus_display(r)
        status = "✅" if active else "🔴"
        rows.append([
            InlineKeyboardButton(text=f"{status} День {day}: {label[:28]}", callback_data="db_noop"),
            InlineKeyboardButton(text="✏️", callback_data=f"dba_edit|{u}|{day}"),
            InlineKeyboardButton(text="🗑", callback_data=f"dba_delc|{u}|{day}"),
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"dba_list|{u}|{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{pages}", callback_data="db_noop"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"dba_list|{u}|{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"db_admin|{u}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _type_select_kb(uid: int) -> InlineKeyboardMarkup:
    u = str(uid)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💵 Деньги",     callback_data=f"dbt_money|{u}"),
            InlineKeyboardButton(text="🚗 Авто",       callback_data=f"dbt_car|{u}"),
        ],
        [
            InlineKeyboardButton(text="🏢 Бизнес",     callback_data=f"dbt_biz|{u}"),
            InlineKeyboardButton(text="⭐ VIP (x2)",   callback_data=f"dbt_vip|{u}"),
        ],
        [
            InlineKeyboardButton(text="📦 Кейс",       callback_data=f"dbt_case|{u}"),
            InlineKeyboardButton(text="🎁 Предмет",    callback_data=f"dbt_item|{u}"),
        ],
        [InlineKeyboardButton(text="❌ Отмена",        callback_data=f"db_admin|{u}")],
    ])


async def _give_bonus_reward(uid: int, reward_row: tuple, bot_instance):
    """Apply a bonus reward to a user and return a description string."""
    _, rtype, rvalue, desc, *_ = reward_row

    if rtype == 'money':
        try:
            amount = int(rvalue)
        except Exception:
            amount = 10_000
        db.update_balance(uid, amount)
        db.add_log(uid, 'daily_bonus_money', desc, amount)
        return f"💵 {fmt(amount)}"

    elif rtype == 'car':
        car_name = desc.lstrip("🚗 ").strip() if desc else "Автомобиль"
        # Try looking up by id in CARS dict
        try:
            cid = int(rvalue)
            if cid > 0 and cid in CARS:
                car_name = CARS[cid][0]
        except Exception:
            cid = 0
        db.add_car(uid, cid, car_name)
        db.add_log(uid, 'daily_bonus_car', car_name, 0)
        return f"🚗 {car_name}"

    elif rtype == 'biz':
        biz_name   = desc.lstrip("🏢 ").strip() if desc else "Бизнес"
        biz_income = 15_000
        try:
            bid = int(rvalue)
            if bid > 0 and bid in BUSINESSES:
                biz_name   = BUSINESSES[bid][0]
                biz_income = BUSINESSES[bid][2]
        except Exception:
            bid = 0
        db.add_business(uid, bid, biz_name, biz_income)
        db.add_log(uid, 'daily_bonus_biz', biz_name, biz_income)
        return f"🏢 {biz_name} (доход {fmt(biz_income)}/3ч)"

    elif rtype == 'vip':
        db.set_x2(uid, True)
        db.add_log(uid, 'daily_bonus_vip', 'x2 зарплата', 0)
        return "⭐ VIP-статус (x2 зарплата)"

    elif rtype == 'case':
        # Random cash prize as a simple case reward
        prizes = [5_000, 10_000, 20_000, 30_000, 50_000, 75_000, 100_000]
        import random as _rnd
        amount = _rnd.choice(prizes)
        db.update_balance(uid, amount)
        db.add_log(uid, 'daily_bonus_case', f'кейс: {amount}', amount)
        return f"📦 Кейс → выпало {fmt(amount)}"

    else:  # item
        item_desc = desc if desc else rvalue
        db.add_log(uid, 'daily_bonus_item', item_desc, 0)
        return f"🎁 {item_desc}"


# ---------- Callback: открыть меню ежедневного бонуса ----------

@dp.callback_query(F.data.startswith("daily_bonus|"))
async def cb_daily_bonus_menu(callback: types.CallbackQuery):
    uid = await _assert_owner(callback)
    if uid is None:
        return
    user = db.get_user(uid)
    if check_user(user) != "ok":
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    text, can_claim = _build_bonus_menu_text(uid)
    kb = _bonus_menu_kb(uid, can_claim, is_admin(uid))
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ---------- Callback: noop (заглушка для "мёртвых" кнопок) ----------

@dp.callback_query(F.data == "db_noop")
async def cb_db_noop(callback: types.CallbackQuery):
    await callback.answer()


# ---------- Callback: забрать бонус ----------

@dp.callback_query(F.data.startswith("db_claim|"))
async def cb_db_claim(callback: types.CallbackQuery):
    uid = await _assert_owner(callback)
    if uid is None:
        return
    user = db.get_user(uid)
    if check_user(user) != "ok":
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    result = db.claim_daily_bonus(uid)

    if not result["success"]:
        await callback.answer("⏳ Бонус уже получен сегодня. Возвращайся завтра!", show_alert=True)
        return

    reward_desc = await _give_bonus_reward(uid, result["reward"], bot)

    reset_text = "\n♻️ <i>Серия была сброшена (прошло >48ч)</i>" if result["reset"] else ""
    text = (
        f"🎉 <b>Бонус получен!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📅 День <b>{result['day']}</b>\n"
        f"🎀 Награда: <b>{reward_desc}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Следующий бонус доступен через <b>24 часа</b>.{reset_text}\n\n"
        f"🔜 Завтра: день <b>{result['next_day']}</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Все награды",    callback_data=f"db_all|{uid}|0")],
        [InlineKeyboardButton(text="🔙 К профилю",     callback_data=f"back_to_info|{uid}")],
    ])
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer("🎁 Бонус получен!", show_alert=False)


# ---------- Callback: все награды (для игрока) ----------

@dp.callback_query(F.data.startswith("db_all|"))
async def cb_db_all_rewards(callback: types.CallbackQuery):
    uid = await _assert_owner(callback)
    if uid is None:
        return
    parts = callback.data.split("|")
    page  = int(parts[2]) if len(parts) > 2 else 0

    state   = db.get_user_bonus_state(uid)
    cday    = state["current_day"]
    rewards = db.get_active_daily_bonus_rewards()

    lines = [f"📅 <b>Все ежедневные награды</b>\n(текущий день: <b>{cday}</b>)\n━━━━━━━━━━━━━━━━━━━"]
    kb = _all_rewards_kb(uid, rewards, page)
    # Build text from visible chunk
    per_page = 7
    pages    = max(1, (len(rewards) + per_page - 1) // per_page)
    page     = max(0, min(page, pages - 1))
    chunk    = rewards[page * per_page:(page + 1) * per_page]
    for r in chunk:
        day, rtype, rvalue, desc, active = r
        marker = "👉 " if day == cday else ("✅ " if day < cday else "")
        label  = _bonus_display(r)
        lines.append(f"{marker}День {day}: {label}")
    text = "\n".join(lines)

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ==================== ЕЖЕДНЕВНЫЙ БОНУС — АДМИН ====================

@dp.callback_query(F.data.startswith("db_admin|"))
async def cb_db_admin(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.clear()   # сбрасываем любой активный FSM
    uid = callback.from_user.id
    kb  = _admin_bonus_main_kb(uid)
    text = (
        "⚙️ <b>Управление ежедневными бонусами</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Выберите действие:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("dba_list|"))
async def cb_dba_list(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    uid   = callback.from_user.id
    parts = callback.data.split("|")
    page  = int(parts[2]) if len(parts) > 2 else 0

    rewards = db.get_all_daily_bonus_rewards()
    kb      = _admin_reward_list_kb(uid, rewards, page)
    text    = (
        f"📋 <b>Список наград</b> — {len(rewards)} дней\n"
        "Нажмите ✏️ для редактирования, 🗑 для удаления."
    )
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ---------- FSM: добавить / изменить день ----------

@dp.callback_query(F.data.startswith("dba_add|"))
async def cb_dba_add(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.update_data(db_editing_day=None)
    await callback.message.answer(
        "➕ <b>Добавить / изменить день</b>\n\n"
        "Введи номер дня (например: <code>15</code> или <code>30</code>):",
        parse_mode="HTML"
    )
    await state.set_state(DailyBonusAdminFSM.enter_day)
    await callback.answer()


@dp.callback_query(F.data.startswith("dba_edit|"))
async def cb_dba_edit(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    parts = callback.data.split("|")
    day   = int(parts[2])
    await state.update_data(db_editing_day=day)
    existing = db.get_daily_bonus_reward(day)
    info = f"\n\n📌 Текущая награда: {_bonus_display(existing)}" if existing else ""
    await callback.message.answer(
        f"✏️ <b>Редактирование дня {day}</b>{info}\n\n"
        f"День уже задан. Теперь выбери <b>тип награды</b>:",
        reply_markup=_type_select_kb(callback.from_user.id),
        parse_mode="HTML"
    )
    await state.set_state(DailyBonusAdminFSM.enter_type)
    await callback.answer()


@dp.message(DailyBonusAdminFSM.enter_day)
async def dba_fsm_day(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        day = int(message.text.strip())
        assert 1 <= day <= 9999
    except Exception:
        await message.answer("❌ Введи корректный номер дня (1–9999):")
        return
    existing = db.get_daily_bonus_reward(day)
    info = f"\n\n📌 Текущая награда: {_bonus_display(existing)}" if existing else ""
    await state.update_data(db_editing_day=day)
    await message.answer(
        f"✅ День <b>{day}</b>{info}\n\nВыбери тип награды:",
        reply_markup=_type_select_kb(message.from_user.id),
        parse_mode="HTML"
    )
    await state.set_state(DailyBonusAdminFSM.enter_type)


@dp.callback_query(DailyBonusAdminFSM.enter_type, F.data.startswith("dbt_"))
async def dba_fsm_type(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    rtype = callback.data.split("|")[0].split("_", 1)[1]  # money / car / biz / vip / case / item
    await state.update_data(db_reward_type=rtype)

    hints = {
        'money': 'Введи сумму в рублях (например: <code>50000</code>):',
        'car':   'Введи ID авто из каталога (например: <code>42</code>)\nили <code>0</code> для особого авто:',
        'biz':   'Введи ID бизнеса из каталога (например: <code>1</code>)\nили <code>0</code> для особого бизнеса:',
        'vip':   'Введи количество дней VIP (или <code>0</code> — бессрочно):',
        'case':  'Введи тип кейса или <code>basic</code> для стандартного:',
        'item':  'Введи название/описание предмета:',
    }
    await callback.message.edit_text(
        f"🔧 Тип: <b>{_BONUS_TYPE_LABEL.get(rtype, rtype)}</b>\n\n"
        + hints.get(rtype, "Введи значение:"),
        parse_mode="HTML"
    )
    await state.set_state(DailyBonusAdminFSM.enter_value)
    await callback.answer()


@dp.message(DailyBonusAdminFSM.enter_value)
async def dba_fsm_value(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    val = message.text.strip()
    await state.update_data(db_reward_value=val)
    data  = await state.get_data()
    rtype = data.get("db_reward_type", "money")

    # For money / numeric types auto-build a description
    auto_desc = ""
    if rtype == 'money':
        try:
            auto_desc = f"💵 {fmt(int(val))}"
        except Exception:
            pass
    elif rtype == 'car':
        try:
            cid = int(val)
            if cid > 0 and cid in CARS:
                auto_desc = f"🚗 {CARS[cid][0]}"
        except Exception:
            pass
    elif rtype == 'biz':
        try:
            bid = int(val)
            if bid > 0 and bid in BUSINESSES:
                auto_desc = f"🏢 {BUSINESSES[bid][0]}"
        except Exception:
            pass
    elif rtype == 'vip':
        auto_desc = "⭐ VIP (x2 зарплата)"
    elif rtype == 'case':
        auto_desc = "📦 Кейс"

    await state.update_data(db_auto_desc=auto_desc)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Использовать: {auto_desc or val}", callback_data="dba_use_auto_desc")],
        [InlineKeyboardButton(text="✏️ Ввести своё описание", callback_data="dba_custom_desc")],
    ]) if auto_desc else None

    if kb:
        await message.answer(
            "Хочешь использовать автоматическое описание или задать своё?",
            reply_markup=kb
        )
        await state.set_state(DailyBonusAdminFSM.enter_desc)
    else:
        await message.answer(
            f"Введи описание награды для отображения игрокам\n"
            f"(например: <code>🎁 Особый предмет</code>):",
            parse_mode="HTML"
        )
        await state.set_state(DailyBonusAdminFSM.enter_desc)


@dp.callback_query(DailyBonusAdminFSM.enter_desc, F.data == "dba_use_auto_desc")
async def dba_use_auto_desc(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    data = await state.get_data()
    await state.update_data(db_reward_desc=data.get("db_auto_desc", ""))
    await _dba_save(callback.message, state, callback.from_user.id)
    await callback.answer()


@dp.callback_query(DailyBonusAdminFSM.enter_desc, F.data == "dba_custom_desc")
async def dba_custom_desc(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    await callback.message.edit_text("✏️ Введи описание награды:")
    await callback.answer()


@dp.message(DailyBonusAdminFSM.enter_desc)
async def dba_fsm_desc(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(db_reward_desc=message.text.strip())
    await _dba_save(message, state, message.from_user.id)


async def _dba_save(msg_obj, state: FSMContext, admin_uid: int):
    """Persist the reward and show confirmation."""
    data  = await state.get_data()
    day   = data.get("db_editing_day")
    rtype = data.get("db_reward_type", "money")
    rval  = data.get("db_reward_value", "0")
    desc  = data.get("db_reward_desc", "")
    await state.clear()

    db.upsert_daily_bonus_reward(day, rtype, rval, desc)
    db.add_log(admin_uid, 'admin_bonus_edit', f"день {day}: {rtype}={rval}", 0)

    text = (
        f"✅ <b>Награда сохранена!</b>\n\n"
        f"📅 День: <b>{day}</b>\n"
        f"🔧 Тип: {_BONUS_TYPE_LABEL.get(rtype, rtype)}\n"
        f"💡 Значение: {rval}\n"
        f"📝 Описание: {desc}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ К управлению", callback_data=f"db_admin|{admin_uid}")],
    ])
    await msg_obj.answer(text, reply_markup=kb, parse_mode="HTML")


# ---------- FSM: удалить день ----------

@dp.callback_query(F.data.startswith("dba_del|"))
async def cb_dba_del(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.message.answer(
        "🗑 <b>Удалить день</b>\n\nВведи номер дня для удаления:",
        parse_mode="HTML"
    )
    await state.set_state(DailyBonusAdminFSM.confirm_del)
    await callback.answer()


@dp.callback_query(F.data.startswith("dba_delc|"))
async def cb_dba_delc_btn(callback: types.CallbackQuery, state: FSMContext):
    """Delete confirmation triggered from the list inline button."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    parts = callback.data.split("|")
    day   = int(parts[2])
    uid   = callback.from_user.id

    existing = db.get_daily_bonus_reward(day)
    if not existing:
        await callback.answer(f"❌ День {day} не найден.", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить",  callback_data=f"dba_do_del|{uid}|{day}"),
            InlineKeyboardButton(text="❌ Отмена",       callback_data=f"dba_list|{uid}|0"),
        ]
    ])
    await callback.message.answer(
        f"🗑 Удалить <b>день {day}</b>?\n"
        f"Награда: {_bonus_display(existing)}\n\n"
        f"<b>Это действие необратимо!</b>",
        reply_markup=kb, parse_mode="HTML"
    )
    await callback.answer()


@dp.message(DailyBonusAdminFSM.confirm_del)
async def dba_fsm_confirm_del(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        day = int(message.text.strip())
    except Exception:
        await message.answer("❌ Введи корректный номер дня:")
        return
    await state.clear()
    uid      = message.from_user.id
    existing = db.get_daily_bonus_reward(day)
    if not existing:
        await message.answer(f"❌ День {day} не найден в таблице.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить",  callback_data=f"dba_do_del|{uid}|{day}"),
            InlineKeyboardButton(text="❌ Отмена",       callback_data=f"dba_list|{uid}|0"),
        ]
    ])
    await message.answer(
        f"🗑 Удалить <b>день {day}</b>?\n"
        f"Награда: {_bonus_display(existing)}\n\n"
        f"<b>Это действие необратимо!</b>",
        reply_markup=kb, parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("dba_do_del|"))
async def cb_dba_do_del(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    parts = callback.data.split("|")
    uid   = int(parts[1])
    day   = int(parts[2])
    db.delete_daily_bonus_reward(day)
    db.add_log(uid, 'admin_bonus_del', f"день {day}", 0)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ К управлению", callback_data=f"db_admin|{uid}")],
    ])
    try:
        await callback.message.edit_text(
            f"✅ День <b>{day}</b> успешно удалён.",
            reply_markup=kb, parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            f"✅ День <b>{day}</b> удалён.",
            reply_markup=kb, parse_mode="HTML"
        )
    await callback.answer("🗑 Удалено")


# ==================== ЗАПУСК ====================

# ==================== ТОТАЛИЗАТОР — клавиатуры и хендлеры ====================

def _toto_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 Сделать ставку", callback_data="toto_matches"),
            InlineKeyboardButton(text="📋 Мои ставки",     callback_data="toto_mybets"),
        ],
        [
            InlineKeyboardButton(text="📊 История",  callback_data="toto_hist"),
            InlineKeyboardButton(text="ℹ️ Правила",  callback_data="toto_rules"),
        ],
    ])


def _toto_matches_kb(matches: list, page: int = 0) -> InlineKeyboardMarkup:
    PER_PAGE = 5
    start = page * PER_PAGE
    chunk = matches[start: start + PER_PAGE]
    rows  = []
    for m in chunk:
        dt    = datetime.fromtimestamp(m["match_time"], tz=timezone.utc) + timedelta(hours=3)
        t_str = dt.strftime("%d.%m %H:%M")
        ht    = m["home_team"][:13]
        at    = m["away_team"][:13]
        label = f"{m['league_flag']} {ht} — {at}  {t_str}"
        rows.append([InlineKeyboardButton(text=label,
                                          callback_data=f"toto_m|{m['match_id']}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Назад",   callback_data=f"toto_mp|{page - 1}"))
    if start + PER_PAGE < len(matches):
        nav.append(InlineKeyboardButton(text="Ещё ➡️",     callback_data=f"toto_mp|{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="toto_refresh"),
        InlineKeyboardButton(text="🔙 Меню",     callback_data="toto_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _toto_match_kb(m: dict) -> InlineKeyboardMarkup:
    mid = m["match_id"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"🟢 П1  {m['odds_home']:.2f}",
                                 callback_data=f"toto_b|{mid}|1"),
            InlineKeyboardButton(text=f"⚪ Х   {m['odds_draw']:.2f}",
                                 callback_data=f"toto_b|{mid}|X"),
            InlineKeyboardButton(text=f"🔵 П2  {m['odds_away']:.2f}",
                                 callback_data=f"toto_b|{mid}|2"),
        ],
        [InlineKeyboardButton(text="🔙 К матчам", callback_data="toto_matches")],
    ])


def _toto_amounts_kb(match_id: str, bet_type: str) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(_TOTO_BET_AMOUNTS), 2):
        row = []
        for a in _TOTO_BET_AMOUNTS[i: i + 2]:
            lbl = f"{a // 1_000}K ₽" if a < 1_000_000 else f"{a // 1_000_000}M ₽"
            row.append(InlineKeyboardButton(
                text=lbl, callback_data=f"toto_ba|{match_id}|{bet_type}|{a}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🔙 Назад",
                                      callback_data=f"toto_m|{match_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _toto_main_text() -> str:
    return (
        "⚽ <b>Футбольный тотализатор</b>\n\n"
        "Ставь на реальные матчи топ-лиг мира.\n"
        "Результаты — по итогам настоящих игр.\n\n"
        "🏴󠁧󠁢󠁥󠁮󠁧󠁿 АПЛ  🇷🇺 РПЛ  🇪🇸 Ла Лига\n"
        "🇩🇪 Бундеслига  🇮🇹 Серия А  🇫🇷 Лига 1\n\n"
        "Выбери раздел:"
    )


# ── текстовая команда ─────────────────────────────────────────────────────────

@dp.message(lambda m: m.text and m.text.lower() == "тотализатор")
async def toto_cmd(message: types.Message):
    if not await _require_game_chat(message):
        return
    user = db.get_user(message.from_user.id)
    status = check_user(user)
    if status == "not_registered":
        await message.answer("❌ Вы не зарегистрированы. Напишите /start")
        return
    if status == "banned":
        await message.answer("⛔ Вы заблокированы.")
        return
    await message.answer(_toto_main_text(), parse_mode="HTML",
                         reply_markup=_toto_menu_kb())


# ── callback: главное меню ────────────────────────────────────────────────────

@dp.callback_query(F.data == "toto_menu")
async def cb_toto_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(_toto_main_text(), parse_mode="HTML",
                                     reply_markup=_toto_menu_kb())
    await callback.answer()


# ── callback: список матчей ───────────────────────────────────────────────────

@dp.callback_query(F.data.in_({"toto_matches", "toto_refresh"}))
async def cb_toto_matches(callback: types.CallbackQuery):
    matches = db.toto_get_upcoming_matches()
    if not matches:
        await callback.answer(
            "⏳ Матчи ещё загружаются… Попробуйте через минуту.", show_alert=True)
        return
    text = (f"📅 <b>Доступные матчи</b> — {len(matches)} шт.\n\n"
            f"Выбери матч для ставки:")
    await callback.message.edit_text(text, parse_mode="HTML",
                                     reply_markup=_toto_matches_kb(matches, 0))
    await callback.answer("✅ Матчи обновлены!" if callback.data == "toto_refresh" else "")


@dp.callback_query(F.data.startswith("toto_mp|"))
async def cb_toto_page(callback: types.CallbackQuery):
    page    = int(callback.data.split("|")[1])
    matches = db.toto_get_upcoming_matches()
    if not matches:
        await callback.answer("Матчи не найдены", show_alert=True)
        return
    text = (f"📅 <b>Доступные матчи</b> — {len(matches)} шт.\n\n"
            f"Выбери матч для ставки:")
    await callback.message.edit_text(text, parse_mode="HTML",
                                     reply_markup=_toto_matches_kb(matches, page))
    await callback.answer()


# ── callback: карточка матча ──────────────────────────────────────────────────

@dp.callback_query(F.data.startswith("toto_m|"))
async def cb_toto_match(callback: types.CallbackQuery):
    match_id = callback.data.split("|")[1]
    m = db.toto_get_match(match_id)
    if not m:
        await callback.answer("❌ Матч не найден", show_alert=True)
        return
    if m["status"] != "pending" or m["match_time"] < int(time.time()) - 120 * 60:
        await callback.answer("⛔ Ставки на этот матч закрыты", show_alert=True)
        return
    dt    = datetime.fromtimestamp(m["match_time"], tz=timezone.utc) + timedelta(hours=3)
    t_str = dt.strftime("%d %b %Y, %H:%M МСК")
    text  = (
        f"{m['league_flag']} <b>{m['league']}</b>\n\n"
        f"🏠 <b>{m['home_team']}</b>\n"
        f"        🆚\n"
        f"✈️ <b>{m['away_team']}</b>\n\n"
        f"🕐 {t_str}\n\n"
        f"<b>Коэффициенты:</b>\n"
        f"  🟢 П1 (хозяева) — <code>{m['odds_home']:.2f}</code>\n"
        f"  ⚪ Х  (ничья)   — <code>{m['odds_draw']:.2f}</code>\n"
        f"  🔵 П2 (гости)   — <code>{m['odds_away']:.2f}</code>\n\n"
        f"Выбери исход:"
    )
    await callback.message.edit_text(text, parse_mode="HTML",
                                     reply_markup=_toto_match_kb(m))
    await callback.answer()


# ── callback: выбор суммы ─────────────────────────────────────────────────────

@dp.callback_query(F.data.startswith("toto_b|"))
async def cb_toto_bet_type(callback: types.CallbackQuery):
    _, match_id, bet_type = callback.data.split("|")
    m = db.toto_get_match(match_id)
    if not m or m["status"] != "pending":
        await callback.answer("⛔ Ставки закрыты", show_alert=True)
        return
    odds_map  = {"1": m["odds_home"], "X": m["odds_draw"], "2": m["odds_away"]}
    label_map = {"1": f"Победа {m['home_team']}", "X": "Ничья", "2": f"Победа {m['away_team']}"}
    text = (
        f"⚽ <b>{m['home_team']} — {m['away_team']}</b>\n\n"
        f"Твой исход: <b>{label_map[bet_type]}</b>\n"
        f"Коэффициент: <code>{odds_map[bet_type]:.2f}</code>\n\n"
        f"Выбери сумму ставки:"
    )
    await callback.message.edit_text(text, parse_mode="HTML",
                                     reply_markup=_toto_amounts_kb(match_id, bet_type))
    await callback.answer()


# ── callback: разместить ставку ───────────────────────────────────────────────

@dp.callback_query(F.data.startswith("toto_ba|"))
async def cb_toto_place_bet(callback: types.CallbackQuery):
    uid  = callback.from_user.id
    _, match_id, bet_type, amount_str = callback.data.split("|")
    amount = float(amount_str)

    user = db.get_user(uid)
    if not user:
        await callback.answer("❌ Вы не зарегистрированы", show_alert=True)
        return
    if user[4] < amount:
        await callback.answer(
            f"❌ Недостаточно средств!\nНужно: {fmt(amount)}\nУ вас: {fmt(user[4])}",
            show_alert=True)
        return

    m = db.toto_get_match(match_id)
    if not m or m["status"] != "pending":
        await callback.answer("⛔ Ставки на этот матч закрыты", show_alert=True)
        return

    odds_map     = {"1": m["odds_home"], "X": m["odds_draw"], "2": m["odds_away"]}
    odds         = odds_map[bet_type]
    potential    = round(amount * odds, 2)

    db.toto_place_bet(uid, match_id, bet_type, amount, potential)

    label_map = {"1": f"П1 — {m['home_team']}", "X": "Х — Ничья",
                 "2": f"П2 — {m['away_team']}"}
    dt    = datetime.fromtimestamp(m["match_time"], tz=timezone.utc) + timedelta(hours=3)
    t_str = dt.strftime("%d.%m %H:%M")
    text  = (
        f"✅ <b>Ставка принята!</b>\n\n"
        f"⚽ {m['league_flag']} {m['home_team']} — {m['away_team']}\n"
        f"🕐 {t_str} МСК\n\n"
        f"📌 Исход: <b>{label_map[bet_type]}</b>\n"
        f"💵 Ставка: <b>{fmt(amount)}</b>\n"
        f"📈 Коэффициент: <code>{odds:.2f}</code>\n"
        f"💰 Возможный выигрыш: <b>{fmt(potential)}</b>\n\n"
        f"💳 Остаток на счёте: {fmt(user[4] - amount)}"
    )
    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Мои ставки",
                                     callback_data="toto_mybets"),
                InlineKeyboardButton(text="🔙 Меню",
                                     callback_data="toto_menu"),
            ]
        ]),
    )
    await callback.answer("✅ Ставка принята!")


# ── callback: мои ставки ──────────────────────────────────────────────────────

@dp.callback_query(F.data == "toto_mybets")
async def cb_toto_mybets(callback: types.CallbackQuery):
    uid  = callback.from_user.id
    bets = db.toto_get_user_bets(uid, status="pending")
    if not bets:
        text = "📋 <b>Мои ставки</b>\n\n<i>Активных ставок нет.</i>"
    else:
        text = f"📋 <b>Мои активные ставки</b> ({len(bets)}):\n\n"
        for b in bets:
            dt    = datetime.fromtimestamp(b["match_time"], tz=timezone.utc) + timedelta(hours=3)
            t_str = dt.strftime("%d.%m %H:%M")
            lm    = {"1": f"П1 ({b['home_team']})",
                     "X": "Х (ничья)",
                     "2": f"П2 ({b['away_team']})"}
            text += (
                f"⏳ {b['league_flag']} <b>{b['home_team']} — {b['away_team']}</b>\n"
                f"   🕐 {t_str} МСК\n"
                f"   📌 {lm[b['bet_type']]}\n"
                f"   💵 {fmt(b['amount'])} → 💰 {fmt(b['potential_win'])}\n\n"
            )
    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Меню", callback_data="toto_menu")]
        ]),
    )
    await callback.answer()


# ── callback: история ─────────────────────────────────────────────────────────

@dp.callback_query(F.data == "toto_hist")
async def cb_toto_hist(callback: types.CallbackQuery):
    uid      = callback.from_user.id
    all_bets = db.toto_get_user_bets(uid)
    done     = [b for b in all_bets if b["status"] in ("won", "lost", "refunded")]
    if not done:
        text = "📊 <b>История ставок</b>\n\n<i>Завершённых ставок пока нет.</i>"
    else:
        won_sum  = sum(b["potential_win"] for b in done if b["status"] == "won")
        lost_sum = sum(b["amount"]        for b in done if b["status"] == "lost")
        text = (
            f"📊 <b>История ставок</b>\n"
            f"✅ Выиграно: {fmt(won_sum)}  |  ❌ Проиграно: {fmt(lost_sum)}\n\n"
        )
        for b in done[:10]:
            icon = _TOTO_STATUS_ICON.get(b["status"], "❓")
            lm   = {"1": "П1", "X": "Х", "2": "П2"}
            if b["status"] == "won":
                result = f"+{fmt(b['potential_win'])}"
            elif b["status"] == "lost":
                result = f"−{fmt(b['amount'])}"
            else:
                result = f"↩️ {fmt(b['amount'])}"
            score = (f" [{b['home_score']}:{b['away_score']}]"
                     if b["home_score"] >= 0 else "")
            text += (
                f"{icon} {b['league_flag']} "
                f"{b['home_team']} — {b['away_team']}{score}\n"
                f"   {lm[b['bet_type']]} | {result}\n\n"
            )
    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Меню", callback_data="toto_menu")]
        ]),
    )
    await callback.answer()


# ── callback: правила ─────────────────────────────────────────────────────────

@dp.callback_query(F.data == "toto_rules")
async def cb_toto_rules(callback: types.CallbackQuery):
    text = (
        "ℹ️ <b>Правила тотализатора</b>\n\n"
        "<b>Как поставить:</b>\n"
        "1. Выбери «Сделать ставку» → матч из списка\n"
        "2. Нажми исход: П1 (хозяева), Х (ничья) или П2 (гости)\n"
        "3. Выбери сумму — деньги спишутся сразу\n\n"
        "<b>Выплата при выигрыше:</b>\n"
        "  Сумма ставки × Коэффициент\n"
        "  Пример: 10 000 ₽ × 1.85 = <b>18 500 ₽</b>\n\n"
        "<b>Матчи и результаты:</b>\n"
        "• Ставки принимаются <b>до начала матча</b>\n"
        "• Результаты берутся из реальных данных\n"
        "• Если матч отменён — ставка возвращается\n"
        "• Список матчей обновляется каждые 15 минут\n\n"
        "<b>Доступные лиги:</b>\n"
        "🏴󠁧󠁢󠁥󠁮󠁧󠁿 АПЛ  •  🇷🇺 РПЛ  •  🇪🇸 Ла Лига\n"
        "🇩🇪 Бундеслига  •  🇮🇹 Серия А  •  🇫🇷 Лига 1"
    )
    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Меню", callback_data="toto_menu")]
        ]),
    )
    await callback.answer()


def load_catalog_from_db():
    for row in db.get_catalog_items('car'):
        _, _, game_id, name, price, *_ = row
        CARS[game_id] = (name, price)
    for row in db.get_catalog_items('biz'):
        _, _, game_id, name, price, income, *_ = row
        BUSINESSES[game_id] = (name, price, income)
    for row in db.get_catalog_items('apt'):
        _, _, game_id, name, price, *_ = row
        APARTMENTS[game_id] = (name, price)


async def main():
    db.init_db()
    db.init_daily_bonus_defaults()
    load_catalog_from_db()
    dp.include_router(crypto_router)   # крипто-биржа (отдельный модуль)
    print("✅ Бот Advance RP запущен!")
    print(f"   💱 Начальный курс USD/RUB: {config.USD_RUB_RATE:.2f} ₽")
    print(f"   🎁 Ежедневный бонус: {len(db.get_all_daily_bonus_rewards())} дней настроено")
    print(f"   📈 Криптовалют в каталоге: {len(_cx.CRYPTO_INFO)}")
    asyncio.create_task(rates_updater())
    asyncio.create_task(totalizator_updater())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
