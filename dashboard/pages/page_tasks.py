# dashboard/pages/page_tasks.py - 完整版本：专注时间与每日目标
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QFrame, QSpinBox, QCheckBox, QProgressBar, QScrollArea, QGridLayout,
    QSizePolicy, QSpacerItem, QApplication, QToolButton, QDialog
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QFont, QPainter, QPen, QBrush, QColor, QPainterPath, QPixmap, QIcon
import time
import math
from datetime import datetime, date

FOCUS_REWARD_COINS_PER_MIN = 1
POMODORO_MINUTES = 25
POMODORO_REWARD_COINS_PER_BLOCK = 30

class HelpDialog(QDialog):
    """专注时间帮助说明对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("专注时间说明")
        self.setFixedSize(400, 300)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("专注时间使用说明")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-bottom: 15px;")
        layout.addWidget(title)
        
        # 说明内容
        content = QLabel("""
<b>用途：</b>設定工作/學習的專注時間\n

<b>獎勵機制：</b>
• 專注任務完成後，獲得金幣獎勵
• 若中途結束，也可依完成部分獲得對應獎勵
• 使用"番茄鐘模式"時，每完成一個 25 分鐘番茄鐘，就可獲得一次金幣獎勵\n

<b>番茄鐘模式：</b>
• 勾選後，系統會自動調整為最接近的番茄鐘數量
• 每個番茄鐘 = 25 分鐘專注時間
        """)
        content.setWordWrap(True)
        content.setStyleSheet("color: #666; line-height: 1.5;")
        layout.addWidget(content)
        
        # 确定按钮
        ok_btn = QPushButton("知道了")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
        """)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn, alignment=Qt.AlignCenter)

