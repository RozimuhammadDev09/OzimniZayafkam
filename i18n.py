"""Matnlar. Barcha matnlar lotin yozuvida yoziladi, kirill tili avtomatik
transliteratsiya qilinadi (HTML teglar, {o'zgaruvchilar} va brend nomlari saqlanadi)."""
import re
from functools import lru_cache

_PROTECT = re.compile(r"(<[^>]+>|\{[^}]*\}|\b(?:Click|Payme|PDF|ID|Telegram|Username)\b)")
_MAP = {
    "a": "а", "b": "б", "d": "д", "f": "ф", "g": "г", "h": "ҳ", "i": "и", "j": "ж",
    "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "қ", "r": "р",
    "s": "с", "t": "т", "u": "у", "v": "в", "w": "в", "x": "х", "y": "й", "z": "з",
    "c": "ц", "e": "е",
}


def _tr_chunk(s: str) -> str:
    s = re.sub("[ʻʼ‘’`´]", "'", s)
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        lo = c.lower()
        nx = s[i + 1].lower() if i + 1 < n else ""
        n2 = s[i + 2] if i + 2 < n else ""
        up = c.isupper()
        pair = lo + nx

        def put(x):
            out.append(x.upper() if up else x)

        if pair in ("o'", "g'"):
            put("ў" if lo == "o" else "ғ"); i += 2; continue
        if pair == "sh":
            put("ш"); i += 2; continue
        if pair == "ch":
            put("ч"); i += 2; continue
        if pair == "yo" and n2 != "'":
            put("ё"); i += 2; continue
        if pair == "yu":
            put("ю"); i += 2; continue
        if pair == "ya":
            put("я"); i += 2; continue
        if pair == "ye":
            put("е"); i += 2; continue
        if lo == "e":
            prev = s[i - 1] if i > 0 else ""
            put("э" if not (prev.isalpha() or prev == "'") else "е"); i += 1; continue
        if lo == "'":
            out.append("ъ"); i += 1; continue
        if lo in _MAP:
            put(_MAP[lo]); i += 1; continue
        out.append(c); i += 1
    return "".join(out)


@lru_cache(maxsize=2048)
def to_cyr(text: str) -> str:
    parts = _PROTECT.split(text)
    return "".join(p if (i % 2 == 1) else _tr_chunk(p) for i, p in enumerate(parts))


def t(key: str, lang: str = "uz", **kw) -> str:
    tpl = T[key]
    if lang == "cr":
        tpl = to_cyr(tpl)
    return tpl.format(**kw)


