"""
crypto_exchange.py — Крипто Биржа Advance RP
Отдельный модуль. Подключается через dp.include_router(router).

Монеты:  BTC · ETH · TON · SOL · BNB · XRP · DOGE · USDT · XAUT
Курсы:   CoinGecko API, обновление каждые 60 сек
Комиссия: 3% на покупку и на продажу → Государственная Казна
"""
from __future__ import annotations

import time
import aiohttp
import config
import database as db

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

# ══════════════════════════ ДАННЫЕ ══════════════════════════════════════════

CRYPTO_INFO: dict[str, dict] = {
    "BTC":  {"name": "Bitcoin",     "icon": "₿",  "gecko_id": "bitcoin",          "dec": 6},
    "ETH":  {"name": "Ethereum",    "icon": "Ξ",  "gecko_id": "ethereum",         "dec": 6},
    "TON":  {"name": "Toncoin",     "icon": "💎", "gecko_id": "the-open-network", "dec": 4},
    "SOL":  {"name": "Solana",      "icon": "◎",  "gecko_id": "solana",           "dec": 4},
    "BNB":  {"name": "BNB",         "icon": "🟡", "gecko_id": "binancecoin",      "dec": 4},
    "XRP":  {"name": "XRP",         "icon": "✕",  "gecko_id": "ripple",           "dec": 2},
    "DOGE": {"name": "Dogecoin",    "icon": "🐕", "gecko_id": "dogecoin",         "dec": 2},
    "USDT": {"name": "Tether",      "icon": "💵", "gecko_id": "tether",           "dec": 2},
    "XAUT": {"name": "Tether Gold", "icon": "🥇", "gecko_id": "tether-gold",      "dec": 6},
}

_GECKO_IDS = ",".join(v["gecko_id"] for v in CRYPTO_INFO.values())
_GECKO_URL = (
    f"https://api.coingecko.com/api/v3/simple/price"
    f"?ids={_GECKO_IDS}&vs_currencies=usd&include_24hr_change=true"
)

# Начальные цены в рублях (≈ USD × 90). Будут перезаписаны при первом запросе к API.
CRYPTO_PRICES: dict[str, float] = {
    "BTC":  9_000_000.0,
    "ETH":    315_000.0,
    "TON":        450.0,
    "SOL":     16_200.0,
    "BNB":     54_000.0,
    "XRP":        180.0,
    "DOGE":        31.5,
    "USDT":        90.0,
    "XAUT":   234_000.0,
}

CRYPTO_24H: dict[str, float] = {s: 0.0 for s in CRYPTO_INFO}

# Используем список, чтобы значение флага можно было менять из rates_updater
_API_OK: list[bool] = [True]

COMMISSION = 0.03   # 3%


# ══════════════════════════ ОБНОВЛЕНИЕ КУРСОВ ════════════════════════════════

