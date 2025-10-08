# database.py
import sqlite3, os, time
from types import SimpleNamespace
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pet.db")

class DB:
    def __init__(self, path: str = DB_PATH):
        self.db_path = path  # 先设置路径
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        self._ensure_pet_row()
        self.init_focus_tables()  # 调用专注时间表初始化

    # ---------------- Schema ----------------
    def _init_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS pet (
            id INTEGER PRIMARY KEY CHECK(id=1),
            name TEXT NOT NULL DEFAULT 'doro',
            coins INTEGER NOT NULL DEFAULT 0,
            hunger INTEGER NOT NULL DEFAULT 80,
            affection INTEGER NOT NULL DEFAULT 0,
            affection_cap INTEGER NOT NULL DEFAULT 100,
            days_alive INTEGER NOT NULL DEFAULT 1,
            avatar_path TEXT,
            user_nickname TEXT
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            icon TEXT,
            hunger_delta INTEGER NOT NULL DEFAULT 5,
            affection_delta INTEGER NOT NULL DEFAULT 1
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            item_id INTEGER PRIMARY KEY,
            qty INTEGER NOT NULL DEFAULT 0,
            created_ts INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            FOREIGN KEY(item_id) REFERENCES items(id)
        )""")
        # 保留原有的 tasks 表结构，但添加新的专注相关表
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks_old (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            minutes_target INTEGER NOT NULL,
            minutes_done INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'todo' -- todo/doing/done
        )""")
        self.conn.commit()

    def _ensure_pet_row(self):
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM pet WHERE id=1")
        if not cur.fetchone():
            cur.execute("INSERT INTO pet(id) VALUES(1)")
            self.conn.commit()

    # ---------------- Pet ----------------
    def read_pet(self):
        row = self.conn.execute("SELECT * FROM pet WHERE id=1").fetchone()
        return SimpleNamespace(**row)

    def add_coins(self, delta: int):
        """增加金币 - 使用现有的 pet 表"""
        self.conn.execute("UPDATE pet SET coins = coins + ? WHERE id=1", (int(delta),))
        self.conn.commit()

    def get_avatar_and_user(self):
        row = self.conn.execute("SELECT avatar_path, user_nickname FROM pet WHERE id=1").fetchone()
        return (row["avatar_path"], row["user_nickname"])

    def set_user_nickname(self, nickname: str):
        self.conn.execute("UPDATE pet SET user_nickname=? WHERE id=1", (nickname,))
        self.conn.commit()

    # 餵食：數值變化
    def feed_effect(self, hunger_delta: int, affection_delta: int, icon: str = "", name: str = ""):
        row = self.read_pet()
        hunger = max(0, min(100, (row.hunger or 0) + int(hunger_delta or 0)))
        affection = max(0, min(row.affection_cap or 100, (row.affection or 0) + int(affection_delta or 0)))
        self.conn.execute("UPDATE pet SET hunger=?, affection=? WHERE id=1", (hunger, affection))
        self.conn.commit()

    # ---------------- Items & Inventory ----------------
    def get_item_id_by_name(self, name: str):
        r = self.conn.execute("SELECT id FROM items WHERE name=?", (name,)).fetchone()
        return r["id"] if r else None

    def ensure_item(self, name: str, icon: str = None, hunger_delta: int = 5, affection_delta: int = 1):
        iid = self.get_item_id_by_name(name)
        if iid is None:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO items(name, icon, hunger_delta, affection_delta) VALUES(?,?,?,?)",
                (name, icon, int(hunger_delta), int(affection_delta))
            )
            self.conn.commit()
            iid = cur.lastrowid
        return iid

    def set_inv_qty(self, item_id: int, qty: int):
        qty = max(0, int(qty))
        cur = self.conn.cursor()
        r = cur.execute("SELECT 1 FROM inventory WHERE item_id=?", (item_id,)).fetchone()
        if r:
            cur.execute("UPDATE inventory SET qty=? WHERE item_id=?", (qty, item_id))
        else:
            cur.execute("INSERT INTO inventory(item_id, qty) VALUES(?,?)", (item_id, qty))
        self.conn.commit()

    def inc_inv(self, item_id: int, delta: int):
        cur = self.conn.cursor()
        r = cur.execute("SELECT qty FROM inventory WHERE item_id=?", (item_id,)).fetchone()
        if r:
            cur.execute("UPDATE inventory SET qty=? WHERE item_id=?", (max(0, r["qty"] + int(delta)), item_id))
        else:
            cur.execute("INSERT INTO inventory(item_id, qty) VALUES(?,?)", (item_id, max(0, int(delta))))
        self.conn.commit()

    def dec_inv(self, item_id: int, delta: int):
        self.inc_inv(item_id, -abs(int(delta)))

    def list_inventory(self):
        """
        回傳 [(item_id, name, icon, qty, hunger_delta, affection_delta), ...]
        供背包與商店使用
        """
        rows = self.conn.execute("""
            SELECT i.id AS item_id, i.name, i.icon, IFNULL(inv.qty,0) AS qty,
                   i.hunger_delta, i.affection_delta
            FROM items i
            LEFT JOIN inventory inv ON inv.item_id = i.id
            WHERE IFNULL(inv.qty,0) > 0
            ORDER BY i.name COLLATE NOCASE
        """).fetchall()
        return [(r["item_id"], r["name"], r["icon"], r["qty"], r["hunger_delta"], r["affection_delta"]) for r in rows]

    # 方便用名稱直接 +1（Shop 的容錯分支會用到）
    def add_inventory_item_by_name(self, name: str, qty: int = 1, icon: str = None,
                                   hunger_delta: int = 5, affection_delta: int = 1):
        iid = self.ensure_item(name, icon, hunger_delta, affection_delta)
        self.inc_inv(iid, int(qty))

    # ---------------- Tasks（給 TasksPage 用） ----------------
    def add_task_old(self, title: str, minutes_target: int):
        self.conn.execute("INSERT INTO tasks_old(title, minutes_target) VALUES(?,?)", (title, int(minutes_target)))
        self.conn.commit()

    def list_tasks_old(self):
        rows = self.conn.execute(
            "SELECT id, title, minutes_target, minutes_done, status FROM tasks_old ORDER BY id DESC"
        ).fetchall()
        return [(r["id"], r["title"], r["minutes_target"], r["minutes_done"], f"[{r['status']}]") for r in rows]

    def set_task_status(self, task_id: int, status: str):
        self.conn.execute("UPDATE tasks_old SET status=? WHERE id=?", (status, int(task_id)))
        self.conn.commit()

    # ---------------- 专注时间功能方法 ----------------
    
    def get_setting(self, key, default_value=None):
        """获取设置值"""
        try:
            cursor = self.conn.execute("""
                SELECT value FROM settings 
                WHERE key = ?
            """, (key,))
            result = cursor.fetchone()
            return result[0] if result else default_value
        except Exception as e:
            print(f"获取设置失败: {e}")
            return default_value

    def set_setting(self, key, value):
        """设置配置值"""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at) 
                VALUES (?, ?, ?)
            """, (key, str(value), datetime.now().isoformat()))
            self.conn.commit()
        except Exception as e:
            print(f"设置配置失败: {e}")

    def add_task(self, text):
        """添加新任务"""
        try:
            self.conn.execute("""
                INSERT INTO tasks (text, completed, created_at) 
                VALUES (?, 0, ?)
            """, (text, datetime.now().isoformat()))
            self.conn.commit()
        except Exception as e:
            print(f"添加任务失败: {e}")

    def get_tasks(self):
        """获取所有任务"""
        try:
            cursor = self.conn.execute("""
                SELECT id, text, completed, created_at 
                FROM tasks 
                ORDER BY completed ASC, created_at DESC
            """)
            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'id': row[0],
                    'text': row[1],
                    'completed': bool(row[2]),
                    'created_at': row[3]
                })
            return tasks
        except Exception as e:
            print(f"获取任务失败: {e}")
            return []

    def toggle_task(self, task_id):
        """切换任务完成状态"""
        try:
            # 获取当前状态
            cursor = self.conn.execute("""
                SELECT completed FROM tasks WHERE id = ?
            """, (task_id,))
            result = cursor.fetchone()
            
            if result:
                new_status = 0 if result[0] else 1
                self.conn.execute("""
                    UPDATE tasks 
                    SET completed = ?, updated_at = ? 
                    WHERE id = ?
                """, (new_status, datetime.now().isoformat(), task_id))
                self.conn.commit()
                
                # 如果任务完成，给予奖励
                if new_status == 1:
                    self.add_coins(5)  # 完成任务奖励5金币
        except Exception as e:
            print(f"切换任务状态失败: {e}")

    def delete_task(self, task_id):
        """删除任务"""
        try:
            self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            self.conn.commit()
        except Exception as e:
            print(f"删除任务失败: {e}")

    def init_focus_tables(self):
        """初始化专注时间相关数据表"""
        try:
            cur = self.conn.cursor()
            
            # 设置表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 检查tasks表是否存在且结构正确
            try:
                cur.execute("SELECT text FROM tasks LIMIT 1")
                print("tasks表结构正确")
            except:
                print("tasks表不存在或结构错误，重建中...")
                # 删除旧表并创建新表
                cur.execute("DROP TABLE IF EXISTS tasks")
                cur.execute("""
                    CREATE TABLE tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        text TEXT NOT NULL,
                        completed INTEGER DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT DEFAULT NULL
                    )
                """)
                print("tasks表重建完成")
            
            # 专注记录表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS focus_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    duration_minutes INTEGER NOT NULL,
                    completed INTEGER DEFAULT 1,
                    is_pomodoro INTEGER DEFAULT 0,
                    coins_earned INTEGER DEFAULT 0,
                    date TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            self.conn.commit()
            print("专注时间数据表初始化完成")
        except Exception as e:
            print(f"初始化专注时间数据表失败: {e}")

    def record_focus_session(self, duration_minutes, completed=True, is_pomodoro=False, coins_earned=0):
        """记录专注会话"""
        try:
            self.conn.execute("""
                INSERT INTO focus_sessions 
                (duration_minutes, completed, is_pomodoro, coins_earned, date, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                duration_minutes, 
                1 if completed else 0,
                1 if is_pomodoro else 0,
                coins_earned,
                date.today().isoformat(),
                datetime.now().isoformat()
            ))
            self.conn.commit()
        except Exception as e:
            print(f"记录专注会话失败: {e}")

    def get_focus_stats(self, days=7):
        """获取专注统计数据"""
        try:
            from datetime import timedelta
            end_date = date.today()
            start_date = end_date - timedelta(days=days-1)
            
            cursor = self.conn.execute("""
                SELECT 
                    date,
                    SUM(duration_minutes) as total_minutes,
                    COUNT(*) as session_count,
                    SUM(coins_earned) as total_coins
                FROM focus_sessions 
                WHERE date BETWEEN ? AND ? AND completed = 1
                GROUP BY date
                ORDER BY date DESC
            """, (start_date.isoformat(), end_date.isoformat()))
            
            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = {
                    'total_minutes': row[1] or 0,
                    'session_count': row[2] or 0,
                    'total_coins': row[3] or 0
                }
            
            return stats
        except Exception as e:
            print(f"获取专注统计失败: {e}")
            return {}

    def get_today_focus_minutes(self):
        """获取今日专注分钟数"""
        try:
            today = date.today().isoformat()
            
            cursor = self.conn.execute("""
                SELECT COALESCE(SUM(duration_minutes), 0) 
                FROM focus_sessions 
                WHERE date = ? AND completed = 1
            """, (today,))
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            print(f"获取今日专注时间失败: {e}")
            return 0

    def get_yesterday_focus_minutes(self):
        """获取昨日专注分钟数"""
        try:
            from datetime import timedelta
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            
            cursor = self.conn.execute("""
                SELECT COALESCE(SUM(duration_minutes), 0) 
                FROM focus_sessions 
                WHERE date = ? AND completed = 1
            """, (yesterday,))
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            print(f"获取昨日专注时间失败: {e}")
            return 0

    def check_consecutive_focus_days(self, target_minutes=180):
        """检查连续专注天数"""
        try:
            from datetime import timedelta
            
            consecutive_days = 0
            current_date = date.today()
            
            while True:
                cursor = self.conn.execute("""
                    SELECT COALESCE(SUM(duration_minutes), 0) 
                    FROM focus_sessions 
                    WHERE date = ? AND completed = 1
                """, (current_date.isoformat(),))
                
                result = cursor.fetchone()
                daily_minutes = result[0] if result else 0
                
                if daily_minutes >= target_minutes:
                    consecutive_days += 1
                    current_date -= timedelta(days=1)
                else:
                    break
                
                # 防止无限循环，最多检查100天
                if consecutive_days >= 100:
                    break
        
            return consecutive_days
        except Exception as e:
            print(f"检查连续专注天数失败: {e}")
            return 0

    def update_daily_goal_progress(self):
        """更新每日目标进度，检查是否需要给予奖励"""
        try:
            today_minutes = self.get_today_focus_minutes()
            goal_minutes = int(self.get_setting('daily_focus_goal', 180))
            
            # 检查今天是否已经给过每日目标奖励
            today = date.today().isoformat()
            last_reward_date = self.get_setting('last_daily_goal_reward_date', '')
            
            if today_minutes >= goal_minutes and last_reward_date != today:
                # 达成每日目标，给予奖励
                base_reward = 50
                consecutive_days = self.check_consecutive_focus_days(goal_minutes)
                bonus_reward = min(consecutive_days * 5, 100)  # 连续天数奖励，最多100
                
                total_reward = base_reward + bonus_reward
                self.add_coins(total_reward)
                
                # 记录奖励日期
                self.set_setting('last_daily_goal_reward_date', today)
                self.set_setting('focus_consecutive_days', str(consecutive_days))
                
                return True, total_reward
            
            return False, 0
        except Exception as e:
            print(f"更新每日目标进度失败: {e}")
            return False, 0

    def get_focus_leaderboard(self, period='week'):
        """获取专注排行榜（为将来的社交功能预留）"""
        try:
            from datetime import timedelta
            
            if period == 'week':
                days = 7
            elif period == 'month':
                days = 30
            else:
                days = 7
            
            end_date = date.today()
            start_date = end_date - timedelta(days=days-1)
            
            cursor = self.conn.execute("""
                SELECT 
                    SUM(duration_minutes) as total_minutes,
                    COUNT(*) as total_sessions,
                    AVG(duration_minutes) as avg_session
                FROM focus_sessions 
                WHERE date BETWEEN ? AND ? AND completed = 1
            """, (start_date.isoformat(), end_date.isoformat()))
            
            result = cursor.fetchone()
            if result:
                return {
                    'total_minutes': result[0] or 0,
                    'total_sessions': result[1] or 0,
                    'avg_session': round(result[2] or 0, 1),
                    'period': period,
                    'days': days
                }
            
            return None
        except Exception as e:
            print(f"获取专注排行榜失败: {e}")
            return None