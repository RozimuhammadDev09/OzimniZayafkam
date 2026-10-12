import asyncio
from aiogram import Router, F, Bot
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import config
import db
import services
from i18n import t
from utils import (B, kb, reply, stk, fmt, esc, ulink, uname, norm_phone, parse_amount,
                   paginate, pager)
from keyboards import admin_kb, cancel_kb
from handlers.common import show_home

router = Router()
router.message.filter(F.from_user.id.in_(config.ADMIN_IDS), F.chat.type == "private")
router.callback_query.filter(F.from_user.id.in_(config.ADMIN_IDS))


class AOrder(StatesGroup):
    text = State()
    phone = State()
    price = State()
    confirm = State()


class ATopup(StatesGroup):
    amount = State()


class ADec(StatesGroup):
    amount = State()


class APay(StatesGroup):
    amount = State()


class ABc(StatesGroup):
    msg = State()


class ASearch(StatesGroup):
    q = State()


def L(uid):
    return db.get_lang(uid)


# ================= ARIZALAR =================
async def send_application(bot: Bot, aid: int, d):
    lang = await db.get_lang(aid)
    await bot.send_message(
        aid, t("admin_app", lang, name_link=ulink(d["tg_id"], d["name"]), phone=esc(d["phone"]),
               username=esc(uname(d["username"])), id=d["tg_id"]),
        reply_markup=kb([B(t("btn_approve", lang), f"dap:{d['tg_id']}"), B(t("btn_reject", lang), f"dar:{d['tg_id']}")]))


@router.callback_query(F.data.startswith("dap:"))
async def app_approve(cb: CallbackQuery, bot: Bot):
    did = int(cb.data.split(":")[1])
    lang = await L(cb.from_user.id)
    d = await db.get_driver(did)
    if not d or d["status"] != "pending":
        return await cb.answer(t("app_already", lang), show_alert=True)
    await db.ex("UPDATE drivers SET status='approved' WHERE tg_id=?", (did,))
    await db.ex("UPDATE users SET role='driver' WHERE tg_id=?", (did,))
    await cb.answer("✅")
    try:
        await cb.message.edit_text(cb.message.html_text + "\n\n" + t("app_done_ok", lang), reply_markup=None)
    except Exception:
        pass
    dl = await db.get_lang(did)
    try:
        await bot.send_message(did, "🎉")
        await bot.send_message(did, t("drv_approved", dl))
        await show_home(bot, did)
    except Exception:
        pass


@router.callback_query(F.data.startswith("dar:"))
async def app_reject(cb: CallbackQuery, bot: Bot):
    did = int(cb.data.split(":")[1])
    lang = await L(cb.from_user.id)
    d = await db.get_driver(did)
    if not d or d["status"] != "pending":
        return await cb.answer(t("app_already", lang), show_alert=True)
    await db.ex("DELETE FROM drivers WHERE tg_id=?", (did,))
    await db.ex("UPDATE users SET role=NULL WHERE tg_id=?", (did,))
    await cb.answer("❌")
    try:
        await cb.message.edit_text(cb.message.html_text + "\n\n" + t("app_done_no", lang), reply_markup=None)
    except Exception:
        pass
    dl = await db.get_lang(did)
    try:
        await bot.send_message(did, "😔")
        await bot.send_message(did, t("drv_rejected", dl))
        await show_home(bot, did)
    except Exception:
        pass


@router.callback_query(F.data == "a:apps")
async def apps_list(cb: CallbackQuery):
    lang = await L(cb.from_user.id)
    rows = await db.qa("SELECT * FROM drivers WHERE status='pending' ORDER BY created")
    await cb.answer()
    if not rows:
        return await reply(cb, t("a_empty", lang), kb([B(t("btn_back", lang), "home")]))
    btns = [[B(f"🆕 {r['name']} · {r['phone']}", f"apv:{r['tg_id']}")] for r in rows[:30]]
    btns.append([B(t("btn_back", lang), "home")])
    await reply(cb, t("a_apps", lang, n=len(rows)), kb(*btns))


@router.callback_query(F.data.startswith("apv:"))
async def app_view(cb: CallbackQuery, bot: Bot):
    d = await db.get_driver(int(cb.data.split(":")[1]))
    await cb.answer()
    if d and d["status"] == "pending":
        await send_application(bot, cb.from_user.id, d)


