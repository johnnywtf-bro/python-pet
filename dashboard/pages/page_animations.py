# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QSpacerItem, QSizePolicy, QFrame, QCheckBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap
from dashboard.event_bus import bus
import os

CHAR_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "character")

# 動作 → 對應檔名
PLAY_LIST = [
    ("walk",         "walk（行走）"),
    ("idle",         "idle（待機）"),
    ("sleep",        "sleep（睡覺）"),
    ("think",        "think（思考）"),
    ("happy",        "happy（開心）"),
    ("sad",          "sad（傷心）"),
    ("love_orange",  "Love Orange（愛哦潤吉）"),
]

class AnimationsPage(QWidget):
    """
    動畫管理
    - 動作列表：每列[勾選框 + 名稱 + 播放按鈕]
    - 開始循環：每 20s 切換到下一個打勾的動作
    備註：
      1) 播放時會呼叫 on_play(gif_path)；若沒有傳入 on_play，會嘗試 event_bus.emit('pet.play', path)
      2) 你可以在 DashboardWindow 建立 on_play，把它發到桌寵那邊去播放
    """
    def __init__(self, db=None, on_play=None):
        super().__init__()
        self.db = db
        # 預設用事件匯流排（面板→桌寵）
        self.on_play = on_play or (lambda key: bus.play_anim.emit(key))

        self._timer = QTimer(self)
        self._timer.setInterval(20_000)       # 20 秒
        self._timer.timeout.connect(self._play_next_checked)
        self._checked_order = []
        self._idx = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        title = QLabel("動畫管理")
        title.setStyleSheet("font-size:26px;font-weight:600;")
        root.addWidget(title)

        sub = QLabel("動作列表（勾選可加入循環；▶ 可立即播放）")
        sub.setStyleSheet("color:#666;")
        root.addWidget(sub)

        # 列表卡片
        card = QFrame()
        card.setObjectName("animCard")
        card.setStyleSheet("#animCard{border:1px solid #eee;border-radius:10px;background:#fff;}")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(16, 10, 16, 10)
        cv.setSpacing(6)

        self._rows = []   # [(key, QCheckBox, QPushButton)] - 修改：增加按鈕引用
        for key, label in PLAY_LIST:
            row = QHBoxLayout()
            
            # 修改1：勾選框樣式 - 從空白框變成顯示√
            cb = QCheckBox(label)
            cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #ccc;
                    border-radius: 3px;
                    background: white;
                }
                QCheckBox::indicator:checked {
                    background: #4CAF50;
                    border-color: #4CAF50;
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEwIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik04LjUgMUwzLjUgNkwxLjUgNCIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+Cg==);
                }
                QCheckBox::indicator:checked:hover {
                    background: #45a049;
                }
            """)
            
            # 修改2：播放按鈕樣式 - 增加橫向尺寸讓圖標能完整展示
            btn = QPushButton("▶")
            btn.setFixedSize(48, 30)  # 增加寬度從 36 到 48
            btn.setStyleSheet("""
                QPushButton {
                    background: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 6px;
                    font-size: 14px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background: #e0e0e0;
                    border-color: #999;
                }
                QPushButton:pressed {
                    background: #d0d0d0;
                }
            """)
            btn.clicked.connect(lambda _, k=key: self.on_play(k))
            
            row.addWidget(cb)
            row.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
            row.addWidget(btn)
            wrap = QFrame(); wrap.setLayout(row)
            cv.addWidget(wrap)
            self._rows.append((key, cb, btn))  # 修改：保存按鈕引用

        root.addWidget(card)

        # 循環控制列
        ctl = QHBoxLayout()
        self.btn_loop = QPushButton("開始循環")
        self.btn_loop.setCheckable(True)
        self.btn_loop.toggled.connect(self._toggle_loop)
        self.btn_loop.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #45a049;
            }
            QPushButton:checked {
                background: #f44336;
            }
            QPushButton:checked:hover {
                background: #da190b;
            }
        """)
        ctl.addWidget(self.btn_loop)
        ctl.addStretch(1)
        root.addLayout(ctl)

    def _toggle_loop(self, on: bool):
        if on:
            # 修改3：修復AttributeError - 使用_rows而不是self.list
            self._checked_order = [k for (k, cb, btn) in self._rows if cb.isChecked()]
            self._idx = 0
            if not self._checked_order:
                self.btn_loop.setChecked(False)
                return
            self.btn_loop.setText("停止循環")
            self.on_play(self._checked_order[self._idx])  # 立即播第一個
            self._timer.start()
        else:
            self._timer.stop()
            self.btn_loop.setText("開始循環")

    def _play_next_checked(self):
        if not self._checked_order:
            self._timer.stop()
            self.btn_loop.setChecked(False)
            return
        self._idx = (self._idx + 1) % len(self._checked_order)
        self.on_play(self._checked_order[self._idx])

    # --- 播放 ---
    def _play_gif(self, path: str):
        if not os.path.exists(path):
            print("動畫檔不存在：", path)
            return

        # 1) 若有從 DashboardWindow 傳入 on_play，直接用
        if callable(self.on_play):
            self.on_play(path)
            return

        # 2) 沒有 on_play，嘗試使用 event_bus（若你專案有）
        try:
            from ..pages.event_bus import EventBus  # 如果你有單例/總線可改這裡
        except Exception:
            EventBus = None

        if EventBus and hasattr(EventBus, "emit"):
            EventBus.emit("pet.play", {"path": path})
        else:
            # 沒有總線也沒 on_play，就先列印
            print("[AnimationsPage] play:", path)