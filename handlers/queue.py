from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

import db
import services
from services import LOCK
from i18n import t
from utils import B, kb, fmt

router = Router()


@router.callback_query(F.data.startswith("q:"))
async def join(cb: CallbackQuery, bot: Bot):
    _, oid, slot = cb.data.split(":")
    oid, slot = int(oid), int(slot)
    uid = cb.from_user.id
    lang = await db.get_lang(uid)
    async with LOCK:
        d = await db.get_driver(uid)
        if not services.driver_ok(d):
            return await cb.answer(t("q_notdrv", lang), show_alert=True)
        o = await db.get_order(oid)
        if not o or o["status"] != "open":
            return await cb.answer(t("q_taken", lang), show_alert=True)
        if d["balance"] <= 0:
            return await cb.answer(t("q_nomoney", lang), show_alert=True)
        if await db.q1("SELECT 1 FROM queue WHERE order_id=? AND slot=? AND state IN ('queued','offered')", (oid, slot)):
            await cb.answer(t("q_busy", lang), show_alert=True)
            return await services.refresh_group(bot, oid)
        if await db.q1("SELECT 1 FROM queue WHERE order_id=? AND driver_id=?", (oid, uid)):
            return await cb.answer(t("q_dup", lang), show_alert=True)
        await db.ex("INSERT INTO queue(order_id,slot,driver_id,state) VALUES(?,?,?,'queued')", (oid, slot, uid))
        await cb.answer(t("q_joined", lang))
        await services.advance(bot, oid)
    await services.refresh_group(bot, oid)


async def _edit(cb, text, markup=None):
    try:
        await cb.message.edit_text(text, reply_markup=markup)
    except Exception:
        await cb.message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("qa:"))
async def accept(cb: CallbackQuery, bot: Bot):
    qid = int(cb.data.split(":")[1])
    uid = cb.from_user.id
    lang = await db.get_lang(uid)
    oid = None
    async with LOCK:
        q = await db.q1("SELECT * FROM queue WHERE id=?", (qid,))
        if not q or q["driver_id"] != uid or q["state"] != "offered":
            await cb.answer(t("order_gone", lang), show_alert=True)
            return await _edit(cb, t("order_gone", lang))
        oid = q["order_id"]
        o = await db.get_order(oid)
        d = await db.get_driver(uid)
        if o["status"] != "open":
            await db.ex("UPDATE queue SET state='closed' WHERE id=?", (qid,))
            await cb.answer()
            return await _edit(cb, t("order_gone", lang))
        if not services.driver_ok(d):
            await db.ex("UPDATE queue SET state='skipped' WHERE id=?", (qid,))
            await cb.answer()
            await _edit(cb, t("frozen_txt", lang))
            await services.advance(bot, oid, prefix=True)
        else:
            n = await db.exr("UPDATE drivers SET balance=balance-? WHERE tg_id=? AND balance>=?",
                             (o["price"], uid, o["price"]))
            if not n:
                await db.ex("UPDATE queue SET state='skipped' WHERE id=?", (qid,))
                await cb.answer()
                await _edit(cb, t("insufficient", lang))
                await services.advance(bot, oid, prefix=True)
            else:
                await db.ex("INSERT INTO transactions(driver_id,amount,kind,ref) VALUES(?,?,?,?)",
                            (uid, -o["price"], "order", oid))
                await db.ex("UPDATE orders SET status='accepted', accepted_by=?, accepted_at=datetime('now','localtime') WHERE id=?",
                            (uid, oid))
                await db.ex("UPDATE queue SET state='accepted' WHERE id=?", (qid,))
                others = await db.qa("SELECT * FROM queue WHERE order_id=? AND id!=? AND state IN ('queued','offered')", (oid, qid))
                await db.ex("UPDATE queue SET state='closed' WHERE order_id=? AND id!=? AND state IN ('queued','offered')", (oid, qid))
                d2 = await db.get_driver(uid)
                await cb.answer("✅")
                await _edit(cb, t("acc_ok", lang, price=fmt(o["price"]), bal=fmt(d2["balance"]),
                                  details=services.order_details(o)))
                for r in others:
                    try:
                        l2 = await db.get_lang(r["driver_id"])
                        await bot.send_message(r["driver_id"], t("q_other_taken", l2, id=oid))
                    except Exception:
                        pass
                if o["source"] == "passenger" and o["creator_id"]:
                    pl = await db.get_lang(o["creator_id"])
                    try:
                        await bot.send_message(o["creator_id"], "🎉")
                        await bot.send_message(o["creator_id"], t("p_accepted", pl),
                                               reply_markup=kb([B(t("btn_order", pl), "porder")]))
                    except Exception:
                        pass
                await services.low_check(bot, uid)
    await services.refresh_group(bot, oid)


@router.callback_query(F.data.startswith("qp:"))
async def skip(cb: CallbackQuery, bot: Bot):
    qid = int(cb.data.split(":")[1])
    uid = cb.from_user.id
    lang = await db.get_lang(uid)
    async with LOCK:
        q = await db.q1("SELECT * FROM queue WHERE id=?", (qid,))
        if not q or q["driver_id"] != uid or q["state"] != "offered":
            await cb.answer(t("order_gone", lang), show_alert=True)
            return await _edit(cb, t("order_gone", lang))
        oid = q["order_id"]
        await db.ex("UPDATE queue SET state='passed' WHERE id=?", (qid,))
        await cb.answer()
        await _edit(cb, t("passed_txt", lang))
        await services.advance(bot, oid, prefix=True)
    await services.refresh_group(bot, oid)