async def update_crypto_rates(session: aiohttp.ClientSession) -> None:
    """Вызывается из rates_updater в bot.py каждые 60 сек."""
    try:
        async with session.get(_GECKO_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            data = await resp.json(content_type=None)
        for sym, info in CRYPTO_INFO.items():
            gid = info["gecko_id"]
            if gid in data and "usd" in data[gid]:
                price_usd = float(data[gid]["usd"])
                CRYPTO_PRICES[sym] = price_usd * config.USD_RUB_RATE
                CRYPTO_24H[sym]    = float(data[gid].get("usd_24h_change") or 0.0)
        _API_OK[0] = True
    except Exception:
        _API_OK[0] = False


# ══════════════════════════ FSM ══════════════════════════════════════════════

class CryptoBuyFSM(StatesGroup):
    wait_rub = State()   # ввод суммы в ₽
    wait_qty = State()   # ввод количества монет

class CryptoSellFSM(StatesGroup):
    wait_rub = State()
    wait_qty = State()


# ══════════════════════════ ФОРМАТИРОВАНИЕ ════════════════════════════════════

def _fc(amount: float, sym: str) -> str:
    """Форматирует количество монеты."""
    dec = CRYPTO_INFO.get(sym, {}).get("dec", 4)
    return f"{amount:.{dec}f}"

def _fr(v: float) -> str:
    """Форматирует рублёвую сумму."""
    if v >= 1_000_000:
        return f"{v:,.0f} ₽".replace(",", " ")
    if v >= 1_000:
        return f"{v:,.2f} ₽".replace(",", " ")
    if v >= 1:
        return f"{v:.2f} ₽"
    if v >= 0.01:
        return f"{v:.4f} ₽"
    if v >= 0.0001:
        return f"{v:.6f} ₽"
    return f"{v:.8f} ₽"

def _pnl(pnl: float) -> str:
    arrow = "🟢 +" if pnl >= 0 else "🔴 "
    return f"{arrow}{_fr(abs(pnl))}"

def _chg(chg: float) -> str:
    arrow = "🟢" if chg >= 0 else "🔴"
    sign  = "+" if chg >= 0 else ""
    return f"{arrow} {sign}{chg:.2f}%"


# ══════════════════════════ КЛАВИАТУРЫ ═══════════════════════════════════════

def _back_btn(uid: int, target: str = "cx_menu") -> InlineKeyboardButton:
    return InlineKeyboardButton(text="⬅️ Главное меню", callback_data=f"{target}|{uid}")

def _main_kb(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📈 Крипторынок", callback_data=f"cx_mkt|{uid}"),
            InlineKeyboardButton(text="🔄 Обновить",    callback_data=f"cx_ref|{uid}"),
        ],
        [
            InlineKeyboardButton(text="💰 Купить",      callback_data=f"cx_buy|{uid}"),
            InlineKeyboardButton(text="💸 Продать",     callback_data=f"cx_sell|{uid}"),
        ],
        [
            InlineKeyboardButton(text="💼 Портфель",    callback_data=f"cx_pf|{uid}"),
            InlineKeyboardButton(text="📜 История",     callback_data=f"cx_hist|{uid}"),
        ],
        [
            InlineKeyboardButton(text="ℹ️ О монете",    callback_data=f"cx_info|{uid}"),
        ],
    ])

def _coin_list_kb(uid: int, cb_prefix: str, coins: list[str] | None = None) -> InlineKeyboardMarkup:
    coins = coins or list(CRYPTO_INFO.keys())
    rows: list = []
    row:  list = []
    for sym in coins:
        info = CRYPTO_INFO[sym]
        row.append(InlineKeyboardButton(
            text=f"{info['icon']} {sym}",
            callback_data=f"{cb_prefix}|{uid}|{sym}"
        ))
        if len(row) == 3:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([_back_btn(uid)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _buy_amounts_kb(uid: int, sym: str) -> InlineKeyboardMarkup:
    presets = [1_000, 5_000, 10_000, 50_000, 100_000]
    rows: list = []
    row:  list = []
    for amt in presets:
        row.append(InlineKeyboardButton(
            text=f"{amt:,} ₽".replace(",", " "),
            callback_data=f"cx_bp|{uid}|{sym}|{amt}"
        ))
        if len(row) == 3:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text="✏️ Сумма (₽)",  callback_data=f"cx_bcr|{uid}|{sym}"),
        InlineKeyboardButton(text="✏️ Количество", callback_data=f"cx_bcq|{uid}|{sym}"),
    ])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cx_buy|{uid}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _sell_pct_kb(uid: int, sym: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 25%",        callback_data=f"cx_sp|{uid}|{sym}|25"),
            InlineKeyboardButton(text="🟢 50%",        callback_data=f"cx_sp|{uid}|{sym}|50"),
            InlineKeyboardButton(text="🟢 75%",        callback_data=f"cx_sp|{uid}|{sym}|75"),
            InlineKeyboardButton(text="🟢 100% (Всё)", callback_data=f"cx_sp|{uid}|{sym}|100"),
        ],
        [
            InlineKeyboardButton(text="✏️ Сумма (₽)",  callback_data=f"cx_scr|{uid}|{sym}"),
            InlineKeyboardButton(text="✏️ Количество", callback_data=f"cx_scq|{uid}|{sym}"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cx_sell|{uid}")],
    ])


