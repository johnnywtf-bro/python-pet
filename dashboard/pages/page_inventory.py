# dashboard/pages/page_inventory.py - 修復版本
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QFrame, QSizePolicy, QSpacerItem
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize

GRID_COLS = 5
GRID_ROWS_MIN = 5
ICON_SIZE  = 72

ASSET_DIR = Path(__file__).resolve().parents[2] / "assets" / "food"

# ✅ 寫死：名稱 → 檔名
ICON_MAP = {
    "麵包": "bread.png",
    "雞蛋吐司": "Egg toast.png",
    "熱狗麵包": "hot dog bread.png",
    "紅豆麵包": "Red bean bread.png",
}

class SlotButton(QPushButton):
    """單一格子"""
    def __init__(self, item=None):
        super().__init__()
        self.setCheckable(True)
        self.setObjectName("invSlot")
        self.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.item = item
        self.count_label = QLabel(self)
        self.count_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.count_label.setStyleSheet(
            "color:#111; font-size:12px; font-weight:600; background:transparent;"
        )
        self.count_label.hide()
        if item:
            self._apply_item()

    def _place_count(self):
        self.count_label.adjustSize()
        m = 4
        x = self.width() - self.count_label.width() - m
        y = self.height() - self.count_label.height() - m
        self.count_label.move(x, y)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.count_label.isVisible():
            self._place_count()

    def _apply_item(self):
        item_id, name, icon, qty, *_ = self.item
        self.setToolTip(f"{name} ×{qty}")

        # ✅ 不用 DB 的 icon，直接用 ICON_MAP
        fname = ICON_MAP.get(name, "")
        abs_path = ASSET_DIR / fname
        pm = QPixmap(str(abs_path))
        if not pm.isNull():
            pm = pm.scaled(ICON_SIZE, ICON_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setIcon(QIcon(pm))
        else:
            self.setIcon(QIcon())

        if qty > 1:
            self.count_label.setText(str(qty))
            self.count_label.show()
            self._place_count()
        else:
            self.count_label.hide()

    def clear_item(self):
        self.item = None
        self.setIcon(QIcon())
        self.setChecked(False)
        self.setToolTip("空")
        self.count_label.hide()


class InventoryPage(QWidget):
    def __init__(self, db, on_changed=None):
        super().__init__()
        self.db = db
        self.on_changed = on_changed or (lambda: None)
        self.selected_btn: SlotButton | None = None
        self.show_food_only = True  # 添加過濾狀態

        root = QVBoxLayout(self)
        root.setContentsMargins(20,16,20,16)
        root.setSpacing(12)

        # 標題列
        title_row = QHBoxLayout()
        title = QLabel("角色背包")
        title.setObjectName("h1")
        title_row.addWidget(title)

        title_row.addItem(QSpacerItem(10,10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.coin_icon = QLabel("🪙")
        self.coin_val  = QLabel("0")
        coin_wrap = QHBoxLayout()
        coin_wrap.addWidget(self.coin_icon)
        coin_wrap.addWidget(self.coin_val)
        coin_w = QFrame(); coin_w.setLayout(coin_wrap)
        title_row.addWidget(coin_w)
        root.addLayout(title_row)

        # 控制列
        ctrl = QHBoxLayout()
        self.btn_food = QPushButton("🍞 食物")
        self.btn_food.setCheckable(True)
        self.btn_food.setChecked(True)
        self.btn_food.clicked.connect(self._filter_food_only)
        # 設置為白色按鈕樣式
        self.btn_food.setProperty("class", "primary")
        ctrl.addWidget(self.btn_food)

        ctrl.addItem(QSpacerItem(10,10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        self.btn_use = QPushButton("使用")
        self.btn_use.setEnabled(False)  # 初始狀態為灰色
        self.btn_use.clicked.connect(self._use_selected)
        ctrl.addWidget(self.btn_use)
        root.addLayout(ctrl)

        # 物品格子
        self.grid = QGridLayout()
        self.grid.setSpacing(14)
        root.addLayout(self.grid)

        self._build_grid()
        self.refresh()

    def _build_grid(self):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.setParent(None)
        total_slots = GRID_COLS * GRID_ROWS_MIN
        self.slots: list[SlotButton] = []
        for i in range(total_slots):
            btn = SlotButton(None)
            btn.clicked.connect(lambda checked, b=btn: self._on_slot_clicked(b))
            self.grid.addWidget(btn, i // GRID_COLS, i % GRID_COLS)
            self.slots.append(btn)

    def _on_slot_clicked(self, btn: SlotButton):
        if self.selected_btn and self.selected_btn is not btn:
            self.selected_btn.setChecked(False)
        self.selected_btn = btn if btn.isChecked() and btn.item else None
        
        # 根據選中狀態更新按鈕樣式
        if self.selected_btn is not None:
            self.btn_use.setEnabled(True)
            self.btn_use.setProperty("class", "primary")  # 白色可用按鈕
        else:
            self.btn_use.setEnabled(False)  # 灰色不可用按鈕
            self.btn_use.setProperty("class", "")
        
        # 刷新按鈕樣式
        self.btn_use.style().unpolish(self.btn_use)
        self.btn_use.style().polish(self.btn_use)

    def _filter_food_only(self):
        """切換食物篩選"""
        self.show_food_only = self.btn_food.isChecked()
        self.refresh()

    def _fill_slots_with_items(self, items):
        for s in self.slots: 
            s.clear_item()
        merged = {}
        for row in items:
            item_id, name, icon, qty, hd, ad = row
            if qty <= 0:
                continue
            
            # 如果開啟食物篩選，只顯示食物類物品
            if self.show_food_only:
                # 這裡可以根據需要添加更多篩選邏輯
                # 目前所有物品都是食物，所以直接通過
                pass
            
            if item_id in merged:
                merged[item_id][3] += qty
            else:
                merged[item_id] = [item_id, name, icon, qty, hd, ad]

        merged_items = list(merged.values())
        for i, row in enumerate(merged_items[:len(self.slots)]):
            self.slots[i].item = row
            self.slots[i]._apply_item()

    def refresh(self):
        ps = self.db.read_pet()
        self.coin_val.setText(str(ps.coins or 0))
        items = self.db.list_inventory()
        self._fill_slots_with_items(items)
        self.selected_btn = None
        self.btn_use.setEnabled(False)
        
        # 重置使用按鈕樣式
        self.btn_use.setProperty("class", "")
        self.btn_use.style().unpolish(self.btn_use)
        self.btn_use.style().polish(self.btn_use)

    def _use_selected(self):
        if not self.selected_btn or not self.selected_btn.item:
            return
        item_id, name, icon, qty, hd, ad = self.selected_btn.item
        if qty <= 0:
            return
        self.db.dec_inv(item_id, 1)
        self.db.feed_effect(hd, ad, icon, name)
        if self.on_changed: 
            self.on_changed()
        else: 
            self.refresh()