# ================= SHOFYORLAR =================
async def show_drivers(cb: CallbackQuery, page: int):
    lang = await L(cb.from_user.id)
    rows = await db.qa("SELECT * FROM drivers WHERE status='approved' ORDER BY name COLLATE NOCASE")
    await cb.answer()
    if not rows:
        return await reply(cb, t("a_empty", lang), kb([B(t("btn_back", lang), "home")]))
    chunk, page, total = paginate(rows, page)
    btns = [[B(f"{'❄️' if r['frozen'] else '🚖'} {r['name']} · {fmt(r['balance'])}", f"dv:{r['tg_id']}")] for r in chunk]
    btns.append(pager("dl", page, total))
    btns.append([B(t("btn_back", lang), "home")])
    await reply(cb, t("a_drivers", lang, n=len(rows)), kb(*btns))


@router.callback_query(F.data.startswith("dl:"))
async def drivers_list(cb: CallbackQuery):
    await show_drivers(cb, int(cb.data.split(":")[1]))


@router.callback_query(F.data == "a:drv")
async def drivers_entry(cb: CallbackQuery):
    await show_drivers(cb, 0)


async def driver_card(did, lang):
    d = await db.get_driver(did)
    if not d:
        return None, None
    text = t("a_drv_detail", lang, name_link=ulink(d["tg_id"], d["name"]), phone=esc(d["phone"]),
             username=esc(uname(d["username"])), id=d["tg_id"], bal=fmt(d["balance"]),
             state=t("st_frozen" if d["frozen"] else "st_active", lang), created=d["created"])
    fz = t("a_btn_unfreeze", lang) if d["frozen"] else t("a_btn_freeze", lang)
    markup = kb(
        [B(t("a_btn_addbal", lang), f"dtop:{did}")],
        [B(t("a_btn_deduct", lang), f"ddec:{did}")],
        [B(t("a_btn_remove", lang), f"drm:{did}")],
        [B(fz, f"dfz:{did}")],
        [B(t("btn_back", lang), "dl:0"), B(t("btn_home", lang), "home")])
    return text, markup