# ══════════════════════════ ГЕНЕРАТОРЫ ТЕКСТА ═════════════════════════════════

def _main_text() -> str:
    return (
        "💱 <b>Крипто Биржа — Advance RP</b>\n\n"
        "Покупай и продавай криптовалюту в реальном времени.\n"
        "📡 Курсы: <b>CoinGecko API</b> · обновление каждые 60 сек\n"
        "🏛️ Комиссия <b>3%</b> на покупку и продажу\n"
        "   → автоматически зачисляется в Государственную Казну\n\n"
        "Выбери действие:"
    )

def _market_text() -> str:
    api_note = (
        "\n⚠️ <i>CoinGecko API временно недоступен. "
        "Используется последняя сохранённая цена.</i>\n"
        if not _API_OK[0] else ""
    )
    lines = [f"📈 <b>Крипторынок — Advance RP</b>{api_note}\n"]
    for sym, info in CRYPTO_INFO.items():
        price = CRYPTO_PRICES[sym]
        chg   = CRYPTO_24H[sym]
        lines.append(
            f"{info['icon']} <b>{sym}</b>  <i>{info['name']}</i>\n"
            f"   💹 {_fr(price)}   {_chg(chg)}\n"
        )
    return "\n".join(lines).rstrip()

def _portfolio_text(uid: int) -> str:
    portfolio = db.get_crypto_portfolio(uid)
    active = [(sym, amt, avg) for sym, amt, avg in portfolio
              if amt > 1e-9 and sym in CRYPTO_INFO]
    if not active:
        return (
            "💼 <b>Портфель пуст</b>\n\n"
            "У тебя пока нет криптовалюты.\n"
            "Нажми <b>💰 Купить</b>, чтобы начать инвестировать."
        )
    text = "💼 <b>Мой криптопортфель</b>\n\n"
    total_val = total_inv = 0.0
    for sym, amt, avg in active:
        info  = CRYPTO_INFO[sym]
        price = CRYPTO_PRICES[sym]
        val   = amt * price
        inv   = amt * avg
        pnl   = val - inv
        pct   = ((val / inv) - 1) * 100 if inv > 0 else 0.0
        s     = "+" if pct >= 0 else ""
        total_val += val
        total_inv += inv
        text += (
            f"{info['icon']} <b>{sym}</b> — {_fc(amt, sym)}\n"
            f"   📥 Ср. цена покупки: {_fr(avg)}\n"
            f"   💹 Текущий курс: {_fr(price)}\n"
            f"   💰 Стоимость: {_fr(val)}\n"
            f"   {'🟢' if pnl>=0 else '🔴'} П/У: "
            f"{('+' if pnl>=0 else '')}{_fr(pnl)} ({s}{pct:.1f}%)\n\n"
        )
    total_pnl = total_val - total_inv
    emoji = "📈" if total_pnl >= 0 else "📉"
    text += (
        "━━━━━━━━━━━━━━━━━━\n"
        f"💼 Общая стоимость: <b>{_fr(total_val)}</b>\n"
        f"💰 Всего вложено: {_fr(total_inv)}\n"
        f"{emoji} {'Прибыль' if total_pnl >= 0 else 'Убыток'}: "
        f"<b>{('+' if total_pnl>=0 else '')}{_fr(total_pnl)}</b>"
    )
    return text

def _history_text(uid: int) -> str:
    rows = db.get_crypto_history(uid, 20)
    if not rows:
        return (
            "📜 <b>История операций пуста</b>\n\n"
            "Сделки появятся здесь после первой покупки или продажи."
        )
    text = "📜 <b>История операций</b> (последние 20)\n\n"
    for ts, sym, action, amount, price in rows:
        dt   = time.strftime("%d.%m %H:%M", time.localtime(ts))
        icon = CRYPTO_INFO[sym]["icon"] if sym in CRYPTO_INFO else "❓"
        act  = "💰 Покупка" if action == "buy" else "💸 Продажа"
        total = amount * price
        text += (
            f"{icon} <b>{sym}</b>  ·  {act}\n"
            f"   📅 {dt}  ·  {_fc(amount, sym)} монет\n"
            f"   💹 {_fr(price)}  ·  Сумма: {_fr(total)}\n\n"
        )
    return text.rstrip()

