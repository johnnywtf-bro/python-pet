# startup_ui_with_model_selector.py
# -*- coding: utf-8 -*-
"""
Doro Desktop Pet - 啟動界面整合模型選擇器
"""

from PyQt5 import QtCore, QtGui, QtWidgets
import sys

class ModelSelectorComboBox(QtWidgets.QComboBox):
    """模型選擇下拉框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 2px solid #FFB6C1;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: #333;
            }
            QComboBox:hover {
                border-color: #FF69B4;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 8px solid #FF69B4;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 2px solid #FFB6C1;
                border-radius: 4px;
                selection-background-color: #FFE4E1;
                color: #333;
                font-size: 14px;
            }
        """)
        
        self.load_models()
    
    def load_models(self):
        """載入可用模型"""
        self.clear()
        
        # 檢查服務可用性並添加模型
        models_info = self.get_available_models_with_status()
        
        for model_info in models_info:
            display_text = f"{model_info['display_name']}"
            if not model_info['available']:
                display_text += " (服務不可用)"
            
            self.addItem(display_text, model_info)
            
            # 如果服務不可用，禁用該項目
            if not model_info['available']:
                item = self.model().item(self.count() - 1)
                item.setEnabled(False)
                item.setForeground(QtGui.QColor(150, 150, 150))
    
    def get_available_models_with_status(self):
        """獲取模型列表並檢查服務狀態"""
        models = []
        
        # 檢查 Ollama 服務
        ollama_available = self.check_ollama_service()
        
        # 檢查 Lemonade 服務
        lemonade_available = self.check_lemonade_service()
        
        # NPU 模型 (Lemonade)
        models.extend([
            {
                'name': 'Qwen-2.5-7B-Instruct-NPU',
                'display_name': '🚀 Qwen 2.5 7B NPU (推薦)',
                'provider': 'lemonade',
                'available': lemonade_available,
                'priority': 1
            },
            {
                'name': 'Qwen-2.5-1.5B-Instruct-NPU',
                'display_name': '⚡ Qwen 2.5 1.5B NPU (快速)',
                'provider': 'lemonade',
                'available': lemonade_available,
                'priority': 2
            }
        ])
        
        # Ollama 模型
        models.extend([
            {
                'name': 'qwen2.5:7b',
                'display_name': '🐋 Qwen 2.5 7B (Ollama)',
                'provider': 'ollama',
                'available': ollama_available,
                'priority': 3
            },
            {
                'name': 'qwen2.5:1.5b',
                'display_name': '🐋 Qwen 2.5 1.5B (Ollama)',
                'provider': 'ollama',
                'available': ollama_available,
                'priority': 4
            }
        ])
        
        # 按優先級和可用性排序
        models.sort(key=lambda x: (0 if x['available'] else 1, x['priority']))
        
        return models
    
    def check_ollama_service(self):
        """檢查 Ollama 服務是否可用"""
        try:
            import requests
            response = requests.get("http://127.0.0.1:11434/api/version", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def check_lemonade_service(self):
        """檢查 Lemonade 服務是否可用"""
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                return True
            # 嘗試模型列表端點
            response = requests.get("http://localhost:8000/api/v1/models", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_selected_model(self):
        """獲取選中的模型信息"""
        current_data = self.currentData()
        return current_data if current_data and current_data.get('available', False) else None


class StartupDialog(QtWidgets.QDialog):
    """啟動對話框 - 整合模型選擇"""
    
    mode_selected = QtCore.pyqtSignal(str, dict)  # (mode, model_info)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🦊 Doro Desktop Pet")
        self.setFixedSize(400, 500)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowCloseButtonHint)
        
        # 設置窗口圖標和樣式
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFE4E1, stop:1 #FFF0F5);
                border-radius: 15px;
            }
            QLabel {
                color: #FF69B4;
                font-weight: bold;
            }
            QPushButton {
                background-color: #FFB6C1;
                border: none;
                border-radius: 12px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
                color: white;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #FF69B4;
                transform: scale(1.05);
            }
            QPushButton:pressed {
                background-color: #FF1493;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        """設置界面"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 標題
        title_label = QtWidgets.QLabel("🦊 Doro Desktop Pet")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #FF69B4;
            margin-bottom: 10px;
        """)
        layout.addWidget(title_label)
        
        # 副標題
        subtitle_label = QtWidgets.QLabel("選擇啟動模式")
        subtitle_label.setAlignment(QtCore.Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            font-size: 16px;
            color: #DB7093;
            margin-bottom: 20px;
        """)
        layout.addWidget(subtitle_label)
        
        # 模型選擇區域
        model_group = QtWidgets.QGroupBox("🤖 AI 模型選擇")
        model_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #FF69B4;
                border: 2px solid #FFB6C1;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: #FFF0F5;
            }
        """)
        
        model_layout = QtWidgets.QVBoxLayout(model_group)
        
        # 模型選擇下拉框
        self.model_selector = ModelSelectorComboBox()
        model_layout.addWidget(self.model_selector)
        
        # 狀態提示
        self.status_label = QtWidgets.QLabel()
        self.status_label.setStyleSheet("""
            color: #666;
            font-size: 12px;
            margin-top: 5px;
        """)
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        model_layout.addWidget(self.status_label)
        
        layout.addWidget(model_group)
        
        # 模式選擇按鈕
        mode_group = QtWidgets.QGroupBox("🎮 選擇啟動模式")
        mode_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #FF69B4;
                border: 2px solid #FFB6C1;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: #FFF0F5;
            }
        """)
        
        mode_layout = QtWidgets.QVBoxLayout(mode_group)
        
        # AI 模式按鈕
        self.ai_mode_btn = QtWidgets.QPushButton("🤖 AI 模式")
        self.ai_mode_btn.clicked.connect(lambda: self.select_mode("ai"))
        mode_layout.addWidget(self.ai_mode_btn)
        
        # 基本模式按鈕
        self.basic_mode_btn = QtWidgets.QPushButton("🎮 基本模式")
        self.basic_mode_btn.clicked.connect(lambda: self.select_mode("basic"))
        mode_layout.addWidget(self.basic_mode_btn)
        
        layout.addWidget(mode_group)
        
        # 底部信息
        info_label = QtWidgets.QLabel("AI 模式需要選擇可用的模型")
        info_label.setAlignment(QtCore.Qt.AlignCenter)
        info_label.setStyleSheet("""
            color: #999;
            font-size: 11px;
            font-style: italic;
        """)
        layout.addWidget(info_label)
        
        # 連接信號
        self.model_selector.currentTextChanged.connect(self.on_model_changed)
        
        # 初始狀態更新
        self.on_model_changed()
    
    def on_model_changed(self):
        """模型選擇改變時的處理"""
        selected_model = self.model_selector.get_selected_model()
        
        if selected_model and selected_model['available']:
            if selected_model['provider'] == 'lemonade':
                self.status_label.setText("✅ NPU 加速模式 - 高效能推理")
                self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            else:
                self.status_label.setText("✅ 標準模式 - 穩定可靠")
                self.status_label.setStyleSheet("color: #2196F3; font-weight: bold;")
            
            # 啟用 AI 模式按鈕
            self.ai_mode_btn.setEnabled(True)
            self.ai_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFB6C1;
                    border: none;
                    border-radius: 12px;
                    padding: 15px;
                    font-size: 16px;
                    font-weight: bold;
                    color: white;
                    min-height: 20px;
                }
                QPushButton:hover {
                    background-color: #FF69B4;
                }
            """)
        else:
            self.status_label.setText("⚠️ 請選擇可用的模型")
            self.status_label.setStyleSheet("color: #f44336;")
            
            # 禁用 AI 模式按鈕
            self.ai_mode_btn.setEnabled(False)
            self.ai_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ccc;
                    border: none;
                    border-radius: 12px;
                    padding: 15px;
                    font-size: 16px;
                    font-weight: bold;
                    color: #888;
                    min-height: 20px;
                }
            """)
    
    def select_mode(self, mode):
        """選擇模式"""
        selected_model = None
        
        if mode == "ai":
            selected_model = self.model_selector.get_selected_model()
            if not selected_model:
                QtWidgets.QMessageBox.warning(
                    self, 
                    "無法啟動", 
                    "請選擇一個可用的 AI 模型才能啟動 AI 模式"
                )
                return
        
        # 發送信號並關閉對話框
        self.mode_selected.emit(mode, selected_model or {})
        self.accept()


