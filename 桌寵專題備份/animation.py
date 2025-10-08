# -*- coding: utf-8 -*-
"""
Doro Desktop Pet - 動畫管理模組
負責載入、管理和切換GIF動畫
"""
import os
import random
from PyQt5 import QtGui
from config import PetConfig

class AnimationManager:
    """動畫管理器"""
    
    def __init__(self, character_folder_path):
        self.character_folder = character_folder_path
        self.config = PetConfig()
        self.movies = {}
        self.current_movie = None
        self.current_behavior = "idle"
        
        self._load_all_gifs()
    
    def _load_all_gifs(self):
        """載入所有 GIF 檔案"""
        for category, filenames in self.config.gif_categories.items():
            self.movies[category] = []
            for filename in filenames:
                filepath = os.path.join(self.character_folder, filename)
                if os.path.exists(filepath):
                    movie = QtGui.QMovie(filepath)
                    movie.setCacheMode(QtGui.QMovie.CacheAll)
                    self.movies[category].append(movie)
                    print(f"載入 GIF: {category} - {filename}")
                else:
                    print(f"找不到檔案: {filepath}")
    
    def get_random_animation(self, category):
        """隨機獲得指定分類的動畫"""
        if category in self.movies and self.movies[category]:
            return random.choice(self.movies[category])
        return None
    
    def switch_animation(self, behavior_type):
        """切換到指定行為的動畫"""
        movie = self.get_random_animation(behavior_type)
        if movie:
            self.current_movie = movie
            self.current_behavior = behavior_type
            print(f"切換動畫到: {behavior_type}")
            return movie
        else:
            print(f"找不到動畫: {behavior_type}")
            return None
    
    def analyze_text_emotion(self, text):
        """分析文字內容，決定要使用的動畫類型"""
        text_lower = text.lower()
        
        # 按優先順序檢查情感
        for emotion, keywords in self.config.emotion_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                # 轉換為對應的動畫類型
                emotion_to_animation = {
                    "orange": "love_orange",
                    "sad": "sad",
                    "happy": "happy",
                    "think": "think"
                }
                return emotion_to_animation.get(emotion, "talking")
        
        # 默認為一般說話
        return "talking"
    
    def get_current_movie(self):
        """獲得當前播放的動畫"""
        return self.current_movie
    
    def get_current_behavior(self):
        """獲得當前行為狀態"""
        return self.current_behavior
    
    def has_animation(self, behavior_type):
        """檢查是否有指定類型的動畫"""
        return behavior_type in self.movies and len(self.movies[behavior_type]) > 0
    
    def get_available_behaviors(self):
        """獲得所有可用的行為類型"""
        return list(self.movies.keys())
    
    def get_animation_count(self, behavior_type):
        """獲得指定行為類型的動畫數量"""
        return len(self.movies.get(behavior_type, []))