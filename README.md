# 🚖 Taksi Bot (aiogram 3 + SQLite)

## O'rnatish
1. Python 3.10+ kerak.
2. `pip install -r requirements.txt`
3. `.env.example` ni `.env` ga nusxalang va to'ldiring (BOT_TOKEN, ADMIN_IDS, GROUP_ID, GROUP_LINK, karta ma'lumotlari).
4. **Botni shofyorlar guruhiga qo'shing va ADMIN qiling** (xabar yuborish/tahrirlash huquqi bilan).
5. `python main.py`

## Guruh ID sini topish
Guruhga @RawDataBot yoki @getidsbot qo'shib ID ni oling (`-100...` ko'rinishida).

## Imkoniyatlar
- Admin / Shofyor / Yo'lovchi rollari, 2 til (lotin va kirill o'zbekcha)
- Shofyor arizasi → admin tasdiqlashi → hisob to'ldirish (admin orqali / chek orqali)
- Guruhda 3 ta navbat tugmasi (🟢 bo'sh / 🔴 band), navbat bilan zakazni lichkaga yuborish
- Qabul qilganda hisobdan zakaz narxi yechiladi, mablag' yetmasa avtomatik keyingi shofyorga o'tadi
- Hisob 20 000 so'mdan kam qolsa eslatma; 0 bo'lsa navbatga yozilib bo'lmaydi
- Admin panel: shofyorlar (sahifalash, pul solish, muzlatish, chiqarish), zakaz tashlash,
  buyurtmalar (kutilayotgan/qabul qilingan, bekor qilish), arizalar, qidirish, xabar yuborish, statistika
- Click/Payme hozircha o'chiq (tugma bor, "mavjud emas" deydi)

Ma'lumotlar `data/bot.db` (SQLite) da saqlanadi.