# 整合到主程式的使用示例
class DoroMainWindow(QtWidgets.QMainWindow):
    """主窗口示例"""
    
    def __init__(self):
        super().__init__()
        self.selected_model = None
        self.show_startup_dialog()
    
    def show_startup_dialog(self):
        """顯示啟動對話框"""
        dialog = StartupDialog(self)
        dialog.mode_selected.connect(self.on_mode_selected)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.initialize_pet()
        else:
            # 用戶取消，退出程序
            QtWidgets.QApplication.quit()
    
    def on_mode_selected(self, mode, model_info):
        """模式選擇回調"""
        print(f"選擇的模式: {mode}")
        if model_info:
            print(f"選擇的模型: {model_info['display_name']} ({model_info['provider']})")
            self.selected_model = model_info
        
        # 在這裡可以根據選擇的模型初始化 LLM 配置
        if mode == "ai" and model_info:
            self.init_llm_config(model_info)
    
    def init_llm_config(self, model_info):
        """初始化 LLM 配置"""
        try:
            # 設置選中的模型為當前模型
            from llm_config import config_manager
            success = config_manager.switch_model(model_info['name'])
            if success:
                print(f"✅ 已設置模型: {model_info['display_name']}")
            else:
                print(f"⚠️ 模型設置失敗: {model_info['name']}")
        except ImportError:
            print("LLM 配置模組不可用")
        except Exception as e:
            print(f"LLM 配置初始化失敗: {e}")
    
    def initialize_pet(self):
        """初始化桌寵"""
        # 這裡是您的桌寵初始化代碼
        print("🦊 Doro 桌寵啟動中...")
        
        # 根據選擇的模型顯示不同的啟動信息
        if self.selected_model:
            if self.selected_model['provider'] == 'lemonade':
                print("🚀 使用 NPU 加速模式")
            else:
                print("🐋 使用 Ollama 標準模式")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    # 設置應用圖標和樣式
    app.setApplicationName("Doro Desktop Pet")
    
    window = DoroMainWindow()
    
    sys.exit(app.exec_())