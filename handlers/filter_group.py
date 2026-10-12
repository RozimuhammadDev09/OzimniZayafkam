"""Filtr guruhi: kalit so'z bor xabarni darhol o'chiradi va zakaz sifatida asosiy guruhga tashlaydi."""
import logging
import re

from aiogram import Router, F, Bot
from aiogram.types import Message

import config
import db
import services
from keywords import match_keyword
from i18n import t
from utils import norm_phone, esc, ulink

log = logging.getLogger("filter")
router = Router()
# faqat filtr guruhidagi xabarlar (GROUP_ID=0 bo'lsa hech qachon mos kelmaydi)
router.message.filter(F.chat.id == config.FILTER_GROUP_ID)
router.edited_message.filter(F.chat.id == config.FILTER_GROUP_ID)

PHONE_RE = re.compile(r"(?<!\d)(?:\+?998[\s\-]?)?\(?\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)")
_warned = False


def split_phones(text: str):
    """Matndan telefon raqamlarni ajratib oladi (guruhda ko'rinmasligi uchun)."""
    phones = []

    def rep(m):
        p = norm_phone(m.group(0))
        if p:
            phones.append(p)
            return ""
        return m.group(0)

    clean = PHONE_RE.sub(rep, text)
    clean = re.sub(r"[ \t]{2,}", " ", clean).strip()
    return clean, phones


async def process(m: Message, bot: Bot):
    global _warned
    if config.FILTER_GROUP_ID == config.GROUP_ID:
        return
    if not m.from_user or m.from_user.is_bot:
        return
    text = m.text or m.caption
    if not text or not match_keyword(text):
        return
    # 1) darhol o'chiramiz
    try:
        await m.delete()
    except Exception as e:
        log.error("Xabarni o'chirib bo'lmadi: %s", e)
        if not _warned:
            _warned = True
            for aid in config.ADMIN_IDS:
                try:
                    await bot.send_message(aid, "⚠️ Filtr guruhida xabarni o'chirib bo'lmadi. Botni guruhda admin qiling va "
                                                "«Xabarlarni o'chirish» huquqini bering.")
                except Exception:
                    pass
        return
    # 2) zakazga aylantiramiz
    clean, phones = split_phones(text.strip())
    oid = await db.ex(
        """INSERT INTO orders(route,text,phone,price,source,creator_id,status,sender_name,sender_username)
           VALUES('',?,?,?, 'filter',?, 'open',?,?)""",
        ((clean or text.strip())[:1500], phones[0] if phones else "", config.FILTER_PRICE,
         m.from_user.id, m.from_user.full_name, m.from_user.username))
    try:
        await services.post_order(bot, oid)
    except Exception as e:
        log.error("Filtr zakazini guruhga yuborib bo'lmadi: %s", e)
        await db.ex("UPDATE orders SET status='cancelled' WHERE id=?", (oid,))
        return
    await notify_sender(bot, m)


async def notify_sender(bot: Bot, m: Message):
    """O'chirilgan xabar o'rniga filtr guruhining o'ziga xabar egasini belgilab javob yozadi."""
    uid = m.from_user.id
    lang = await db.get_lang(uid)
    try:
        await bot.send_message(config.FILTER_GROUP_ID,
                               t("f_sent", lang, name=ulink(uid, m.from_user.full_name)))
    except Exception as e:
        log.warning("Filtr guruhiga javob yozib bo'lmadi: %s", e)


@router.message()
async def on_message(m: Message, bot: Bot):
    await process(m, bot)


@router.edited_message()
async def on_edited(m: Message, bot: Bot):
    await process(m, bot)