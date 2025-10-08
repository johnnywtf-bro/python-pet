# dashboard/pages/page_tasks.py - 美化版本
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QFrame, QSpinBox, QCheckBox, QProgressBar, QScrollArea, QGridLayout,
    QSizePolicy, QSpacerItem, QApplication
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QFont, QPainter, QPen, QBrush, QColor, QPainterPath
import time
import math
# 直接覆蓋原本的 FocusPanel
from PyQt5.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QSpinBox, QCheckBox, QPushButton, QTextBrowser, QToolButton)
from PyQt5.QtCore import QTimer, Qt

FOCUS_REWARD_COINS_PER_MIN = 1
POMODORO_MINUTES = 25
POMODORO_REWARD_COINS_PER_BLOCK = 30

class FocusPanel(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._build_ui()

        self._timer = QTimer(self); self._timer.timeout.connect(self._on_tick)
        self._seconds_left = 0
        self._seconds_total = 0
        self._pomo_paid_blocks = 0
        self._running = False

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # 卡片（單層，無內框）
        card = QFrame()
        card.setObjectName("focusCard")
        card.setStyleSheet("""
        #focusCard {
            background: #ffffff;
            border: 1px solid #E8EAED;
            border-radius: 12px;
        }
        QLabel#titleSmall { font-size:16px; font-weight:600; color:#1f1f1f; }
        QLabel#titleMain  { font-size:22px; font-weight:600; color:#303133; }
        QPushButton, QToolButton { border-radius:8px; height:34px; padding:0 14px; }
        QPushButton#start { background:#3B82F6; color:white; }
        QPushButton#start:disabled { background:#AFC7FB; color:white; }
        QPushButton#stop  { background:#E5E7EB; color:#6B7280; }
        QPushButton#stop:disabled { background:#F3F4F6; color:#BCC0C6; }
        QSpinBox { min-width:88px; height:36px; border:1px solid #E5E7EB; border-radius:8px; padding:0 8px; }
        """)
        cv = QVBoxLayout(card)
        cv.setContentsMargins(14, 12, 14, 12)   # 整體更小
        cv.setSpacing(10)

        # Header：圖示 + 小標題 + ? 按鈕（都在同一卡片）
        header = QHBoxLayout(); header.setSpacing(8)
        icon = QLabel("⏱️")
        title = QLabel("專注時間"); title.setObjectName("titleSmall")
        header.addWidget(icon); header.addWidget(title); header.addStretch(1)

        self.btn_help = QToolButton()
        self.btn_help.setText("？")
        self.btn_help.setToolTip("查看使用說明")
        self.btn_help.clicked.connect(self._toggle_help)
        header.addWidget(self.btn_help)
        cv.addLayout(header)

        # 說明（隱藏式浮層）
        self.help_box = QTextBrowser()
        self.help_box.setVisible(False)
        self.help_box.setStyleSheet("background:#fff;border:1px solid #E5E7EB;border-radius:8px; padding:8px;")
        self.help_box.setHtml("""
        <b>使用幫助</b><br>
        設定一段專注時間；完成後獲得金幣。<br>
        中途停止也依完成比例給獎勵。<br><br>
        勾選「番茄鐘」會調整為最接近 25 分鐘倍數，<br>
        每完成一個番茄鐘，立即發一次金幣獎勵。
        """)
        cv.addWidget(self.help_box)

        # 主標題（在卡片內、周邊不再有任何框）
        title2 = QLabel("開始專注"); title2.setObjectName("titleMain")
        title2.setAlignment(Qt.AlignHCenter)
        cv.addWidget(title2)

        # 時分 + 番茄鐘
        row_time = QHBoxLayout(); row_time.setSpacing(8)
        row_time.addStretch(1)
        self.sp_h = QSpinBox(); self.sp_h.setRange(0, 24); row_time.addWidget(self.sp_h)
        row_time.addWidget(QLabel("時"))
        self.sp_m = QSpinBox(); self.sp_m.setRange(0, 59); self.sp_m.setValue(25)
        row_time.addWidget(self.sp_m)
        row_time.addWidget(QLabel("分"))
        row_time.addStretch(1)
        cv.addLayout(row_time)

        self.cb_pomo = QCheckBox("使用番茄鐘")
        self.cb_pomo.setStyleSheet("color:#334155;")
        cv.addWidget(self.cb_pomo, alignment=Qt.AlignHCenter)

        self.lbl_hint = QLabel("中途將不會有休息時間。")
        self.lbl_hint.setStyleSheet("color:#6B7280;")
        cv.addWidget(self.lbl_hint, alignment=Qt.AlignHCenter)

        # 按鈕列（更小、更緊）
        btns = QHBoxLayout(); btns.setSpacing(10)
        btns.addStretch(1)
        self.btn_start = QPushButton("▶ 開始"); self.btn_start.setObjectName("start")
        self.btn_stop  = QPushButton("■ 停止"); self.btn_stop.setObjectName("stop"); self.btn_stop.setEnabled(False)
        self.btn_start.clicked.connect(self._start_focus)
        self.btn_stop.clicked.connect(self._stop_focus)
        btns.addWidget(self.btn_start); btns.addWidget(self.btn_stop)
        btns.addStretch(1)
        cv.addLayout(btns)

        # 狀態列（小字）
        self.lbl_status = QLabel("未開始")
        self.lbl_status.setStyleSheet("color:#64748B;")
        cv.addWidget(self.lbl_status, alignment=Qt.AlignHCenter)

        root.addWidget(card)
        # 卡片寬度更精簡（可視需要微調）
        self.setMinimumWidth(420)

    def _toggle_help(self):
        self.help_box.setVisible(not self.help_box.isVisible())

    # ---------- 行為 ----------
    def _start_focus(self):
        hrs, mins = int(self.sp_h.value()), int(self.sp_m.value())
        total_minutes = hrs * 60 + mins
        if total_minutes <= 0:
            self.lbl_status.setText("請先設定時間")
            return

        if self.cb_pomo.isChecked():
            blocks = max(1, round(total_minutes / POMODORO_MINUTES))
            total_minutes = blocks * POMODORO_MINUTES
            self._pomo_paid_blocks = 0
            self.lbl_hint.setText(f"番茄鐘模式：{blocks} 個 × 25 分鐘")
        else:
            self.lbl_hint.setText("中途將不會有休息時間。")

        self._seconds_total = total_minutes * 60
        self._seconds_left = self._seconds_total
        self._running = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._timer.start(1000)
        self._update_status_label()

    def _stop_focus(self):
        self._timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        earned = self._calc_partial_reward()
        self._grant_coins(earned)
        self._reset("已停止")

    def _on_tick(self):
        if not self._running: return
        if self._seconds_left <= 0:
            self._grant_coins(self._calc_finish_reward())
            self._reset("完成！")
            return

        self._seconds_left -= 1
        if self.cb_pomo.isChecked():
            elapsed = self._seconds_total - self._seconds_left
            blocks_done = elapsed // (POMODORO_MINUTES * 60)
            if blocks_done > self._pomo_paid_blocks:
                diff = blocks_done - self._pomo_paid_blocks
                self._pomo_paid_blocks = blocks_done
                self._grant_coins(diff * POMODORO_REWARD_COINS_PER_BLOCK)
        self._update_status_label()

    # ---------- 獎勵與狀態 ----------
    def _calc_finish_reward(self):
        if self.cb_pomo.isChecked():
            blocks = self._seconds_total // (POMODORO_MINUTES * 60)
            return (blocks - self._pomo_paid_blocks) * POMODORO_REWARD_COINS_PER_BLOCK
        return (self._seconds_total // 60) * FOCUS_REWARD_COINS_PER_MIN

    def _calc_partial_reward(self):
        if self._seconds_total <= 0: return 0
        finished = self._seconds_total - self._seconds_left
        if self.cb_pomo.isChecked():
            blocks_done = finished // (POMODORO_MINUTES * 60)
            return max(0, blocks_done - self._pomo_paid_blocks) * POMODORO_REWARD_COINS_PER_BLOCK
        return round(finished / 60) * FOCUS_REWARD_COINS_PER_MIN

    def _grant_coins(self, coins: int):
        if coins <= 0: return
        try:
            self.db.add_coins(coins)
            from dashboard.event_bus import bus
            bus.coins_changed.emit(coins)
            bus.log_added.emit("coin", f"🎯 專注時間獎勵 +{coins} 金幣")
        except Exception as e:
            print("[FocusPanel] grant_coins error:", e)

    def _reset(self, msg=""):
        self._timer.stop()
        self._running = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._seconds_left = 0
        self._seconds_total = 0
        self._pomo_paid_blocks = 0
        self.lbl_status.setText(msg or "未開始")

    def _update_status_label(self):
        m, s = self._seconds_left // 60, self._seconds_left % 60
        total_m = self._seconds_total // 60
        self.lbl_status.setText(f"進行中：{m:02d}:{s:02d}／{total_m} 分")

class CircularProgress(QWidget):
    """圓形進度條"""
    def __init__(self, value=0, maximum=100, parent=None):
        super().__init__(parent)
        self.value = value
        self.maximum = maximum
        self.setFixedSize(120, 120)
        
    def setValue(self, value):
        self.value = value
        self.update()
        
    def setMaximum(self, maximum):
        self.maximum = maximum
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 繪製背景圓環
        painter.setPen(QPen(QColor(230, 230, 230), 8))
        painter.drawEllipse(10, 10, 100, 100)
        
        # 繪製進度圓環
        if self.maximum > 0:
            progress = self.value / self.maximum
            span_angle = int(progress * 360 * 16)  # Qt uses 1/16th degrees
            
            painter.setPen(QPen(QColor(74, 144, 226), 8))
            painter.drawArc(10, 10, 100, 100, 90 * 16, -span_angle)
        
        # 繪製中心文字
        painter.setPen(QColor(60, 60, 60))
        painter.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        text = f"{self.value} 分鐘"
        painter.drawText(self.rect(), Qt.AlignCenter, text)

class StatsCard(QFrame):
    """統計卡片"""
    def __init__(self, title, value, unit="", color="#4A90E2", parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 80)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E5E5E5;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # 數值
        value_label = QLabel(str(value))
        value_label.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold;")
        value_label.setAlignment(Qt.AlignCenter)
        
        # 單位
        unit_label = QLabel(unit)
        unit_label.setStyleSheet("color: #666; font-size: 12px;")
        unit_label.setAlignment(Qt.AlignCenter)
        
        # 標題
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #999; font-size: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(value_label)
        layout.addWidget(unit_label)
        layout.addWidget(title_label)

class FocusTimer(QFrame):
    """專注計時器 - 美化版"""
    coins_earned = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_timer)
        
        self.remaining_seconds = 0
        self.total_seconds = 0
        self.is_running = False
        self.use_pomodoro = False
        self.pomodoro_work_minutes = 25
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 標題區域
        title_frame = QFrame()
        title_frame.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        title_layout = QHBoxLayout(title_frame)
        
        # 時鐘圖標
        clock_label = QLabel("🕐")
        clock_label.setStyleSheet("font-size: 20px;")
        title_layout.addWidget(clock_label)
        
        title_label = QLabel("專注時間")
        title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #333;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        layout.addWidget(title_frame)
        
        # 開始專注區域
        focus_frame = QFrame()
        focus_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                border: 1px solid #E5E5E5;
            }
        """)
        focus_layout = QVBoxLayout(focus_frame)
        focus_layout.setContentsMargins(24, 24, 24, 24)
        focus_layout.setSpacing(20)
        
        # "開始專注" 標題
        start_title = QLabel("開始專注")
        start_title.setAlignment(Qt.AlignCenter)
        start_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #333; margin-bottom: 10px;")
        focus_layout.addWidget(start_title)
        
        # 時間輸入區域
        time_input_layout = QHBoxLayout()
        
        # 小時
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 5)
        self.hours_spin.setStyleSheet("""
            QSpinBox {
                border: 2px solid #E5E5E5;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                min-width: 60px;
            }
            QSpinBox:focus {
                border-color: #4A90E2;
            }
        """)
        
        hours_label = QLabel("時")
        hours_label.setStyleSheet("color: #666; font-size: 14px; margin: 0 10px;")
        
        # 分鐘
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(1, 59)
        self.minutes_spin.setValue(25)
        self.minutes_spin.setStyleSheet("""
            QSpinBox {
                border: 2px solid #E5E5E5;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                min-width: 60px;
            }
            QSpinBox:focus {
                border-color: #4A90E2;
            }
        """)
        
        minutes_label = QLabel("分")
        minutes_label.setStyleSheet("color: #666; font-size: 14px; margin: 0 10px;")
        
        time_input_layout.addStretch()
        time_input_layout.addWidget(self.hours_spin)
        time_input_layout.addWidget(hours_label)
        time_input_layout.addWidget(self.minutes_spin)
        time_input_layout.addWidget(minutes_label)
        time_input_layout.addStretch()
        
        focus_layout.addLayout(time_input_layout)
        
        # 番茄鐘選項
        pomodoro_layout = QHBoxLayout()
        self.pomodoro_checkbox = QCheckBox("使用番茄鐘")
        self.pomodoro_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                color: #333;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #E5E5E5;
            }
            QCheckBox::indicator:checked {
                background-color: #4A90E2;
                border-color: #4A90E2;
            }
        """)
        self.pomodoro_checkbox.toggled.connect(self._on_pomodoro_toggle)
        pomodoro_layout.addStretch()
        pomodoro_layout.addWidget(self.pomodoro_checkbox)
        pomodoro_layout.addStretch()
        focus_layout.addLayout(pomodoro_layout)
        
        # 番茄鐘說明
        self.pomodoro_info = QLabel("每專注 25 分鐘你將休息 5 分鐘。")
        self.pomodoro_info.setAlignment(Qt.AlignCenter)
        self.pomodoro_info.setStyleSheet("color: #666; font-size: 12px; margin-top: 8px;")
        self.pomodoro_info.hide()
        focus_layout.addWidget(self.pomodoro_info)
        
        # 控制按鈕
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("▷ 開始")
        self.start_button.setFixedSize(120, 40)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:pressed {
                background-color: #2968A3;
            }
        """)
        self.start_button.clicked.connect(self._toggle_timer)
        
        self.stop_button = QPushButton("⏹ 停止")
        self.stop_button.setFixedSize(120, 40)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #545B62;
            }
            QPushButton:disabled {
                background-color: #ADB5BD;
            }
        """)
        self.stop_button.clicked.connect(self._stop_timer)
        
        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        button_layout.addSpacing(10)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch()
        
        focus_layout.addLayout(button_layout)
        layout.addWidget(focus_frame)
        
    def _on_pomodoro_toggle(self, checked):
        self.use_pomodoro = checked
        if checked:
            self.pomodoro_info.show()
            self.hours_spin.setValue(0)
            self.minutes_spin.setValue(25)
            self.hours_spin.setEnabled(False)
            self.minutes_spin.setEnabled(False)
        else:
            self.pomodoro_info.hide()
            self.hours_spin.setEnabled(True)
            self.minutes_spin.setEnabled(True)
    
    def _toggle_timer(self):
        if not self.is_running:
            self._start_timer()
        else:
            self._pause_timer()
    
    def _start_timer(self):
        if self.remaining_seconds == 0:
            hours = self.hours_spin.value()
            minutes = self.minutes_spin.value()
            self.total_seconds = hours * 3600 + minutes * 60
            self.remaining_seconds = self.total_seconds
        
        self.is_running = True
        self.timer.start(1000)
        
        self.start_button.setText("⏸ 暫停")
        self.stop_button.setEnabled(True)
        self.hours_spin.setEnabled(False)
        self.minutes_spin.setEnabled(False)
        self.pomodoro_checkbox.setEnabled(False)
    
    def _pause_timer(self):
        self.is_running = False
        self.timer.stop()
        self.start_button.setText("▷ 繼續")
    
    def _stop_timer(self):
        self.is_running = False
        self.timer.stop()
        self.remaining_seconds = 0
        
        self.start_button.setText("▷ 開始")
        self.stop_button.setEnabled(False)
        
        if not self.use_pomodoro:
            self.hours_spin.setEnabled(True)
            self.minutes_spin.setEnabled(True)
        self.pomodoro_checkbox.setEnabled(True)
    
    def _update_timer(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
        else:
            self._timer_finished()
    
    def _timer_finished(self):
        total_minutes = self.total_seconds // 60
        coins = max(5, total_minutes)
        self.coins_earned.emit(coins)
        self._stop_timer()

class TaskItem(QFrame):
    """任務項目 - 美化版"""
    status_changed = pyqtSignal(int, str)  # task_id, new_status
    
    def __init__(self, task_id, title, minutes_target, minutes_done, status):
        super().__init__()
        self.task_id = task_id
        self.title = title
        self.minutes_target = minutes_target
        self.minutes_done = minutes_done
        self.status = self._clean_status(status)
        
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E5E5E5;
                margin: 4px 0;
            }
            QFrame:hover {
                border-color: #4A90E2;
            }
        """)
        self.setFixedHeight(60)
        self._setup_ui()
        
    def _clean_status(self, status):
        if isinstance(status, str):
            cleaned = status.strip('[]')
            if cleaned in ['todo', 'doing', 'done']:
                return cleaned
        return 'todo'
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # 狀態指示器
        status_indicator = QLabel("●")
        status_colors = {
            'todo': '#ADB5BD',
            'doing': '#4A90E2', 
            'done': '#28A745'
        }
        status_indicator.setStyleSheet(f"color: {status_colors.get(self.status, '#ADB5BD')}; font-size: 16px;")
        layout.addWidget(status_indicator)
        
        # 任務標題
        title_label = QLabel(self.title)
        title_label.setStyleSheet("font-size: 14px; font-weight: 500; color: #333;")
        layout.addWidget(title_label, 1)
        
        # 進度條
        progress = QProgressBar()
        progress.setFixedSize(80, 6)
        progress.setRange(0, self.minutes_target)
        progress.setValue(self.minutes_done)
        progress.setTextVisible(False)
        progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #F1F3F4;
            }
            QProgressBar::chunk {
                border-radius: 3px;
                background-color: #4A90E2;
            }
        """)
        layout.addWidget(progress)
        
        # 時間標籤
        time_label = QLabel(f"{self.minutes_done}/{self.minutes_target}分")
        time_label.setStyleSheet("color: #666; font-size: 12px; min-width: 60px;")
        layout.addWidget(time_label)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            new_status = {"todo": "doing", "doing": "done", "done": "todo"}[self.status]
            self.status_changed.emit(self.task_id, new_status)