class GoalEditDialog(QDialog):
    """每日目标编辑对话框"""
    def __init__(self, current_minutes=180, parent=None):
        super().__init__(parent)
        self.setWindowTitle("編輯每日目標")
        self.setFixedSize(320, 200)
        self.setModal(True)
        
        self.current_minutes = current_minutes
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("设置每日专注目标")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 时间输入
        time_layout = QHBoxLayout()
        
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 8)
        self.hours_spin.setValue(current_minutes // 60)
        self.hours_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-width: 60px;
            }
        """)
        
        hours_label = QLabel("時")
        hours_label.setStyleSheet("color: #666; margin: 0 10px; border: none; background: transparent;")
        
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setValue(current_minutes % 60)
        self.minutes_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-width: 60px;
            }
        """)
        
        minutes_label = QLabel("分")
        minutes_label.setStyleSheet("color: #666; margin: 0 10px; border: none; background: transparent;")
        
        time_layout.addStretch()
        time_layout.addWidget(self.hours_spin)
        time_layout.addWidget(hours_label)
        time_layout.addWidget(self.minutes_spin)
        time_layout.addWidget(minutes_label)
        time_layout.addStretch()
        
        layout.addLayout(time_layout)
        
        # 说明
        desc = QLabel("达到设定的时间后，可获得金币奖励\n若每日连续达标，会有额外奖励")
        desc.setStyleSheet("color: #666; font-size: 12px; text-align: center; margin: 15px 0;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #666;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
        """)
        save_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
    
    def get_total_minutes(self):
        return self.hours_spin.value() * 60 + self.minutes_spin.value()

class CircularProgress(QWidget):
    """自定义圆形进度条"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self.progress = 0  # 0-100
        self.max_value = 100
        self.current_value = 0
    
    def set_progress(self, current, maximum):
        """设置进度"""
        self.current_value = current
        self.max_value = max(1, maximum)  # 避免除零
        self.progress = min(100, (current / self.max_value) * 100)
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景圆
        rect = self.rect().adjusted(8, 8, -8, -8)
        painter.setPen(QPen(QColor("#e0e0e0"), 6))
        painter.drawEllipse(rect)
        
        # 绘制进度弧
        if self.progress > 0:
            painter.setPen(QPen(QColor("#4285f4"), 6, Qt.SolidLine, Qt.RoundCap))
            start_angle = -90 * 16  # 从顶部开始
            span_angle = -(self.progress / 100.0) * 360 * 16
            painter.drawArc(rect, start_angle, span_angle)
        
        # 绘制中心文字
        painter.setPen(QColor("#333"))
        painter.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        
        if self.current_value >= 60:
            text = f"{self.current_value // 60}小时{self.current_value % 60}分钟" if self.current_value % 60 else f"{self.current_value // 60}小时"
        else:
            text = f"{self.current_value}分钟"
            
        painter.drawText(rect, Qt.AlignCenter, text)

class StatsCard(QFrame):
    """统计卡片组件"""
    def __init__(self, label, value, color="#333", parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 60)
        self.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border-radius: 8px;
                border: 1px solid #e5e5e5;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        
        self.value_label = QLabel(str(value))
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        
        self.desc_label = QLabel(label)
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setStyleSheet("color: #666; font-size: 12px;")
        
        layout.addWidget(self.value_label)
        layout.addWidget(self.desc_label)
    
    def set_value(self, value):
        self.value_label.setText(str(value))

class FocusPanel(QWidget):
    """专注时间面板"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.parent_page = parent
        
        # 计时器相关 - 先初始化所有属性
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._seconds_left = 0
        self._seconds_total = 0
        self._pomo_paid_blocks = 0
        self._running = False
        self._is_pomodoro = False
        
        # 每日目标数据 - 先加载数据
        self.daily_goal_minutes = self._load_daily_goal()
        self.today_minutes = self._load_today_progress()
        self.yesterday_minutes = self._load_yesterday_progress()
        self.consecutive_days = self._load_consecutive_days()
        
        # 最后构建UI
        self._build_ui()

    def _build_ui(self):
        """构建界面"""
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(16)

        # 专注时间区域
        self._build_focus_section(root)
        
        # 每日目标区域
        self._build_daily_goals_section(root)

    def _build_focus_section(self, parent_layout):
        """构建专注时间区域"""
        # 标题区域
        title_frame = QFrame()
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("專注時間")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #333;")
        
        help_btn = QToolButton()
        help_btn.setText("?")
        help_btn.setStyleSheet("""
            QToolButton {
                border: 1px solid #ccc;
                border-radius: 12px;
                width: 24px;
                height: 24px;
                background: white;
                color: #666;
                font-size: 12px;
            }
            QToolButton:hover {
                background: #f0f0f0;
            }
        """)
        help_btn.clicked.connect(self._show_help)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(help_btn)
        
        parent_layout.addWidget(title_frame)
        
        # 专注设置卡片
        focus_card = QFrame()
        focus_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e5e5e5;
            }
        """)
        focus_layout = QVBoxLayout(focus_card)
        focus_layout.setContentsMargins(24, 24, 24, 24)
        focus_layout.setSpacing(20)
        
        # "开始专注" 标题
        start_title = QLabel("開始專注")
        start_title.setAlignment(Qt.AlignCenter)
        start_title.setStyleSheet("font-size: 20px; font-weight: 500; color: #333; margin-bottom: 10px; border: none; background: transparent;")
        focus_layout.addWidget(start_title)
        
        # 时间输入区域
        time_input_layout = QHBoxLayout()
        time_input_layout.setSpacing(20)
        
        # 小时输入
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 5)
        self.hours_spin.setValue(0)
        self.hours_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 8px;
                font-size: 16px;
                min-width: 60px;
                background: #f9f9f9;
            }
            QSpinBox:focus {
                border-color: #4285f4;
                background: white;
            }
        """)
        
        hours_label = QLabel("時")
        hours_label.setStyleSheet("color: #666; font-size: 14px; border: none; background: transparent;")
        
        # 分钟输入
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(1, 59)
        self.minutes_spin.setValue(25)
        self.minutes_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 8px;
                font-size: 16px;
                min-width: 60px;
                background: #f9f9f9;
            }
            QSpinBox:focus {
                border-color: #4285f4;
                background: white;
            }
        """)
        
        minutes_label = QLabel("分")
        minutes_label.setStyleSheet("color: #666; font-size: 14px; border: none; background: transparent;")
        
        time_input_layout.addStretch()
        time_input_layout.addWidget(self.hours_spin)
        time_input_layout.addWidget(hours_label)
        time_input_layout.addWidget(self.minutes_spin)
        time_input_layout.addWidget(minutes_label)
        time_input_layout.addStretch()
        
        focus_layout.addLayout(time_input_layout)
        
        # 番茄钟选项
        pomodoro_layout = QHBoxLayout()
        self.use_pomodoro = QCheckBox("使用番茄钟")
        self.use_pomodoro.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                color: #333;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.use_pomodoro.stateChanged.connect(self._on_pomodoro_changed)
        
        pomodoro_layout.addStretch()
        pomodoro_layout.addWidget(self.use_pomodoro)
        pomodoro_layout.addStretch()
        
        focus_layout.addLayout(pomodoro_layout)
        
        # 描述文本
        self.description = QLabel("中途將不會有休息時間")
        self.description.setAlignment(Qt.AlignCenter)
        self.description.setStyleSheet("color: #666; font-size: 12px; border: none; background: transparent;")
        focus_layout.addWidget(self.description)
        
        # 计时器显示（隐藏状态）
        self.timer_display = QFrame()
        self.timer_display.setStyleSheet("""
            QFrame {
                background: #f0f7ff;
                border-radius: 8px;
                border: 1px solid #4285f4;
            }
        """)
        timer_layout = QVBoxLayout(self.timer_display)
        timer_layout.setContentsMargins(16, 12, 16, 12)
        
        self.timer_time = QLabel("25:00")
        self.timer_time.setAlignment(Qt.AlignCenter)
        self.timer_time.setStyleSheet("font-size: 32px; font-weight: bold; color: #4285f4;")
        
        self.timer_status = QLabel("專注中...")
        self.timer_status.setAlignment(Qt.AlignCenter)
        self.timer_status.setStyleSheet("color: #666; font-size: 14px;")
        
        timer_layout.addWidget(self.timer_time)
        timer_layout.addWidget(self.timer_status)
        
        self.timer_display.hide()
        focus_layout.addWidget(self.timer_display)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)
        
        self.start_btn = QPushButton("开始")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
        """)
        self.start_btn.clicked.connect(self._start_focus)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #999;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
            }
        """)
        self.stop_btn.clicked.connect(self._stop_focus)
        self.stop_btn.setEnabled(False)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addStretch()
        
        focus_layout.addLayout(btn_layout)
        
        parent_layout.addWidget(focus_card)

    def _build_daily_goals_section(self, parent_layout):
        """构建每日目标区域"""
        # 标题区域
        goals_header = QFrame()
        goals_layout = QHBoxLayout(goals_header)
        goals_layout.setContentsMargins(0, 0, 0, 0)
        
        # 三角形图标
        triangle_label = QLabel("🔺")
        triangle_label.setStyleSheet("font-size: 16px; color: #4285f4;")
        
        goals_title = QLabel("每日目標")
        goals_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #333;")
        
        edit_btn = QToolButton()
        edit_btn.setText("✏")
        edit_btn.setStyleSheet("""
            QToolButton {
                border: none;
                background: none;
                color: #666;
                font-size: 14px;
                padding: 4px;
            }
            QToolButton:hover {
                color: #4285f4;
            }
        """)
        edit_btn.clicked.connect(self._edit_daily_goal)
        
        goals_layout.addWidget(triangle_label)
        goals_layout.addWidget(goals_title)
        goals_layout.addStretch()
        goals_layout.addWidget(edit_btn)
        
        parent_layout.addWidget(goals_header)
        
        # 每日目标卡片
        goals_card = QFrame()
        goals_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e5e5e5;
            }
        """)
        goals_card_layout = QVBoxLayout(goals_card)
        goals_card_layout.setContentsMargins(24, 24, 24, 24)
        goals_card_layout.setSpacing(20)
        
        # "今日进度" 标题
        progress_title = QLabel("今日進度")
        progress_title.setAlignment(Qt.AlignCenter)
        progress_title.setStyleSheet("font-size: 18px; font-weight: 500; color: #333; margin-bottom: 10px; border: none; background: transparent;")
        goals_card_layout.addWidget(progress_title)
        
        # 圆形进度条
        progress_layout = QHBoxLayout()
        self.circular_progress = CircularProgress()
        progress_layout.addStretch()
        progress_layout.addWidget(self.circular_progress)
        progress_layout.addStretch()
        goals_card_layout.addLayout(progress_layout)
        
        # 每日目标文本
        self.daily_goal_label = QLabel(f"每日目標：{self.daily_goal_minutes} 分鐘")
        self.daily_goal_label.setAlignment(Qt.AlignCenter)
        self.daily_goal_label.setStyleSheet("color: #666; font-size: 12px; border: none; background: transparent;")
        goals_card_layout.addWidget(self.daily_goal_label)
        
        # 统计卡片区域
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        
        self.yesterday_card = StatsCard("昨日", f"{self.yesterday_minutes}")
        self.consecutive_card = StatsCard("連續達標", f"{self.consecutive_days}", "#28a745")
        
        stats_layout.addStretch()
        stats_layout.addWidget(self.yesterday_card)
        stats_layout.addWidget(self.consecutive_card)
        stats_layout.addStretch()
        
        goals_card_layout.addLayout(stats_layout)
        
        parent_layout.addWidget(goals_card)
        
        # 更新进度显示
        self._update_progress_display()

    # ========== 事件处理 ==========
    
    def _show_help(self):
        """显示帮助对话框"""
        dialog = HelpDialog(self)
        dialog.exec_()

    def _edit_daily_goal(self):
        """编辑每日目标"""
        dialog = GoalEditDialog(self.daily_goal_minutes, self)
        if dialog.exec_() == QDialog.Accepted:
            self.daily_goal_minutes = dialog.get_total_minutes()
            self._save_daily_goal()
            self.daily_goal_label.setText(f"每日目标：{self.daily_goal_minutes} 分钟")
            self._update_progress_display()

    def _on_pomodoro_changed(self, state):
        """番茄钟选项变化"""
        if state == Qt.Checked:
            self.description.setText("系统会自动调整为最接近的番茄钟数量（每个番茄钟 = 25 分钟）")
            self.description.setStyleSheet("color: #666; font-size: 12px; border: none; background: transparent;")
        else:
            self.description.setText("中途将不会有休息时间。")
            self.description.setStyleSheet("color: #666; font-size: 12px; border: none; background: transparent;")

    def _start_focus(self):
        """开始专注"""
        hours = self.hours_spin.value()
        minutes = self.minutes_spin.value()
        total_minutes = hours * 60 + minutes
        
        if total_minutes <= 0:
            return
        
        self._is_pomodoro = self.use_pomodoro.isChecked()
        
        if self._is_pomodoro:
            # 调整为最接近的番茄钟数量
            pomodoro_count = max(1, round(total_minutes / POMODORO_MINUTES))
            total_minutes = pomodoro_count * POMODORO_MINUTES
        
        self._seconds_total = total_minutes * 60
        self._seconds_left = self._seconds_total
        self._pomo_paid_blocks = 0
        self._running = True
        
        # 更新界面状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        # 显示计时器
        self.timer_display.show()
        self._update_timer_display()
        
        # 启动计时器
        self._timer.start(1000)  # 每秒更新

    def _stop_focus(self):
        """停止专注"""
        if not self._running:
            return
        
        # 计算已完成的分钟数
        completed_seconds = self._seconds_total - self._seconds_left
        completed_minutes = completed_seconds // 60
        
        # 给予奖励
        if completed_minutes > 0:
            coins = completed_minutes * FOCUS_REWARD_COINS_PER_MIN
            self._give_coins(coins)
            
            # 更新今日进度
            self.today_minutes += completed_minutes
            self._save_today_progress()
            self._update_progress_display()
        
        self._reset_focus_state()

    def _on_tick(self):
        """计时器每秒回调"""
        if not self._running:
            return
        
        self._seconds_left -= 1
        self._update_timer_display()
        
        # 检查是否完成
        if self._seconds_left <= 0:
            self._complete_focus()
        # 检查番茄钟奖励
        elif self._is_pomodoro:
            completed_seconds = self._seconds_total - self._seconds_left
            completed_blocks = completed_seconds // (POMODORO_MINUTES * 60)
            
            if completed_blocks > self._pomo_paid_blocks:
                self._give_coins(POMODORO_REWARD_COINS_PER_BLOCK)
                self._pomo_paid_blocks = completed_blocks

    def _complete_focus(self):
        """专注时间完成"""
        completed_minutes = self._seconds_total // 60
        
        # 给予完成奖励
        if self._is_pomodoro:
            # 番茄钟模式：可能还有未支付的最后一个块
            total_blocks = self._seconds_total // (POMODORO_MINUTES * 60)
            self.timer_status.setText(f"番茄钟 {completed_blocks + 1}/{total_blocks}")
        else:
            self.timer_status.setText("专注中...")

    def _update_progress_display(self):
        """更新每日进度显示"""
        self.circular_progress.set_progress(self.today_minutes, self.daily_goal_minutes)
        self.yesterday_card.set_value(f"{self.yesterday_minutes}")
        self.consecutive_card.set_value(f"{self.consecutive_days}")

    def _check_daily_goal_completion(self):
        """检查每日目标完成情况"""
        if self.today_minutes >= self.daily_goal_minutes:
            # 目标完成，给予额外奖励
            bonus_coins = 50  # 完成每日目标的奖励
            self._give_coins(bonus_coins)
            
            # 更新连续天数
            self.consecutive_days += 1
            self._save_consecutive_days()

    def _give_coins(self, amount):
        """给予金币奖励"""
        if self.db and hasattr(self.db, 'add_coins'):
            self.db.add_coins(amount)
            
            # 通知父页面刷新
            if self.parent_page and hasattr(self.parent_page, '_refresh_all'):
                self.parent_page._refresh_all()

    # ========== 数据持久化 ==========
    
    def _load_daily_goal(self):
        """加载每日目标"""
        try:
            if self.db and hasattr(self.db, 'get_setting'):
                return int(self.db.get_setting('daily_focus_goal', 180))
        except:
            pass
        return 180
    
    def _save_daily_goal(self):
        """保存每日目标"""
        try:
            if self.db and hasattr(self.db, 'set_setting'):
                self.db.set_setting('daily_focus_goal', str(self.daily_goal_minutes))
        except:
            pass
    
    def _load_today_progress(self):
        """加载今日进度"""
        today = date.today().isoformat()
        try:
            if self.db and hasattr(self.db, 'get_setting'):
                saved_date = self.db.get_setting('focus_progress_date', '')
                if saved_date == today:
                    return int(self.db.get_setting('focus_progress_minutes', 0))
                else:
                    # 新的一天，重置进度
                    self._save_today_progress(0)
        except:
            pass
        return 0
    
    def _save_today_progress(self, minutes=None):
        """保存今日进度"""
        if minutes is None:
            minutes = self.today_minutes
            
        today = date.today().isoformat()
        try:
            if self.db and hasattr(self.db, 'set_setting'):
                self.db.set_setting('focus_progress_date', today)
                self.db.set_setting('focus_progress_minutes', str(minutes))
        except:
            pass
    
    def _load_yesterday_progress(self):
        """加载昨日进度"""
        try:
            if self.db and hasattr(self.db, 'get_setting'):
                return int(self.db.get_setting('focus_yesterday_minutes', 0))
        except:
            pass
        return 0
    
    def _load_consecutive_days(self):
        """加载连续达标天数"""
        try:
            if self.db and hasattr(self.db, 'get_setting'):
                return int(self.db.get_setting('focus_consecutive_days', 0))
        except:
            pass
        return 0
    
    def _save_consecutive_days(self):
        """保存连续达标天数"""
        try:
            if self.db and hasattr(self.db, 'set_setting'):
                self.db.set_setting('focus_consecutive_days', str(self.consecutive_days))
        except:
            pass

class BeautifulTasksPage(QWidget):
    """美化版任务页面 - 包含专注时间和每日目标"""
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.tasks = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        """构建主界面"""
        # 主滚动区域
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: #f8f9fa;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)

        # 滚动内容容器
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 页面标题
        title_frame = QFrame()
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_icon = QLabel("📋")
        title_icon.setStyleSheet("font-size: 20px;")
        title_label = QLabel("日常任务")
        title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #333;")
        
        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addWidget(title_frame)

        # 专注时间和每日目标面板
        self.focus_panel = FocusPanel(self.db, self)
        layout.addWidget(self.focus_panel)
        
        # 任务管理区域
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
        
        # 任务标题
        task_title_layout = QHBoxLayout()
        task_icon = QLabel("📋")
        task_icon.setStyleSheet("font-size: 16px; border: none; background: transparent;")
        task_title = QLabel("待办事项")
        task_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #333; border: none; background: transparent;")

        self.completed_label = QLabel("已完成 0 项任务")
        self.completed_label.setStyleSheet("color: #28A745; font-size: 12px; border: none; background: transparent;")
        
        task_title_layout.addWidget(task_icon)
        task_title_layout.addWidget(task_title)
        task_title_layout.addStretch()
        task_title_layout.addWidget(self.completed_label)

        tasks_layout.addLayout(task_title_layout)
        
        # 新任务输入
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("添加新任务")
        self.task_input.setStyleSheet("""
            QLineEdit {
                border: none;
                border-bottom: 1px solid #E5E7EB;
                padding: 8px 0;
                font-size: 14px;
                background: transparent;
            }
            QLineEdit:focus {
                border-bottom-color: #4A90E2;
                outline: none;
            }
        """)

        add_btn = QPushButton("✓")
        add_btn.setFixedSize(45, 30)  # 与删除按钮大小一致
        add_btn.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                color: #28A745;  # 使用绿色表示添加操作
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: #D4EDDA;  # 绿色的浅色背景
                color: #155724;       # 深绿色文字
            }
        """)
        
        input_layout.addWidget(self.task_input, 1)
        input_layout.addWidget(add_btn)
        tasks_layout.addLayout(input_layout)

        # 进行中标题
        ongoing_title = QLabel("进行中")
        ongoing_title.setStyleSheet("""
            font-size: 14px; 
            font-weight: 600; 
            color: #333; 
            margin: 16px 0 8px 0; 
            border: none; 
            background: transparent;
            border-bottom: 1px solid #E5E5E5;
            padding-bottom: 8px;
        """)
        tasks_layout.addWidget(ongoing_title)

        # 进行中任务列表容器
        self.ongoing_task_widget = QWidget()
        self.ongoing_task_layout = QVBoxLayout(self.ongoing_task_widget)
        self.ongoing_task_layout.setContentsMargins(0, 0, 0, 0)
        self.ongoing_task_layout.setSpacing(4)
        tasks_layout.addWidget(self.ongoing_task_widget)

        # 已完成标题
        completed_title = QLabel("已完成")
        completed_title.setStyleSheet("""
            font-size: 14px; 
            font-weight: 600; 
            color: #333; 
            margin: 16px 0 8px 0; 
            border: none; 
            background: transparent;
            border-bottom: 1px solid #E5E5E5;
            padding-bottom: 8px;
        """)
        tasks_layout.addWidget(completed_title)

        # 已完成任务列表容器
        self.completed_task_widget = QWidget()
        self.completed_task_layout = QVBoxLayout(self.completed_task_widget)
        self.completed_task_layout.setContentsMargins(0, 0, 0, 0)
        self.completed_task_layout.setSpacing(4)
        tasks_layout.addWidget(self.completed_task_widget)

        layout.addWidget(tasks_frame)
        
        # 设置滚动区域
        scroll.setWidget(content)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        
        # 连接事件
        add_btn.clicked.connect(self._add_task)
        self.task_input.returnPressed.connect(self._add_task)

    def _add_task(self):
        """添加新任务"""
        text = self.task_input.text().strip()
        if not text:
            return
            
        # 添加到数据库
        if self.db and hasattr(self.db, 'add_task'):
            self.db.add_task(text)
        else:
            # 简单的内存存储
            task_data = {
                'id': len(self.tasks) + 1,
                'text': text,
                'completed': False,
                'created_at': datetime.now().isoformat()
            }
            self.tasks.append(task_data)
        
        self.task_input.clear()
        self.refresh()

    def _toggle_task(self, task_id):
        """切换任务完成状态"""
        if self.db and hasattr(self.db, 'toggle_task'):
            self.db.toggle_task(task_id)
        else:
            # 简单的内存操作
            for task in self.tasks:
                if task['id'] == task_id:
                    task['completed'] = not task['completed']
                    break
        self.refresh()

    def _delete_task(self, task_id):
        """删除任务"""
        if self.db and hasattr(self.db, 'delete_task'):
            self.db.delete_task(task_id)
        else:
            # 简单的内存操作
            self.tasks = [task for task in self.tasks if task['id'] != task_id]
        self.refresh()

    def refresh(self):
        """刷新任务列表"""
        # 清空现有任务显示
        for i in reversed(range(self.ongoing_task_layout.count())):
            child = self.ongoing_task_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        for i in reversed(range(self.completed_task_layout.count())):
            child = self.completed_task_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # 加载任务数据
        if self.db and hasattr(self.db, 'get_tasks'):
            self.tasks = self.db.get_tasks()
        
        completed_count = 0
        
        # 分别显示进行中和已完成的任务
        for task in self.tasks:
            task_widget = self._create_task_widget(task)
            
            if task.get('completed', False):
                self.completed_task_layout.addWidget(task_widget)
                completed_count += 1
            else:
                self.ongoing_task_layout.addWidget(task_widget)
        
        # 更新完成统计
        self.completed_label.setText(f"已完成 {completed_count} 项任务")
        
        # 添加弹性空间
        self.ongoing_task_layout.addStretch()
        self.completed_task_layout.addStretch()

    def _create_task_widget(self, task):
        """创建任务组件"""
        is_completed = task.get('completed', False)
        
        # 修改任务框架样式 - 添加白色背景和边框
        task_frame = QFrame()
        task_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #E5E5E5;
                border-radius: 8px;
                margin: 4px 0;
                padding: 12px;
            }
            QFrame:hover {
                border-color: #D0D7DE;
            }
        """)
        
        layout = QHBoxLayout(task_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 完成状态复选框
        checkbox = QCheckBox()
        checkbox.setChecked(is_completed)
        
        checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #ddd;
                background: white;
            }
            QCheckBox::indicator:hover {
                border-color: #28A745;
            }
            QCheckBox::indicator:checked {
                background-color: #28A745;
                border-color: #28A745;
            }
        """ + ("""
            QCheckBox::indicator:checked {
                background-color: #ADB5BD;
                border-color: #ADB5BD;
            }
        """ if is_completed else ""))
        
        layout.addWidget(checkbox)
        
        checkbox.stateChanged.connect(lambda: self._toggle_task(task['id']))
        
        # 任务文本
        text_label = QLabel(task.get('text', ''))
        text_style = "color: #333; font-size: 14px; padding-left: 8px;"
        if is_completed:
            text_style = "color: #ADB5BD; font-size: 14px; text-decoration: line-through; padding-left: 8px;"
        text_label.setStyleSheet(text_style)
        
        # 删除按钮
        delete_btn = QPushButton("✕")
        delete_btn.setFixedSize(24, 24)
        delete_btn.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                color: #DC3545;
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: #F8D7DA;
                color: #721C24;
            }
        """)
        delete_btn.clicked.connect(lambda: self._delete_task(task['id']))
        
        layout.addWidget(text_label, 1)
        layout.addWidget(delete_btn)
        
        return task_frame

    def _refresh_all(self):
        """刷新所有组件（用于父页面调用）"""
        self.refresh()
        if hasattr(self.focus_panel, '_update_progress_display'):
            self.focus_panel._update_progress_display()
            unpaid_blocks = total_blocks - self._pomo_paid_blocks
            if unpaid_blocks > 0:
                self._give_coins(unpaid_blocks * POMODORO_REWARD_COINS_PER_BLOCK)
        else:
            # 普通模式：按分钟给奖励
            coins = completed_minutes * FOCUS_REWARD_COINS_PER_MIN
            self._give_coins(coins)
        
        # 更新今日进度
        self.today_minutes += completed_minutes
        self._save_today_progress()
        self._check_daily_goal_completion()
        self._update_progress_display()
        
        self._reset_focus_state()

    def _reset_focus_state(self):
        """重置专注状态"""
        self._running = False
        self._timer.stop()
        
        # 重置界面状态
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #999;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
            }
        """)
        
        # 隐藏计时器
        self.timer_display.hide()

    def _update_timer_display(self):
        """更新计时器显示"""
        if self._seconds_left <= 0:
            self.timer_time.setText("00:00")
            self.timer_status.setText("专注完成！")
            return
        
        minutes = self._seconds_left // 60
        seconds = self._seconds_left % 60
        self.timer_time.setText(f"{minutes:02d}:{seconds:02d}")
        
        if self._is_pomodoro:
            completed_blocks = (self._seconds_total - self._seconds_left) // (POMODORO_MINUTES * 60)
            total_blocks = self._seconds_total // (POMODORO_MINUTES * 60)