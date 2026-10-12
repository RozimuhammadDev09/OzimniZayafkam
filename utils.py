import html
import re
from aiogram.types import (InlineKeyboardButton as IB, InlineKeyboardMarkup as IM,
                           CallbackQuery, ReplyKeyboardMarkup, KeyboardButton)
from aiogram.exceptions import TelegramBadRequest
import config
from i18n import t


def B(text, cb=None, url=None):
    return IB(text=text, callback_data=cb) if cb is not None else IB(text=text, url=url)


def kb(*rows):
    return IM(inline_keyboard=[list(r) if isinstance(r, (list, tuple)) else [r] for r in rows])


def fmt(n):
    return f"{int(n or 0):,}".replace(",", " ")


def esc(s):
    return html.escape(str(s if s is not None else ""))


def ulink(uid, name):
    return f'<a href="tg://user?id={uid}">{esc(name)}</a>'


def uname(u):
    return "@" + u if u else "—"


def norm_phone(s):
    d = re.sub(r"\D", "", s or "")
    if len(d) == 9:
        d = "998" + d
    if len(d) == 12 and d.startswith("998"):
        return "+" + d
    return None


def parse_amount(s):
    d = re.sub(r"\D", "", s or "")
    if not d:
        return None
    v = int(d)
    return v if 0 < v < 10**10 else None


def admin_url():
    if config.ADMIN_USERNAME:
        return f"https://t.me/{config.ADMIN_USERNAME}"
    if config.ADMIN_IDS:
        return f"tg://user?id={config.ADMIN_IDS[0]}"
    return "https://t.me/"


def contact_btn(lang):
    return B(t("btn_contact_admin", lang), url=admin_url())


def phone_kb(lang):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("btn_send_phone", lang), request_contact=True)],
                  [KeyboardButton(text=t("btn_cancel", lang))]],
        resize_keyboard=True, one_time_keyboard=True)


def is_cancel(text):
    return (text or "") in (t("btn_cancel", "uz"), t("btn_cancel", "cr"))


def pager(prefix, page, total):
    row = []
    if page > 0:
        row.append(B("◀️", f"{prefix}:{page - 1}"))
    row.append(B(f"{page + 1}/{total}", "noop"))
    if page < total - 1:
        row.append(B("▶️", f"{prefix}:{page + 1}"))
    return row


def paginate(items, page, per=None):
    per = per or config.PER_PAGE
    total = max(1, (len(items) + per - 1) // per)
    page = max(0, min(page, total - 1))
    return items[page * per:(page + 1) * per], page, total


def _strip_urls(markup):
    if not markup:
        return markup
    rows = [[b for b in row if not b.url] for row in markup.inline_keyboard]
    rows = [r for r in rows if r]
    return IM(inline_keyboard=rows) if rows else None


async def _safe_answer(target, text, markup):
    try:
        await target.answer(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "BUTTON" in str(e).upper() or "URL" in str(e).upper():
            await target.answer(text, reply_markup=_strip_urls(markup))
        else:
            raise


async def reply(event, text, markup=None):
    """CallbackQuery bo'lsa xabarni tahrirlaydi, aks holda yangi yuboradi."""
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=markup)
            return
        except TelegramBadRequest as e:
            if "not modified" in str(e):
                return
        await _safe_answer(event.message, text, markup)
    else:
        await _safe_answer(event, text, markup)


async def stk(bot, chat_id, emoji):
    """Katta animatsion emoji (stiker o'rnida)."""
    try:
        await bot.send_message(chat_id, emoji)
    except Exception:
        pass