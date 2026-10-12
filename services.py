"""Umumiy xizmatlar: balans, navbat, guruh xabari."""
import asyncio
import logging
from aiogram import Bot
import config
import db
from i18n import t, to_cyr
from utils import B, kb, fmt, esc, ulink, contact_btn

LOCK = asyncio.Lock()
log = logging.getLogger("services")
NUMS = ["1️⃣", "2️⃣", "3️⃣"]


# ---------------- balans ----------------
async def send_group_join(bot: Bot, did: int):
    await db.ex("UPDATE drivers SET group_sent=1 WHERE tg_id=?", (did,))
    lang = await db.get_lang(did)
    rows = []
    if config.GROUP_LINK:
        rows.append([B(t("btn_join_group", lang), url=config.GROUP_LINK)])
    try:
        await bot.send_message(did, "👥")
        await bot.send_message(did, t("join_group", lang), reply_markup=kb(*rows) if rows else None)
    except Exception as e:
        log.warning("group join send: %s", e)


async def credit(bot: Bot, did: int, amount: int, kind: str, notify: str = "admin", ref=None):
    await db.ex("UPDATE drivers SET balance=balance+? WHERE tg_id=?", (amount, did))
    await db.ex("INSERT INTO transactions(driver_id,amount,kind,ref) VALUES(?,?,?,?)", (did, amount, kind, ref))
    d = await db.get_driver(did)
    if d["balance"] > config.LOW_BALANCE:
        await db.ex("UPDATE drivers SET low_warned=0 WHERE tg_id=?", (did,))
    lang = await db.get_lang(did)
    key = "drv_topped_check" if notify == "check" else "drv_topped_admin"
    try:
        await bot.send_message(did, "💰")
        await bot.send_message(did, t(key, lang, amount=fmt(amount), bal=fmt(d["balance"])))
    except Exception as e:
        log.warning("credit notify: %s", e)
    if not d["group_sent"]:
        await send_group_join(bot, did)
    return d["balance"]


async def low_check(bot: Bot, did: int):
    d = await db.get_driver(did)
    if d and d["balance"] <= config.LOW_BALANCE and not d["low_warned"]:
        await db.ex("UPDATE drivers SET low_warned=1 WHERE tg_id=?", (did,))
        lang = await db.get_lang(did)
        try:
            await bot.send_message(did, "⚠️")
            await bot.send_message(did, t("low_bal", lang, bal=fmt(d["balance"])),
                                   reply_markup=kb([contact_btn(lang)], [B(t("btn_topup", lang), "topup")]))
        except Exception as e:
            log.warning("low notify: %s", e)


def driver_ok(d):
    return bool(d) and d["status"] == "approved" and not d["frozen"]


# ---------------- zakaz ko'rinishi ----------------
def order_details(o, with_phone=True):
    lines = []
    if o["route"]:
        lines.append(f"📍 {esc(o['route'])}")
    lines.append(f"📝 {esc(o['text'])}")
    if with_phone:
        lines.append(f"📞 Telefon: {esc(o['phone'])}")
    return "\n".join(lines) + "\n"


async def queue_slots(oid):
    rows = await db.qa("""SELECT q.slot, q.driver_id, d.name FROM queue q
                          LEFT JOIN drivers d ON d.tg_id=q.driver_id
                          WHERE q.order_id=? AND q.state IN ('queued','offered')""", (oid,))
    return {r["slot"]: r for r in rows}


async def queue_text(oid):
    slots = await queue_slots(oid)
    lines = []
    for i in (1, 2, 3):
        r = slots.get(i)
        lines.append(f"{NUMS[i - 1]} {ulink(r['driver_id'], r['name']) if r else '—'}")
    return "\n".join(lines)


async def render_group(o):
    route = f"📍 {esc(o['route'])}\n" if o["route"] else ""
    txt = t("g_order", "cr", id=o["id"], route=route, text=esc(o["text"]), queue=await queue_text(o["id"]))
    if o["status"] == "accepted":
        d = await db.get_driver(o["accepted_by"])
        txt += t("g_accepted", "cr", link=ulink(o["accepted_by"], d["name"] if d else "Shofyor"))
    elif o["status"] == "cancelled":
        txt += t("g_cancelled", "cr")
    return txt


async def group_kb(o):
    if o["status"] != "open":
        return None
    slots = await queue_slots(o["id"])
    rows = []
    for i in (1, 2, 3):
        rows.append([B(("🔴 " if i in slots else "🟢 ") + str(i), f"q:{o['id']}:{i}")])
    return kb(*rows)


