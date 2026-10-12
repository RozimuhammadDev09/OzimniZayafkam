import os
import aiosqlite
import config

_db = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  tg_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'uz', role TEXT,
  full_name TEXT, username TEXT, phone TEXT, created TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS drivers(
  tg_id INTEGER PRIMARY KEY, name TEXT, phone TEXT, username TEXT,
  status TEXT, frozen INTEGER DEFAULT 0, balance INTEGER DEFAULT 0,
  low_warned INTEGER DEFAULT 0, group_sent INTEGER DEFAULT 0,
  created TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY AUTOINCREMENT, route TEXT, text TEXT, phone TEXT,
  price INTEGER, source TEXT, creator_id INTEGER, status TEXT,
  group_msg_id INTEGER, accepted_by INTEGER,
  created TEXT DEFAULT (datetime('now','localtime')), accepted_at TEXT);
CREATE TABLE IF NOT EXISTS queue(
  id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, slot INTEGER,
  driver_id INTEGER, state TEXT, offer_msg_id INTEGER,
  created TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS payments(
  id INTEGER PRIMARY KEY AUTOINCREMENT, driver_id INTEGER, file_id TEXT,
  file_type TEXT, status TEXT, amount INTEGER, admin_id INTEGER,
  created TEXT DEFAULT (datetime('now','localtime')));
CREATE TABLE IF NOT EXISTS transactions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, driver_id INTEGER, amount INTEGER,
  kind TEXT, ref INTEGER, created TEXT DEFAULT (datetime('now','localtime')));
"""


async def init():
    global _db
    d = os.path.dirname(config.DB_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    _db = await aiosqlite.connect(config.DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.executescript(SCHEMA)
    await _db.commit()


async def q1(sql, args=()):
    cur = await _db.execute(sql, args)
    r = await cur.fetchone()
    await cur.close()
    return r


async def qa(sql, args=()):
    cur = await _db.execute(sql, args)
    r = await cur.fetchall()
    await cur.close()
    return r


async def ex(sql, args=()):
    cur = await _db.execute(sql, args)
    await _db.commit()
    return cur.lastrowid


async def exr(sql, args=()):
    cur = await _db.execute(sql, args)
    await _db.commit()
    return cur.rowcount


async def val(sql, args=()):
    r = await q1(sql, args)
    return (r[0] or 0) if r else 0


async def get_lang(uid):
    r = await q1("SELECT lang FROM users WHERE tg_id=?", (uid,))
    return r["lang"] if r and r["lang"] else "uz"


async def get_driver(uid):
    return await q1("SELECT * FROM drivers WHERE tg_id=?", (uid,))


async def get_order(oid):
    return await q1("SELECT * FROM orders WHERE id=?", (oid,))