@router.callback_query(F.data.startswith("dv:"))
async def driver_view(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await L(cb.from_user.id)
    text, markup = await driver_card(int(cb.data.split(":")[1]), lang)
    await cb.answer()
    if not text:
        return await reply(cb, t("a_empty", lang), kb([B(t("btn_back", lang), "dl:0")]))
    await reply(cb, text, markup)


@router.callback_query(F.data.startswith("dtop:"))
async def driver_topup_ask(cb: CallbackQuery, state: FSMContext):
    did = int(cb.data.split(":")[1])
    lang = await L(cb.from_user.id)
    await cb.answer()
    await state.set_state(ATopup.amount)
    await state.update_data(did=did)
    await reply(cb, t("a_ask_amount", lang), kb([B(t("btn_back", lang), f"dv:{did}"), B(t("btn_home", lang), "home")]))


@router.message(ATopup.amount, F.text)
async def driver_topup_do(m: Message, state: FSMContext, bot: Bot):
    lang = await L(m.from_user.id)
    amount = parse_amount(m.text)
    if not amount:
        return await m.answer(t("bad_amount", lang))
    did = (await state.get_data())["did"]
    await state.clear()
    d = await db.get_driver(did)
    if not d:
        return await show_home(bot, m.from_user.id, m)
    bal = await services.credit(bot, did, amount, "topup_admin", "admin")
    await stk(bot, m.from_user.id, "✅")
    await m.answer(t("a_topped", lang, name_link=ulink(did, d["name"]), amount=fmt(amount), bal=fmt(bal)),
                   reply_markup=kb([B(t("btn_back", lang), f"dv:{did}")], [B(t("btn_home", lang), "home")]))


@router.callback_query(F.data.startswith("ddec:"))
async def driver_deduct_ask(cb: CallbackQuery, state: FSMContext):
    did = int(cb.data.split(":")[1])
    lang = await L(cb.from_user.id)
    await cb.answer()
    await state.set_state(ADec.amount)
    await state.update_data(did=did)
    await reply(cb, t("a_ask_deduct", lang), kb([B(t("btn_back", lang), f"dv:{did}"), B(t("btn_home", lang), "home")]))


@router.message(ADec.amount, F.text)
async def driver_deduct_do(m: Message, state: FSMContext, bot: Bot):
    lang = await L(m.from_user.id)
    amount = parse_amount(m.text)
    if not amount:
        return await m.answer(t("bad_amount", lang))
    did = (await state.get_data())["did"]
    d = await db.get_driver(did)
    if not d:
        await state.clear()
        return await show_home(bot, m.from_user.id, m)
    n = await db.exr("UPDATE drivers SET balance=balance-? WHERE tg_id=? AND balance>=?", (amount, did, amount))
    if not n:
        return await m.answer(t("a_deduct_more", lang, bal=fmt(d["balance"])))
    await state.clear()
    await db.ex("INSERT INTO transactions(driver_id,amount,kind) VALUES(?,?,?)", (did, -amount, "deduct_admin"))
    d = await db.get_driver(did)
    dl = await db.get_lang(did)
    try:
        await bot.send_message(did, "➖")
        await bot.send_message(did, t("drv_deducted", dl, amount=fmt(amount), bal=fmt(d["balance"])))
    except Exception:
        pass
    await services.low_check(bot, did)
    await m.answer(t("a_deducted", lang, name_link=ulink(did, d["name"]), amount=fmt(amount), bal=fmt(d["balance"])),
                   reply_markup=kb([B(t("btn_back", lang), f"dv:{did}")], [B(t("btn_home", lang), "home")]))


@router.callback_query(F.data.startswith("drm:"))
async def driver_remove_ask(cb: CallbackQuery):
    did = int(cb.data.split(":")[1])
    lang = await L(cb.from_user.id)
    d = await db.get_driver(did)
    await cb.answer()
    if not d:
        return
    await reply(cb, t("a_rm_confirm", lang, name=esc(d["name"])),
                kb([B(t("btn_yes", lang), f"drmy:{did}"), B(t("btn_no", lang), f"dv:{did}")]))


@router.callback_query(F.data.startswith("drmy:"))
async def driver_remove(cb: CallbackQuery, bot: Bot):
    did = int(cb.data.split(":")[1])
    lang = await L(cb.from_user.id)
    await db.ex("UPDATE drivers SET status='removed' WHERE tg_id=?", (did,))
    await cb.answer("🚫")
    await services.drop_from_queues(bot, did)
    dl = await db.get_lang(did)
    try:
        await bot.send_message(did, t("drv_removed_notice", dl))
    except Exception:
        pass
    await reply(cb, t("a_removed", lang), kb([B(t("btn_back", lang), "dl:0")]))


@router.callback_query(F.data.startswith("dfz:"))
async def driver_freeze(cb: CallbackQuery, bot: Bot):
    did = int(cb.data.split(":")[1])
    lang = await L(cb.from_user.id)
    d = await db.get_driver(did)
    if not d:
        return await cb.answer()
    dl = await db.get_lang(did)
    if d["frozen"]:
        await db.ex("UPDATE drivers SET frozen=0 WHERE tg_id=?", (did,))
        await cb.answer(t("a_unfrozen", lang), show_alert=True)
        try:
            await bot.send_message(did, "🔥")
            await bot.send_message(did, t("drv_unfrozen_notice", dl))
            await show_home(bot, did)
        except Exception:
            pass
    else:
        await db.ex("UPDATE drivers SET frozen=1 WHERE tg_id=?", (did,))
        await cb.answer(t("a_frozen", lang), show_alert=True)
        await services.drop_from_queues(bot, did)
        try:
            await bot.send_message(did, "❄️")
            await bot.send_message(did, t("drv_frozen_notice", dl))
        except Exception:
            pass
    text, markup = await driver_card(did, lang)
    await reply(cb, text, markup)


# ================= QIDIRISH =================
@router.callback_query(F.data == "a:search")
async def search_ask(cb: CallbackQuery, state: FSMContext):
    lang = await L(cb.from_user.id)
    await cb.answer()
    await state.set_state(ASearch.q)
    await reply(cb, t("a_search_ask", lang), cancel_kb(lang))


@router.message(ASearch.q, F.text)
async def search_do(m: Message, state: FSMContext):
    lang = await L(m.from_user.id)
    q = m.text.strip()
    await state.clear()
    digits = "".join(c for c in q if c.isdigit())
    like = f"%{q}%"
    rows = await db.qa("""SELECT * FROM drivers WHERE status='approved' AND
                          (name LIKE ? OR username LIKE ? OR phone LIKE ? OR CAST(tg_id AS TEXT)=?)
                          LIMIT 15""", (like, like, f"%{digits}%" if digits else "@@", digits or "-"))
    if not rows:
        return await m.answer(t("a_search_none", lang), reply_markup=kb([B(t("btn_home", lang), "home")]))
    btns = [[B(f"🚖 {r['name']} · {fmt(r['balance'])}", f"dv:{r['tg_id']}")] for r in rows]
    btns.append([B(t("btn_home", lang), "home")])
    await m.answer(t("a_search_res", lang), reply_markup=kb(*btns))


# ================= ZAKAZ TASHLASH =================
@router.callback_query(F.data == "a:order")
async def order_start(cb: CallbackQuery, state: FSMContext):
    lang = await L(cb.from_user.id)
    await cb.answer()
    await state.set_state(AOrder.text)
    await reply(cb, t("o_text", lang), cancel_kb(lang))


@router.message(AOrder.text, F.text)
async def order_text(m: Message, state: FSMContext):
    lang = await L(m.from_user.id)
    await state.update_data(text=m.text.strip()[:1500])
    await state.set_state(AOrder.phone)
    await m.answer(t("o_phone", lang), reply_markup=cancel_kb(lang))


@router.message(AOrder.phone, F.text)
async def order_phone(m: Message, state: FSMContext):
    lang = await L(m.from_user.id)
    phone = norm_phone(m.text)
    if not phone:
        return await m.answer(t("bad_phone", lang))
    await state.update_data(phone=phone)
    await state.set_state(AOrder.price)
    rows = [[B(t("som", lang, n=fmt(p)), f"pr:{p}")] for p in config.ADMIN_PRICES]
    rows.append([B(t("btn_cancel", lang), "home")])
    await m.answer(t("o_price", lang), reply_markup=kb(*rows))


@router.callback_query(AOrder.price, F.data.startswith("pr:"))
async def order_price(cb: CallbackQuery, state: FSMContext):
    lang = await L(cb.from_user.id)
    price = int(cb.data.split(":")[1])
    if price not in config.ADMIN_PRICES:
        return await cb.answer()
    await state.update_data(price=price)
    await state.set_state(AOrder.confirm)
    d = await state.get_data()
    await cb.answer()
    await reply(cb, t("o_preview", lang, text=esc(d["text"]), phone=esc(d["phone"]),
                      price=fmt(price)),
                kb([B(t("btn_approve", lang), "ord_ok"), B(t("btn_reject", lang), "home")]))


@router.callback_query(AOrder.confirm, F.data == "ord_ok")
async def order_confirm(cb: CallbackQuery, state: FSMContext, bot: Bot):
    lang = await L(cb.from_user.id)
    d = await state.get_data()
    await state.clear()
    oid = await db.ex("""INSERT INTO orders(route,text,phone,price,source,creator_id,status)
                         VALUES(?,?,?,?, 'admin',?, 'open')""",
                      ('', d["text"], d["phone"], d["price"], cb.from_user.id))
    await cb.answer()
    try:
        await services.post_order(bot, oid)
    except Exception as e:
        await db.ex("UPDATE orders SET status='cancelled' WHERE id=?", (oid,))
        return await reply(cb, t("o_error", lang, err=esc(e)), kb([B(t("btn_home", lang), "home")]))
    await stk(bot, cb.from_user.id, "✅")
    await reply(cb, t("o_posted", lang), kb([B(t("a_btn_order", lang), "a:order")], [B(t("btn_home", lang), "home")]))


# ================= BUYURTMALAR =================
@router.callback_query(F.data == "a:orders")
async def orders_menu(cb: CallbackQuery):
    lang = await L(cb.from_user.id)
    n_open = await db.val("SELECT COUNT(*) FROM orders WHERE status='open'")
    n_acc = await db.val("SELECT COUNT(*) FROM orders WHERE status='accepted'")
    await cb.answer()
    await reply(cb, t("a_orders_menu", lang), kb(
        [B(t("a_btn_open", lang, n=n_open), "ol:open:0")],
        [B(t("a_btn_acc", lang, n=n_acc), "ol:accepted:0")],
        [B(t("btn_back", lang), "home")]))


@router.callback_query(F.data.startswith("ol:"))
async def orders_list(cb: CallbackQuery):
    lang = await L(cb.from_user.id)
    _, status, page = cb.data.split(":")
    rows = await db.qa("SELECT * FROM orders WHERE status=? ORDER BY id DESC", (status,))
    await cb.answer()
    if not rows:
        return await reply(cb, t("a_empty", lang), kb([B(t("btn_back", lang), "a:orders")]))
    chunk, page, total = paginate(rows, int(page))
    btns = []
    for o in chunk:
        label = (o["route"] or o["text"] or "")[:28]
        btns.append([B(f"#{o['id']} · {label} · {fmt(o['price'])}", f"ov:{o['id']}")])
    btns.append(pager(f"ol:{status}", page, total))
    btns.append([B(t("btn_back", lang), "a:orders")])
    await reply(cb, t("a_orders_list_open" if status == "open" else "a_orders_list_acc", lang), kb(*btns))


@router.callback_query(F.data.startswith("ov:"))
async def order_view(cb: CallbackQuery):
    lang = await L(cb.from_user.id)
    oid = int(cb.data.split(":")[1])
    o = await db.get_order(oid)
    await cb.answer()
    if not o:
        return
    drv = "—"
    if o["accepted_by"]:
        d = await db.get_driver(o["accepted_by"])
        drv = ulink(o["accepted_by"], d["name"] if d else o["accepted_by"])
    text = t("a_order_detail", lang, id=o["id"], route=esc(o["route"] or "—"), text=esc(o["text"]),
             phone=esc(o["phone"]), price=fmt(o["price"]),
             source=t("src_admin" if o["source"] == "admin" else "src_passenger", lang),
             state=t("ost_" + o["status"], lang), driver=drv,
             queue=await services.queue_text(oid), created=o["created"])
    rows = []
    if o["status"] == "open":
        rows.append([B(t("a_btn_cancel_order", lang), f"oc:{oid}")])
    rows.append([B(t("btn_back", lang), f"ol:{o['status']}:0")])
    await reply(cb, text, kb(*rows))


@router.callback_query(F.data.startswith("oc:"))
async def order_cancel(cb: CallbackQuery, bot: Bot):
    lang = await L(cb.from_user.id)
    oid = int(cb.data.split(":")[1])
    await services.cancel_order(bot, oid)
    await cb.answer(t("a_order_cancelled", lang), show_alert=True)
    await reply(cb, t("a_order_cancelled", lang), kb([B(t("btn_back", lang), "ol:open:0")]))


# ================= TO'LOV CHEKI =================
@router.callback_query(F.data.startswith("pyok:"))
async def pay_ok(cb: CallbackQuery, state: FSMContext):
    lang = await L(cb.from_user.id)
    pid = int(cb.data.split(":")[1])
    p = await db.q1("SELECT * FROM payments WHERE id=?", (pid,))
    if not p or p["status"] not in ("pending", "awaiting"):
        return await cb.answer(t("pay_already", lang), show_alert=True)
    await db.ex("UPDATE payments SET status='awaiting', admin_id=? WHERE id=?", (cb.from_user.id, pid))
    await state.set_state(APay.amount)
    await state.update_data(pid=pid)
    await cb.answer()
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await cb.message.answer(t("pay_ask_amount", lang), reply_markup=cancel_kb(lang))


@router.message(APay.amount, F.text)
async def pay_amount(m: Message, state: FSMContext, bot: Bot):
    lang = await L(m.from_user.id)
    amount = parse_amount(m.text)
    if not amount:
        return await m.answer(t("bad_amount", lang))
    pid = (await state.get_data())["pid"]
    await state.clear()
    p = await db.q1("SELECT * FROM payments WHERE id=?", (pid,))
    if not p or p["status"] not in ("awaiting", "pending"):
        return await m.answer(t("pay_already", lang))
    await db.ex("UPDATE payments SET status='approved', amount=? WHERE id=?", (amount, pid))
    d = await db.get_driver(p["driver_id"])
    bal = await services.credit(bot, p["driver_id"], amount, "topup_check", "check", ref=pid)
    await stk(bot, m.from_user.id, "✅")
    await m.answer(t("a_topped", lang, name_link=ulink(d["tg_id"], d["name"]), amount=fmt(amount), bal=fmt(bal)),
                   reply_markup=kb([B(t("btn_home", lang), "home")]))


@router.callback_query(F.data.startswith("pyno:"))
async def pay_no(cb: CallbackQuery, bot: Bot):
    lang = await L(cb.from_user.id)
    pid = int(cb.data.split(":")[1])
    p = await db.q1("SELECT * FROM payments WHERE id=?", (pid,))
    if not p or p["status"] not in ("pending", "awaiting"):
        return await cb.answer(t("pay_already", lang), show_alert=True)
    await db.ex("UPDATE payments SET status='rejected', admin_id=? WHERE id=?", (cb.from_user.id, pid))
    await cb.answer("❌")
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await cb.message.answer(t("pay_rejected_admin", lang))
    dl = await db.get_lang(p["driver_id"])
    try:
        from utils import contact_btn
        await bot.send_message(p["driver_id"], t("pay_rejected", dl), reply_markup=kb([contact_btn(dl)]))
    except Exception:
        pass


# ================= XABAR YUBORISH =================
@router.callback_query(F.data == "a:bc")
async def bc_start(cb: CallbackQuery):
    lang = await L(cb.from_user.id)
    await cb.answer()
    await reply(cb, t("b_target", lang), kb(
        [B(t("b_drivers", lang), "bct:drivers")],
        [B(t("b_passengers", lang), "bct:passengers")],
        [B(t("b_all", lang), "bct:all")],
        [B(t("btn_back", lang), "home")]))


@router.callback_query(F.data.startswith("bct:"))
async def bc_target(cb: CallbackQuery, state: FSMContext):
    lang = await L(cb.from_user.id)
    await state.set_state(ABc.msg)
    await state.update_data(target=cb.data.split(":")[1])
    await cb.answer()
    await reply(cb, t("b_ask", lang), cancel_kb(lang))


@router.message(ABc.msg)
async def bc_send(m: Message, state: FSMContext, bot: Bot):
    lang = await L(m.from_user.id)
    target = (await state.get_data())["target"]
    await state.clear()
    ids = set()
    if target in ("drivers", "all"):
        ids |= {r[0] for r in await db.qa("SELECT tg_id FROM drivers WHERE status='approved'")}
    if target in ("passengers", "all"):
        ids |= {r[0] for r in await db.qa("SELECT tg_id FROM users WHERE role='passenger'")}
    ids -= set(config.ADMIN_IDS)
    ok = fail = 0
    for uid in ids:
        try:
            await bot.copy_message(uid, m.chat.id, m.message_id)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await m.answer(t("b_done", lang, ok=ok, fail=fail), reply_markup=kb([B(t("btn_home", lang), "home")]))


# ================= STATISTIKA =================
@router.callback_query(F.data == "a:stats")
async def stats(cb: CallbackQuery):
    lang = await L(cb.from_user.id)
    v = db.val
    text = t("a_stats", lang,
             d_active=await v("SELECT COUNT(*) FROM drivers WHERE status='approved' AND frozen=0"),
             d_frozen=await v("SELECT COUNT(*) FROM drivers WHERE status='approved' AND frozen=1"),
             d_pending=await v("SELECT COUNT(*) FROM drivers WHERE status='pending'"),
             d_removed=await v("SELECT COUNT(*) FROM drivers WHERE status='removed'"),
             d_balance=fmt(await v("SELECT SUM(balance) FROM drivers WHERE status='approved'")),
             pass_cnt=await v("SELECT COUNT(*) FROM users WHERE role='passenger'"),
             o_total=await v("SELECT COUNT(*) FROM orders"),
             o_today=await v("SELECT COUNT(*) FROM orders WHERE date(created)=date('now','localtime')"),
             o_open=await v("SELECT COUNT(*) FROM orders WHERE status='open'"),
             o_acc=await v("SELECT COUNT(*) FROM orders WHERE status='accepted'"),
             o_can=await v("SELECT COUNT(*) FROM orders WHERE status='cancelled'"),
             topups=fmt(await v("SELECT SUM(amount) FROM transactions WHERE kind LIKE 'topup%'")),
             income=fmt(-await v("SELECT SUM(amount) FROM transactions WHERE kind='order'")),
             income_today=fmt(-await v("SELECT SUM(amount) FROM transactions WHERE kind='order' AND date(created)=date('now','localtime')")))
    await cb.answer()
    await reply(cb, text, kb([B("🔄", "a:stats")], [B(t("btn_back", lang), "home")]))