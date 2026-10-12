from aiogram import Router, F, Bot
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove

import config
import db
from i18n import t
from utils import (B, kb, reply, stk, fmt, esc, ulink, uname, norm_phone, phone_kb,
                   is_cancel, contact_btn)
from handlers.common import show_home, ensure_user

router = Router()
router.message.filter(F.chat.type == "private")


class Reg(StatesGroup):
    phone = State()
    name = State()
    confirm = State()


class Topup(StatesGroup):
    check = State()


async def active_driver(event, uid):
    """Faol shofyor bo'lsa qaytaradi, aks holda tegishli xabarni ko'rsatadi."""
    lang = await db.get_lang(uid)
    d = await db.get_driver(uid)
    if not d or d["status"] == "pending":
        await reply(event, t("pending_txt", lang), kb([contact_btn(lang)]))
        return None
    if d["status"] == "removed":
        await reply(event, t("removed_txt", lang), kb([contact_btn(lang)]))
        return None
    if d["frozen"]:
        await reply(event, t("frozen_txt", lang), kb([contact_btn(lang)]))
        return None
    return d


# ---------------- ro'yxatdan o'tish ----------------
@router.callback_query(F.data == "role:driver")
async def role_driver(cb: CallbackQuery, state: FSMContext, bot: Bot):
    lang = await db.get_lang(cb.from_user.id)
    await cb.answer()
    d = await db.get_driver(cb.from_user.id)
    if d:
        return await show_home(bot, cb.from_user.id, cb)
    await ensure_user(cb.from_user)
    await db.ex("UPDATE users SET role='driver' WHERE tg_id=?", (cb.from_user.id,))
    await state.set_state(Reg.phone)
    await stk(bot, cb.from_user.id, "🚖")
    await cb.message.answer(t("drv_ask_phone", lang), reply_markup=phone_kb(lang))


@router.message(Reg.phone)
async def reg_phone(m: Message, state: FSMContext, bot: Bot):
    lang = await db.get_lang(m.from_user.id)
    if is_cancel(m.text):
        await state.clear()
        await m.answer("🔄", reply_markup=ReplyKeyboardRemove())
        await db.ex("UPDATE users SET role=NULL WHERE tg_id=?", (m.from_user.id,))
        return await show_home(bot, m.from_user.id, m)
    raw = m.contact.phone_number if m.contact else (m.text or "")
    phone = norm_phone(raw)
    if not phone and m.contact:
        digits = "".join(c for c in raw if c.isdigit())
        phone = "+" + digits if digits else None
    if not phone:
        return await m.answer(t("bad_phone", lang))
    await state.update_data(phone=phone)
    await state.set_state(Reg.name)
    await m.answer(t("drv_ask_name", lang), reply_markup=ReplyKeyboardRemove())
    await m.answer("👤", reply_markup=kb([B(t("btn_cancel", lang), "home")]))


@router.message(Reg.name, F.text)
async def reg_name(m: Message, state: FSMContext):
    lang = await db.get_lang(m.from_user.id)
    name = m.text.strip()
    if len(name) < 3 or name.startswith("/"):
        return await m.answer(t("bad_name", lang))
    await state.update_data(name=name[:80])
    await state.set_state(Reg.confirm)
    data = await state.get_data()
    await m.answer(t("saved", lang))
    await m.answer(
        t("drv_summary", lang, name_link=ulink(m.from_user.id, name), phone=esc(data["phone"]),
          username=esc(uname(m.from_user.username))),
        reply_markup=kb([B(t("btn_send", lang), "reg_send"), B(t("btn_cancel", lang), "home")]))


@router.callback_query(Reg.confirm, F.data == "reg_send")
async def reg_send(cb: CallbackQuery, state: FSMContext, bot: Bot):
    lang = await db.get_lang(cb.from_user.id)
    data = await state.get_data()
    await state.clear()
    uid = cb.from_user.id
    await db.ex("""INSERT OR REPLACE INTO drivers(tg_id,name,phone,username,status,frozen,balance,low_warned,group_sent)
                   VALUES(?,?,?,?, 'pending',0,0,0,0)""",
                (uid, data["name"], data["phone"], cb.from_user.username))
    await cb.answer()
    await reply(cb, t("drv_sent", lang), kb([contact_btn(lang)]))
    await stk(bot, uid, "📨")
    from handlers.admin import send_application
    d = await db.get_driver(uid)
    for aid in config.ADMIN_IDS:
        try:
            await send_application(bot, aid, d)
        except Exception:
            pass


