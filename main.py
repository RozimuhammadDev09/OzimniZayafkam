import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
import db
from handlers import common, admin, driver, passenger, queue


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not config.BOT_TOKEN or not config.ADMIN_IDS:
        sys.exit("❌ .env faylida BOT_TOKEN va ADMIN_IDS ni to'ldiring (.env.example dan nusxa oling).")
    await db.init()
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(driver.router)
    dp.include_router(passenger.router)
    dp.include_router(queue.router)
    dp.include_router(common.fallback)
    await bot.delete_webhook(drop_pending_updates=True)
    if not config.ADMIN_USERNAME:
        for aid in config.ADMIN_IDS:
            try:
                ch = await bot.get_chat(aid)
                if ch.username:
                    config.ADMIN_USERNAME = ch.username
                    break
            except Exception:
                pass
    me = await bot.get_me()
    logging.info("Bot ishga tushdi: @%s", me.username)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())