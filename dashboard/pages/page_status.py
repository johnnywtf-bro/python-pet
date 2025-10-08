# dashboard/pages/page_status.py
import os, time
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame,
    QLineEdit, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

def stars_by_days(days:int)->str:
    n = 0
    if days >= 1:  n = 1
    if days >= 5:  n = 2
    if days >= 10: n = 3
    if days >= 20: n = 4
    if days >= 40: n = 5
    return "★"*n + "☆"*(5-n)

class StatusPage(QWidget):
    def __init__(self, db):
        super().__init__(); self.db = db
        root = QVBoxLayout(self); root.setContentsMargins(20,16,20,16); root.setSpacing(6)

        # ── 標題列：左「角色狀態」，右「用戶暱稱 ______」 ──
        head = QHBoxLayout(); head.setSpacing(12)
        title = QLabel("角色狀態"); title.setObjectName("h1")
        head.addWidget(title)
        head.addItem(QSpacerItem(10,10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        head.addWidget(QLabel("用戶暱稱"))
        self.edit_user = QLineEdit(); self.edit_user.setPlaceholderText("輸入你的名字")
        self.edit_user.setFixedWidth(240)
        self.edit_user.editingFinished.connect(self._save_nickname)
        head.addWidget(self.edit_user)
        root.addLayout(head)

        # ── 狀態卡 ──
        card = QFrame(); card.setObjectName("statusCard")
        cv = QHBoxLayout(card)  # ← 左右並排：左頭像、右資訊欄
        cv.setContentsMargins(18,14,18,14); cv.setSpacing(14)

        # 讓卡片「高度固定，寬度自適應」，不去撐開下一行
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # 左：大頭像
        self.avatar = QLabel(); self.avatar.setFixedSize(96,96)
        self.avatar.setObjectName("avatar")
        cv.addWidget(self.avatar, 0, Qt.AlignTop)
        root.addWidget(card)

        # 右：資訊欄（四行）
        info = QVBoxLayout(); info.setSpacing(10)

        # 行1：名稱 + （已餵養X天）
        row_name = QHBoxLayout()
        self.lab_name = QLabel("doro"); self.lab_name.setObjectName("petName")
        row_name.addWidget(self.lab_name)
        self.lab_days = QLabel("（已餵養 1 天）"); self.lab_days.setObjectName("days")
        row_name.addWidget(self.lab_days)
        row_name.addStretch(1)
        info.addLayout(row_name)
        # 分隔線（細）
        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet("background:#EAECEF;"); info.addWidget(sep)

        # 行2：等級（星星）
        row_level = QHBoxLayout()
        row_level.addWidget(QLabel("等級"))
        self.lab_stars = QLabel("★☆☆☆☆"); self.lab_stars.setObjectName("stars")
        row_level.addWidget(self.lab_stars)
        row_level.addStretch(1)
        info.addLayout(row_level)

        # 行3：飽食度
        row_h = QHBoxLayout()
        row_h.addWidget(QLabel("飽食度"))
        self.pb_h = QProgressBar(); self.pb_h.setObjectName("hungerBar")
        self.pb_h.setTextVisible(True); self.pb_h.setFormat("%v/%m")
        row_h.addWidget(self.pb_h, 1)
        info.addLayout(row_h)

        # 行4：好感度
        row_a = QHBoxLayout()
        row_a.addWidget(QLabel("好感度"))
        self.pb_a = QProgressBar(); self.pb_a.setObjectName("affBar")
        self.pb_a.setTextVisible(True); self.pb_a.setFormat("%v/%m")
        row_a.addWidget(self.pb_a, 1)
        info.addLayout(row_a)

        cv.addLayout(info, 1)
        root.addWidget(card)

        # 「狀態日誌」標題（下面接你的日誌區塊或原本 widget）
        log_title = QLabel("狀態日誌")
        log_title.setObjectName("h2")
        log_title.setStyleSheet("margin-top:0px; margin-bottom:2px;")
        root.addWidget(log_title, 0, Qt.AlignTop)

        # 定時刷新（飽食度衰減 & 天數進位）
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh)
        self.timer.start(10_000)

        self._init_user_and_avatar()
        self.refresh()

    # 讀 DB 的暱稱／頭像，首次載入
    def _init_user_and_avatar(self):
        ava, nickname = self.db.get_avatar_and_user()
        if nickname:
            self.edit_user.setText(nickname)

        # 預設頭像（相對路徑）
        if not ava:
            ava = "character/doro.png"

        p = Path(ava)
        if not p.is_absolute():
            p = Path(__file__).resolve().parents[2] / p  # 專案根/character/doro.png
        p = p.resolve()
        if p.exists():
            pm = QPixmap(str(p)).scaled(96,96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.avatar.setPixmap(pm)

    def _save_nickname(self):
        self.db.set_user_nickname(self.edit_user.text().strip())

    def refresh(self):
        ps = self.db.read_pet()
        # 名稱／天數／星級
        self.lab_name.setText(ps.name)
        self.lab_days.setText(f"（已餵養 {ps.days_alive} 天）")
        self.lab_stars.setText(stars_by_days(ps.days_alive))
        # 兩條進度條
        self.pb_h.setRange(0, 100); self.pb_h.setValue(max(0, min(100, ps.hunger)))
        self.pb_a.setRange(0, ps.affection_cap); self.pb_a.setValue(max(0, min(ps.affection_cap, ps.affection)))
