# reminders.py
# -*- coding: utf-8 -*-
"""
桌寵提醒／記事本模組（PyQt5／SQLite）
------------------------------------
功能：
1) 右鍵開啟「提醒／記事本…」視窗，查看所有待辦、已完成事項
2) 可新增／編輯／刪除提醒（標題、內容、日期、時間）
3) 到時間自動彈窗提醒，亦可重複提醒（可選）
4) SQLite 永久儲存，跨程式重啟不丟失

整合方式：請在你的 pet.py 內：
- from reminders import ReminderListWindow, ReminderChecker, ReminderManager
- 在主視窗（例如 Pet 類）初始化時建立 ReminderManager 與 ReminderChecker
- 在右鍵選單加入一個 QAction 來開啟 ReminderListWindow
- 在 _on_reminder_due handler 中呼叫彈窗（本檔已附帶預設彈窗，也可改成 pet 的對話框）

備註：
- PyQt5 介面元件：QMainWindow, QDialog, QTableView（QStandardItemModel）
- 以本地時間為準（time.time() 的秒數）
- 檢查頻率預設 30 秒（可在 ReminderChecker(start_interval_s=30) 調整）
"""

from __future__ import annotations
import os
import sqlite3
import time
from dataclasses import dataclass
from typing import List, Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QDate, QTime
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView,
    QDialog, QLabel, QLineEdit, QTextEdit, QDateEdit, QTimeEdit, QMessageBox,
    QApplication
)

# -----------------------------
# 資料層：SQLite + dataclass
# -----------------------------

@dataclass
class Reminder:
    id: Optional[int]
    title: str
    notes: str
    due_ts: int  # UNIX seconds
    done: int = 0
    created_ts: int = 0


class ReminderManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                notes TEXT DEFAULT '',
                due_ts INTEGER NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_ts INTEGER NOT NULL
            );
            """
        )
        self.conn.commit()

    # CRUD
    def add(self, title: str, notes: str, due_ts: int) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO reminders (title, notes, due_ts, done, created_ts) VALUES (?, ?, ?, 0, ?)",
            (title, notes, due_ts, int(time.time())),
        )
        self.conn.commit()
        return cur.lastrowid

    def update(self, rid: int, title: str, notes: str, due_ts: int, done: int):
        self.conn.execute(
            "UPDATE reminders SET title=?, notes=?, due_ts=?, done=? WHERE id=?",
            (title, notes, due_ts, int(done), rid),
        )
        self.conn.commit()

    def delete(self, rid: int):
        self.conn.execute("DELETE FROM reminders WHERE id=?", (rid,))
        self.conn.commit()

    def mark_done(self, rid: int, done: bool = True):
        self.conn.execute("UPDATE reminders SET done=? WHERE id=?", (1 if done else 0, rid))
        self.conn.commit()

    def get_all(self) -> List[Reminder]:
        rows = self.conn.execute(
            "SELECT id, title, notes, due_ts, done, created_ts FROM reminders ORDER BY due_ts ASC"
        ).fetchall()
        return [Reminder(*row) for row in rows]

    def get_due(self, now_ts: int) -> List[Reminder]:
        rows = self.conn.execute(
            "SELECT id, title, notes, due_ts, done, created_ts FROM reminders WHERE done=0 AND due_ts<=? ORDER BY due_ts ASC",
            (now_ts,),
        ).fetchall()
        return [Reminder(*row) for row in rows]


# -----------------------------------
# UI：新增／編輯對話框
# -----------------------------------

class ReminderDialog(QDialog):
    def __init__(self, parent=None, reminder: Optional[Reminder] = None):
        super().__init__(parent)
        self.setWindowTitle("新增／編輯提醒")
        self.reminder = reminder

        layout = QVBoxLayout(self)

        # 標題
        layout.addWidget(QLabel("標題"))
        self.title_edit = QLineEdit()
        layout.addWidget(self.title_edit)

        # 內容
        layout.addWidget(QLabel("內容（可留空）"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(120)
        layout.addWidget(self.notes_edit)

        # 日期時間
        dt_row = QHBoxLayout()
        layout.addLayout(dt_row)
        dt_row.addWidget(QLabel("日期"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        dt_row.addWidget(self.date_edit)

        dt_row.addWidget(QLabel("時間"))
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime.currentTime())
        dt_row.addWidget(self.time_edit)

        # 按鈕
        btns = QHBoxLayout()
        layout.addLayout(btns)
        self.btn_ok = QPushButton("儲存")
        self.btn_cancel = QPushButton("取消")
        btns.addStretch(1)
        btns.addWidget(self.btn_ok)
        btns.addWidget(self.btn_cancel)

        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        if reminder:
            self.title_edit.setText(reminder.title)
            self.notes_edit.setText(reminder.notes)
            dt = time.localtime(reminder.due_ts)
            self.date_edit.setDate(QDate(dt.tm_year, dt.tm_mon, dt.tm_mday))
            self.time_edit.setTime(QTime(dt.tm_hour, dt.tm_min))

    def result_payload(self):
        title = self.title_edit.text().strip() or "(未命名)"
        notes = self.notes_edit.toPlainText().strip()
        d = self.date_edit.date()
        t = self.time_edit.time()
        # 本地時間 → time.mktime
        due_struct = time.struct_time((d.year(), d.month(), d.day(), t.hour(), t.minute(), 0, -1, -1, -1))
        due_ts = int(time.mktime(due_struct))
        return title, notes, due_ts


# -----------------------------------
# UI：列表視窗（記事本樣式）
# -----------------------------------

class ReminderListWindow(QMainWindow):
    def __init__(self, manager: ReminderManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("提醒／記事本")
        self.manager = manager

        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)

        # 表格
        self.model = QStandardItemModel(0, 5, self)
        self.model.setHorizontalHeaderLabels(["ID", "標題", "日期時間", "狀態", "內容"])

        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setSelectionBehavior(QTableView.SelectRows)
        self.view.setEditTriggers(QTableView.NoEditTriggers)
        self.view.setColumnWidth(0, 60)
        self.view.setColumnWidth(1, 220)
        self.view.setColumnWidth(2, 160)
        self.view.setColumnWidth(3, 80)
        v.addWidget(self.view)

        # 按鈕列
        h = QHBoxLayout()
        v.addLayout(h)
        self.btn_add = QPushButton("新增")
        self.btn_edit = QPushButton("編輯")
        self.btn_done = QPushButton("完成/未完成")
        self.btn_del = QPushButton("刪除")
        h.addWidget(self.btn_add)
        h.addWidget(self.btn_edit)
        h.addWidget(self.btn_done)
        h.addWidget(self.btn_del)
        h.addStretch(1)

        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_done.clicked.connect(self._on_toggle_done)
        self.btn_del.clicked.connect(self._on_delete)

        self.refresh()

    def refresh(self):
        self.model.removeRows(0, self.model.rowCount())
        rows = self.manager.get_all()
        for r in rows:
            dt_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(r.due_ts))
            status = "✅ 完成" if r.done else "⏳ 未完成"
            items = [
                QStandardItem(str(r.id)),
                QStandardItem(r.title),
                QStandardItem(dt_str),
                QStandardItem(status),
                QStandardItem(r.notes),
            ]
            for it in items:
                it.setEditable(False)
            self.model.appendRow(items)

    def _selected_id(self) -> Optional[int]:
        idxs = self.view.selectionModel().selectedRows()
        if not idxs:
            return None
        row = idxs[0].row()
        rid = int(self.model.item(row, 0).text())
        return rid

    def _on_add(self):
        dlg = ReminderDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            title, notes, due_ts = dlg.result_payload()
            self.manager.add(title, notes, due_ts)
            self.refresh()

    def _on_edit(self):
        rid = self._selected_id()
        if rid is None:
            QMessageBox.information(self, "提示", "請先選擇一筆資料")
            return
        # 讀取既有資料
        r = next((x for x in self.manager.get_all() if x.id == rid), None)
        if not r:
            return
        dlg = ReminderDialog(self, reminder=r)
        if dlg.exec_() == QDialog.Accepted:
            title, notes, due_ts = dlg.result_payload()
            self.manager.update(rid, title, notes, due_ts, r.done)
            self.refresh()

    def _on_toggle_done(self):
        rid = self._selected_id()
        if rid is None:
            QMessageBox.information(self, "提示", "請先選擇一筆資料")
            return
        # 查現在狀態
        r = next((x for x in self.manager.get_all() if x.id == rid), None)
        if not r:
            return
        self.manager.mark_done(rid, not bool(r.done))
        self.refresh()

    def _on_delete(self):
        rid = self._selected_id()
        if rid is None:
            QMessageBox.information(self, "提示", "請先選擇一筆資料")
            return
        if QMessageBox.question(self, "確認", "確定要刪除這筆提醒嗎？") == QMessageBox.Yes:
            self.manager.delete(rid)
            self.refresh()


# -----------------------------------
# 定時器：定期檢查是否到期
# -----------------------------------

class ReminderChecker(QObject):
    reminder_due = pyqtSignal(Reminder)

    def __init__(self, manager: ReminderManager, parent=None, start_interval_s: int = 30):
        super().__init__(parent)
        self.manager = manager
        self.timer = QTimer(self)
        self.timer.setInterval(start_interval_s * 1000)
        self.timer.timeout.connect(self.check)

    def start(self):
        self.timer.start()
        self.check()  # 啟動時先檢一次

    def stop(self):
        self.timer.stop()

    def check(self):
        now_ts = int(time.time())
        due_list = self.manager.get_due(now_ts)
        for r in due_list:
            # 發出提醒事件，交給外部決定如何顯示
            self.reminder_due.emit(r)
            # 預設：提醒後標記為完成（避免重複提醒）；如需重複提醒可改邏輯
            self.manager.mark_done(r.id, True)


# -----------------------------------
# 預設提醒彈窗（亦可在外部自定義）
# -----------------------------------

def show_reminder_popup(parent, reminder: Reminder):
    dt_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(reminder.due_ts))
    msg = QMessageBox(parent)
    msg.setWindowTitle("時間到囉！")
    msg.setText(f"到 {dt_str} 時間了，您該做預先定好的事項：\n\n『{reminder.title}』")
    if reminder.notes:
        msg.setInformativeText(reminder.notes)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.setIcon(QMessageBox.Information)
    msg.exec_()


# -----------------------------------
# （可選）獨立跑測試
# -----------------------------------
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    db = os.path.join(os.path.expanduser("~"), ".deskpet", "reminders.db")
    mgr = ReminderManager(db)
    w = ReminderListWindow(mgr)
    w.resize(800, 480)
    w.show()

    checker = ReminderChecker(mgr)
    checker.reminder_due.connect(lambda r: show_reminder_popup(w, r))
    checker.start()

    sys.exit(app.exec_())