T = {
    # ---------- umumiy ----------
    "choose_role": "👋 Assalomu alaykum!\n\nSiz kimsiz? Tanlang:",
    "btn_driver": "🚖 Shofyor bo'lish",
    "btn_passenger": "📦 Yo'lovchi — e'lon berish",
    "btn_lang": "🌐 Tilni o'zgartirish",
    "choose_lang": "🌐 Tilni tanlang:",
    "lang_changed": "✅ Til o'zgartirildi!",
    "btn_cancel": "❌ Bekor qilish",
    "btn_back": "⬅️ Orqaga",
    "btn_home": "🏠 Asosiy menyu",
    "btn_contact_admin": "👨‍💼 Adminga bog'lanish",
    "btn_send_phone": "📱 Raqamni yuborish",
    "bad_phone": "⚠️ Telefon raqam noto'g'ri. Qaytadan kiriting (masalan: 901234567).",
    "cancelled": "❌ Bekor qilindi.",
    "not_admin": "⛔ Sizda ruxsat yo'q.",
    # ---------- shofyor ro'yxatdan o'tish ----------
    "drv_ask_phone": "👋 Salom! Shofyor bo'lish uchun telefon raqamingizni yuboring.\n\n📱 Pastdagi tugmani bosing yoki raqamni qo'lda yozing (masalan: 901234567).",
    "drv_ask_name": "✅ Raqam saqlandi!\n\n👤 Endi ism va familiyangizni yozib yuboring:",
    "bad_name": "⚠️ Ism va familiyani to'liq yozing.",
    "saved": "✅ Saqlandi!",
    "drv_summary": "📋 <b>Sizning ma'lumotlaringiz:</b>\n\n👤 Ism familiya: {name_link}\n📞 Telefon: {phone}\n🔗 Username: {username}\n\nMa'lumotlar tayyor. Adminga yuborasizmi?",
    "btn_send": "✅ Yuborish",
    "drv_sent": "📨 So'rov adminga yuborildi. Iltimos, admin javobini kuting yoki adminga bog'laning.",
    "admin_app": "🆕 <b>Yangi shofyor arizasi</b>\n\n👤 {name_link}\n📞 {phone}\n🔗 Username: {username}\n🆔 ID: <code>{id}</code>",
    "btn_approve": "✅ Tasdiqlash",
    "btn_reject": "❌ Rad etish",
    "drv_approved": "🎉 Tabriklaymiz! Arizangiz tasdiqlandi. Endi botdan foydalanishingiz mumkin.",
    "drv_rejected": "😔 Arizangiz rad etildi. Iltimos, qaytadan urinib ko'ring.",
    "pending_txt": "⏳ Arizangiz ko'rib chiqilmoqda. Iltimos, admin javobini kuting.",
    "removed_txt": "🚫 Siz botdan chiqarilgansiz.",
    "frozen_txt": "❄️ Hisobingiz muzlatilgan. Batafsil ma'lumot uchun adminga murojaat qiling.",
    "app_done_ok": "✅ Tasdiqlandi",
    "app_done_no": "❌ Rad etildi",
    "app_already": "⚠️ Bu ariza allaqachon ko'rib chiqilgan.",
    # ---------- shofyor menyusi ----------
    "drv_menu": "🚖 <b>Shofyor bo'limi</b>\n\n💰 Hisobingiz: <b>{bal}</b> so'm\n\nKerakli bo'limni tanlang:",
    "topup_need": "💳 Botdan to'liq foydalanish uchun hisobingizni to'ldirishingiz zarur.",
    "btn_topup": "💳 Hisobni to'ldirish",
    "btn_balance": "💰 Hisobim",
    "balance_txt": "💰 <b>Hisobingiz:</b> {bal} so'm\n\n📌 Har bir zakaz qabul qilinganda hisobingizdan zakaz narxi yechiladi.",
    # ---------- to'lov ----------
    "pay_choose": "💳 <b>Hisobni to'ldirish</b>\n\nMinimal to'ldirish summasi: <b>{min}</b> so'm.\n\nO'zingizga qulay to'lov turini tanlang:",
    "btn_pay_admin": "👨‍💼 Admin orqali to'ldirish",
    "btn_pay_check": "🧾 To'lov cheki orqali",
    "btn_click": "🔵 Click (avtomatik)",
    "btn_payme": "🟢 Payme (avtomatik)",
    "pay_unavail": "⚠️ Hozircha bu to'lov turi mavjud emas. Iltimos, boshqa to'lov turidan foydalaning.\n\n",
    "pay_admin_txt": "👨‍💼 <b>Admin orqali to'ldirish</b>\n\nAdminga murojaat qilib to'lovni amalga oshiring. To'lovingizni tasdiqlagach, admin hisobingizni to'ldirib qo'yadi.",
    "pay_check_txt": "🧾 <b>Karta orqali to'lov</b>\n\n💳 Karta raqami: <code>{card}</code>\n👤 Karta egasi: {owner}\n📞 Ulangan raqam: {cphone}\n\nShu kartaga to'lov qilib, chekni <b>rasm</b> yoki <b>PDF</b> ko'rinishida yuboring.",
    "check_bad": "⚠️ Iltimos, chekni rasm yoki PDF ko'rinishida yuboring.",
    "check_sent": "✅ To'lov cheki adminga yuborildi. Iltimos, admin javobini kuting. Chek soxta bo'lmasa, admin albatta hisobingizni to'ldirib qo'yadi.",
    "admin_check": "🧾 <b>Yangi to'lov cheki</b>\n\n👤 {name_link}\n📞 {phone}\n💰 Hozirgi balans: {bal} so'm",
    "pay_ask_amount": "✅ To'lov tasdiqlandi.\n\n💵 Foydalanuvchi hisobi qanchaga to'ldirilsin? (so'mda yozing, masalan: 100000)",
    "pay_already": "⚠️ Bu to'lov allaqachon ko'rib chiqilgan.",
    "pay_rejected_admin": "❌ To'lov rad etildi.",
    "pay_rejected": "❌ To'lov chekingiz rad etildi. Savollaringiz bo'lsa, adminga murojaat qiling.",
    "drv_topped_check": "✅ Sizning to'lovingiz tasdiqlandi!\n\n💰 Hisobingiz <b>{amount}</b> so'mga to'ldirildi.\n💳 Joriy balans: <b>{bal}</b> so'm",
    "drv_topped_admin": "💰 Hisobingiz admin tomonidan <b>{amount}</b> so'm to'ldirildi.\n💳 Joriy balans: <b>{bal}</b> so'm",
    "join_group": "🚖 Botni ishlatish va zakaz olish uchun guruhimizga ulanib oling!",
    "btn_join_group": "👥 Guruhga o'tish",
    "low_bal": "⚠️ Hisobingizda <b>{bal}</b> so'm qoldi.\n\nHisobni to'ldirib oling, aks holda qimmatroq zakazlar kelganda ola olmay qolishingiz mumkin.",
    # ---------- navbat / zakaz (shofyor) ----------
    "q_notdrv": "⚠️ Siz faol shofyor emassiz.",
    "q_nomoney": "❌ Hisobingizda mablag' yo'q. Iltimos, hisobingizni to'ldiring!",
    "q_busy": "⚠️ Bu navbat band!",
    "q_taken": "⚠️ Zakaz band qilingan!",
    "q_joined": "✅ Navbatga qo'shildingiz!",
    "q_dup": "⚠️ Siz bu zakazda allaqachon navbatdasiz.",
    "offer": "🚖 <b>Zakaz #{id}</b>\n\n{prefix}{details}\n💵 Narxi: <b>{price}</b> so'm\n\nZakazni qabul qilasizmi?",
    "offer_prefix": "⏭ Oldingi shofyor qabul qilmadi, navbat sizda!\n\n",
    "btn_accept": "✅ Qabul qilish",
    "btn_pass": "⏭ O'tkazib yuborish",
    "acc_ok": "✅ <b>Siz zakazni qabul qildingiz!</b>\n💸 Hisobingizdan <b>{price}</b> so'm yechildi.\n💰 Qolgan balans: <b>{bal}</b> so'm\n\n{details}",
    "insufficient": "⚠️ Hisobingizdagi mablag' ushbu zakazga yetmadi. Zakaz avtomatik keyingi navbatdagi shofyorga yuborildi.",
    "passed_txt": "⏭ Zakazni o'tkazib yubordingiz.",
    "order_gone": "⚠️ Bu zakaz endi mavjud emas yoki band qilingan.",
    "q_other_taken": "ℹ️ Zakaz #{id} boshqa shofyor tomonidan qabul qilindi.",
    # ---------- guruh ----------
    "g_order": "🚖 <b>Yangi zakaz #{id}</b>\n\n{route}📝 {text}\n\n🚦 <b>Navbat:</b>\n{queue}",
    "g_accepted": "\n\n✅ Ushbu zakaz {link} nomidan qabul qilindi.\nKeyingi zakazlarda faol bo'ling!",
    "g_cancelled": "\n\n❌ Zakaz bekor qilindi.",
    # ---------- yo'lovchi ----------
    "p_ask_phone": "👋 Assalomu alaykum! Telefon raqamingizni yuboring.\n\n📱 Tugmani bosing yoki raqamni qo'lda yozing (masalan: 901234567).",
    "p_phone_saved": "✅ Raqam saqlandi!\n\n📝 Endi zakazni yozib botga yuboring (qayerdan qayerga, vaqti va h.k.):",
    "p_ask_order": "📝 Zakazni yozib yuboring (qayerdan qayerga, vaqti va h.k.):",
    "p_sent": "✅ Zakazingiz shofyorlarga yuborildi. Iltimos, shofyor javobini kuting.",
    "p_accepted": "✅ Zakazingiz qabul qilindi!\n\nBizning botdan foydalanganingiz uchun rahmat. Yana zakaz berishingiz mumkin 👇",
    "p_menu": "👋 Assalomu alaykum!\n\nZakaz berish uchun tugmani bosing:",
    "btn_order": "📝 Zakaz berish",
    "p_fail": "⚠️ Zakazni yuborishda xatolik yuz berdi. Keyinroq urinib ko'ring.",
    # ---------- admin ----------
    "a_hello": "👋 Salom, admin!\n\nKerakli bo'limni tanlang:",
    "a_btn_drivers": "👥 Shofyorlar",
    "a_btn_order": "📝 Zakaz tashlash",
    "a_btn_stats": "📊 Statistika",
    "a_btn_orders": "📦 Buyurtmalar",
    "a_btn_apps": "🆕 Arizalar",
    "a_btn_search": "🔍 Qidirish",
    "a_btn_bc": "📢 Xabar yuborish",
    "a_drivers": "👥 <b>Tasdiqlangan shofyorlar</b> ({n} ta):",
    "a_empty": "📭 Hozircha ro'yxat bo'sh.",
    "a_drv_detail": "👤 <b>Shofyor ma'lumotlari</b>\n\n👤 Ism familiya: {name_link}\n📞 Telefon: {phone}\n🔗 Username: {username}\n🆔 ID: <code>{id}</code>\n\n💰 Hisobida: <b>{bal}</b> so'm qoldi\n📌 Holat: {state}\n📅 Ro'yxatdan o'tgan: {created}",
    "st_active": "✅ Faol",
    "st_frozen": "❄️ Muzlatilgan",
    "a_btn_addbal": "➕ Hisobiga pul solish",
    "a_btn_subbal": "➖ Hisobidan pul ayirish",
    "a_ask_sub": "💵 Hisobidan qancha so'm ayiramiz? (masalan: 20000)\n\n💰 Hozirgi balans: <b>{bal}</b> so'm",
    "a_sub_too_much": "⚠️ Hisobda faqat <b>{bal}</b> so'm bor. Shundan oshmaydigan summa kiriting.",
    "a_subbed": "✅ {name_link} hisobidan <b>{amount}</b> so'm ayirildi.\n💰 Yangi balans: <b>{bal}</b> so'm",
    "drv_deducted": "➖ Hisobingizdan admin tomonidan <b>{amount}</b> so'm ayirildi.\n💳 Joriy balans: <b>{bal}</b> so'm",
    "a_btn_deduct": "➖ Hisobidan pul ayirish",
    "a_ask_deduct": "💵 Hisobidan qancha so'm ayirasiz? (masalan: 20000)",
    "a_deduct_more": "⚠️ Shofyor hisobida faqat <b>{bal}</b> so'm bor. Shundan oshmaydigan summa kiriting.",
    "a_deducted": "✅ {name_link} hisobidan <b>{amount}</b> so'm ayirildi.\n💰 Yangi balans: <b>{bal}</b> so'm",
    "drv_deducted": "➖ Hisobingizdan admin tomonidan <b>{amount}</b> so'm ayirildi.\n💳 Joriy balans: <b>{bal}</b> so'm",
    "a_btn_remove": "🚫 Botdan chiqarish",
    "a_btn_freeze": "❄️ Hisobni muzlatish",
    "a_btn_unfreeze": "🔥 Hisobni muzdan chiqarish",
    "a_btn_sub": "➖ Hisobidan pul ayirish",
    "a_ask_sub": "💵 Hisobidan qancha so'm ayiramiz? (masalan: 20000)\n\n💰 Hozirgi balans: <b>{bal}</b> so'm",
    "a_sub_big": "⚠️ Shofyor hisobida faqat <b>{bal}</b> so'm bor. Undan kam summa kiriting.",
    "a_subtracted": "✅ {name_link} hisobidan <b>{amount}</b> so'm ayirildi.\n💰 Yangi balans: <b>{bal}</b> so'm",
    "drv_deducted": "➖ Hisobingizdan admin tomonidan <b>{amount}</b> so'm ayirildi.\n💳 Joriy balans: <b>{bal}</b> so'm",
    "a_ask_amount": "💵 Qancha so'm qo'shasiz? (masalan: 50000)",
    "bad_amount": "⚠️ Summani raqamda kiriting (masalan: 50000).",
    "a_topped": "✅ {name_link} hisobi <b>{amount}</b> so'mga to'ldirildi.\n💰 Yangi balans: <b>{bal}</b> so'm",
    "a_rm_confirm": "⚠️ Haqiqatan ham <b>{name}</b> ni botdan chiqarasizmi?",
    "btn_yes": "✅ Ha",
    "btn_no": "❌ Yo'q",
    "a_removed": "🚫 Shofyor botdan chiqarildi.",
    "a_frozen": "❄️ Shofyor hisobi muzlatildi.",
    "a_unfrozen": "🔥 Shofyor hisobi muzdan chiqarildi.",
    "drv_frozen_notice": "❄️ Sizning hisobingiz muzlatildi. Botdan foydalana olmaysiz. Batafsil ma'lumot uchun adminga murojaat qiling.",
    "drv_unfrozen_notice": "🔥 Hisobingiz muzdan chiqarildi. Botdan yana foydalanishingiz mumkin!",
    "drv_removed_notice": "🚫 Siz botdan chiqarildingiz.",
    # admin zakaz tashlash
    "o_route": "📍 Yo'nalishni kiriting (masalan: Toshkent — Samarqand):",
    "o_text": "📝 Zakaz matnini kiriting (yo'nalish va boshqa ma'lumotlar, telefon raqamsiz):",
    "o_phone": "📞 Zakaz egasining telefon raqamini kiriting:",
    "o_price": "💵 Zakaz narxini tanlang:",
    "o_preview": "📋 <b>Zakaz ma'lumotlari</b>\n\n📝 {text}\n📞 {phone}\n💵 Narxi: <b>{price}</b> so'm\n\nTasdiqlaysizmi?",
    "o_posted": "✅ Zakaz guruhga yuborildi!",
    "o_error": "❌ Guruhga yuborib bo'lmadi: {err}\n\nBot guruhda admin ekanligini va GROUP_ID to'g'riligini tekshiring.",
    "som": "{n} so'm",
    # buyurtmalar
    "a_orders_menu": "📦 <b>Buyurtmalar</b>\n\nBo'limni tanlang:",
    "a_btn_open": "⏳ Kutilayotgan ({n})",
    "a_btn_acc": "✅ Qabul qilingan ({n})",
    "a_orders_list_open": "⏳ <b>Kutilayotgan buyurtmalar</b>:",
    "a_orders_list_acc": "✅ <b>Qabul qilingan buyurtmalar</b>:",
    "a_order_detail": "📦 <b>Zakaz #{id}</b>\n\n📍 Yo'nalish: {route}\n📝 Matn: {text}\n📞 Telefon: {phone}\n💵 Narxi: <b>{price}</b> so'm\n👤 Kim bergan: {source}\n📌 Holat: {state}\n🚗 Qabul qilgan: {driver}\n🚦 Navbat:\n{queue}\n📅 Sana: {created}",
    "src_admin": "Admin",
    "src_passenger": "Yo'lovchi",
    "ost_open": "⏳ Kutilmoqda",
    "ost_accepted": "✅ Qabul qilingan",
    "ost_cancelled": "❌ Bekor qilingan",
    "a_btn_cancel_order": "🗑 Zakazni bekor qilish",
    "a_order_cancelled": "🗑 Zakaz bekor qilindi.",
    # arizalar / qidirish
    "a_apps": "🆕 <b>Kutilayotgan arizalar</b> ({n} ta):",
    "a_search_ask": "🔍 Shofyor ismi, telefon raqami yoki ID sini yozing:",
    "a_search_none": "❌ Hech narsa topilmadi.",
    "a_search_res": "🔍 <b>Natijalar:</b>",
    # xabar yuborish
    "b_target": "📢 <b>Xabar yuborish</b>\n\nKimlarga yuboramiz?",
    "b_drivers": "🚖 Shofyorlarga",
    "b_passengers": "📦 Yo'lovchilarga",
    "b_all": "👥 Hammaga",
    "b_ask": "✉️ Yuboriladigan xabarni yuboring (matn, rasm, video — istalgan):",
    "b_done": "✅ Xabar yuborildi!\n\n📨 Yetkazildi: <b>{ok}</b> ta\n⚠️ Xatolik: <b>{fail}</b> ta",
    # statistika
    "a_stats": "📊 <b>Statistika</b>\n\n🚖 <b>Shofyorlar</b>\n• Faol: {d_active}\n• Muzlatilgan: {d_frozen}\n• Kutilayotgan arizalar: {d_pending}\n• Chiqarilgan: {d_removed}\n• Jami balans: {d_balance} so'm\n\n📦 Yo'lovchilar: {pass_cnt}\n\n🧾 <b>Zakazlar</b>\n• Jami: {o_total}\n• Bugun: {o_today}\n• Kutilayotgan: {o_open}\n• Qabul qilingan: {o_acc}\n• Bekor qilingan: {o_can}\n\n💵 <b>Moliya</b>\n• Jami to'ldirilgan: {topups} so'm\n• Jami daromad (zakazlardan): {income} so'm\n• Bugungi daromad: {income_today} so'm",
}