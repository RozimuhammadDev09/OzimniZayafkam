from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove

import config
import db
from i18n import t
from utils import B, kb, reply, stk, fmt, contact_btn
from keyboards import admin_kb

router = Router()
router.message.filter(F.chat.type == "private")


async def ensure_user(user):
    await db.ex("""INSERT INTO users(tg_id, full_name, username) VALUES(?,?,?)
                   ON CONFLICT(tg_id) DO UPDATE SET full_name=excluded.full_name, username=excluded.username""",
                (user.id, user.full_name, user.username))


async def show_home(bot: Bot, uid: int, event=None):
    lang = await db.get_lang(uid)
    fresh = event is None or isinstance(event, Message)

    async def out(text, markup=None):
        if event is not None:
            await reply(event, text, markup)
        else:
            await bot.send_message(uid, text, reply_markup=markup)

    langb = B(t("btn_lang", lang), "lang")
    if uid in config.ADMIN_IDS:
        if fresh:
            await stk(bot, uid, "👨‍💼")
        return await out(t("a_hello", lang), admin_kb(lang))

    drv = await db.get_driver(uid)
    if drv:
        st = drv["status"]
        if st == "pending":
            return await out(t("pending_txt", lang), kb([contact_btn(lang)], [langb]))
        if st == "removed":
            return await out(t("removed_txt", lang), kb([contact_btn(lang)]))
        if drv["frozen"]:
            return await out(t("frozen_txt", lang), kb([contact_btn(lang)], [langb]))
        bal = drv["balance"]
        if bal <= 0:
            if fresh:
                await stk(bot, uid, "💳")
            return await out(t("topup_need", lang), kb(
                [B(t("btn_topup", lang), "topup")], [B(t("btn_balance", lang), "dbal")], [langb]))
        return await out(t("drv_menu", lang, bal=fmt(bal)), kb(
            [B(t("btn_balance", lang), "dbal"), B(t("btn_topup", lang), "topup")], [langb]))

    u = await db.q1("SELECT role FROM users WHERE tg_id=?", (uid,))
    if u and u["role"] == "passenger":
        return await out(t("p_menu", lang), kb([B(t("btn_order", lang), "porder")], [langb]))
    if fresh:
        await stk(bot, uid, "👋")
    return await out(t("choose_role", lang), kb(
        [B(t("btn_driver", lang), "role:driver")],
        [B(t("btn_passenger", lang), "role:passenger")],
        [langb]))


@router.message(CommandStart())
@router.message(Command("menu"))
@router.message(Command("admin"))
async def start(m: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await ensure_user(m.from_user)
    await m.answer("🔄", reply_markup=ReplyKeyboardRemove())
    await show_home(bot, m.from_user.id, m)


@router.callback_query(F.data == "home")
async def home(cb: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await cb.answer()
    await show_home(bot, cb.from_user.id, cb)


@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery):
    await cb.answer()


@router.callback_query(F.data == "lang")
async def lang_menu(cb: CallbackQuery):
    lang = await db.get_lang(cb.from_user.id)
    await cb.answer()
    await reply(cb, t("choose_lang", lang), kb(
        [B("🇺🇿 O'zbekcha", "setlang:uz")],
        [B("🇺🇿 Ўзбекча", "setlang:cr")],
        [B(t("btn_back", lang), "home")]))


@router.callback_query(F.data.startswith("setlang:"))
async def set_lang(cb: CallbackQuery, bot: Bot):
    code = cb.data.split(":")[1]
    await ensure_user(cb.from_user)
    await db.ex("UPDATE users SET lang=? WHERE tg_id=?", (code, cb.from_user.id))
    await cb.answer(t("lang_changed", code))
    await show_home(bot, cb.from_user.id, cb)


# Hech qaysi holatga tushmagan xabarlar uchun (eng oxirida ulanadi)
fallback = Router()
fallback.message.filter(F.chat.type == "private")


@fallback.message()
async def any_message(m: Message, bot: Bot):
    await ensure_user(m.from_user)
    await show_home(bot, m.from_user.id, m)
