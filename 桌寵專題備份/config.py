# -*- coding: utf-8 -*-
"""
Doro Desktop Pet - 設定檔模組
包含所有設定相關的常數和配置
"""

import os
import sys
from PyQt5 import QtCore

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