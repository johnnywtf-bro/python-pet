# -*- coding: utf-8 -*-
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QGridLayout, QFrame, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon

GRID_COLS = 2
CARD_W = 360
ICON_SIZE = 72

ASSET_DIR = Path(__file__).resolve().parents[2] / "assets" / "food"

# ✅ 寫死：名稱 → 檔名
ICON_MAP = {
    "麵包": "bread.png",
    "雞蛋吐司": "Egg toast.png",
    "熱狗麵包": "hot dog bread.png",
    "紅豆麵包": "Red bean bread.png",
}

PRICE_TABLE = {
    "麵包": 0,
    "雞蛋吐司": 0,
    "熱狗麵包": 0,
    "紅豆麵包": 0,
}

CATEGORY_TABLE = {
    "麵包": "主食",
    "雞蛋吐司": "主食",
    "熱狗麵包": "主食",
    "紅豆麵包": "主食",
}

CATALOG = [
    {"id": None, "name": "麵包",     "price": PRICE_TABLE["麵包"],     "category": "主食", "module": "系統物品"},
    {"id": None, "name": "雞蛋吐司", "price": PRICE_TABLE["雞蛋吐司"], "category": "主食", "module": "系統物品"},
    {"id": None, "name": "熱狗麵包", "price": PRICE_TABLE["熱狗麵包"], "category": "主食", "module": "系統物品"},
    {"id": None, "name": "紅豆麵包", "price": PRICE_TABLE["紅豆麵包"], "category": "主食", "module": "系統物品"},
]