_COIN_DESCS = {
    "BTC":  "Первая и самая известная криптовалюта. Создана Сатоши Накамото в 2009 г. Жёсткое ограничение эмиссии — 21 млн монет.",
    "ETH":  "Платформа смарт-контрактов. Основа DeFi и NFT экосистемы. Создана Виталиком Бутериным в 2015 г.",
    "TON":  "Блокчейн от команды Telegram. Высокая скорость, интеграция с мини-приложениями и TON Space.",
    "SOL":  "Высокоскоростной блокчейн — до 65 000 TPS. Популярен в NFT, DeFi и игровой индустрии.",
    "BNB":  "Нативный токен экосистемы Binance. Используется для оплаты комиссий и в DeFi на BNB Chain.",
    "XRP":  "Разработан Ripple для мгновенных международных переводов. Транзакция занимает ~3 секунды.",
    "DOGE": "Начался как мем, стал реальным активом. Любимая монета Илона Маска для микроплатежей.",
    "USDT": "Стейблкоин, привязан к USD 1:1. Самый ликвидный цифровой доллар, база большинства торговых пар.",
    "XAUT": "Токен обеспечен реальным золотом (1 XAUT = 1 тройская унция). Надёжная защита от инфляции.",
}

def _coin_info_text(sym: str) -> str:
    info  = CRYPTO_INFO[sym]
    price = CRYPTO_PRICES[sym]
    chg   = CRYPTO_24H[sym]
    return (
        f"{info['icon']} <b>{info['name']} ({sym})</b>\n\n"
        f"💹 Текущая цена: <b>{_fr(price)}</b>\n"
        f"📊 Изменение за 24ч: {_chg(chg)}\n\n"
        f"📖 {_COIN_DESCS.get(sym, '—')}"
    )


# ══════════════════════════ БИЗНЕС-ЛОГИКА ════════════════════════════════════

async def _do_buy(uid: int, sym: str, qty: float) -> tuple[bool, str]:
    if qty <= 1e-12:
        return False, "❌ Количество должно быть больше нуля."
    price       = CRYPTO_PRICES[sym]
    total_cost  = qty * price
    commission  = total_cost * COMMISSION
    total_debit = total_cost + commission
    user = db.get_user(uid)
    if not user:
        return False, "❌ Вы не зарегистрированы. Напишите /start"
    bal = user[4]
    if bal < total_debit:
        return False, (
            f"❌ <b>Недостаточно средств</b>\n"
            f"Нужно: {_fr(total_debit)} (с учётом комиссии {_fr(commission)})\n"
            f"У вас: {_fr(bal)}"
        )
    db.update_balance(uid, -total_debit)
    db.buy_crypto(uid, sym, qty, price)
    db.add_crypto_history(uid, sym, 'buy', qty, price)
    db.update_treasury(commission, 'crypto_commission_buy', uid, f"3% buy {sym}")
    db.add_log(uid, 'crypto_buy', f'{sym} {qty}', total_debit)
    user2 = db.get_user(uid)
    info  = CRYPTO_INFO[sym]
    return True, (
        f"✅ <b>Покупка успешна!</b>\n\n"
        f"{info['icon']} <b>{info['name']} ({sym})</b>\n"
        f"📦 Куплено: <b>{_fc(qty, sym)} {sym}</b>\n"
        f"💹 Цена покупки: {_fr(price)}\n"
        f"💸 Стоимость актива: {_fr(total_cost)}\n"
        f"🏛️ Комиссия (3%): {_fr(commission)}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💰 Остаток баланса: <b>{_fr(user2[4])}</b>"
    )

