# model_selector_ui.py
# -*- coding: utf-8 -*-
"""
模型選擇器 UI 界面
提供圖形化的模型切換功能
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from llm_adapter import llm_adapter
from llm_config import config_manager

class ModelSelectorDialog(QtWidgets.QDialog):
    """模型選擇對話框"""
    
    model_changed = QtCore.pyqtSignal(str)  # 模型切換信號
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🤖 LLM 模型選擇器")
        self.setFixedSize(500, 400)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        
        self.setup_ui()
        self.load_models()
        self.setup_connections()
    
    def setup_ui(self):
        """設置 UI 界面"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # 標題
        title = QtWidgets.QLabel("選擇 LLM 模型")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # 當前模型顯示
        self.current_model_label = QtWidgets.QLabel()
        self.current_model_label.setStyleSheet("""
            background-color: #e8f5e8;
            border: 2px solid #4CAF50;
            border-radius: 8px;
            padding: 10px;
            margin: 5px;
        """)
        layout.addWidget(self.current_model_label)
        
        # 模型分組
        tab_widget = QtWidgets.QTabWidget()
        
        # Ollama 模型頁
        ollama_widget = QtWidgets.QWidget()
        ollama_layout = QtWidgets.QVBoxLayout(ollama_widget)
        
        self.ollama_list = QtWidgets.QListWidget()
        self.ollama_list.setStyleSheet("""
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ddd;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #f0f0f0;
            }
        """)
        ollama_layout.addWidget(self.ollama_list)
        
        # Ollama 狀態
        self.ollama_status = QtWidgets.QLabel("檢查中...")
        ollama_layout.addWidget(self.ollama_status)
        
        tab_widget.addTab(ollama_widget, "🐋 Ollama 模型")
        
        # Lemonade 模型頁
        lemonade_widget = QtWidgets.QWidget()
        lemonade_layout = QtWidgets.QVBoxLayout(lemonade_widget)
        
        self.lemonade_list = QtWidgets.QListWidget()
        self.lemonade_list.setStyleSheet("""
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ddd;
            }
            QListWidget::item:selected {
                background-color: #FF9800;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #f0f0f0;
            }
        """)
        lemonade_layout.addWidget(self.lemonade_list)
        
        # Lemonade 狀態
        self.lemonade_status = QtWidgets.QLabel("檢查中...")
        lemonade_layout.addWidget(self.lemonade_status)
        
        tab_widget.addTab(lemonade_widget, "🍋 Lemonade 模型")
        
        layout.addWidget(tab_widget)
        
        # 按鈕區域
        button_layout = QtWidgets.QHBoxLayout()
        
        self.test_button = QtWidgets.QPushButton("🧪 測試連接")
        self.test_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        
        self.switch_button = QtWidgets.QPushButton("✅ 切換模型")
        self.switch_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #2e7d2e;
            }
        """)
        
        self.close_button = QtWidgets.QPushButton("❌ 關閉")
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #a01308;
            }
        """)
        
        button_layout.addWidget(self.test_button)
        button_layout.addWidget(self.switch_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        # 狀態顯示區域
        self.status_label = QtWidgets.QLabel("準備就緒")
        self.status_label.setStyleSheet("""
            color: #666;
            padding: 5px;
            background-color: #f9f9f9;
            border-radius: 3px;
        """)
        layout.addWidget(self.status_label)
    
    def setup_connections(self):
        """設置信號連接"""
        self.test_button.clicked.connect(self.test_model)
        self.switch_button.clicked.connect(self.switch_model)
        self.close_button.clicked.connect(self.close)
        
        self.ollama_list.itemDoubleClicked.connect(self.switch_model)
        self.lemonade_list.itemDoubleClicked.connect(self.switch_model)
    
    def load_models(self):
        """載入模型列表"""
        try:
            # 更新當前模型顯示
            current_model = llm_adapter.get_current_model_info()
            self.current_model_label.setText(
                f"當前模型: {current_model['display_name']}\n"
                f"提供商: {current_model['provider'].upper()}\n"
                f"API 地址: {current_model['api_base']}"
            )
            
            # 清空列表
            self.ollama_list.clear()
            self.lemonade_list.clear()
            
            # 載入模型
            models = llm_adapter.get_available_models()
            
            for model in models:
                item_text = f"{model['display_name']}"
                if model['is_current']:
                    item_text += " (當前)"
                
                item = QtWidgets.QListWidgetItem(item_text)
                item.setData(QtCore.Qt.UserRole, model['name'])  # 存儲模型名稱
                
                # 設置圖標和樣式
                if model['is_current']:
                    item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                
                if model['provider'] == 'ollama':
                    self.ollama_list.addItem(item)
                elif model['provider'] == 'lemonade':
                    self.lemonade_list.addItem(item)
            
            # 更新狀態
            self.update_provider_status()
            
        except Exception as e:
            self.status_label.setText(f"載入模型失敗: {e}")
            self.status_label.setStyleSheet("color: red;")
    
    def update_provider_status(self):
        """更新提供商狀態"""
        try:
            status = config_manager.get_provider_status()
            
            # 更新 Ollama 狀態
            ollama_status = status.get('ollama', '未知')
            if ollama_status == '可用':
                self.ollama_status.setText("✅ Ollama 服務正常")
                self.ollama_status.setStyleSheet("color: green;")
            else:
                self.ollama_status.setText("❌ Ollama 服務不可用")
                self.ollama_status.setStyleSheet("color: red;")
            
            # 更新 Lemonade 狀態
            lemonade_status = status.get('lemonade', '未知')
            if lemonade_status == '可用':
                self.lemonade_status.setText("✅ Lemonade 服務正常")
                self.lemonade_status.setStyleSheet("color: green;")
            else:
                self.lemonade_status.setText("❌ Lemonade 服務不可用")
                self.lemonade_status.setStyleSheet("color: red;")
                
        except Exception as e:
            self.ollama_status.setText(f"狀態檢查失敗: {e}")
            self.lemonade_status.setText(f"狀態檢查失敗: {e}")
    
    def get_selected_model(self) -> str:
        """獲取選中的模型"""
        # 檢查 Ollama 列表
        current_ollama = self.ollama_list.currentItem()
        if current_ollama:
            return current_ollama.data(QtCore.Qt.UserRole)
        
        # 檢查 Lemonade 列表
        current_lemonade = self.lemonade_list.currentItem()
        if current_lemonade:
            return current_lemonade.data(QtCore.Qt.UserRole)
        
        return None
    
    def test_model(self):
        """測試模型連接"""
        selected_model = self.get_selected_model()
        if not selected_model:
            QtWidgets.QMessageBox.warning(self, "警告", "請先選擇一個模型")
            return
        
        self.status_label.setText("正在測試連接...")
        self.status_label.setStyleSheet("color: blue;")
        QtWidgets.QApplication.processEvents()
        
        try:
            result = llm_adapter.test_model_connection(selected_model)
            
            if result["success"]:
                self.status_label.setText("✅ 連接測試成功")
                self.status_label.setStyleSheet("color: green;")
                
                # 顯示測試結果
                QtWidgets.QMessageBox.information(
                    self, "測試成功", 
                    f"{result['message']}\n\n回應預覽:\n{result['response_preview']}"
                )
            else:
                self.status_label.setText("❌ 連接測試失敗")
                self.status_label.setStyleSheet("color: red;")
                
                QtWidgets.QMessageBox.critical(
                    self, "測試失敗", 
                    f"模型連接失敗:\n{result['error']}"
                )
                
        except Exception as e:
            self.status_label.setText(f"測試出錯: {e}")
            self.status_label.setStyleSheet("color: red;")
    
    def switch_model(self):
        """切換模型"""
        selected_model = self.get_selected_model()
        if not selected_model:
            QtWidgets.QMessageBox.warning(self, "警告", "請先選擇一個模型")
            return
        
        # 確認切換
        reply = QtWidgets.QMessageBox.question(
            self, "確認切換", 
            f"確定要切換到模型 '{selected_model}' 嗎？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply != QtWidgets.QMessageBox.Yes:
            return
        
        try:
            success = llm_adapter.switch_model(selected_model)
            
            if success:
                self.status_label.setText("✅ 模型切換成功")
                self.status_label.setStyleSheet("color: green;")
                
                # 發射信號
                self.model_changed.emit(selected_model)
                
                # 重新載入模型列表以更新當前模型顯示
                self.load_models()
                
                QtWidgets.QMessageBox.information(
                    self, "切換成功", 
                    f"已成功切換到模型: {selected_model}"
                )
            else:
                self.status_label.setText("❌ 模型切換失敗")
                self.status_label.setStyleSheet("color: red;")
                
                QtWidgets.QMessageBox.critical(
                    self, "切換失敗", 
                    "模型切換失敗，請檢查模型是否可用"
                )
                
        except Exception as e:
            self.status_label.setText(f"切換出錯: {e}")
            self.status_label.setStyleSheet("color: red;")
            QtWidgets.QMessageBox.critical(self, "錯誤", f"切換模型時出錯:\n{e}")


class ModelSelectorWidget(QtWidgets.QWidget):
    """簡化的模型選擇器小部件（可嵌入其他界面）"""
    
    model_changed = QtCore.pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_models()
    
    def setup_ui(self):
        """設置簡化的 UI"""
        layout = QtWidgets.QHBoxLayout(self)
        
        # 模型選擇下拉框
        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.setMinimumWidth(200)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        
        # 切換按鈕
        self.switch_btn = QtWidgets.QPushButton("切換")
        self.switch_btn.clicked.connect(self.switch_model)
        
        # 設置按鈕（打開完整對話框）
        self.settings_btn = QtWidgets.QPushButton("⚙️")
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.clicked.connect(self.open_settings)
        
        layout.addWidget(QtWidgets.QLabel("模型:"))
        layout.addWidget(self.model_combo)
        layout.addWidget(self.switch_btn)
        layout.addWidget(self.settings_btn)
    
    def load_models(self):
        """載入模型到下拉框"""
        self.model_combo.clear()
        
        models = llm_adapter.get_available_models()
        for model in models:
            display_text = f"{model['display_name']}"
            if model['is_current']:
                display_text += " (當前)"
            
            self.model_combo.addItem(display_text, model['name'])
            
            # 設置當前選中項
            if model['is_current']:
                self.model_combo.setCurrentIndex(self.model_combo.count() - 1)
    
    def on_model_changed(self):
        """模型選擇改變時"""
        pass
    
    def switch_model(self):
        """切換模型"""
        current_data = self.model_combo.currentData()
        if current_data:
            success = llm_adapter.switch_model(current_data)
            if success:
                self.model_changed.emit(current_data)
                self.load_models()  # 重新載入以更新顯示
    
    def open_settings(self):
        """打開完整的設置對話框"""
        dialog = ModelSelectorDialog(self)
        dialog.model_changed.connect(self.model_changed)
        dialog.exec_()
        self.load_models()  # 對話框關閉後重新載入