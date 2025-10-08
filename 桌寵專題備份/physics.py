# -*- coding: utf-8 -*-
"""
Doro Desktop Pet - 物理引擎模組
負責處理桌寵的移動、碰撞和物理行為
"""
from PyQt5 import QtWidgets
from config import PetConfig

class PhysicsEngine:
    """物理引擎類"""
    
    def __init__(self, pet_instance):
        self.pet = pet_instance
        self.config = PetConfig()
        
        # 速度向量
        self.vx = 0.0  # 水平速度
        self.vy = 0.0  # 垂直速度
        
        # 物理屬性
        self.gravity_enabled = True
        self.wander_enabled = True
        
        # 螢幕邊界
        self.floor_y = None
        self._update_screen_bounds()
    
    def _update_screen_bounds(self):
        """更新螢幕邊界"""
        screen = QtWidgets.QApplication.primaryScreen()
        geo = screen.availableGeometry()
        
        self.ground = geo.bottom() - self.config.PET_HEIGHT - self.config.BOUNDARY_MARGIN
        self.left_bound = geo.left() + self.config.BOUNDARY_MARGIN
        self.right_bound = geo.right() - self.config.PET_WIDTH - self.config.BOUNDARY_MARGIN
        self.top_bound = geo.top() + self.config.BOUNDARY_MARGIN
    
    def set_initial_position(self):
        """設置初始位置（螢幕右下角）"""
        screen = QtWidgets.QApplication.primaryScreen()
        geo = screen.availableGeometry()
        
        x = geo.right() - self.config.PET_WIDTH - self.config.BOUNDARY_OFFSET_X
        y = geo.bottom() - self.config.PET_HEIGHT - self.config.BOUNDARY_OFFSET_Y
        
        self.floor_y = y
        self.pet.move(x, y)
        return x, y
    
    def update_physics(self):
        """更新物理狀態"""
        if self.pet.dragging:
            return
        
        # 更新螢幕邊界（應對多螢幕或縮放變化）
        self._update_screen_bounds()
        
        # 重力
        if self.gravity_enabled:
            self.vy += self.config.GRAVITY
        
        # 根據行為模式處理水平移動
        self._handle_behavior_movement()
        
        # 更新位置
        self._update_position()
    
    def _handle_behavior_movement(self):
        """根據行為模式處理移動"""
        current_behavior = self.pet.animation_manager.get_current_behavior()
        behavior_setting = self.config.behavior_settings.get(current_behavior, {})
        
        if current_behavior == "walk" and self.wander_enabled:
            # 行走模式：保持移動
            if abs(self.vx) < 0.1:
                self.vx = self.config.SPEED_WALK if self.pet.face_right else -self.config.SPEED_WALK
        else:
            # 其他模式：根據設定進行速度衰減
            decay_speed = behavior_setting.get("decay_speed", 0.95)
            if decay_speed == 0.0:  # sleep模式完全停止
                self.vx = 0
            else:
                self.vx *= decay_speed
    
    def _update_position(self):
        """更新位置並處理碰撞"""
        # 計算新位置
        new_x = self.pet.x() + int(self.vx)
        new_y = self.pet.y() + int(self.vy)
        
        # 地面碰撞
        if new_y >= self.ground:
            new_y = self.ground
            self.vy = 0.0
            # 地面摩擦（非walk模式時）
            if self.pet.animation_manager.get_current_behavior() != "walk":
                self.vx *= self.config.FRICTION
        
        # 左右邊界碰撞
        if new_x <= self.left_bound:
            new_x = self.left_bound
            self.vx = abs(self.vx)
            self.pet.face_right = True
        elif new_x >= self.right_bound:
            new_x = self.right_bound
            self.vx = -abs(self.vx)
            self.pet.face_right = False
        
        # 頂部邊界碰撞
        if new_y <= self.top_bound:
            new_y = self.top_bound
            if self.vy < 0:
                self.vy = 0
        
        # 移動到新位置
        self.pet.move(new_x, new_y)
    
    def start_dragging(self):
        """開始拖拽時停止所有速度"""
        self.vx = 0.0
        self.vy = 0.0
    
    def stop_dragging(self):
        """停止拖拽時恢復速度"""
        current_behavior = self.pet.animation_manager.get_current_behavior()
        if current_behavior == "walk" and self.wander_enabled:
            self.vx = self.config.SPEED_WALK if self.pet.face_right else -self.config.SPEED_WALK
    
    def toggle_gravity(self):
        """切換重力狀態"""
        self.gravity_enabled = not self.gravity_enabled
        return self.gravity_enabled
    
    def toggle_wander(self):
        """切換閒逛狀態"""
        self.wander_enabled = not self.wander_enabled
        if not self.wander_enabled:
            self.vx = 0  # 停止移動
        elif self.pet.animation_manager.get_current_behavior() == "walk":
            # 恢復移動
            self.vx = self.config.SPEED_WALK if self.pet.face_right else -self.config.SPEED_WALK
        return self.wander_enabled
    
    def get_physics_info(self):
        """獲得物理狀態信息"""
        return {
            "velocity": {"x": self.vx, "y": self.vy},
            "position": {"x": self.pet.x(), "y": self.pet.y()},
            "gravity_enabled": self.gravity_enabled,
            "wander_enabled": self.wander_enabled,
            "face_right": self.pet.face_right
        }