async def _do_sell(uid: int, sym: str, qty: float) -> tuple[bool, str]:
    if qty <= 1e-12:
        return False, "❌ Количество должно быть больше нуля."
    held, avg_buy = db.get_crypto_holding(uid, sym)
    if held < qty - 1e-9:
        return False, (
            f"❌ <b>Недостаточно {sym}</b>\n"
            f"У вас: {_fc(held, sym)} {sym}\n"
            f"Нужно: {_fc(qty, sym)} {sym}"
        )
    price       = CRYPTO_PRICES[sym]
    total_gross = qty * price
    commission  = total_gross * COMMISSION
    total_net   = total_gross - commission
    ok = db.sell_crypto(uid, sym, qty)
    if not ok:
        return False, "❌ Ошибка продажи. Попробуйте ещё раз."
    db.update_balance(uid, total_net)
    db.add_crypto_history(uid, sym, 'sell', qty, price)
    db.update_treasury(commission, 'crypto_commission_sell', uid, f"3% sell {sym}")
    db.add_log(uid, 'crypto_sell', f'{sym} {qty}', total_net)
    pnl = total_gross - (qty * avg_buy)
    info = CRYPTO_INFO[sym]
    held_left, _ = db.get_crypto_holding(uid, sym)
    return True, (
        f"✅ <b>Продажа успешна!</b>\n\n"
        f"{info['icon']} <b>{info['name']} ({sym})</b>\n"
        f"📦 Продано: <b>{_fc(qty, sym)} {sym}</b>\n"
        f"💹 Цена продажи: {_fr(price)}\n"
        f"💵 Выручка: {_fr(total_gross)}\n"
        f"🏛️ Комиссия (3%): {_fr(commission)}\n"
        f"💰 Получено: <b>{_fr(total_net)}</b>\n"
        f"📊 П/У по сделке: {_pnl(pnl)}\n"
        f"━━━━━━━━━━━━━━\n"
        f"📦 Остаток: {_fc(held_left, sym)} {sym}"
    )


# ══════════════════════════ ХЕНДЛЕРЫ ══════════════════════════════════════════

# ── Утилита: безопасное редактирование сообщения ─────────────────────────────
async def _edit_or_answer(callback: types.CallbackQuery, text: str,
                          kb: InlineKeyboardMarkup) -> None:
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


# ── Entry point: текстовая команда ───────────────────────────────────────────
@router.message(lambda m: m.text and m.text.lower().strip() in {
    "крипта", "биржа", "крипто", "крипторынок", "exchange", "crypto", "биткоин"
})
async def cx_entry(message: types.Message, state: FSMContext) -> None:
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Напишите /start")
        return
    await state.clear()
    uid = message.from_user.id
    await message.answer(_main_text(), parse_mode="HTML", reply_markup=_main_kb(uid))


# ── Главное меню (кнопка «Назад» / обновить) ─────────────────────────────────
@router.callback_query(F.data.startswith("cx_menu|"))
async def cx_menu_cb(callback: types.CallbackQuery, state: FSMContext) -> None:
    uid = int(callback.data.split("|")[1])
    if callback.from_user.id != uid:
        await callback.answer("❌ Это чужое меню.", show_alert=True); return
    await state.clear()
    await _edit_or_answer(callback, _main_text(), _main_kb(uid))
    await callback.answer()


# ── Обновить ─────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_ref|"))
async def cx_refresh_cb(callback: types.CallbackQuery) -> None:
    uid = int(callback.data.split("|")[1])
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    await _edit_or_answer(callback, _main_text(), _main_kb(uid))
    await callback.answer("🔄 Обновлено!")


# ── Рынок ─────────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_mkt|"))
async def cx_market_cb(callback: types.CallbackQuery) -> None:
    uid = int(callback.data.split("|")[1])
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"cx_mkt|{uid}"),
        _back_btn(uid),
    ]])
    await _edit_or_answer(callback, _market_text(), kb)
    await callback.answer()