class ShopPage(QWidget):
    def __init__(self, db, on_changed=None):
        super().__init__()
        self.db = db
        self.on_changed = on_changed or (lambda: None)

        self.current_keyword = ""
        self.current_category = None
        self.current_module = "系統物品"
        self.mode = "buy"

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ── 標題列 ──
        head = QHBoxLayout()
        self.lbl_title = QLabel("商店"); self.lbl_title.setObjectName("h1")
        head.addWidget(self.lbl_title)
        head.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.coin_icon = QLabel("🪙"); self.lbl_coins = QLabel("0")
        coin_wrap = QHBoxLayout(); coin_wrap.addWidget(self.coin_icon); coin_wrap.addWidget(self.lbl_coins)
        coin_widget = QFrame(); coin_widget.setLayout(coin_wrap)
        head.addWidget(coin_widget)
        root.addLayout(head)

        # 模式切換
        mode_row = QHBoxLayout(); mode_row.setSpacing(8)
        self.btn_mode_buy = QPushButton("買"); self.btn_mode_sell = QPushButton("賣")
        for b in (self.btn_mode_buy, self.btn_mode_sell):
            b.setCheckable(True); b.setAutoExclusive(True)
        self.btn_mode_buy.setChecked(True)
        self.btn_mode_buy.clicked.connect(lambda: self._switch_mode("buy"))
        self.btn_mode_sell.clicked.connect(lambda: self._switch_mode("sell"))
        mode_row.addWidget(self.btn_mode_buy); mode_row.addWidget(self.btn_mode_sell)
        root.addLayout(mode_row)

        # 搜索框
        bar = QHBoxLayout()
        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText("按名稱、模組搜索…")
        self.search_edit.textChanged.connect(self._on_search_changed)
        bar.addWidget(self.search_edit)
        root.addLayout(bar)

        # 篩選按鈕列
        filter_row = QHBoxLayout()
        self.btn_all = QPushButton("全部")
        self.btn_food = QPushButton("主食")
        for b in (self.btn_all, self.btn_food):
            b.setCheckable(True); b.setAutoExclusive(True)
        self.btn_all.setChecked(True)
        self.btn_all.clicked.connect(lambda: self._set_category(None))
        self.btn_food.clicked.connect(lambda: self._set_category("主食"))
        filter_row.addWidget(self.btn_all)
        filter_row.addWidget(self.btn_food)
        filter_row.addStretch(1)
        root.addLayout(filter_row)

        # 商品格區
        self.list_wrap = QFrame()
        self.list_wrap.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.grid = QGridLayout(self.list_wrap); self.grid.setSpacing(12)
        root.addWidget(self.list_wrap, 1)

        self.refresh()


    # === 新增方法到 ShopPage ===
    def _set_category(self, cat):
        """切換分類後刷新商店"""
        self.current_category = cat
        self.refresh()

    # === 搜索 ===
    def _on_search_changed(self, text: str):
        """當搜尋框內容變化時，重新篩選商品"""
        self.current_keyword = text.strip()
        self._rebuild_grid()

    # === 模式切換 ===
    def _switch_mode(self, m: str):
        self.mode = m
        self.lbl_title.setText("商店（買）" if m == "buy" else "商店（賣）")
        self._rebuild_grid()

    # === 修改 _list_buy_items ===
    def _list_buy_items(self):
        name2qty = {}
        try:
            inv = self.db.list_inventory()
            for _, name, _, qty, *_ in inv:
                name2qty[name] = max(0, int(qty or 0))
        except Exception as e:
            print("list_buy_items error:", e)

        rows = []
        for it in CATALOG:
            # 🔑 篩選分類
            if self.current_category and it["category"] != self.current_category:
                continue
            # 🔑 關鍵字搜尋
            if self.current_keyword and self.current_keyword not in it["name"]:
                continue

            rows.append({
                "id": it["id"],
                "name": it["name"],
                "qty": name2qty.get(it["name"], 0),
                "price": it["price"],
                "category": it["category"],
                "module": it["module"],
            })
        return rows

    # === 修改 _list_sellable_items ===
    def _list_sellable_items(self):
        rows = []
        try:
            inv = self.db.list_inventory()
            for item_id, name, icon, qty, *_ in inv:
                if qty and qty > 0:
                    # 🔑 篩選分類
                    if self.current_category and CATEGORY_TABLE.get(name, "主食") != self.current_category:
                        continue
                    # 🔑 關鍵字搜尋
                    if self.current_keyword and self.current_keyword not in name:
                        continue

                    rows.append({
                        "id": item_id,
                        "name": name,
                        "qty": qty,
                        "price": PRICE_TABLE.get(name, 50),
                        "category": CATEGORY_TABLE.get(name, "主食"),
                        "module": "系統物品",
                    })
        except Exception as e:
            print("list_sellable_items error:", e)
        return rows

    # === Grid ===
    def _clear_grid(self):
        while self.grid.count():
            it = self.grid.takeAt(0); w = it.widget()
            if w: w.setParent(None)

    def _rebuild_grid(self):
        self._clear_grid()
        items = self._list_buy_items() if self.mode == "buy" else self._list_sellable_items()

        if not items:
            empty = QLabel("沒有符合條件的物品")
            self.grid.addWidget(empty, 0, 0)
            self.lbl_coins.setText(str(self._get_coins()))
            return

        for i, it in enumerate(items):
            card = self._build_item_card(it)
            r, c = divmod(i, GRID_COLS)
            self.grid.addWidget(card, r, c)

        self.lbl_coins.setText(str(self._get_coins()))

    # === 輔助：保證圖片一定顯示 ===
    def _icon_path(self, name: str) -> str:
        fname = ICON_MAP.get(name, "")
        return str(ASSET_DIR / fname)

    def _build_item_card(self, it: dict) -> QFrame:
        card = QFrame()
        v = QVBoxLayout(card)
        card.setStyleSheet("""
            QFrame {
                background: #fff;
                border: 1px solid #ccc;
                border-radius: 12px;
                padding: 8px;
            }
        """)
        
        # 圖片
        pic = QLabel()
        abs_path = self._icon_path(it["name"])
        pm = QPixmap(str(abs_path))
        if not pm.isNull():
            pm = pm.scaled(ICON_SIZE, ICON_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pic.setPixmap(pm)
        else:
            pic.setText("🖼️")
        pic.setFixedSize(ICON_SIZE, ICON_SIZE)
        pic.setAlignment(Qt.AlignCenter)
        v.addWidget(pic, 0, Qt.AlignLeft)

        # 名稱
        v.addWidget(QLabel(it["name"]))

        # 背包數量
        v.addWidget(QLabel(f"背包：{it['qty']}"))

        # 價格 + 按鈕
        bar = QHBoxLayout()
        bar.addWidget(QLabel(f"🪙 {it['price']}"))
        bar.addStretch(1)
        
        if self.mode == "buy":
            btn = QPushButton("購買")
            # 檢查是否有足夠金幣
            if self._get_coins() < it['price']:
                btn.setEnabled(False)  # 這會觸發 disabled 樣式（灰色）
            else:
                btn.setProperty("class", "primary")  # 白色按鈕
            btn.clicked.connect(lambda _, data=it: self._buy_item(data))
        else:
            btn = QPushButton("出售")
            # 檢查是否有物品可賣
            if it['qty'] <= 0:
                btn.setEnabled(False)  # 灰色
            else:
                btn.setProperty("class", "primary")  # 白色按鈕
            btn.clicked.connect(lambda _, data=it: self._sell_item(data))
        
        # 刷新按鈕樣式
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        
        bar.addWidget(btn)
        v.addLayout(bar)

        return card

    # === 金幣 ===
    def _get_coins(self) -> int:
        try: return int(self.db.read_pet().coins or 0)
        except Exception: return 0

    def _add_coins(self, delta: int):
        try:
            if hasattr(self.db, "add_coins"):
                self.db.add_coins(delta)
            else:
                self.db.conn.execute("UPDATE pet SET coins=COALESCE(coins,0)+? WHERE id=1", (int(delta),))
                self.db.conn.commit()
        except Exception as e:
            print("add_coins error:", e)

    # === 賣 ===
    def _sell_item(self, it: dict):
        try:
            self.db.dec_inv(it["id"], 1)
            self._add_coins(it["price"])
        except Exception as e:
            print("sell error:", e)
        self.on_changed(); self.refresh()

    # === 買 ===
    def _buy_item(self, it: dict):
        price = int(it.get("price", 0))
        if self._get_coins() < price:
            print("金幣不足"); return
        item_id = it.get("id")
        if not item_id:
            item_id = None
        try:
            if hasattr(self.db, "inc_inv") and item_id is not None:
                self.db.inc_inv(int(item_id), 1)
            elif hasattr(self.db, "add_inventory_item_by_name"):
                self.db.add_inventory_item_by_name(it["name"], 1)
            elif hasattr(self.db, "add_inventory"):
                self.db.add_inventory(it["name"], 1)
        except Exception as e:
            print("buy error:", e)
        self._add_coins(-price)
        self.on_changed(); self.refresh()

    def refresh(self):
        self.lbl_coins.setText(str(self._get_coins()))
        self._rebuild_grid()