class BeautifulTasksPage(QWidget):
    """美化的待辦事項頁面"""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._setup_ui()
        self.refresh()
        
        
    def _setup_ui(self):
        # 主滾動區域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #F8F9FA;
            }
            QScrollBar:vertical {
                background: #F1F3F4;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #C1C8CD;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #A8B2BA;
            }
        """)
        
        # 滾動內容容器
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #F8F9FA;")
        scroll.setWidget(scroll_content)
        
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 標題區域
        title_frame = QFrame()
        title_frame.setFixedHeight(60)
        title_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                border: 1px solid #E5E5E5;
            }
        """)
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(20, 0, 20, 0)
        
        # 標題圖標和文字
        title_icon = QLabel("📋")
        title_icon.setStyleSheet("font-size: 24px;")
        
        title_label = QLabel("日常任務")
        title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #333;")
        
        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addWidget(title_frame)
        
        # 統計區域
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                border: 1px solid #E5E5E5;
            }
        """)
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setContentsMargins(20, 16, 20, 16)
        
        # 圓形進度
        progress_layout = QHBoxLayout()
        self.circular_progress = CircularProgress()
        progress_layout.addStretch()
        progress_layout.addWidget(self.circular_progress)
        progress_layout.addStretch()
        stats_layout.addLayout(progress_layout)
        
        # 每日目標
        goal_label = QLabel("每日目標：180 分鐘")
        goal_label.setAlignment(Qt.AlignCenter)
        goal_label.setStyleSheet("color: #666; font-size: 14px; margin-top: 8px;")
        stats_layout.addWidget(goal_label)
        
        # 統計卡片
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        
        self.minutes_card = StatsCard("分鐘", "0")
        self.days_card = StatsCard("天", "0", color="#28A745")
        
        cards_layout.addStretch()
        cards_layout.addWidget(self.minutes_card)
        cards_layout.addWidget(self.days_card)
        cards_layout.addStretch()
        
        stats_layout.addLayout(cards_layout)
        layout.addWidget(stats_frame)

        self.focus_panel = FocusPanel(self.db, self)
        layout.addWidget(self.focus_panel)
        
        # 任務管理區域
        tasks_frame = QFrame()
        tasks_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                border: 1px solid #E5E5E5;
            }
        """)
        tasks_layout = QVBoxLayout(tasks_frame)
        tasks_layout.setContentsMargins(20, 16, 20, 16)
        
        # 任務標題
        task_title_layout = QHBoxLayout()
        task_icon = QLabel("📝")
        task_icon.setStyleSheet("font-size: 16px;")
        task_title = QLabel("待辦事項")
        task_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #333;")
        
        self.completed_label = QLabel("已完成 0 項任務")
        self.completed_label.setStyleSheet("color: #28A745; font-size: 12px; font-weight: 500;")
        
        task_title_layout.addWidget(task_icon)
        task_title_layout.addWidget(task_title)
        task_title_layout.addStretch()
        task_title_layout.addWidget(self.completed_label)
        
        tasks_layout.addLayout(task_title_layout)
        
        # 新增任務
        add_layout = QHBoxLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("添加新任務...")
        self.title_input.setFixedHeight(36)
        self.title_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E5E5E5;
                border-radius: 18px;
                padding: 0 16px;
                font-size: 14px;
                background-color: #F8F9FA;
            }
            QLineEdit:focus {
                border-color: #4A90E2;
                background-color: white;
            }
        """)
        
        add_button = QPushButton("✓")
        add_button.setFixedSize(36, 36)
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
        """)
        add_button.clicked.connect(self._add_task)
        
        add_layout.addWidget(self.title_input, 1)
        add_layout.addWidget(add_button)
        
        tasks_layout.addLayout(add_layout)
        
        # 任務列表容器
        self.tasks_container = QVBoxLayout()
        self.tasks_container.setSpacing(8)
        tasks_layout.addLayout(self.tasks_container)
        
        layout.addWidget(tasks_frame)
        
        
        layout.addStretch()
        
        # 設置主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
    def _add_task(self):
        title = self.title_input.text().strip()
        if title:
            # 默認30分鐘
            self.db.add_task(title, 30)
            self.title_input.clear()
            self.refresh()
    
    def _on_coins_earned(self, coins):
        try:
            if hasattr(self.db, 'add_coins'):
                self.db.add_coins(coins)
            else:
                self.db.conn.execute("UPDATE pet SET coins = COALESCE(coins, 0) + ? WHERE id=1", (coins,))
                self.db.conn.commit()
            print(f"用戶獲得 {coins} 金幣！")
        except Exception as e:
            print(f"添加金幣時發生錯誤: {e}")
    
    def _clean_status(self, status):
        if isinstance(status, str):
            cleaned = status.strip('[]')
            if cleaned in ['todo', 'doing', 'done']:
                return cleaned
        return 'todo'
    
    def _on_task_status_changed(self, task_id, new_status):
        self.db.set_task_status(task_id, new_status)
        self.refresh()
    
    def refresh(self):
        # 清空任務列表
        while self.tasks_container.count():
            child = self.tasks_container.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
        
        # 重新載入任務
        tasks = self.db.list_tasks()
        completed_count = 0
        total_minutes = 0
        
        # 按狀態分組
        todo_tasks = []
        doing_tasks = []
        done_tasks = []
        
        for task_id, title, minutes_target, minutes_done, status in tasks:
            cleaned_status = self._clean_status(status)
            task_item = TaskItem(task_id, title, minutes_target, minutes_done, cleaned_status)
            task_item.status_changed.connect(self._on_task_status_changed)
            
            if cleaned_status == "todo":
                todo_tasks.append(task_item)
            elif cleaned_status == "doing":
                doing_tasks.append(task_item)
                total_minutes += minutes_done
            else:  # done
                done_tasks.append(task_item)
                completed_count += 1
                total_minutes += minutes_target
        
        # 添加任務到界面（進行中 -> 待辦 -> 已完成）
        all_tasks = doing_tasks + todo_tasks + done_tasks
        for task_item in all_tasks:
            self.tasks_container.addWidget(task_item)
        
        # 更新統計
        self.completed_label.setText(f"已完成 {completed_count} 項任務")
        self.circular_progress.setValue(total_minutes)
        self.circular_progress.setMaximum(180)  # 每日目標180分鐘
        
        # 更新統計卡片
        days_alive = 1  # 可以從數據庫獲取
        try:
            pet_data = self.db.read_pet()
            days_alive = pet_data.days_alive
        except:
            pass
            
        # 重新創建統計卡片
        if hasattr(self, 'minutes_card'):
            self.minutes_card.setParent(None)
            self.days_card.setParent(None)
        
                # 更新統計卡片
        days_alive = 1  # 可以從數據庫獲取
        try:
            pet_data = self.db.read_pet()
            days_alive = pet_data.days_alive
        except:
            pass