# main_dashboard.py 片段
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QListWidget, QStackedWidget, QListWidgetItem
)
from .pages.page_status import StatusPage
from .pages.page_inventory import InventoryPage
from .pages.page_shop import ShopPage
from .pages.page_animations import AnimationsPage
from .pages.page_tasks import BeautifulTasksPage
from database import DB
from .event_bus import bus

class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("角色面板")
        self.resize(860, 520)
        self.db = DB()

        # ---- 佈局骨架 ----
        root = QWidget()
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)

        # 側邊欄
        self.side = QListWidget()
        self.side.setFixedWidth(160)
        for name in ["狀態", "背包", "商店", "動作", "任務"]:
            self.side.addItem(QListWidgetItem(name))
        h.addWidget(self.side)

        # 右側堆疊
        self.stack = QStackedWidget()
        h.addWidget(self.stack, 1)

        # ---- 先建狀態頁（供回呼刷新）----
        self.page_status = StatusPage(self.db)

        # 這個回呼會被「動畫分頁」呼叫
        def on_play_from_page(key: str):
            # 交給事件匯流排 -> 由桌寵接手播放
            bus.play_anim.emit(key)

        # 統一資料變更回呼：任何頁動到資料 → 刷新這幾頁
        def on_data_changed():
            self.page_status.refresh()
            self.page_inventory.refresh()
            self.page_shop.refresh()

        # 其餘頁面，將回呼丟給會改資料的頁（背包/商店）
        self.page_inventory  = InventoryPage(self.db, on_changed=on_data_changed)
        self.page_shop       = ShopPage(self.db, on_changed=on_data_changed)
        self.page_animations = AnimationsPage(self.db)
        self.page_tasks      = BeautifulTasksPage(self.db)

        # 加入堆疊
        self.pages = [
            self.page_status,
            self.page_inventory,
            self.page_shop,
            self.page_animations,
            self.page_tasks,
        ]
        for p in self.pages:
            self.stack.addWidget(p)

        self.side.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.side.setCurrentRow(0)

        self.page_animations = AnimationsPage(self.db, on_play=on_play_from_page)

        # ---- 載入 QSS ----
        qss = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(qss):
            with open(qss, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
    def _refresh_all(self):
        # 讓狀態/背包/商店在數據改變時同步刷新
        if hasattr(self.page_status, "refresh"): self.page_status.refresh()
        if hasattr(self.page_inventory, "refresh"): self.page_inventory.refresh()
        if hasattr(self.page_shop, "refresh"): self.page_shop.refresh()