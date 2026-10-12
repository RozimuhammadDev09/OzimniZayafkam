import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.strip().lstrip("-").isdigit()]
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "").strip().lstrip("@")
GROUP_ID = int(os.getenv("GROUP_ID", "0") or 0)
GROUP_LINK = os.getenv("GROUP_LINK", "").strip()
CARD_NUMBER = os.getenv("CARD_NUMBER", "")
CARD_OWNER = os.getenv("CARD_OWNER", "")
CARD_PHONE = os.getenv("CARD_PHONE", "")
MIN_TOPUP = int(os.getenv("MIN_TOPUP", "50000"))
LOW_BALANCE = int(os.getenv("LOW_BALANCE", "20000"))
PASSENGER_PRICE = int(os.getenv("PASSENGER_PRICE", "10000"))
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
ADMIN_PRICES = [5000, 10000, 15000, 20000]
PER_PAGE = 6
