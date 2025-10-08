# -*- coding: utf-8 -*-
"""
Doro Desktop Pet - 主要桌寵類
整合所有功能模組的核心類別（包含天氣、OCR、提醒、語音、Dashboard 串接）
"""

import os
import random
import webbrowser
from PIL import Image, ImageGrab

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtGui import QKeySequence

from opencc import OpenCC

# ---- 你的專案模組 ----
from ocr_helper import OCRHelper
from ocr_result_window import OcrResultWindow
from say import SpeechBubble
from config import PetConfig
from animation import AnimationManager
from calculator import CalculatorHelper
from physics import PhysicsEngine
from ai_chat import DoroAIChat
from speech_vosk import VoskStreamer
from reminders import (
    ReminderListWindow, ReminderChecker, ReminderManager, show_reminder_popup
)
from dashboard.main_dashboard import DashboardWindow
# ---- Dashboard 導入（新增在這裡）----
try:
    from dashboard.modern_dashboard import ModernDashboard
    MODERN_DASHBOARD_AVAILABLE = True
    print("✅ 載入現代化Dashboard")
except ImportError as e:
    print(f"⚠️  現代化Dashboard不可用: {e}")
    try:
        from dashboard.main_dashboard import DashboardWindow as ModernDashboard
        MODERN_DASHBOARD_AVAILABLE = True
        print("✅ 載入標準Dashboard")
    except ImportError as e2:
        print(f"⚠️  標準Dashboard不可用: {e2}")
        try:
            from simple_dashboard import SimpleDashboard as ModernDashboard
            MODERN_DASHBOARD_AVAILABLE = False
            print("✅ 載入簡化Dashboard")
        except ImportError as e3:
            print(f"❌ 所有Dashboard模組都不可用: {e3}")
            ModernDashboard = None
            MODERN_DASHBOARD_AVAILABLE = False
from dashboard.event_bus import bus

cc = OpenCC('s2t')


def run_on_main_thread(func):
    """確保方法在主執行緒執行，否則用 QTimer 切回主執行緒。"""
    def wrapper(self, *args, **kwargs):
        if QtCore.QThread.currentThread() == QtWidgets.QApplication.instance().thread():
            return func(self, *args, **kwargs)
        else:
            QtCore.QTimer.singleShot(0, lambda: func(self, *args, **kwargs))
    return wrapper