# ── Купить — выбор монеты ─────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_buy|"))
async def cx_buy_cb(callback: types.CallbackQuery) -> None:
    uid = int(callback.data.split("|")[1])
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    await _edit_or_answer(
        callback,
        "💰 <b>Купить</b> — выбери монету:",
        _coin_list_kb(uid, "cx_bc")
    )
    await callback.answer()


# ── Купить — выбрана монета ───────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_bc|"))
async def cx_buy_coin_cb(callback: types.CallbackQuery) -> None:
    parts = callback.data.split("|")
    uid, sym = int(parts[1]), parts[2]
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    info  = CRYPTO_INFO[sym]
    price = CRYPTO_PRICES[sym]
    user  = db.get_user(uid)
    bal   = user[4] if user else 0.0
    text = (
        f"{info['icon']} <b>{info['name']} ({sym})</b>\n\n"
        f"💹 Текущий курс: <b>{_fr(price)}</b>\n"
        f"💳 Ваш баланс: {_fr(bal)}\n"
        f"🏛️ Комиссия: 3%\n\n"
        f"💡 <i>При выборе суммы в ₽ — комиссия учитывается автоматически.</i>\n\n"
        f"Выбери сумму покупки:"
    )
    await _edit_or_answer(callback, text, _buy_amounts_kb(uid, sym))
    await callback.answer()


# ── Купить — быстрая сумма (preset) ──────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_bp|"))
async def cx_buy_preset_cb(callback: types.CallbackQuery) -> None:
    parts = callback.data.split("|")
    uid, sym, rub = int(parts[1]), parts[2], float(parts[3])
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    # qty рассчитывается так, чтобы total_cost + commission == rub
    price = CRYPTO_PRICES[sym]
    qty   = rub / (price * (1 + COMMISSION))
    ok, text = await _do_buy(uid, sym, qty)
    if ok:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="💰 Купить ещё", callback_data=f"cx_bc|{uid}|{sym}"),
            _back_btn(uid),
        ]])
    else:
        kb = _buy_amounts_kb(uid, sym)
    await _edit_or_answer(callback, text, kb)
    await callback.answer("✅" if ok else "❌")


# ── Купить — ввести сумму ₽ (FSM) ────────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_bcr|"))
async def cx_buy_custom_rub_cb(callback: types.CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("|")
    uid, sym = int(parts[1]), parts[2]
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    await state.update_data(cx_sym=sym, cx_uid=uid)
    await state.set_state(CryptoBuyFSM.wait_rub)
    info = CRYPTO_INFO[sym]
    await callback.message.answer(
        f"✏️ Введи сумму в рублях для покупки {info['icon']} <b>{sym}</b>:\n"
        f"<i>Пример: 5000</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"cx_menu|{uid}")
        ]])
    )
    await callback.answer()


# ── Купить — ввести количество (FSM) ─────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_bcq|"))
async def cx_buy_custom_qty_cb(callback: types.CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("|")
    uid, sym = int(parts[1]), parts[2]
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    await state.update_data(cx_sym=sym, cx_uid=uid)
    await state.set_state(CryptoBuyFSM.wait_qty)
    info = CRYPTO_INFO[sym]
    await callback.message.answer(
        f"✏️ Введи количество {info['icon']} <b>{sym}</b> для покупки:\n"
        f"<i>Пример: 0.001</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"cx_menu|{uid}")
        ]])
    )
    await callback.answer()


# ── FSM Buy: ввод суммы ₽ ────────────────────────────────────────────────────
@router.message(CryptoBuyFSM.wait_rub)
async def cx_buy_fsm_rub(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    sym, uid = data.get("cx_sym"), message.from_user.id
    if not sym:
        await state.clear(); return
    try:
        rub = float(message.text.strip().replace(" ", "").replace("₽", "").replace(",", "."))
        if rub <= 0: raise ValueError
    except Exception:
        await message.answer("❌ Введи корректную сумму (например: <code>5000</code>)", parse_mode="HTML")
        return
    price = CRYPTO_PRICES[sym]
    qty   = rub / (price * (1 + COMMISSION))
    await state.clear()
    ok, text = await _do_buy(uid, sym, qty)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💰 Купить ещё", callback_data=f"cx_bc|{uid}|{sym}"),
        InlineKeyboardButton(text="⬅️ Меню",       callback_data=f"cx_menu|{uid}"),
    ]])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


