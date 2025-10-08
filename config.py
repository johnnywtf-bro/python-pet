# config.py
# -*- coding: utf-8 -*-
"""
Doro Desktop Pet - 設定檔模組
包含所有設定相關的常數和配置
"""

import os
import sys
from PyQt5 import QtCore, QtGui

def setup_qt_environment():
    """設定 Qt 環境與插件路徑"""
    # 設定 Qt 插件路徑
    import PyQt5
    qt_path = os.path.dirname(PyQt5.__file__)
    os.environ['QT_PLUGIN_PATH'] = os.path.join(qt_path, 'Qt5', 'plugins')
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(qt_path, 'Qt5', 'plugins', 'platforms')
        
    # 設定 Qt 共享 OpenGL 內容
    if hasattr(QtCore.Qt, 'AA_ShareOpenGLContexts'):
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)

class PetConfig:
    """桌寵設定類"""
    
    # 應用程式基本設定
    APP_NAME = "Doro Desktop Pet"
    SOURCE_FACES_RIGHT = False  # Doro 素材預設朝左
    
    # 物理參數
    GRAVITY = 1.1              # 重力加速度
    FRICTION = 0.85            # 地面摩擦
    SPEED_WALK = 3.2           # 閒逛水平速度
    FPS = 16                   # 畫面更新間隔(ms)
    
    # 桌寵尺寸
    PET_WIDTH = 160
    PET_HEIGHT = 160
    
    # 邊界偏移
    BOUNDARY_OFFSET_X = 40     # 距離螢幕右邊的距離
    BOUNDARY_OFFSET_Y = 20     # 距離螢幕底部的距離
    BOUNDARY_MARGIN = 10       # 邊界碰撞邊距
    
    # GIF 檔案分類
    gif_categories = {
        "walk": ["pet_walk.gif"],
        "idle": ["pet_idle.gif", "doro_idle1.gif", "doro_idle2.gif"],
        "sleep": ["pet_sleep.gif"],
        "think": ["doro_think.gif"],
        "love_orange": ["doro_love_orange.gif"],
        "sad": ["doro_orange.gif"],
        "happy": ["doro_idle1.gif", "doro_idle2.gif"],
        "talking": ["doro_idle1.gif", "doro_idle2.gif", "doro_think.gif"]
    }
    
    # 情感關鍵字
    emotion_keywords = {
        "orange": ["哦潤吉", "orange", "橘子", "🍊"],
        "sad": ["傷心", "難過", "哭", "嗚嗚", "不開心", "失望", "沮喪"],
        "happy": ["開心", "高興", "快樂", "哈哈", "耶", "讚", "棒", "好棒"],
        "think": ["想", "思考", "考慮", "想想", "讓我想想"]
    }
    
    # 對話泡泡主題對應
    bubble_themes = {
        "love_orange": "yellow",
        "sad": "gray",
        "happy": "green",
        "think": "blue",
        "talking": "blue",
        "default": "blue"
    }
    
    # 隨機對話內容
    random_greetings = [
        ("こんにちは~", "happy"),
        ("Hi~", "happy"),
        ("喵？", "talking"),
        ("要摸摸~", "love_orange"),
        ("ヾ(•ω•`)o", "happy"),
        ("人～Doro來了！", "happy"),
        ("哦潤吉！", "love_orange")
    ]
    
    # 計算器相關設定
    calculator_messages = {
        "start": "開始計算: {}",
        "launching": "正在啟動計算器...",
        "complete": "計算完成！請查看計算器窗口",
        "error": "計算出錯: {}"
    }
    
    # 行為狀態設定
    behavior_settings = {
        "walk": {"allow_movement": True, "decay_speed": 1.0},
        "idle": {"allow_movement": False, "decay_speed": 0.95},
        "sleep": {"allow_movement": False, "decay_speed": 0.0},
        "think": {"allow_movement": False, "decay_speed": 0.95},
        "love_orange": {"allow_movement": False, "decay_speed": 0.95},
        "sad": {"allow_movement": False, "decay_speed": 0.95},
        "happy": {"allow_movement": False, "decay_speed": 0.95},
        "talking": {"allow_movement": False, "decay_speed": 0.95}
    }
    
    # 自動回復到idle的時間(毫秒)
    AUTO_RETURN_TO_IDLE_TIME = 3000
    
    # UI 風格設定
    UI_STYLE = "original"              # "original" 或 "win11"
    ALLOW_STYLE_SWITCHING = True       # 是否允許運行時切換風格
    
    # Win11 風格特定設定
    WIN11_BLUR_EFFECT = True           # 是否啟用毛玻璃效果
    WIN11_ANIMATIONS = True            # 是否啟用過渡動畫
    
    # Win11 主題配置（使用 QtGui.QColor 需要在類方法中定義或使用字符串）
    @classmethod
    def get_win11_theme(cls):
        """獲取 Win11 主題配置（動態生成以避免導入錯誤）"""
        return {
            "background": QtGui.QColor(32, 32, 32, 240),    # Win11 暗色背景
            "accent": QtGui.QColor(0, 120, 215),            # Win11 藍色主題
            "text": QtGui.QColor(255, 255, 255),            # 白色文字
            "border_radius": 8,                             # Win11 圓角風格
            "blur_effect": True                             # 毛玻璃效果
        }
    
    # 或者使用字符串格式的顏色配置
    WIN11_THEME_COLORS = {
        "background": "#20202040",      # RGBA 格式
        "accent": "#0078d4",           # 十六進制格式
        "text": "#ffffff",
        "surface": "#2d2d2d",
        "surface_variant": "#3a3a3a",
        "border": "#404040"
    }
    
    # 擴展的對話泡泡主題（包含 Win11 風格）
    @classmethod
    def get_bubble_themes(cls, ui_style="original"):
        """根據 UI 風格獲取對話泡泡主題"""
        if ui_style == "win11":
            return {
                "love_orange": "win11_orange",
                "sad": "win11_gray",
                "happy": "win11_green",
                "think": "win11_blue",
                "talking": "win11_blue",
                "default": "win11_blue"
            }
        else:
            return cls.bubble_themes

# 全局配置實例
config_instance = PetConfig()

# 兼容性函數
def get_config():
    """獲取配置實例"""
    return config_instance

def get_ui_style():
    """獲取當前 UI 風格"""
    return config_instance.UI_STYLE

def set_ui_style(style: str):
    """設置 UI 風格"""
    if style in ["original", "win11"]:
        config_instance.UI_STYLE = style
        return True
    return False