@router.callback_query(F.data == "reg_send")
async def reg_send_stale(cb: CallbackQuery, bot: Bot):
    await cb.answer()
    await show_home(bot, cb.from_user.id, cb)


# ---------------- hisob ----------------
@router.callback_query(F.data == "dbal")
async def balance(cb: CallbackQuery):
    d = await active_driver(cb, cb.from_user.id)
    if not d:
        return await cb.answer()
    lang = await db.get_lang(cb.from_user.id)
    await cb.answer()
    await reply(cb, t("balance_txt", lang, bal=fmt(d["balance"])),
                kb([B(t("btn_topup", lang), "topup")], [B(t("btn_back", lang), "home")]))


def pay_kb(lang):
    return kb(
        [B(t("btn_pay_admin", lang), "pay:admin")],
        [B(t("btn_pay_check", lang), "pay:check")],
        [B(t("btn_click", lang), "pay:click")],
        [B(t("btn_payme", lang), "pay:payme")],
        [B(t("btn_back", lang), "home")])


@router.callback_query(F.data == "topup")
async def topup(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await active_driver(cb, cb.from_user.id):
        return await cb.answer()
    lang = await db.get_lang(cb.from_user.id)
    await cb.answer()
    await reply(cb, t("pay_choose", lang, min=fmt(config.MIN_TOPUP)), pay_kb(lang))


@router.callback_query(F.data.in_({"pay:click", "pay:payme"}))
async def pay_unavailable(cb: CallbackQuery):
    if not await active_driver(cb, cb.from_user.id):
        return await cb.answer()
    lang = await db.get_lang(cb.from_user.id)
    await cb.answer("⚠️", show_alert=False)
    await reply(cb, t("pay_unavail", lang) + t("pay_choose", lang, min=fmt(config.MIN_TOPUP)), pay_kb(lang))


@router.callback_query(F.data == "pay:admin")
async def pay_admin(cb: CallbackQuery):
    if not await active_driver(cb, cb.from_user.id):
        return await cb.answer()
    lang = await db.get_lang(cb.from_user.id)
    await cb.answer()
    await reply(cb, t("pay_admin_txt", lang), kb([contact_btn(lang)], [B(t("btn_back", lang), "topup")]))


@router.callback_query(F.data == "pay:check")
async def pay_check(cb: CallbackQuery, state: FSMContext):
    if not await active_driver(cb, cb.from_user.id):
        return await cb.answer()
    lang = await db.get_lang(cb.from_user.id)
    await cb.answer()
    await state.set_state(Topup.check)
    await reply(cb, t("pay_check_txt", lang, card=esc(config.CARD_NUMBER), owner=esc(config.CARD_OWNER),
                      cphone=esc(config.CARD_PHONE)), kb([B(t("btn_back", lang), "topup")]))


@router.message(Topup.check)
async def got_check(m: Message, state: FSMContext, bot: Bot):
    lang = await db.get_lang(m.from_user.id)
    d = await active_driver(m, m.from_user.id)
    if not d:
        return await state.clear()
    file_id = ftype = None
    if m.photo:
        file_id, ftype = m.photo[-1].file_id, "photo"
    elif m.document and ((m.document.mime_type or "") == "application/pdf"
                         or (m.document.mime_type or "").startswith("image/")):
        file_id, ftype = m.document.file_id, "document"
    if not file_id:
        return await m.answer(t("check_bad", lang))
    pid = await db.ex("INSERT INTO payments(driver_id,file_id,file_type,status) VALUES(?,?,?,'pending')",
                      (m.from_user.id, file_id, ftype))
    await state.clear()
    await m.answer(t("check_sent", lang), reply_markup=kb([contact_btn(lang)], [B(t("btn_home", lang), "home")]))
    for aid in config.ADMIN_IDS:
        al = await db.get_lang(aid)
        cap = t("admin_check", al, name_link=ulink(d["tg_id"], d["name"]), phone=esc(d["phone"]), bal=fmt(d["balance"]))
        markup = kb([B(t("btn_approve", al), f"pyok:{pid}"), B(t("btn_reject", al), f"pyno:{pid}")])
        try:
            if ftype == "photo":
                await bot.send_photo(aid, file_id, caption=cap, reply_markup=markup)
            else:
                await bot.send_document(aid, file_id, caption=cap, reply_markup=markup)
        except Exception:
            pass
