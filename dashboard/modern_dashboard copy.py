# dashboard/modern_dashboard.py 修復版本
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, 
    QPushButton, QLabel, QFrame, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QPen, QColor
from pathlib import Path

from .pages.page_status import StatusPage
from .pages.page_inventory import InventoryPage
from .pages.page_shop import ShopPage
from .pages.page_animations import AnimationsPage
from .pages.page_tasks import TasksPage
from database import DB
from .event_bus import bus

class IconButton(QPushButton):
    """自定義圖標按鈕"""
    def __init__(self, icon_path: str, text: str, parent=None):
        super().__init__(parent)
        self.text_label = text
        self.icon_path = icon_path
        self.is_active = False
        
        # 設置按鈕樣式 - 簡潔版本
        self.setFixedSize(60, 60)
        self.setFlat(True)  # 扁平化按鈕
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                color: #666;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
        """)
        
        # 載入圖標
        self._load_icon()
        
    def _load_icon(self):
        """載入並設置圖標"""
        print(f"[DEBUG] 嘗試載入圖標: {self.icon_path}")
        
        if os.path.exists(self.icon_path):
            try:
                pixmap = QPixmap(self.icon_path)
                if not pixmap.isNull():
                    # 調整圖標大小
                    scaled_pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.setIcon(QIcon(scaled_pixmap))
                    self.setIconSize(QSize(32, 32))
                    print(f"[DEBUG] 圖標載入成功: {self.text_label}")
                else:
                    print(f"[DEBUG] 圖標文件無效: {self.icon_path}")
                    self._set_fallback_icon()
            except Exception as e:
                print(f"[DEBUG] 載入圖標時發生錯誤: {e}")
                self._set_fallback_icon()
        else:
            print(f"[DEBUG] 圖標文件不存在: {self.icon_path}")
            self._set_fallback_icon()
    
    def _set_fallback_icon(self):
        """設置備用圖標（使用文字）"""
        self.setText(self.text_label[0])  # 顯示首字母
        # 不設置特殊樣式，保持原本的簡潔外觀

    def set_active(self, active: bool):
        """設置激活狀態"""
        self.is_active = active
        # 不使用 setChecked，避免藍色樣式
        self.update()

    def paintEvent(self, event):
        """自定義繪製"""
        super().paintEvent(event)
        
        # 如果是激活狀態，繪製左側指示線（簡潔版本）
        if self.is_active:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 繪製左側細線指示
            pen = QPen(QColor(100, 100, 100), 2)  # 灰色細線
            painter.setPen(pen)
            painter.drawLine(2, 15, 2, self.height() - 15)

class CollapsibleSidebar(QFrame):
    """可收縮的側邊欄"""
    page_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.expanded = False
        self.buttons = []
        
        # 修復UI資源路徑 - 使用絕對路徑
        current_file = Path(__file__).resolve()
        project_root = current_file.parents[1]  # 回到專案根目錄
        self.ui_path = project_root / "assets" / "ui"
        
        print(f"[DEBUG] UI資源路徑: {self.ui_path}")
        print(f"[DEBUG] UI資源路徑是否存在: {self.ui_path.exists()}")
        
        # 列出UI資源目錄內容
        if self.ui_path.exists():
            ui_files = list(self.ui_path.glob("*.png"))
            print(f"[DEBUG] 找到的UI文件: {[f.name for f in ui_files]}")
        
        # 設置側邊欄基本屬性
        self.setFixedWidth(70)  # 收縮狀態寬度
        self.expanded_width = 200  # 展開狀態寬度
        self.collapsed_width = 70
        
        # 設置樣式
        self.setStyleSheet("""
            CollapsibleSidebar {
                background-color: #f8f9fa;
                border-right: 1px solid #e9ecef;
            }
        """)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """設置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 漢堡菜單按鈕
        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedSize(60, 40)
        self.menu_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 18px;
                font-weight: bold;
                color: #495057;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-radius: 8px;
            }
        """)
        self.menu_btn.clicked.connect(self.toggle_sidebar)
        layout.addWidget(self.menu_btn)
        
        # 分隔線
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #e9ecef;")
        layout.addWidget(separator)
        
        # 導航按鈕容器
        self.nav_container = QWidget()
        nav_layout = QVBoxLayout(self.nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)
        
        # 創建導航按鈕
        nav_items = [
            ("狀態", "home.png"),
            ("背包", "bag.png"),
            ("商店", "shop.png"),
            ("動作", "bell.png"),
            ("任務", "list.png")
        ]
        
        for i, (name, icon_file) in enumerate(nav_items):
            icon_path = str(self.ui_path / icon_file)
            btn = IconButton(icon_path, name)
            btn.clicked.connect(lambda checked, idx=i: self._on_button_clicked(idx))
            
            # 創建按鈕容器（包含圖標和文字）
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setSpacing(10)
            
            btn_layout.addWidget(btn)
            
            # 文字標籤（初始隱藏）
            text_label = QLabel(name)
            text_label.setStyleSheet("""
                QLabel {
                    color: #495057;
                    font-size: 14px;
                    font-weight: 500;
                }
            """)
            text_label.hide()  # 初始隱藏
            btn_layout.addWidget(text_label)
            btn_layout.addStretch()
            
            nav_layout.addWidget(btn_container)
            
            # 保存引用
            self.buttons.append({
                'button': btn,
                'container': btn_container,
                'label': text_label,
                'name': name
            })
        
        # 設置第一個按鈕為激活狀態
        if self.buttons:
            self.buttons[0]['button'].set_active(True)
        
        nav_layout.addStretch()
        
        # 滾動區域
        scroll = QScrollArea()
        scroll.setWidget(self.nav_container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        layout.addWidget(scroll)
        
        # 動畫設置
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
    def _on_button_clicked(self, index: int):
        """處理按鈕點擊"""
        # 更新激活狀態（不使用 Qt 的 checked 狀態）
        for i, btn_info in enumerate(self.buttons):
            btn_info['button'].set_active(i == index)
        
        # 發送頁面切換信號
        self.page_changed.emit(index)
    
    def toggle_sidebar(self):
        """切換側邊欄展開/收縮"""
        self.expanded = not self.expanded
        
        target_width = self.expanded_width if self.expanded else self.collapsed_width
        
        # 執行動畫
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(target_width)
        self.animation.start()
        
        # 顯示/隱藏文字標籤
        for btn_info in self.buttons:
            if self.expanded:
                btn_info['label'].show()
            else:
                btn_info['label'].hide()


class ModernDashboard(QMainWindow):
    """現代化角色面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("角色面板")
        self.resize(900, 600)
        self.db = DB()
        
        self._setup_ui()
        self._load_styles()
        
    def _setup_ui(self):
        """設置UI"""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 側邊欄
        self.sidebar = CollapsibleSidebar()
        self.sidebar.page_changed.connect(self._on_page_changed)
        layout.addWidget(self.sidebar)
        
        # 右側內容區域
        self.content_stack = QStackedWidget()
        
        # 創建頁面
        self._create_pages()
        
        layout.addWidget(self.content_stack, 1)
        
    def _create_pages(self):
        """創建所有頁面"""
        # 狀態頁面
        self.page_status = StatusPage(self.db)
        self.content_stack.addWidget(self.page_status)
        
        # 統一資料變更回調
        def on_data_changed():
            self.page_status.refresh()
            self.page_inventory.refresh()
            self.page_shop.refresh()
        
        # 背包頁面
        self.page_inventory = InventoryPage(self.db, on_changed=on_data_changed)
        self.content_stack.addWidget(self.page_inventory)
        
        # 商店頁面
        self.page_shop = ShopPage(self.db, on_changed=on_data_changed)
        self.content_stack.addWidget(self.page_shop)
        
        # 動作頁面
        def on_play_from_page(key: str):
            bus.play_anim.emit(key)
        
        self.page_animations = AnimationsPage(self.db, on_play=on_play_from_page)
        self.content_stack.addWidget(self.page_animations)
        
        # 任務頁面 - 使用增強版本
        from .pages.page_tasks import EnhancedTasksPage
        self.page_tasks = EnhancedTasksPage(self.db)
        self.content_stack.addWidget(self.page_tasks)
        
        # 設置默認頁面
        self.content_stack.setCurrentIndex(0)
    
    def _on_page_changed(self, index: int):
        """處理頁面切換"""
        self.content_stack.setCurrentIndex(index)
        
        # 刷新當前頁面數據
        current_widget = self.content_stack.currentWidget()
        if hasattr(current_widget, 'refresh'):
            current_widget.refresh()
    
    def _load_styles(self):
        """載入樣式表"""
        qss_path = Path(__file__).parent / "modern_styles.qss"
        if qss_path.exists():
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        else:
            # 默認樣式
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #ffffff;
                }
                QStackedWidget {
                    background-color: #ffffff;
                    border: none;
                }
            """)