# -*- coding: utf-8 -*- 
"""
Doro Desktop Pet - 主程式入口（整合啟動器功能）
"""
import os
import sys
from PyQt5 import QtCore
from config import setup_qt_environment
import asyncio

# 在建立任何 Qt 物件前設定環境
setup_qt_environment()

# 確保 Qt 能找到平台插件
if hasattr(QtCore.Qt, 'AA_ShareOpenGLContexts'):
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)

def _append_run_path():
    if getattr(sys, 'frozen', False):
        pathlist = []
        
        # 如果是打包後的 exe
        pathlist.append(os.path.dirname(sys.executable))
        
    elif sys.platform == 'win32':
        pathlist = []
        # 預設 PyQt5 安裝路徑
        import PyQt5
        qt_path = os.path.dirname(PyQt5.__file__)
        pathlist.append(os.path.join(qt_path, 'Qt5', 'plugins'))
        pathlist.append(qt_path)
        
    for path in pathlist:
        if path not in sys.path:
            sys.path.append(path)

_append_run_path()

from PyQt5 import QtWidgets, QtGui
import random
from ai_chat import DoroAIChat
from config import PetConfig
from pet import Pet
import asyncio
from concurrent.futures import ThreadPoolExecutor

def check_dependencies():
    """檢查必要的依賴和檔案"""
    issues = []
    
    # 檢查 character 資料夾
    character_folder = os.path.join(os.path.dirname(__file__), "character")
    if not os.path.exists(character_folder):
        issues.append(f"找不到 character 資料夾：{character_folder}")
    
    # 檢查基本 GIF 檔案
    basic_gifs = ["pet_walk.gif", "pet_idle.gif", "pet_sleep.gif"]
    for gif_file in basic_gifs:
        gif_path = os.path.join(character_folder, gif_file)
        if not os.path.exists(gif_path):
            issues.append(f"找不到必要的 GIF 檔案：{gif_file}")
    
    # 檢查 AI 設定檔案
    test_json_path = os.path.join(os.path.dirname(__file__), "test.json")
    ai_config_available = os.path.exists(test_json_path)
    
    return issues, ai_config_available

def check_ai_dependencies():
    """檢查 AI 模式所需的依賴套件"""
    missing_deps = []
    
    try:
        import ollama
    except ImportError:
        missing_deps.append("ollama")
    
    return len(missing_deps) == 0, missing_deps

def show_startup_dialog_with_model_selector():
    """顯示整合模型選擇的啟動對話框"""
    try:
        from startup_ui_with_model_selector import StartupDialog
        
        dialog = StartupDialog()
        selected_mode = None
        selected_model = None
        
        def on_mode_selected(mode, model_info):
            nonlocal selected_mode, selected_model
            selected_mode = mode
            selected_model = model_info
            print(f"用戶選擇: {mode} 模式")
            if model_info:
                print(f"選擇模型: {model_info['display_name']} ({model_info['provider']})")
        
        dialog.mode_selected.connect(on_mode_selected)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            return selected_mode, selected_model
        else:
            return None, None
            
    except ImportError:
        print("新的模型選擇界面不可用，使用基本啟動對話框")
        mode = show_basic_startup_dialog()
        return mode, None

