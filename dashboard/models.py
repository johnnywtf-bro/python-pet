# dashboard/models.py
import os, sqlite3, time
from dataclasses import dataclass
from typing import List, Optional, Tuple

DB_DIR = os.path.join(os.path.expanduser("~"), ".deskpet")
CORE_DB = os.path.join(DB_DIR, "deskpet.db")
os.makedirs(DB_DIR, exist_ok=True)

@dataclass
class PetState:
    name: str; days_alive: int; level: int
    hunger: int; affection: int; affection_cap: int; coins: int

class DB:
    def __init__(self, path: str = CORE_DB):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._init_schema()
        self._seed_if_empty()

    def _init_schema(self):
        c = self.conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS pet (
          id INTEGER PRIMARY KEY, name TEXT, days_alive INT, level INT,
          hunger INT, affection INT, affection_cap INT, coins INT
        );
        CREATE TABLE IF NOT EXISTS item_catalog(
          id INTEGER PRIMARY KEY, name TEXT UNIQUE, icon TEXT, type TEXT,
          hunger_delta INT, affection_delta INT, price INT, sell_price INT
        );
        CREATE TABLE IF NOT EXISTS inventory(
          item_id INT PRIMARY KEY, qty INT
        );
        CREATE TABLE IF NOT EXISTS logs(
          id INTEGER PRIMARY KEY, ts INT, icon TEXT, text TEXT
        );
        CREATE TABLE IF NOT EXISTS animations(
          key TEXT PRIMARY KEY, label TEXT, require_state TEXT, enabled INT
        );
        CREATE TABLE IF NOT EXISTS tasks(
          id INTEGER PRIMARY KEY, title TEXT, minutes_target INT, minutes_done INT, status TEXT
        );
        """)
        self.conn.commit()
        self._migrate_columns()   # ← 新增：確保新欄位存在

    def _migrate_columns(self):
        cur = self.conn.cursor()
        cols = {r[1] for r in cur.execute("PRAGMA table_info(pet)").fetchall()}
        if "last_hunger_ts" not in cols:
            cur.execute("ALTER TABLE pet ADD COLUMN last_hunger_ts INT")
        if "hunger_decay_per_min" not in cols:
            cur.execute("ALTER TABLE pet ADD COLUMN hunger_decay_per_min INT")
        if "avatar_path" not in cols:
            cur.execute("ALTER TABLE pet ADD COLUMN avatar_path TEXT")
        if "pet_name" not in cols:
            cur.execute("ALTER TABLE pet ADD COLUMN pet_name TEXT")
        if "user_nickname" not in cols:
            cur.execute("ALTER TABLE pet ADD COLUMN user_nickname TEXT")
        if "last_seen_ymd" not in cols:
            cur.execute("ALTER TABLE pet ADD COLUMN last_seen_ymd TEXT")
        self.conn.commit()
        # 若是第一次，填初值
        import time, datetime as _dt, os as _os
        row = cur.execute("SELECT last_hunger_ts, hunger_decay_per_min, avatar_path, pet_name, user_nickname, last_seen_ymd FROM pet WHERE id=1").fetchone()
        if row:
            ts, rate, ava, pname, uname, ymd = row
            changed = False
            if ts is None:
                ts = int(time.time()); changed = True
            if rate is None:
                rate = 1; changed = True                       # 每分鐘掉 1 點
            if not ava:
                ava = _os.path.join("\character\doro.png"); changed = True
            if not pname:
                pname = "doro"; changed = True
            if uname is None:
                uname = ""; changed = True
            if not ymd:
                ymd = _dt.date.today().isoformat(); changed = True
            if changed:
                cur.execute("UPDATE pet SET last_hunger_ts=?, hunger_decay_per_min=?, avatar_path=?, pet_name=?, user_nickname=?, last_seen_ymd=? WHERE id=1",
                            (ts, rate, ava, pname, uname, ymd))
                self.conn.commit()

    def _apply_daily_progress(self):
        import datetime as _dt
        cur = self.conn.cursor()
        days, last = cur.execute("SELECT days_alive, last_seen_ymd FROM pet WHERE id=1").fetchone()
        today = _dt.date.today().isoformat()
        if last != today:
            cur.execute("UPDATE pet SET days_alive=?, last_seen_ymd=? WHERE id=1", (max(1, (days or 1) + 1), today))
            self.conn.commit()

    def _apply_hunger_decay(self):
        """依經過時間衰減飽食度；每次讀取狀態或操作時自動套用"""
        import time as _t
        cur = self.conn.cursor()
        name,days,level,hunger,aff,cap,coins,ts,rate = cur.execute(
            "SELECT name,days_alive,level,hunger,affection,affection_cap,coins,last_hunger_ts,hunger_decay_per_min FROM pet WHERE id=1"
        ).fetchone()
        now = int(_t.time())
        if ts is None or rate is None:
            ts = now; rate = 1
        minutes = max(0, (now - ts) // 60)
        if minutes > 0 and hunger is not None:
            new_h = max(0, hunger - minutes * max(0, rate))
            cur.execute("UPDATE pet SET hunger=?, last_hunger_ts=? WHERE id=1", (new_h, now))
            self.conn.commit()

    def _seed_if_empty(self):
        cur = self.conn.cursor()
        if cur.execute("SELECT COUNT(*) FROM pet").fetchone()[0] == 0:
            cur.execute("INSERT INTO pet(id,name,days_alive,level,hunger,affection,affection_cap,coins) VALUES(1,?,?,?,?,?,?,?)",
                        ("Kitty", 3, 1, 90, 0, 120, 0))
        if cur.execute("SELECT COUNT(*) FROM item_catalog").fetchone()[0] == 0:
            # 依你的 assets 檔名填入
            foods = [
                ("麵包",        "assets/food/bread.png",        "food",  +8,  +1, 50,  25),
                ("雞蛋吐司",    "assets/food/Egg toast.png",    "food", +12,  +1, 50,  25),
                ("熱狗麵包",    "assets/food/hot dog bread.png","food", +15,  +1,100,  50),
                ("紅豆麵包",    "assets/food/Red bean bread.png","food",+18,  +2,100,  50),
            ]
            cur.executemany("INSERT OR IGNORE INTO item_catalog(name,icon,type,hunger_delta,affection_delta,price,sell_price) VALUES(?,?,?,?,?,?,?)", foods)
            # 背包先給幾個
            cur.executemany("INSERT OR IGNORE INTO inventory(item_id, qty) VALUES(?,?)",
                            [(1,1),(2,1),(3,1),(4,1)])
        if cur.execute("SELECT COUNT(*) FROM animations").fetchone()[0] == 0:
            anims = [("idle","站立","normal",1),("angry","生氣","hungry",1),("walk","左右行走","active",0),("sleep","睡覺","hungry",0)]
            cur.executemany("INSERT OR IGNORE INTO animations(key,label,require_state,enabled) VALUES(?,?,?,?)", anims)
        self.conn.commit()

    def read_pet(self):
        self._apply_hunger_decay()
        self._apply_daily_progress()
        row = self.conn.execute(
            "SELECT pet_name,days_alive,level,hunger,affection,affection_cap,coins FROM pet WHERE id=1"
        ).fetchone()
        return PetState(*row)
    
    def get_avatar_and_user(self):
        return self.conn.execute("SELECT avatar_path, user_nickname FROM pet WHERE id=1").fetchone()  # (avatar, nickname or "")
    
    def set_user_nickname(self, name:str):
        self.conn.execute("UPDATE pet SET user_nickname=? WHERE id=1", (name.strip(),))
        self.conn.commit()

    def feed_effect(self, hunger_delta:int, affection_delta:int, src_icon:str, src_name:str):
        """餵食回補（供背包使用），會更新 last_hunger_ts 防止剛餵就再扣"""
        import time as _t
        ps = self.read_pet()
        new_h = min(100, ps.hunger + max(0, hunger_delta))
        new_a = ps.affection + max(0, affection_delta)
        level, cap = ps.level, ps.affection_cap
        if new_a >= cap:
            new_a -= cap; level += 1; cap += 40
        self.conn.execute(
            "UPDATE pet SET hunger=?, affection=?, level=?, affection_cap=?, last_hunger_ts=? WHERE id=1",
            (new_h, new_a, level, cap, int(_t.time()))
        )
        self.conn.commit()
        self.append_log(src_icon, f"[{src_name}] +1")

    def update_pet(self, **kw):
        sets = ",".join(f"{k}=?" for k in kw.keys())
        self.conn.execute(f"UPDATE pet SET {sets} WHERE id=1", tuple(kw.values())); self.conn.commit()

    def list_catalog(self):  # [ (id,name,icon,price,...), ... ]
        return self.conn.execute("SELECT id,name,icon,price,sell_price,hunger_delta,affection_delta FROM item_catalog ORDER BY id").fetchall()
    
    def list_inventory(self):
        q = """SELECT i.item_id, c.name, c.icon, i.qty, c.hunger_delta, c.affection_delta
               FROM inventory i JOIN item_catalog c ON i.item_id=c.id ORDER BY i.item_id"""
        return self.conn.execute(q).fetchall()
    
    def add_inv(self, item_id:int, n:int=1):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO inventory(item_id,qty) VALUES(?,COALESCE((SELECT qty FROM inventory WHERE item_id=?),0)+?) ON CONFLICT(item_id) DO UPDATE SET qty=qty+?", (item_id,item_id,n,n))
        self.conn.commit()

    def dec_inv(self, item_id:int, n:int=1):
        self.conn.execute("UPDATE inventory SET qty=MAX(qty-?,0) WHERE item_id=?", (n,item_id)); self.conn.commit()

    def append_log(self, icon:str, text:str):
        self.conn.execute("INSERT INTO logs(ts,icon,text) VALUES(?,?,?)", (int(time.time()), icon, text)); self.conn.commit()
    def list_logs(self, limit=20):
        return self.conn.execute("SELECT ts,icon,text FROM logs ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()

    def list_anims(self):
        return self.conn.execute("SELECT key,label,require_state,enabled FROM animations").fetchall()
    def set_anim_enabled(self, key:str, enabled:bool):
        self.conn.execute("UPDATE animations SET enabled=? WHERE key=?", (1 if enabled else 0, key)); self.conn.commit()

    def list_tasks(self):
        return self.conn.execute("SELECT id,title,minutes_target,minutes_done,status FROM tasks ORDER BY id DESC").fetchall()
    def add_task(self, title:str, minutes:int):
        self.conn.execute("INSERT INTO tasks(title,minutes_target,minutes_done,status) VALUES(?,?,0,'todo')",(title,minutes)); self.conn.commit()
    def set_task_status(self, tid:int, status:str):
        self.conn.execute("UPDATE tasks SET status=? WHERE id=?", (status,tid)); self.conn.commit()
