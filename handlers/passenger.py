from aiogram import Router, F, Bot
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove

import config
import db
import services
from i18n import t
from utils import B, kb, reply, stk, norm_phone, phone_kb, is_cancel
from handlers.common import show_home, ensure_user

router = Router()
router.message.filter(F.chat.type == "private")


class PReg(StatesGroup):
    phone = State()


class POrder(StatesGroup):
    text = State()


async def ask_order(event_msg, state, lang):
    await state.set_state(POrder.text)
    await event_msg.answer(t("p_ask_order", lang), reply_markup=kb([B(t("btn_cancel", lang), "home")]))


async def begin(cb: CallbackQuery, state: FSMContext, bot: Bot):
    lang = await db.get_lang(cb.from_user.id)
    await ensure_user(cb.from_user)
    u = await db.q1("SELECT phone FROM users WHERE tg_id=?", (cb.from_user.id,))
    await cb.answer()
    await stk(bot, cb.from_user.id, "📦")
    if u and u["phone"]:
        await ask_order(cb.message, state, lang)
    else:
        await state.set_state(PReg.phone)
        await cb.message.answer(t("p_ask_phone", lang), reply_markup=phone_kb(lang))


@router.callback_query(F.data == "role:passenger")
async def role_passenger(cb: CallbackQuery, state: FSMContext, bot: Bot):
    await ensure_user(cb.from_user)
    await db.ex("UPDATE users SET role='passenger' WHERE tg_id=?", (cb.from_user.id,))
    await begin(cb, state, bot)


@router.callback_query(F.data == "porder")
async def porder(cb: CallbackQuery, state: FSMContext, bot: Bot):
    await begin(cb, state, bot)


@router.message(PReg.phone)
async def p_phone(m: Message, state: FSMContext, bot: Bot):
    lang = await db.get_lang(m.from_user.id)
    if is_cancel(m.text):
        await state.clear()
        await db.ex("UPDATE users SET role=NULL WHERE tg_id=? AND phone IS NULL", (m.from_user.id,))
        await m.answer("🔄", reply_markup=ReplyKeyboardRemove())
        return await show_home(bot, m.from_user.id, m)
    raw = m.contact.phone_number if m.contact else (m.text or "")
    phone = norm_phone(raw)
    if not phone and m.contact:
        digits = "".join(c for c in raw if c.isdigit())
        phone = "+" + digits if digits else None
    if not phone:
        return await m.answer(t("bad_phone", lang))
    await db.ex("UPDATE users SET phone=? WHERE tg_id=?", (phone, m.from_user.id))
    await state.set_state(POrder.text)
    await m.answer(t("p_phone_saved", lang), reply_markup=ReplyKeyboardRemove())
    await m.answer("📝", reply_markup=kb([B(t("btn_cancel", lang), "home")]))


@router.message(POrder.text, F.text)
async def p_order(m: Message, state: FSMContext, bot: Bot):
    lang = await db.get_lang(m.from_user.id)
    u = await db.q1("SELECT phone FROM users WHERE tg_id=?", (m.from_user.id,))
    text = m.text.strip()
    if text.startswith("/"):
        return
    oid = await db.ex("""INSERT INTO orders(route,text,phone,price,source,creator_id,status)
                         VALUES('',?,?,?, 'passenger',?, 'open')""",
                      (text[:1500], u["phone"] if u else "", config.PASSENGER_PRICE, m.from_user.id))
    try:
        await services.post_order(bot, oid)
    except Exception:
        await db.ex("UPDATE orders SET status='cancelled' WHERE id=?", (oid,))
        await state.clear()
        await m.answer(t("p_fail", lang))
        return await show_home(bot, m.from_user.id, m)
    await state.clear()
    await stk(bot, m.from_user.id, "✅")
    await m.answer(t("p_sent", lang), reply_markup=kb([B(t("btn_home", lang), "home")]))
