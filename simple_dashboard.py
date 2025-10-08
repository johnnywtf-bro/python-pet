# simple_dashboard.py
# -*- coding: utf-8 -*-
"""
簡單儀表板 - 當完整版儀表板不可用時的降級方案
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class SimpleDashboard(QMainWindow):
    """簡單儀表板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Doro Desktop Pet - 簡單控制面板")
        self.setGeometry(200, 200, 600, 400)
        
        self.setup_ui()
        print("✅ 簡單儀表板初始化完成")
    
    def setup_ui(self):
        """設置 UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 標題
        title = QLabel("🐱 Doro Desktop Pet 控制面板")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                margin: 20px;
                padding: 10px;
            }
        """)
        layout.addWidget(title)
        
        # 狀態區域
        status_group = QGroupBox("桌寵狀態")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("狀態: 正常運行中")
        self.behavior_label = QLabel("當前行為: 閒置")
        self.position_label = QLabel("位置: (100, 100)")
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.behavior_label) 
        status_layout.addWidget(self.position_label)
        
        layout.addWidget(status_group)
        
        # 控制按鈕區域
        control_group = QGroupBox("控制操作")
        control_layout = QGridLayout(control_group)
        
        # 行為控制按鈕
        behaviors = [
            ("閒置", "idle"),
            ("行走", "walk"),
            ("睡覺", "sleep"),
            ("思考", "think"),
            ("開心", "happy"),
            ("傷心", "sad")
        ]
        
        for i, (name, behavior) in enumerate(behaviors):
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, b=behavior: self.change_behavior(b))
            btn.setStyleSheet("""
                QPushButton {
                    padding: 8px;
                    font-size: 12px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background-color: #f0f0f0;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """)
            control_layout.addWidget(btn, i // 3, i % 3)
        
        layout.addWidget(control_group)
        
        # 功能按鈕
        function_group = QGroupBox("功能操作")
        function_layout = QHBoxLayout(function_group)
        
        ocr_btn = QPushButton("截圖識別")
        ocr_btn.clicked.connect(self.trigger_ocr)
        
        voice_btn = QPushButton("語音聊天")
        voice_btn.clicked.connect(self.toggle_voice)
        
        function_layout.addWidget(ocr_btn)
        function_layout.addWidget(voice_btn)
        
        layout.addWidget(function_group)
        
        layout.addStretch()
        
        # 設置整體樣式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 8px;
                margin: 5px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
    
    def change_behavior(self, behavior):
        """改變行為"""
        print(f"請求改變行為到: {behavior}")
        self.behavior_label.setText(f"當前行為: {behavior}")
        
        # 如果有父組件（桌寵），嘗試調用其方法
        parent_window = self.parent()
        if parent_window and hasattr(parent_window, 'set_behavior'):
            parent_window.set_behavior(behavior)
    
    def trigger_ocr(self):
        """觸發 OCR"""
        print("觸發 OCR 功能")
        
    def toggle_voice(self):
        """切換語音"""
        print("切換語音聊天")
    
    def switch_to_style(self, style):
        """風格切換（兼容性方法）"""
        print(f"簡單儀表板不支援風格切換，當前請求: {style}")
        return False
