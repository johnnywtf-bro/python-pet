# -*- coding: utf-8 -*-
"""
Doro Desktop Pet - 主要桌寵類
整合所有功能模組的核心類別
"""
import os
import random
from PyQt5 import QtCore, QtGui, QtWidgets
from say import SpeechBubble
from config import PetConfig
from animation import AnimationManager
from calculator import CalculatorHelper
from physics import PhysicsEngine
from ai_chat import DoroAIChat

def run_on_main_thread(func):
    """確保方法在主執行緒執行，否則用 QTimer 切回主執行緒。
    """
    def wrapper(self, *args, **kwargs):
        if QtCore.QThread.currentThread() == QtWidgets.QApplication.instance().thread():
            return func(self, *args, **kwargs)
        else:
            QtCore.QTimer.singleShot(0, lambda: func(self, *args, **kwargs))
    return wrapper

class Pet(QtWidgets.QLabel):
    """桌寵主體類"""
    
    def __init__(self):
        super().__init__()
        
        # 載入設定
        self.config = PetConfig()
        
        # 基本設置
        self._setup_window()
        
        # 初始化各功能模組
        character_folder = os.path.join(os.path.dirname(__file__), "character")
        self.animation_manager = AnimationManager(character_folder)
        self.calculator_helper = CalculatorHelper(self)
        self.physics_engine = PhysicsEngine(self)
        self.ai_chat = DoroAIChat(self)  # 新增 AI 聊天系統
        
        # UI 組件
        self.bubble = SpeechBubble(theme="blue")
        
        # 狀態變量
        self.dragging = False
        self.drag_offset = QtCore.QPoint()
        self.face_right = True
        self.is_thinking = False
        
        # 設置初始狀態
        self._setup_initial_state()
        
        # 創建系統托盤
        self._create_tray()
    
    def _setup_window(self):
        """設置窗口屬性"""
        self.setWindowTitle(self.config.APP_NAME)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Tool |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self.resize(self.config.PET_WIDTH, self.config.PET_HEIGHT)
    
    def _setup_initial_state(self):
        """設置初始狀態"""
        # 設置初始位置
        self.physics_engine.set_initial_position()
        
        # 切換到初始動畫
        self.animation_manager.switch_animation("walk")
        
        # 設置初始移動方向
        self.physics_engine.vx = self.config.SPEED_WALK if self.face_right else -self.config.SPEED_WALK
        
        # 啟動物理更新計時器
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update_tick)
        self.timer.start(self.config.FPS)
    
    def _update_tick(self):
        """主要更新循環"""
        self.physics_engine.update_physics()
        self._update_animation_display()
    
    def _update_animation_display(self):
        """更新動畫顯示"""
        current_movie = self.animation_manager.get_current_movie()
        if current_movie and current_movie != self.movie():
            self.setMovie(current_movie)
            current_movie.start()
    
    def paintEvent(self, e: QtGui.QPaintEvent):
        """繪製事件"""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        current_movie = self.animation_manager.get_current_movie()
        if current_movie:
            frame = current_movie.currentPixmap()
            if not frame.isNull():
                # 根據朝向決定是否翻轉
                need_flip = (self.face_right != self.config.SOURCE_FACES_RIGHT)
                if need_flip:
                    frame = frame.transformed(QtGui.QTransform().scale(-1, 1))
                p.drawPixmap(self.rect(), frame)
        else:
            # 備用繪製：粉色圓形
            p.setBrush(QtGui.QColor(255, 182, 193, 220))
            p.setPen(QtCore.Qt.NoPen)
            r = self.rect().adjusted(8, 8, -8, -8)
            p.drawEllipse(r)
    
    # ==================== 公共 API 方法 ====================
    
    @run_on_main_thread
    def ai_speak(self, text: str, emotion_override: str = None):
        """安全地顯示 AI 對話泡泡"""
        emotion = emotion_override or self.animation_manager.analyze_text_emotion(text)
        self.set_behavior(emotion)
        theme = getattr(self.config, "bubble_themes", {}).get(emotion, "blue")
        self.say(text, theme=theme)

    @run_on_main_thread
    def show_thinking(self):
        """安全地顯示思考動畫"""
        self.is_thinking = True
        self.animation_manager.switch_animation("think")
        self._update_animation_display()

    @run_on_main_thread
    def hide_thinking(self):
        """安全地隱藏思考動畫"""
        self.is_thinking = False
        if self.animation_manager.get_current_behavior() == "think":
            self.animation_manager.switch_animation("idle")
            self._update_animation_display()
    
    def set_behavior(self, behavior: str):
        """手動設置行為模式"""
        if self.animation_manager.has_animation(behavior):
            self.animation_manager.switch_animation(behavior)
            self._update_animation_display()
            
            # 根據行為調整物理狀態
            if behavior == "walk" and self.physics_engine.wander_enabled:
                self.physics_engine.vx = self.config.SPEED_WALK if self.face_right else -self.config.SPEED_WALK
            elif behavior == "sleep":
                self.physics_engine.vx = 0
                self.physics_engine.vy = 0
    
    def say(self, text: str, theme: str = None):
        """顯示對話泡泡"""
        if theme is None:
            themes = ["blue", "green", "pink", "yellow", "gray"]
            theme = random.choice(themes)
        self.bubble.say(text, self.pos(), theme=theme)
    
    def _return_to_idle(self):
        """自動返回idle狀態"""
        if not self.is_thinking and self.animation_manager.get_current_behavior() not in ["walk", "sleep"]:
            self.animation_manager.switch_animation("idle")
            self._update_animation_display()
    
    def chat_with_doro(self, message: str):
        """與 Doro AI 聊天的主要接口"""
        self.ai_chat.chat_with_ai(message)
    
    def is_ai_ready(self) -> bool:
        """檢查 AI 是否準備就緒"""
        return self.ai_chat.is_ai_ready()
    
    def get_ai_info(self) -> dict:
        """獲得 AI 資訊"""
        return self.ai_chat.get_character_info()
    
    # ==================== 輸入事件處理 ====================
    
    def mousePressEvent(self, e: QtGui.QMouseEvent):
        """鼠標按下事件"""
        if e.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.drag_offset = e.globalPos() - self.frameGeometry().topLeft()
            self.physics_engine.start_dragging()
            e.accept()
    
    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        """鼠標移動事件"""
        if self.dragging:
            self.move(e.globalPos() - self.drag_offset)
            e.accept()
    
    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        """鼠標釋放事件"""
        if e.button() == QtCore.Qt.LeftButton and self.dragging:
            self.dragging = False
            self.physics_engine.stop_dragging()
            e.accept()
    
    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent):
        """鼠標雙擊事件"""
        text, emotion = random.choice(self.config.random_greetings)
        self.ai_speak(text, emotion)
        e.accept()
    
    # ==================== 選單和托盤 ====================
    
    def _show_context_menu(self, pos):
        """顯示右鍵選單"""
        menu = QtWidgets.QMenu(self)
        
        # 行為模式子選單
        behavior_menu = menu.addMenu("切換行為模式")
        behavior_actions = {}
        
        behavior_names = {
            "walk": "Walk (行走)",
            "idle": "Idle (待機)", 
            "sleep": "Sleep (睡覺)",
            "think": "Think (思考)",
            "happy": "Happy (開心)",
            "sad": "Sad (傷心)",
            "love_orange": "Love Orange (愛哦潤吉)"
        }
        
        current_behavior = self.animation_manager.get_current_behavior()
        
        for behavior, display_name in behavior_names.items():
            if self.animation_manager.has_animation(behavior):
                action = behavior_menu.addAction(display_name)
                if behavior == current_behavior:
                    action.setText("✓ " + display_name)
                behavior_actions[action] = behavior
        
        menu.addSeparator()
        
        # 其他功能
        act_say = menu.addAction("說一句…")
        act_chat = menu.addAction("💬 與 Doro 聊天")
        act_calc = menu.addAction("🧮 計算器助手")
        
        menu.addSeparator()
        
        # AI 功能子選單
        ai_menu = menu.addMenu("🤖 AI 功能")
        act_ai_stats = ai_menu.addAction("查看 AI 狀態")
        act_ai_clear = ai_menu.addAction("清除 AI 記憶")
        act_ai_backup = ai_menu.addAction("備份 AI 記憶")
        
        menu.addSeparator()
        
        # 設置選項
        act_grav = menu.addAction(
            "關閉重力" if self.physics_engine.gravity_enabled else "開啟重力"
        )
        act_wander = menu.addAction(
            "暫停移動" if self.physics_engine.wander_enabled else "恢復移動"
        )
        act_top = menu.addAction(
            "取消置頂" if self.testAttribute(QtCore.Qt.WA_AlwaysStackOnTop) else "置頂顯示"
        )
        
        menu.addSeparator()
        act_quit = menu.addAction("退出")
        
        # 處理選單選擇
        chosen = menu.exec_(self.mapToGlobal(pos))
        if chosen is None:
            return
        
        self._handle_menu_action(chosen, behavior_actions, {
            'say': act_say,
            'chat': act_chat,
            'calc': act_calc, 
            'gravity': act_grav,
            'wander': act_wander,
            'top': act_top,
            'quit': act_quit,
            'ai_stats': act_ai_stats,
            'ai_clear': act_ai_clear,
            'ai_backup': act_ai_backup
        })
    
    def _handle_menu_action(self, chosen, behavior_actions, other_actions):
        """處理選單動作"""
        # 行為切換
        if chosen in behavior_actions:
            behavior = behavior_actions[chosen]
            self.set_behavior(behavior)
            return
        
        # 其他動作
        if chosen == other_actions['say']:
            text, ok = QtWidgets.QInputDialog.getText(self, "讓桌寵說話", "內容：")
            if ok and text.strip():
                self.ai_speak(text.strip())
        
        elif chosen == other_actions['chat']:
            text, ok = QtWidgets.QInputDialog.getText(self, "與 Doro 聊天", "說點什麼給 Doro 聽：")
            if ok and text.strip():
                self.chat_with_doro(text.strip())
        
        elif chosen == other_actions['calc']:
            expression = self.calculator_helper.open_calculator_dialog(self)
            if expression:
                self.calculator_helper.calculate_with_system_calculator(expression)
        
        elif chosen == other_actions['ai_stats']:
            stats = self.ai_chat.get_ai_stats()
            if stats.get('status') == 'ready':
                info_text = f"""AI 狀態資訊：
角色名稱：{stats.get('character_name', 'Doro')}
短期記憶：{stats.get('short_term_count', 0)} 筆
長期記憶：{stats.get('long_term_count', 0)} 筆
對話歷史：{stats.get('total_conversations', 0)} 筆
狀態：就緒"""
            else:
                info_text = f"AI 狀態：{stats.get('status', '未知')}"
            
            QtWidgets.QMessageBox.information(self, "AI 狀態", info_text)
        
        elif chosen == other_actions['ai_clear']:
            reply = QtWidgets.QMessageBox.question(
                self, "清除記憶", 
                "確定要清除 Doro 的所有記憶嗎？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                self.ai_chat.clear_ai_memory()
        
        elif chosen == other_actions['ai_backup']:
            self.ai_chat.backup_ai_memories()
        
        elif chosen == other_actions['gravity']:
            self.physics_engine.toggle_gravity()
        
        elif chosen == other_actions['wander']:
            self.physics_engine.toggle_wander()
        
        elif chosen == other_actions['top']:
            self._toggle_always_on_top()
        
        elif chosen == other_actions['quit']:
            QtWidgets.QApplication.quit()
    
    def _toggle_always_on_top(self):
        """切換置頂狀態"""
        flags = self.windowFlags()
        if flags & QtCore.Qt.WindowStaysOnTopHint:
            self.setWindowFlags(flags & ~QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags | QtCore.Qt.WindowStaysOnTopHint)
        self.show()
    
    def _create_tray(self):
        """創建系統托盤"""
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        # 創建托盤圖標
        icon = self._create_tray_icon()
        
        self.tray = QtWidgets.QSystemTrayIcon(icon, self)
        
        # 創建托盤選單
        menu = QtWidgets.QMenu()
        act_show = menu.addAction("顯示/置前")
        act_hide = menu.addAction("隱藏")
        menu.addSeparator()
        act_quit = menu.addAction("退出")
        
        # 連接信號
        act_show.triggered.connect(self._show_and_raise)
        act_hide.triggered.connect(self.hide)
        act_quit.triggered.connect(QtWidgets.QApplication.quit)
        
        self.tray.setContextMenu(menu)
        self.tray.setToolTip(self.config.APP_NAME)
        self.tray.show()
    
    def _create_tray_icon(self):
        """創建托盤圖標"""
        icon = QtGui.QIcon.fromTheme("face-smile")
        if icon.isNull():
            # 創建簡單的粉色圓形圖標
            pix = QtGui.QPixmap(64, 64)
            pix.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(pix)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setBrush(QtGui.QColor(255, 182, 193))
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(4, 4, 56, 56)
            p.end()
            icon = QtGui.QIcon(pix)
        return icon
    
    def _show_and_raise(self):
        """顯示並置前"""
        self.show()
        self.raise_()
        self.activateWindow()
    
    # ==================== 調試和信息 ====================
    
    def get_status_info(self):
        """獲得桌寵狀態信息"""
        return {
            "animation": {
                "current_behavior": self.animation_manager.get_current_behavior(),
                "available_behaviors": self.animation_manager.get_available_behaviors(),
                "is_thinking": self.is_thinking
            },
            "physics": self.physics_engine.get_physics_info(),
            "ui": {
                "position": {"x": self.x(), "y": self.y()},
                "size": {"width": self.width(), "height": self.height()},
                "visible": self.isVisible(),
                "dragging": self.dragging
            }
        }