# ── FSM Buy: ввод количества ─────────────────────────────────────────────────
@router.message(CryptoBuyFSM.wait_qty)
async def cx_buy_fsm_qty(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    sym, uid = data.get("cx_sym"), message.from_user.id
    if not sym:
        await state.clear(); return
    try:
        qty = float(message.text.strip().replace(",", "."))
        if qty <= 0: raise ValueError
    except Exception:
        await message.answer("❌ Введи корректное количество (например: <code>0.001</code>)", parse_mode="HTML")
        return
    await state.clear()
    ok, text = await _do_buy(uid, sym, qty)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💰 Купить ещё", callback_data=f"cx_bc|{uid}|{sym}"),
        InlineKeyboardButton(text="⬅️ Меню",       callback_data=f"cx_menu|{uid}"),
    ]])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


# ── Продать — выбор монеты ────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_sell|"))
async def cx_sell_cb(callback: types.CallbackQuery) -> None:
    uid = int(callback.data.split("|")[1])
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    portfolio = db.get_crypto_portfolio(uid)
    active = [sym for sym, amt, _ in portfolio if amt > 1e-9 and sym in CRYPTO_INFO]
    if not active:
        await callback.answer("💼 У вас нет криптовалюты для продажи.", show_alert=True)
        return
    await _edit_or_answer(
        callback,
        "💸 <b>Продать</b> — выбери монету:",
        _coin_list_kb(uid, "cx_sc", active)
    )
    await callback.answer()


# ── Продать — выбрана монета ──────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_sc|"))
async def cx_sell_coin_cb(callback: types.CallbackQuery) -> None:
    parts = callback.data.split("|")
    uid, sym = int(parts[1]), parts[2]
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    held, avg = db.get_crypto_holding(uid, sym)
    info  = CRYPTO_INFO[sym]
    price = CRYPTO_PRICES[sym]
    val   = held * price
    pnl   = val - (held * avg)
    text = (
        f"{info['icon']} <b>{info['name']} ({sym})</b>\n\n"
        f"📦 У вас: <b>{_fc(held, sym)} {sym}</b>\n"
        f"💹 Текущий курс: {_fr(price)}\n"
        f"💰 Стоимость: {_fr(val)}\n"
        f"📊 П/У: {_pnl(pnl)}\n"
        f"🏛️ Комиссия: 3%\n\n"
        f"Выбери количество для продажи:"
    )
    await _edit_or_answer(callback, text, _sell_pct_kb(uid, sym))
    await callback.answer()


# ── Продать — процент ─────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_sp|"))
async def cx_sell_pct_cb(callback: types.CallbackQuery) -> None:
    parts = callback.data.split("|")
    uid, sym, pct = int(parts[1]), parts[2], int(parts[3])
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    held, _ = db.get_crypto_holding(uid, sym)
    qty = held * (pct / 100)
    ok, text = await _do_sell(uid, sym, qty)
    if ok:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="💸 Продать ещё", callback_data=f"cx_sell|{uid}"),
            _back_btn(uid),
        ]])
    else:
        kb = _sell_pct_kb(uid, sym)
    await _edit_or_answer(callback, text, kb)
    await callback.answer("✅" if ok else "❌")


# ── Продать — ввести сумму ₽ (FSM) ───────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_scr|"))
async def cx_sell_custom_rub_cb(callback: types.CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("|")
    uid, sym = int(parts[1]), parts[2]
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    await state.update_data(cx_sym=sym, cx_uid=uid)
    await state.set_state(CryptoSellFSM.wait_rub)
    info = CRYPTO_INFO[sym]
    await callback.message.answer(
        f"✏️ Введи сумму в рублях для продажи {info['icon']} <b>{sym}</b>:\n"
        f"<i>Пример: 5000</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"cx_menu|{uid}")
        ]])
    )
    await callback.answer()