def show_basic_startup_dialog():
    """顯示基本啟動對話框（備用）"""
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle("Doro Desktop Pet")
    dialog.setWindowIcon(QtGui.QIcon("assets/icon.png"))
    dialog.setFixedSize(400, 300)
    
    # 設定背景顏色為淺粉色
    dialog.setStyleSheet("""
        QDialog {
            background-color: #FFF0F5;
        }
        QPushButton {
            background-color: #FFB6C1;
            border: none;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #FF69B4;
        }
        QLabel {
            color: #FF69B4;
            font-size: 16px;
        }
    """)

    layout = QtWidgets.QVBoxLayout()
    
    # 標題和圖示
    title_label = QtWidgets.QLabel("🦊 Doro Desktop Pet")
    title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #FF69B4; margin: 20px;")
    title_label.setAlignment(QtCore.Qt.AlignCenter)
    
    # 模式選擇標題
    mode_label = QtWidgets.QLabel("選擇啟動模式")
    mode_label.setAlignment(QtCore.Qt.AlignCenter)
    
    # AI 模式按鈕
    ai_btn = QtWidgets.QPushButton("🤖 AI 模式")
    ai_btn.setFixedSize(200, 50)
    
    # 檢查 AI 依賴時捕捉任何可能的例外
    try:
        ai_ready, missing_deps = check_ai_dependencies()
        if not ai_ready:
            ai_btn.setEnabled(False)
            ai_btn.setToolTip("需要安裝 AI 相關套件")
            deps_text = " ".join(missing_deps)
            install_label = QtWidgets.QLabel(f"💡 安裝 AI 功能:\npip install {deps_text}")
            install_label.setStyleSheet("color: #808080; font-size: 12px;")
            layout.addWidget(install_label)
    except Exception as e:
        print(f"檢查 AI 依賴時發生錯誤: {e}")
        ai_btn.setEnabled(False)
        ai_btn.setToolTip(f"檢查依賴失敗: {e}")
    
    # 基本模式按鈕
    basic_btn = QtWidgets.QPushButton("🎮 基本模式")
    basic_btn.setFixedSize(200, 50)
    
    # 添加元件到布局
    layout.addWidget(title_label)
    layout.addWidget(mode_label)
    layout.addSpacing(20)
    layout.addWidget(ai_btn, alignment=QtCore.Qt.AlignCenter)
    layout.addSpacing(10)
    layout.addWidget(basic_btn, alignment=QtCore.Qt.AlignCenter)
    layout.addStretch()
    
    dialog.setLayout(layout)

    # 綁定按鈕事件
    mode = ["basic"]  # 使用列表儲存選擇結果
    ai_btn.clicked.connect(lambda: mode.append("ai") or dialog.accept())
    basic_btn.clicked.connect(lambda: mode.append("basic") or dialog.accept())
    
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        return mode[-1]  # 回傳最後選擇的模式
    else:
        return None

def setup_selected_model(model_info):
    """設定用戶選擇的模型"""
    if not model_info:
        return True  # 基本模式不需要模型
    
    try:
        # 檢查是否有 LLM 適配器
        try:
            from llm_config import config_manager
            success = config_manager.switch_model(model_info['name'])
            if success:
                print(f"✅ 已設定模型: {model_info['display_name']}")
                return True
            else:
                print(f"❌ 模型設定失敗: {model_info['name']}")
                return False
        except ImportError:
            print("⚠️ LLM 配置模組不可用，使用預設配置")
            return True
            
    except Exception as e:
        print(f"❌ 模型配置失敗: {e}")
        return False

def setup_application():
    """設置應用程式"""
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(PetConfig.APP_NAME)
    return app

def start_ai_mode_with_model(model_info):
    """啟動 AI 模式並設定模型"""
    print("進入 start_ai_mode_with_model")
    
    # 首先設定模型
    if not setup_selected_model(model_info):
        QtWidgets.QMessageBox.critical(
            None, 
            "啟動失敗", 
            f"無法設定模型 {model_info['display_name']}，請檢查服務是否運行"
        )
        return None
    
    # 創建寵物和 AI
    pet = Pet()
    print("Pet 建立完成")
    pet.show()
    print("Pet show 完成")
    
    # 創建 AI 聊天
    ai = DoroAIChat(pet)
    print("DoroAIChat 建立完成")
    
    # 顯示當前使用的模型
    try:
        if model_info:
            model_name = model_info['display_name']
            provider = model_info['provider']
            if provider == 'lemonade':
                startup_msg = f"AI 模式啟動！我現在使用高效的 NPU 模型 {model_name} 🚀"
            else:
                startup_msg = f"AI 模式啟動！我現在使用 {model_name} 💻"
            
            # 延遲顯示，讓 AI 初始化完成
            QtCore.QTimer.singleShot(2000, lambda: pet.ai_speak(startup_msg, "happy"))
    except Exception as e:
        print(f"顯示模型信息失敗: {e}")
    
    return pet