class Pet(QtWidgets.QLabel):
    """桌寵主體類"""

    # -------------------- 建構與初始化 --------------------
    def __init__(self):
        super().__init__()

        # 設定
        self.config = PetConfig()

        # 視窗 / 基本 UI
        self._setup_window()

        # 功能模組
        character_folder = os.path.join(os.path.dirname(__file__), "character")
        self.animation_manager = AnimationManager(character_folder)   # ✅ 僅初始化一次
        self.calculator_helper = CalculatorHelper(self)
        self.physics_engine = PhysicsEngine(self)
        self.ai_chat = DoroAIChat(self)  # AI 聊天

        # 泡泡
        self.bubble = SpeechBubble(theme="blue")

        # 狀態
        self.dragging = False
        self.drag_offset = QtCore.QPoint()
        self.face_right = True
        self.is_thinking = False
        self._speech_active = False
        self._vosk = None

        # 初始狀態（切 walk + 啟動計時器）
        self._setup_initial_state()

        # 系統托盤
        self._create_tray()

        # 熱鍵
        self._init_shortcuts()

        # OCR
        self.ocr = OCRHelper(lang="ch")
        self._ocr_window = OcrResultWindow(self)

        # 提醒
        self._reminder_db = os.path.join(os.path.expanduser("~"), ".deskpet", "reminders.db")
        self.reminder_manager = ReminderManager(self._reminder_db)
        self.reminder_checker = ReminderChecker(self.reminder_manager, parent=self, start_interval_s=30)
        self.reminder_checker.reminder_due.connect(self._on_reminder_due)
        self.reminder_checker.start()
        self._reminder_window = None

        # 角色面板
        self._dash = None

        # 與 Dashboard 事件匯流排串接：播放動畫
        bus.play_anim.connect(self._on_play_anim)

    def _init_shortcuts(self):
        """註冊快速鍵（F9 切換語音輸入 / F10 剪貼簿 OCR）"""
        self._sc_toggle_speech = QShortcut(QKeySequence("F9"), self)
        self._sc_toggle_speech.setAutoRepeat(False)
        self._sc_toggle_speech.activated.connect(self._toggle_speech)

        self._sc_clipboard_ocr = QShortcut(QKeySequence("F10"), self)
        self._sc_clipboard_ocr.setAutoRepeat(False)
        self._sc_clipboard_ocr.activated.connect(self.ocr_from_clipboard)

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
        # 讓 QLabel 依容器拉伸時，Movie 也能鋪滿（不失真會靠 paintEvent）
        self.setScaledContents(False)

    def _setup_initial_state(self):
        """設置初始狀態"""
        # 初始座標
        self.physics_engine.set_initial_position()

        # 切到 walk（若素材缺失會自動回退成球，但我們會檢查）
        self.animation_manager.switch_animation("walk")
        self._update_animation_display(force_start=True)

        # 初始速度
        self.physics_engine.vx = self.config.SPEED_WALK if self.face_right else -self.config.SPEED_WALK

        # 計時器（以毫秒為單位）
        tick_ms = getattr(self.config, "TICK_MS", None)
        if not tick_ms:
            fps = getattr(self.config, "FPS", 30)
            fps = max(1, int(fps))
            tick_ms = max(1, int(1000 / fps))
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update_tick)
        self.timer.start(tick_ms)

    # -------------------- 主迴圈與繪製 --------------------
    def _update_tick(self):
        """主要更新循環"""
        # 物理
        self.physics_engine.update_physics()
        # 顯示動畫
        self._update_animation_display()

    def _update_animation_display(self, force_start=False):
        """更新動畫顯示（必要時重新 start）"""
        movie = self.animation_manager.get_current_movie()
        if movie:
            if force_start or movie != self.movie():
                self.setMovie(movie)
                movie.start()
        # 否則 paintEvent 會畫出粉紅色球做為保底

    def paintEvent(self, e: QtGui.QPaintEvent):
        """自訂繪製（可處理水平翻轉）"""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        movie = self.animation_manager.get_current_movie()
        if movie:
            frame = movie.currentPixmap()
            if not frame.isNull():
                # 依朝向水平翻轉
                need_flip = (self.face_right != self.config.SOURCE_FACES_RIGHT)
                if need_flip:
                    frame = frame.transformed(QtGui.QTransform().scale(-1, 1))
                p.drawPixmap(self.rect(), frame)
                return  # 有正確影格就不畫球

        # 備援：粉紅色圓球（代表動畫尚未載入成功）
        p.setBrush(QtGui.QColor(255, 182, 193, 220))
        p.setPen(QtCore.Qt.NoPen)
        r = self.rect().adjusted(8, 8, -8, -8)
        p.drawEllipse(r)

    # -------------------- 與 Dashboard 串接 --------------------
    def _on_play_anim(self, key: str):
        """Dashboard 要求播放某個行為（例如 'walk' / 'idle' / 'sleep' …）"""
        try:
            self.set_behavior(key)  # 直接切換行為
        except Exception as e:
            print("[Pet] play_anim error:", e)
    # -------------------- 資源檢查 --------------------
    def check_ui_resources(self):
        """檢查UI資源是否存在"""
        ui_path = Path(__file__).parent / "assets" / "ui"
        required_icons = ["bag.png", "bell.png", "home.png", "list.png", "shop.png"]
        
        missing_icons = []
        for icon in required_icons:
            if not (ui_path / icon).exists():
                missing_icons.append(icon)
        
        if missing_icons:
            print(f"警告：缺少UI圖標: {missing_icons}")
            print(f"請確保以下文件存在於 {ui_path}/")
            for icon in missing_icons:
                print(f"  - {icon}")
        
        return len(missing_icons) == 0

    # -------------------- 提醒觸發 --------------------
    def _on_reminder_due(self, r):
        # 桌寵對話泡泡（可選）
        try:
            if hasattr(self, "say"):
                self.say(f"時間到囉！該做：{r.title}")
        except Exception:
            pass
        # 系統提醒彈窗
        show_reminder_popup(self, r)

    # -------------------- 天氣 --------------------
    def open_weather(self):
        """打開本地天氣網頁"""
        try:
            self.ai_speak("人～正在為你查看天氣資訊～", "think")
            webbrowser.open("https://www.msn.com/zh-tw/weather")
            QtCore.QTimer.singleShot(
                2000,
                lambda: self.ai_speak("天氣頁面已經打開囉～記得看看要不要帶傘呢～", "happy"),
            )
        except Exception as e:
            self.ai_speak(f"嗚嗚...無法打開天氣頁面: {str(e)}", "sad")

    # -------------------- OCR --------------------
    def show_ocr_result(self, full_text: str):
        txt = (full_text or "").strip()
        if txt:
            preview = "\n".join(txt.splitlines()[:3])
            self.ai_speak(f"人～我幫你看到這些文字：\n{preview}", "think")
        else:
            self.ai_speak("人～這張圖裡好像沒有偵測到文字…", "sad")

        self._ocr_window.set_text(txt)
        self._ocr_window.show()
        self._ocr_window.raise_()
        self._ocr_window.activateWindow()

    def ocr_from_file_dialog(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "選擇圖片", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return
        self.show_thinking()
        QtCore.QTimer.singleShot(100, lambda: self._run_ocr_on_path(path))

    def _run_ocr_on_path(self, path: str):
        try:
            text = self.ocr.extract_text(path)
        except Exception as e:
            text = f"[OCR 錯誤] {e}"
        self.hide_thinking()
        self.show_ocr_result(text)

    def ocr_from_clipboard(self):
        img = ImageGrab.grabclipboard()
        if not isinstance(img, Image.Image):
            self.ai_speak("剪貼簿裡沒有圖片，先用 Shift+Win+S 截圖喔～", "sad")
            return
        self.show_thinking()
        QtCore.QTimer.singleShot(100, lambda: self._run_ocr_on_pil(img))

    def _run_ocr_on_pil(self, pil_img):
        try:
            text = self.ocr.extract_text_from_pil(pil_img)
        except Exception as e:
            text = f"[OCR 錯誤] {e}"
        self.hide_thinking()
        self.show_ocr_result(text)

    # -------------------- 提醒視窗 --------------------
    def _open_reminder_window(self):
        if not hasattr(self, "_reminder_window") or self._reminder_window is None:
            self._reminder_window = ReminderListWindow(self.reminder_manager, parent=self)
            self._reminder_window.resize(800, 480)
            self._reminder_window.destroyed.connect(lambda: setattr(self, "_reminder_window", None))
        self._reminder_window.show()
        self._reminder_window.raise_()
        self._reminder_window.activateWindow()

    # -------------------- 對外 API（說話 / 動畫） --------------------
    @run_on_main_thread
    def ai_speak(self, text: str, emotion_override: str = None):
        emotion = emotion_override or self.animation_manager.analyze_text_emotion(text)
        self.set_behavior(emotion)
        theme = getattr(self.config, "bubble_themes", {}).get(emotion, "blue")
        self.say(text, theme=theme)

    @run_on_main_thread
    def show_thinking(self):
        self.is_thinking = True
        self.animation_manager.switch_animation("think")
        self._update_animation_display(force_start=True)

    @run_on_main_thread
    def hide_thinking(self):
        self.is_thinking = False
        if self.animation_manager.get_current_behavior() == "think":
            self.animation_manager.switch_animation("idle")
            self._update_animation_display(force_start=True)

    def set_behavior(self, behavior: str):
        """手動切換行為模式（walk / idle / sleep / think / happy / sad / love_orange …）"""
        if self.animation_manager.has_animation(behavior):
            self.animation_manager.switch_animation(behavior)
            self._update_animation_display(force_start=True)

            # 依行為調整物理狀態
            if behavior == "walk" and self.physics_engine.wander_enabled:
                self.physics_engine.vx = (
                    self.config.SPEED_WALK if self.face_right else -self.config.SPEED_WALK
                )
            elif behavior == "sleep":
                self.physics_engine.vx = 0
                self.physics_engine.vy = 0

    def say(self, text: str, theme: str = None):
        if theme is None:
            theme = random.choice(["blue", "green", "pink", "yellow", "gray"])
        self.bubble.say(text, self.pos(), theme=theme)

    def _return_to_idle(self):
        """自動返回 idle 狀態"""
        if not self.is_thinking and self.animation_manager.get_current_behavior() not in ["walk", "sleep"]:
            self.animation_manager.switch_animation("idle")
            self._update_animation_display(force_start=True)

    # -------------------- AI 聊天 --------------------
    def chat_with_doro(self, message: str):
        self.show_thinking()
        self.ai_chat.chat_with_ai(message)

    def is_ai_ready(self) -> bool:
        return self.ai_chat.is_ai_ready()

    def get_ai_info(self) -> dict:
        return self.ai_chat.get_character_info()

    # -------------------- 語音（Vosk） --------------------
    def _toggle_speech(self):
        if not self._speech_active:
            try:
                print("正在初始化語音識別...")
                model_path = r"vosk-model-small-cn-0.22"
                print(f"模型路徑: {model_path}")
                print(f"路徑是否存在: {os.path.exists(model_path)}")
                self._vosk = VoskStreamer(model_path, samplerate=16000)
                self._vosk.partial.connect(self._on_partial_stt)
                self._vosk.final.connect(self._on_final_stt)
                self._vosk.start()
                self._speech_active = True
                self.ai_speak("人～語音輸入開啟啦！", "happy")
            except Exception as e:
                self.ai_speak(f"語音啟動失敗：{e}", "sad")
                self._speech_active = False
        else:
            try:
                if self._vosk:
                    self._vosk.stop()
            finally:
                self._speech_active = False
                self.ai_speak("人～語音輸入關閉囉～", "think")

    def _on_partial_stt(self, text: str):
        if text:
            self.say(f"(聽：{text})", theme="gray")

    def _on_final_stt(self, text: str):
        if text:
            trad_text = cc.convert(text)
            self.say(f"你說：{trad_text}", theme="green")
            self.chat_with_doro(trad_text)

    # -------------------- 滑鼠事件 --------------------
    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.drag_offset = e.globalPos() - self.frameGeometry().topLeft()
            self.physics_engine.start_dragging()
            e.accept()

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self.dragging:
            self.move(e.globalPos() - self.drag_offset)
            e.accept()

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton and self.dragging:
            self.dragging = False
            self.physics_engine.stop_dragging()
            e.accept()

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent):
        text, emotion = random.choice(self.config.random_greetings)
        self.ai_speak(text, emotion)
        e.accept()

    # -------------------- 右鍵選單 / 托盤 --------------------
    def _show_context_menu(self, pos):
        menu = QtWidgets.QMenu(self)

        # 行為模式
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
        act_dash = menu.addAction("📊 角色面板")
        act_say = menu.addAction("說一句…")
        act_chat = menu.addAction("💬 與 Doro 聊天")
        act_calc = menu.addAction("🧮 計算器助手")
        act_weather = menu.addAction("🌤️ 查看天氣")
        act_web = menu.addAction("🌐 分析網頁…")
        act_ocr = menu.addAction("📸 截圖文字辨識（F10）")
        act_translate = menu.addAction("🌏 翻譯文字…")
        act_reminder = menu.addAction("⏰ 提醒事項…")
        act_speech = menu.addAction("🎤 語音輸入 (F9) " + ("關閉" if self._speech_active else "開啟"))

        menu.addSeparator()

        # AI 子選單
        ai_menu = menu.addMenu("🤖 AI 功能")
        act_ai_stats = ai_menu.addAction("查看 AI 狀態")
        act_ai_clear = ai_menu.addAction("清除 AI 記憶")
        act_ai_backup = ai_menu.addAction("備份 AI 記憶")

        menu.addSeparator()

        act_grav = menu.addAction("關閉重力" if self.physics_engine.gravity_enabled else "開啟重力")
        act_wander = menu.addAction("暫停移動" if self.physics_engine.wander_enabled else "恢復移動")
        act_top = menu.addAction("取消置頂" if self.testAttribute(QtCore.Qt.WA_AlwaysStackOnTop) else "置頂顯示")

        menu.addSeparator()
        act_quit = menu.addAction("退出")

        chosen = menu.exec_(self.mapToGlobal(pos))
        if chosen is None:
            return

        self._handle_menu_action(chosen, behavior_actions, {
            'say': act_say,
            'chat': act_chat,
            'calc': act_calc,
            'ocr': act_ocr,
            'weather': act_weather,
            'speech': act_speech,
            'gravity': act_grav,
            'wander': act_wander,
            'top': act_top,
            'quit': act_quit,
            'ai_stats': act_ai_stats,
            'ai_clear': act_ai_clear,
            'ai_backup': act_ai_backup,
            'web_analyze': act_web,
            'translate': act_translate,
            'reminder': act_reminder,
            'dashboard': act_dash,
        })

    def _handle_menu_action(self, chosen, behavior_actions, other_actions):
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

        elif chosen == other_actions['dashboard']:
            if self._dash is None:
                if MODERN_DASHBOARD_AVAILABLE:
                    self._dash = ModernDashboard()
                else:
                    # 降級處理
                    QtWidgets.QMessageBox.information(
                        self, "提示", 
                        "Dashboard 模組不可用，請檢查相關文件是否存在。"
                    )
                    return
            
            self._dash.show()
            self._dash.raise_()
            self._dash.activateWindow()

        elif chosen == other_actions['calc']:
            expression = self.calculator_helper.open_calculator_dialog(self)
            if expression:
                self.calculator_helper.calculate_with_system_calculator(expression)

        elif chosen == other_actions['weather']:
            self.open_weather()

        elif chosen == other_actions['speech']:
            self._toggle_speech()

        elif chosen == other_actions['ocr']:
            self.ocr_from_file_dialog()

        elif chosen == other_actions['reminder']:
            self._open_reminder_window()

        elif chosen == other_actions['web_analyze']:
            from PyQt5.QtWidgets import QInputDialog, QMessageBox
            url, ok = QInputDialog.getText(self, "分析網頁", "請貼上要分析的 URL：")
            if ok:
                try:
                    from plugins_runtime import get_executor
                    executor = get_executor()
                    result = executor.call("summarize_page", url=url.strip() or None)
                    if result.get("error"):
                        self.say("（插件）" + result["error"])
                    else:
                        preview = result.get("summary", "")[:180]
                        self.say(preview + ("…" if len(result.get("summary", "")) > 180 else ""))
                        title = result.get("title", "")
                        kind = result.get("kind", "")
                        summary = result.get("summary", "")
                        points = result.get("points") or []
                        if summary or points:
                            full = f"《{title}》\n\n{summary}\n\n" + \
                                   ("\n".join(f"• {p}" for p in points) if points else "")
                            QMessageBox.information(self, "分析結果", full)
                except Exception as e:
                    self.say(f"分析失敗：{e}")
            return

        elif chosen == other_actions['translate']:
            from PyQt5.QtWidgets import QInputDialog, QMessageBox
            txt, ok = QInputDialog.getText(self, "翻譯文字", "請輸入要翻譯的內容：")
            if ok and txt.strip():
                try:
                    from plugins_runtime import get_executor
                    executor = get_executor()
                    result = executor.call("translate_text", text=txt.strip(), target_lang="zh-TW")
                    if result.get("error"):
                        self.say("（翻譯）" + result["error"])
                    else:
                        translated = result.get("translated", "")
                        self.say(translated[:100] + ("…" if len(translated) > 100 else ""))
                        QMessageBox.information(self, "翻譯結果", f"原文：{txt}\n\n翻譯：{translated}")
                except Exception as e:
                    self.say(f"翻譯失敗：{e}")

        elif chosen == other_actions['ai_stats']:
            stats = self.ai_chat.get_ai_stats()
            if stats.get('status') == 'ready':
                functions_list = ", ".join(stats.get('available_functions', []))
                info_text = f"""AI 狀態資訊：
                                角色名稱：{stats.get('character_name', 'Doro')}
                                短期記憶：{stats.get('short_term_count', 0)} 筆
                                長期記憶：{stats.get('long_term_count', 0)} 筆
                                可用功能：{functions_list}
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
        flags = self.windowFlags()
        if flags & QtCore.Qt.WindowStaysOnTopHint:
            self.setWindowFlags(flags & ~QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags | QtCore.Qt.WindowStaysOnTopHint)
        self.show()

    def _create_tray(self):
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = self._create_tray_icon()
        self.tray = QtWidgets.QSystemTrayIcon(icon, self)

        menu = QtWidgets.QMenu()
        act_show = menu.addAction("顯示/置前")
        act_hide = menu.addAction("隱藏")
        menu.addSeparator()
        act_quit = menu.addAction("退出")

        act_show.triggered.connect(self._show_and_raise)
        act_hide.triggered.connect(self.hide)
        act_quit.triggered.connect(QtWidgets.QApplication.quit)

        self.tray.setContextMenu(menu)
        self.tray.setToolTip(self.config.APP_NAME + " (含天氣功能)")
        self.tray.show()

    def _create_tray_icon(self):
        icon = QtGui.QIcon.fromTheme("face-smile")
        if icon.isNull():
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
        self.show()
        self.raise_()
        self.activateWindow()

    # -------------------- 訊息 / 偵錯 --------------------
    def get_status_info(self):
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
            },
            "ai": self.get_ai_info(),
            "available_functions": ["calculator", "weather"]
        }