# ── Продать — ввести количество (FSM) ────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_scq|"))
async def cx_sell_custom_qty_cb(callback: types.CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("|")
    uid, sym = int(parts[1]), parts[2]
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    await state.update_data(cx_sym=sym, cx_uid=uid)
    await state.set_state(CryptoSellFSM.wait_qty)
    info = CRYPTO_INFO[sym]
    await callback.message.answer(
        f"✏️ Введи количество {info['icon']} <b>{sym}</b> для продажи:\n"
        f"<i>Пример: 0.005</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"cx_menu|{uid}")
        ]])
    )
    await callback.answer()


# ── FSM Sell: ввод суммы ₽ ───────────────────────────────────────────────────
@router.message(CryptoSellFSM.wait_rub)
async def cx_sell_fsm_rub(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    sym, uid = data.get("cx_sym"), message.from_user.id
    if not sym:
        await state.clear(); return
    try:
        rub = float(message.text.strip().replace(" ", "").replace("₽", "").replace(",", "."))
        if rub <= 0: raise ValueError
    except Exception:
        await message.answer("❌ Введи корректную сумму (например: <code>5000</code>)", parse_mode="HTML")
        return
    price = CRYPTO_PRICES[sym]
    qty   = rub / price
    await state.clear()
    ok, text = await _do_sell(uid, sym, qty)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💸 Продать ещё", callback_data=f"cx_sell|{uid}"),
        InlineKeyboardButton(text="⬅️ Меню",        callback_data=f"cx_menu|{uid}"),
    ]])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


# ── FSM Sell: ввод количества ─────────────────────────────────────────────────
@router.message(CryptoSellFSM.wait_qty)
async def cx_sell_fsm_qty(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    sym, uid = data.get("cx_sym"), message.from_user.id
    if not sym:
        await state.clear(); return
    try:
        qty = float(message.text.strip().replace(",", "."))
        if qty <= 0: raise ValueError
    except Exception:
        await message.answer("❌ Введи корректное количество (например: <code>0.005</code>)", parse_mode="HTML")
        return
    await state.clear()
    ok, text = await _do_sell(uid, sym, qty)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💸 Продать ещё", callback_data=f"cx_sell|{uid}"),
        InlineKeyboardButton(text="⬅️ Меню",        callback_data=f"cx_menu|{uid}"),
    ]])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


# ── Портфель ──────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_pf|"))
async def cx_portfolio_cb(callback: types.CallbackQuery) -> None:
    uid = int(callback.data.split("|")[1])
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"cx_pf|{uid}"),
        _back_btn(uid),
    ]])
    await _edit_or_answer(callback, _portfolio_text(uid), kb)
    await callback.answer()


# ── История ───────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_hist|"))
async def cx_history_cb(callback: types.CallbackQuery) -> None:
    uid = int(callback.data.split("|")[1])
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"cx_hist|{uid}"),
        _back_btn(uid),
    ]])
    await _edit_or_answer(callback, _history_text(uid), kb)
    await callback.answer()


# ── Информация — выбор монеты ─────────────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_info|"))
async def cx_info_cb(callback: types.CallbackQuery) -> None:
    uid = int(callback.data.split("|")[1])
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    await _edit_or_answer(
        callback,
        "ℹ️ <b>О монете</b> — выбери криптовалюту:",
        _coin_list_kb(uid, "cx_ic")
    )
    await callback.answer()


# ── Информация — конкретная монета ────────────────────────────────────────────
@router.callback_query(F.data.startswith("cx_ic|"))
async def cx_info_coin_cb(callback: types.CallbackQuery) -> None:
    parts = callback.data.split("|")
    uid, sym = int(parts[1]), parts[2]
    if callback.from_user.id != uid:
        await callback.answer("❌", show_alert=True); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Купить",   callback_data=f"cx_bc|{uid}|{sym}"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data=f"cx_ic|{uid}|{sym}"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cx_info|{uid}")],
    ])
    await _edit_or_answer(callback, _coin_info_text(sym), kb)
    await callback.answer()