def start_ai_mode():
    """啟動 AI 模式（舊版兼容）"""
    print("進入 start_ai_mode")
    pet = Pet()
    print("Pet 建立完成")
    pet.show()
    print("Pet show 完成")
    ai = DoroAIChat(pet)
    print("DoroAIChat 建立完成")
    return pet

def start_basic_mode():
    """啟動基本模式"""
    try:
        print("正在啟動基本模式...")
        
        # 創建基本版本的桌寵類
        class BasicPet(QtWidgets.QLabel):
            """基本桌寵（不包含AI功能）"""
            
            def __init__(self):
                super().__init__()
                from config import PetConfig
                from animation import AnimationManager
                from calculator import CalculatorHelper
                from physics import PhysicsEngine
                from say import SpeechBubble
                
                self.config = PetConfig()
                self._setup_window()
                
                # 初始化基本功能模組
                character_folder = os.path.join(os.path.dirname(__file__), "character")
                self.animation_manager = AnimationManager(character_folder)
                self.calculator_helper = CalculatorHelper(self)
                self.physics_engine = PhysicsEngine(self)
                self.bubble = SpeechBubble(theme="blue")
                
                # 狀態變量
                self.dragging = False
                self.drag_offset = QtCore.QPoint()
                self.face_right = True
                self.is_thinking = False
                
                # 設置初始狀態
                self._setup_initial_state()
                self._create_tray()
            
            def _setup_window(self):
                """設置窗口屬性"""
                self.setWindowTitle(self.config.APP_NAME + " (基本模式)")
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
                self.physics_engine.set_initial_position()
                self.animation_manager.switch_animation("walk")
                self.physics_engine.vx = self.config.SPEED_WALK if self.face_right else -self.config.SPEED_WALK
                
                # 啟動物理更新計時器
                self.timer = QtCore.QTimer(self)
                self.timer.timeout.connect(self._update_tick)
                self.timer.start(self.config.FPS)
            
            def _update_tick(self):
                """主要更新循環"""
                self.physics_engine.update_physics()
                current_movie = self.animation_manager.current_movie
                if current_movie and current_movie != self.movie():
                    self.setMovie(current_movie)
                    current_movie.start()
            
            def paintEvent(self, e):
                """繪製事件"""
                p = QtGui.QPainter(self)
                p.setRenderHint(QtGui.QPainter.Antialiasing)

                current_movie = self.animation_manager.current_movie
                if current_movie:
                    frame = current_movie.currentPixmap()
                    if not frame.isNull():
                        need_flip = (self.face_right != self.config.SOURCE_FACES_RIGHT)
                        if need_flip:
                            frame = frame.transformed(QtGui.QTransform().scale(-1, 1))
                        p.drawPixmap(self.rect(), frame)
                else:
                    p.setBrush(QtGui.QColor(255, 182, 193, 220))
                    p.setPen(QtCore.Qt.NoPen)
                    r = self.rect().adjusted(8, 8, -8, -8)
                    p.drawEllipse(r)
            
            def ai_speak(self, text: str, emotion_override: str = None):
                """基本說話方法"""
                if emotion_override:
                    anim_type = emotion_override
                else:
                    anim_type = self.animation_manager.analyze_text_emotion(text)
                
                self.animation_manager.switch_animation(anim_type)
                theme = "blue"  # 基本模式使用藍色主題
                self.bubble.say(text, self.pos(), theme=theme)
                
                QtCore.QTimer.singleShot(5000, 
                                       lambda: self.animation_manager.switch_animation("idle"))
            
            def mousePressEvent(self, e):
                if e.button() == QtCore.Qt.LeftButton:
                    self.dragging = True
                    self.drag_offset = e.globalPos() - self.frameGeometry().topLeft()
                    self.physics_engine.start_dragging()
                    e.accept()
            
            def mouseMoveEvent(self, e):
                if self.dragging:
                    self.move(e.globalPos() - self.drag_offset)
                    e.accept()
            
            def mouseReleaseEvent(self, e):
                if e.button() == QtCore.Qt.LeftButton and self.dragging:
                    self.dragging = False
                    self.physics_engine.stop_dragging()
                    e.accept()
            
            def mouseDoubleClickEvent(self, e):
                greetings = [
                    ("人～你好！", "happy"),
                    ("有什麼事嗎？", "think"),
                    ("Doro在這裡～", "happy"),
                    ("想要升級到AI模式嗎？", "think")
                ]
                text, emotion = random.choice(greetings)
                self.ai_speak(text, emotion)
                e.accept()
            
            def _show_context_menu(self, pos):
                """顯示右鍵選單（基本版）"""
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
                
                current_behavior = self.animation_manager.current_behavior
                
                for behavior, display_name in behavior_names.items():
                    if behavior in self.animation_manager.movies:
                        action = behavior_menu.addAction(display_name)
                        if behavior == current_behavior:
                            action.setText("✓ " + display_name)
                        behavior_actions[action] = behavior
                
                menu.addSeparator()
                
                # 其他功能
                act_say = menu.addAction("說一句…")
                act_calc = menu.addAction("🧮 計算器助手")
                
                menu.addSeparator()
                
                # 設置選項
                act_grav = menu.addAction(
                    "關閉重力" if self.physics_engine.gravity_enabled else "開啟重力"
                )
                act_wander = menu.addAction(
                    "暫停移動" if self.physics_engine.wander_enabled else "恢復移動"
                )
                act_top = menu.addAction(
                    "取消置頂" if self.windowFlags() & QtCore.Qt.WindowStaysOnTopHint else "置頂顯示"
                )
                
                menu.addSeparator()
                
                # AI 升級提示
                act_ai_info = menu.addAction("💡 升級到 AI 模式")
                
                menu.addSeparator()
                act_quit = menu.addAction("退出")
                
                # 處理選單選擇
                chosen = menu.exec_(self.mapToGlobal(pos))
                if chosen is None:
                    return
                
                # 行為切換
                if chosen in behavior_actions:
                    behavior = behavior_actions[chosen]
                    self.animation_manager.switch_animation(behavior)
                    if behavior == "walk" and self.physics_engine.wander_enabled:
                        self.physics_engine.vx = self.config.SPEED_WALK if self.face_right else -self.config.SPEED_WALK
                    elif behavior == "sleep":
                        self.physics_engine.vx = 0
                        self.physics_engine.vy = 0
                
                elif chosen == act_say:
                    text, ok = QtWidgets.QInputDialog.getText(self, "讓桌寵說話", "內容：")
                    if ok and text.strip():
                        self.ai_speak(text.strip())
                
                elif chosen == act_calc:
                    try:
                        expression = self.calculator_helper.open_calculator_dialog(self)
                        if expression:
                            self.calculator_helper.calculate_with_system_calculator(expression)
                    except Exception as e:
                        self.ai_speak(f"計算器功能出錯：{e}", "sad")
                
                elif chosen == act_grav:
                    self.physics_engine.toggle_gravity()
                
                elif chosen == act_wander:
                    self.physics_engine.toggle_wander()
                
                elif chosen == act_top:
                    flags = self.windowFlags()
                    if flags & QtCore.Qt.WindowStaysOnTopHint:
                        self.setWindowFlags(flags & ~QtCore.Qt.WindowStaysOnTopHint)
                    else:
                        self.setWindowFlags(flags | QtCore.Qt.WindowStaysOnTopHint)
                    self.show()
                
                elif chosen == act_ai_info:
                    _, missing_deps = check_ai_dependencies()
                    if missing_deps:
                        info_text = f"升級到 AI 模式需要：\n\n安裝命令：\npip install {' '.join(missing_deps)}\n\n安裝後重新啟動程式即可使用 AI 功能！"
                    else:
                        info_text = "AI 依賴已安裝！\n\n請確保有 test.json 設定檔，\n然後重新啟動程式選擇 AI 模式。"
                    
                    QtWidgets.QMessageBox.information(self, "升級到 AI 模式", info_text)
                
                elif chosen == act_quit:
                    QtWidgets.QApplication.quit()
            
            def _create_tray(self):
                """創建系統托盤"""
                if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
                    return
                
                # 簡單圖標
                pix = QtGui.QPixmap(64, 64)
                pix.fill(QtCore.Qt.transparent)
                p = QtGui.QPainter(pix)
                p.setRenderHint(QtGui.QPainter.Antialiasing)
                p.setBrush(QtGui.QColor(255, 182, 193))
                p.setPen(QtCore.Qt.NoPen)
                p.drawEllipse(4, 4, 56, 56)
                p.end()
                
                self.tray = QtWidgets.QSystemTrayIcon(QtGui.QIcon(pix), self)
                
                menu = QtWidgets.QMenu()
                act_show = menu.addAction("顯示/置前")
                act_hide = menu.addAction("隱藏")
                menu.addSeparator()
                act_quit = menu.addAction("退出")
                
                act_show.triggered.connect(lambda: (self.show(), self.raise_(), self.activateWindow()))
                act_hide.triggered.connect(self.hide)
                act_quit.triggered.connect(QtWidgets.QApplication.quit)
                
                self.tray.setContextMenu(menu)
                self.tray.setToolTip(self.config.APP_NAME + " (基本模式)")
                self.tray.show()
        
        # 創建基本桌寵
        pet = BasicPet()
        pet.show()
        
        # 顯示歡迎訊息
        welcome_messages = [
            ("人～Doro 來了！", "happy"),
            ("基本模式啟動成功～", "happy"),
            ("想要更多功能可以升級到 AI 模式哦～", "think")
        ]
        text, emotion = random.choice(welcome_messages)
        QtCore.QTimer.singleShot(1000, lambda: pet.ai_speak(text, emotion))
        
        print("🎮 基本模式已啟動")
        print("💡 右鍵點擊可以升級到 AI 模式")
        
        return pet
        
    except Exception as e:
        QtWidgets.QMessageBox.critical(
            None, "啟動失敗", f"基本模式啟動失敗：{e}"
        )
        return None

