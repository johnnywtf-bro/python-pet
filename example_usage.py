# -*- coding: utf-8 -*-
"""
Doro Desktop Pet - 使用範例
展示如何與桌寵進行交互和整合 AI 聊天系統
"""
import sys
import time
from PyQt5 import QtCore, QtWidgets
from main import setup_application
from pet import Pet
from config import PetConfig

class DoroAIIntegration:
    """Doro AI 整合範例"""
    
    def __init__(self):
        self.pet = Pet()
        self.pet.show()
        
        # 模擬 AI 對話的計時器
        self.demo_timer = QtCore.QTimer()
        self.demo_timer.timeout.connect(self.run_demo_conversation)
        
    def simulate_ai_thinking(self):
        """模擬 AI 思考過程"""
        self.pet.show_thinking()
        # 模擬思考時間
        QtCore.QTimer.singleShot(2000, self.pet.hide_thinking)
    
    def simulate_ai_response(self, user_input: str):
        """模擬 AI 回應"""
        # 顯示思考
        self.pet.show_thinking()
        
        # 模擬處理時間
        QtCore.QTimer.singleShot(1500, lambda: self._process_response(user_input))
    
    def _process_response(self, user_input: str):
        """處理並回應用戶輸入"""
        self.pet.hide_thinking()
        
        # 簡單的關鍵字回應邏輯
        responses = {
            "哦潤吉": ("人～哦潤吉！🍊 Doro最愛了！", "love_orange"),
            "傷心": ("人...不要傷心，Doro陪你～", "sad"),
            "開心": ("人～一起開心吧！", "happy"),
            "你好": ("人～你好！Doro很高興見到你！", "happy"),
            "再見": ("人...要走了嗎？記得再來找Doro玩～", "sad")
        }
        
        # 找匹配的回應
        response_text = "人～Doro聽到了，但不太懂呢..."
        emotion = "think"
        
        for keyword, (text, emo) in responses.items():
            if keyword in user_input:
                response_text = text
                emotion = emo
                break
        
        # AI 說話
        self.pet.ai_speak(response_text, emotion)
    
    def run_demo_conversation(self):
        """運行示範對話"""
        demo_inputs = [
            "你好",
            "哦潤吉好好吃",
            "今天有點傷心",
            "但是看到你就開心了",
            "再見"
        ]
        
        if hasattr(self, 'demo_index'):
            if self.demo_index < len(demo_inputs):
                user_input = demo_inputs[self.demo_index]
                print(f"用戶: {user_input}")
                self.simulate_ai_response(user_input)
                self.demo_index += 1
            else:
                self.demo_timer.stop()
                print("示範對話結束")
        else:
            self.demo_index = 0
            self.demo_timer.start(4000)  # 每4秒一次對話

def example_basic_usage():
    """基本使用範例"""
    app = setup_application()
    
    # 創建桌寵
    pet = Pet()
    pet.show()
    
    # 基本對話測試
    messages = [
        ("人～Doro來啦！", "happy"),
        ("哦潤吉！🍊", "love_orange"),
        ("今天心情如何呢？", "think"),
        ("有點想睡覺了...", "sad")
    ]
    
    def show_next_message(index=0):
        if index < len(messages):
            text, emotion = messages[index]
            pet.ai_speak(text, emotion)
            QtCore.QTimer.singleShot(3000, lambda: show_next_message(index + 1))
    
    # 延遲開始顯示訊息
    QtCore.QTimer.singleShot(1000, show_next_message)
    
    return app

def example_ai_integration():
    """AI 整合範例"""
    app = setup_application()
    
    # 創建 AI 整合實例
    ai_integration = DoroAIIntegration()
    
    # 歡迎訊息
    QtCore.QTimer.singleShot(1000, lambda: 
        ai_integration.pet.ai_speak("人～準備開始示範對話！", "happy"))
    
    # 開始示範對話
    QtCore.QTimer.singleShot(3000, ai_integration.run_demo_conversation)
    
    return app

def example_manual_control():
    """手動控制範例"""
    app = setup_application()
    
    pet = Pet()
    pet.show()
    
    # 創建控制面板
    control_window = QtWidgets.QWidget()
    control_window.setWindowTitle("Doro 控制面板")
    control_window.resize(300, 200)
    
    layout = QtWidgets.QVBoxLayout(control_window)
    
    # 行為按鈕
    behaviors = ["walk", "idle", "sleep", "think", "happy", "sad", "love_orange"]
    for behavior in behaviors:
        if pet.animation_manager.has_animation(behavior):
            btn = QtWidgets.QPushButton(f"切換到 {behavior}")
            btn.clicked.connect(lambda checked, b=behavior: pet.set_behavior(b))
            layout.addWidget(btn)
    
    # 說話按鈕
    speak_btn = QtWidgets.QPushButton("讓 Doro 說話")
    speak_btn.clicked.connect(lambda: pet.ai_speak("人～這是手動控制的訊息！", "talking"))
    layout.addWidget(speak_btn)
    
    # 狀態信息按鈕
    info_btn = QtWidgets.QPushButton("顯示狀態信息")
    def show_status():
        status = pet.get_status_info()
        print("=== Doro 狀態信息 ===")
        print(f"當前動畫: {status['animation']['current_behavior']}")
        print(f"位置: ({status['ui']['position']['x']}, {status['ui']['position']['y']})")
        print(f"速度: ({status['physics']['velocity']['x']:.2f}, {status['physics']['velocity']['y']:.2f})")
        print(f"重力: {status['physics']['gravity_enabled']}")
        print(f"閒逛: {status['physics']['wander_enabled']}")
        print("==================")
    
    info_btn.clicked.connect(show_status)
    layout.addWidget(info_btn)
    
    control_window.show()
    
    return app

def example_calculator_integration():
    """計算器整合範例"""
    app = setup_application()
    
    pet = Pet()
    pet.show()
    
    # 模擬用戶要求計算
    def simulate_calculation():
        pet.ai_speak("人～要幫你計算嗎？", "think")
        
        # 模擬計算過程
        QtCore.QTimer.singleShot(2000, lambda:
            pet.calculator_helper.calculate_with_system_calculator("2+3*4"))
    
    QtCore.QTimer.singleShot(1000, simulate_calculation)
    
    return app

if __name__ == "__main__":
    print("Doro Desktop Pet 使用範例")
    print("請選擇要運行的範例：")
    print("1. 基本使用")
    print("2. AI 整合")
    print("3. 手動控制") 
    print("4. 計算器整合")
    
    try:
        choice = input("請輸入選項 (1-4): ").strip()
        
        if choice == "1":
            print("運行基本使用範例...")
            app = example_basic_usage()
        elif choice == "2":
            print("運行 AI 整合範例...")
            app = example_ai_integration()
        elif choice == "3":
            print("運行手動控制範例...")
            app = example_manual_control()
        elif choice == "4":
            print("運行計算器整合範例...")
            app = example_calculator_integration()
        else:
            print("無效選項，運行基本使用範例...")
            app = example_basic_usage()
        
        print("桌寵已啟動！按 Ctrl+C 退出。")
        sys.exit(app.exec_())
        
    except KeyboardInterrupt:
        print("\n程式已退出")
    except Exception as e:
        print(f"發生錯誤: {e}")