async def post_order(bot: Bot, oid: int):
    if not config.GROUP_ID:
        raise RuntimeError("GROUP_ID .env faylida ko'rsatilmagan")
    o = await db.get_order(oid)
    m = await bot.send_message(config.GROUP_ID, await render_group(o), reply_markup=await group_kb(o))
    await db.ex("UPDATE orders SET group_msg_id=? WHERE id=?", (m.message_id, oid))


async def refresh_group(bot: Bot, oid: int):
    o = await db.get_order(oid)
    if not o or not o["group_msg_id"]:
        return
    try:
        await bot.edit_message_text(await render_group(o), chat_id=config.GROUP_ID,
                                    message_id=o["group_msg_id"], reply_markup=await group_kb(o))
    except Exception as e:
        if "not modified" not in str(e):
            log.warning("refresh group: %s", e)


# ---------------- navbat mantiqi (LOCK ichida chaqiriladi) ----------------
async def offer(bot: Bot, qrow, prefix=False) -> bool:
    o = await db.get_order(qrow["order_id"])
    lang = await db.get_lang(qrow["driver_id"])
    text = t("offer", lang, id=o["id"], prefix=t("offer_prefix", lang) if prefix else "",
             details=order_details(o), price=fmt(o["price"]))
    markup = kb([B(t("btn_accept", lang), f"qa:{qrow['id']}")], [B(t("btn_pass", lang), f"qp:{qrow['id']}")])
    try:
        m = await bot.send_message(qrow["driver_id"], text, reply_markup=markup)
    except Exception as e:
        log.warning("offer failed: %s", e)
        await db.ex("UPDATE queue SET state='skipped' WHERE id=?", (qrow["id"],))
        return False
    await db.ex("UPDATE queue SET state='offered', offer_msg_id=? WHERE id=?", (m.message_id, qrow["id"]))
    return True


async def advance(bot: Bot, oid: int, prefix=False):
    """Agar hozir hech kimga taklif qilinmagan bo'lsa, navbatdagi keyingi shofyorga yuboradi."""
    o = await db.get_order(oid)
    if not o or o["status"] != "open":
        return
    while True:
        if await db.q1("SELECT 1 FROM queue WHERE order_id=? AND state='offered'", (oid,)):
            return
        nxt = await db.q1("SELECT * FROM queue WHERE order_id=? AND state='queued' ORDER BY id LIMIT 1", (oid,))
        if not nxt:
            return
        d = await db.get_driver(nxt["driver_id"])
        if not driver_ok(d) or d["balance"] <= 0:
            await db.ex("UPDATE queue SET state='skipped' WHERE id=?", (nxt["id"],))
            continue
        if await offer(bot, nxt, prefix):
            return


async def drop_from_queues(bot: Bot, did: int):
    """Shofyor muzlatilsa/chiqarilsa — navbatlardan olib tashlanadi."""
    async with LOCK:
        rows = await db.qa("SELECT id, order_id, state, offer_msg_id FROM queue WHERE driver_id=? AND state IN ('queued','offered')", (did,))
        for r in rows:
            await db.ex("UPDATE queue SET state='closed' WHERE id=?", (r["id"],))
            if r["state"] == "offered" and r["offer_msg_id"]:
                try:
                    await bot.edit_message_reply_markup(chat_id=did, message_id=r["offer_msg_id"], reply_markup=None)
                except Exception:
                    pass
        for oid in {r["order_id"] for r in rows}:
            await advance(bot, oid, prefix=True)
    for oid in {r["order_id"] for r in rows}:
        await refresh_group(bot, oid)


async def cancel_order(bot: Bot, oid: int):
    async with LOCK:
        o = await db.get_order(oid)
        if not o or o["status"] != "open":
            return False
        await db.ex("UPDATE orders SET status='cancelled' WHERE id=?", (oid,))
        rows = await db.qa("SELECT * FROM queue WHERE order_id=? AND state IN ('queued','offered')", (oid,))
        for r in rows:
            await db.ex("UPDATE queue SET state='closed' WHERE id=?", (r["id"],))
            if r["state"] == "offered" and r["offer_msg_id"]:
                try:
                    await bot.edit_message_reply_markup(chat_id=r["driver_id"], message_id=r["offer_msg_id"], reply_markup=None)
                except Exception:
                    pass
    await refresh_group(bot, oid)
    return True