class AsyncHelper(QtCore.QObject):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self._loop_thread = None

    def start_loop(self):
        self._loop_thread = QtCore.QThread()
        self._loop_thread.run = self._run_loop
        self._loop_thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop_loop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self._loop_thread:
            self._loop_thread.quit()
            self._loop_thread.wait()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # 初始化異步處理
        self.loop = asyncio.new_event_loop()
        self.async_helper = AsyncHelper(self.loop)
        self.async_helper.start_loop()

    def run_coroutine(self, coro):
        """執行異步協程"""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    def closeEvent(self, event):
        if hasattr(self, 'async_helper'):
            self.async_helper.stop_loop()
        event.accept()

def main():
    """主函數"""
    app = setup_application()
    
    # 顯示整合模型選擇的啟動對話框
    mode, model_info = show_startup_dialog_with_model_selector()
    
    if mode is None:
        print("用戶取消啟動")
        return
    
    # 根據選擇啟動對應模式
    try:
        if mode == "ai":
            if model_info:
                pet = start_ai_mode_with_model(model_info)
            else:
                pet = start_ai_mode()  # 兼容舊版
        elif mode == "basic":
            pet = start_basic_mode()
        else:
            print("未知的啟動模式")
            return
        
        if pet is None:
            print("啟動失敗")
            return
        
        # 顯示使用提示
        model_info_text = ""
        if mode == "ai" and model_info:
            model_info_text = f"\n當前模型: {model_info['display_name']} ({model_info['provider'].upper()})"
        
        print(f"""
=== Doro Desktop Pet ===
模式：{mode.upper()}{model_info_text}
🦊 桌寵已啟動！

操作提示：
- 雙擊桌寵：隨機說話
- 拖拽桌寵：移動位置  
- 右鍵選單：更多功能
- 系統托盤：顯示/隱藏控制

按 Ctrl+C 退出
========================
""")

        # 啟動應用程式
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"啟動失敗: {e}")
        import traceback
        traceback.print_exc()
        return

import traceback

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("主程式發生例外：", e)
        traceback.print_exc()
        input("按 Enter 結束...")

def ai_worker():
    try:
        # 原本的 AI 回應流程
        ...
    except Exception as e:
        print("AI 執行緒發生例外：", e)
        import traceback
        traceback.print_exc()