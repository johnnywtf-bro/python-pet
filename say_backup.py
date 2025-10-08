# -*- coding: utf-8 -*-
"""
Doro Desktop Pet - 對話泡泡模組
可主題化的遊戲式對話框
"""
from PyQt5 import QtCore, QtGui, QtWidgets

class SpeechBubble(QtWidgets.QWidget):
    """可主題化的遊戲式對話框（圓角 + 彩色外框 + 尾巴 + 陰影）"""
    
    THEMES = {
        "blue":   {
            "fill": QtGui.QColor(245, 248, 255, 235), 
            "border": QtGui.QColor(60, 120, 255), 
            "text": QtGui.QColor(20, 30, 60)
        },
        "green":  {
            "fill": QtGui.QColor(242, 255, 245, 235), 
            "border": QtGui.QColor(50, 170, 100), 
            "text": QtGui.QColor(15, 50, 25)
        },
        "pink":   {
            "fill": QtGui.QColor(255, 245, 250, 235), 
            "border": QtGui.QColor(230, 95, 145), 
            "text": QtGui.QColor(70, 25, 40)
        },
        "yellow": {
            "fill": QtGui.QColor(255, 252, 230, 235), 
            "border": QtGui.QColor(220, 170, 30), 
            "text": QtGui.QColor(70, 55, 15)
        },
        "gray":   {
            "fill": QtGui.QColor(248, 248, 250, 235), 
            "border": QtGui.QColor(120, 120, 140), 
            "text": QtGui.QColor(35, 35, 45)
        },
    }

    def __init__(self, parent=None, theme="blue"):
        super().__init__(parent)
        
        # 窗口設置
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Tool |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        
        # 樣式屬性
        self._text = ""
        self._theme = theme
        self._radius = 12
        self._border_w = 3
        self._padding = QtCore.QMargins(14, 12, 14, 14)  # 內容留白
        self._tail_side = "right"  # "left" 或 "right"
        self._tail_size = QtCore.QSize(16, 12)  # 尾巴寬、高
        self._tail_offset = 18  # 尾巴與上邊距離
        self._font = QtGui.QFont("Microsoft JhengHei", 11)
        self._shadow_pad = 10   # 陰影內縮，避免越界

        # 自動隱藏計時器
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.hide)
        self.timer.setSingleShot(True)
        
        self.hide()

    def set_theme(self, name: str):
        """設置主題"""
        if name in self.THEMES:
            self._theme = name
            self.update()

    def say(self, text: str, at: QtCore.QPoint, ms: int = 2200, theme: str = None, tail_side: str = None):
        """顯示對話泡泡
        
        Args:
            text: 要顯示的文字
            at: 顯示位置（通常是桌寵的位置）
            ms: 顯示持續時間（毫秒）
            theme: 主題名稱
            tail_side: 尾巴方向（"left" 或 "right"）
        """
        # 更新主題和尾巴方向
        if theme:
            self.set_theme(theme)
        if tail_side in ("left", "right"):
            self._tail_side = tail_side

        # 設置文字並重新佈局
        self._text = text
        self._relayout()

        # 計算顯示位置
        pos = self._calculate_position(at)
        
        # 確保位置在螢幕範圍內
        pos = self._clamp_to_screen(pos)
        
        # 顯示泡泡
        self.move(pos.x(), pos.y())
        self.show()
        self.raise_()
        
        # 設置自動隱藏
        self.timer.start(ms)

    def _calculate_position(self, pet_pos: QtCore.QPoint) -> QtCore.QPoint:
        """計算對話泡泡的顯示位置"""
        # 預設顯示在桌寵上方稍微偏移的位置
        offset_x = 20 if self._tail_side == "right" else -20
        offset_y = -self.height() - 10
        
        return QtCore.QPoint(
            pet_pos.x() + offset_x, 
            pet_pos.y() + offset_y
        )

    def _clamp_to_screen(self, pos: QtCore.QPoint) -> QtCore.QPoint:
        """將位置限制在螢幕範圍內"""
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        
        x = max(screen.left(), min(pos.x(), screen.right() - self.width()))
        y = max(screen.top(), min(pos.y(), screen.bottom() - self.height()))
        
        return QtCore.QPoint(x, y)

    def _relayout(self):
        """重新計算大小"""
        # 測量文字大小
        fm = QtGui.QFontMetrics(self._font)
        text_rect = fm.boundingRect(
            QtCore.QRect(0, 0, 380, 10000),
            QtCore.Qt.TextWordWrap, 
            self._text
        )
        
        # 計算氣泡大小
        w = text_rect.width() + self._padding.left() + self._padding.right() + self._tail_size.width()
        h = text_rect.height() + self._padding.top() + self._padding.bottom()
        
        # 加上陰影空間
        w += self._shadow_pad * 2
        h += self._shadow_pad * 2
        
        self.resize(w, h)

    def paintEvent(self, e: QtGui.QPaintEvent):
        """繪製事件"""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setClipRect(self.rect())  # 防止越界繪製

        # 獲取主題顏色
        colors = self.THEMES[self._theme]
        fill = colors["fill"]
        border = colors["border"] 
        textc = colors["text"]

        # 計算主體區域
        body_rect = self.rect().adjusted(
            self._shadow_pad, self._shadow_pad, 
            -self._shadow_pad, -self._shadow_pad
        )
        
        if self._tail_side == "right":
            body_rect.adjust(0, 0, -self._tail_size.width(), 0)
        else:
            body_rect.adjust(self._tail_size.width(), 0, 0, 0)

        # 創建主體路徑
        path = self._create_bubble_path(body_rect)

        # 繪製陰影
        self._draw_shadow(p, path)

        # 繪製主體
        p.setPen(QtGui.QPen(border, self._border_w))
        p.setBrush(fill)
        p.drawPath(path)

        # 繪製文字
        self._draw_text(p, body_rect, textc)

    def _create_bubble_path(self, body_rect: QtCore.QRect) -> QtGui.QPainterPath:
        """創建氣泡形狀路徑"""
        # 主體圓角矩形
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(body_rect), self._radius, self._radius)

        # 尾巴
        tail_path = self._create_tail_path(body_rect)
        path = path.united(tail_path)

        return path

    def _create_tail_path(self, body_rect: QtCore.QRect) -> QtGui.QPainterPath:
        """創建尾巴路徑"""
        tail_h = self._tail_size.height()
        tail_w = self._tail_size.width()
        top_y = body_rect.top() + self._tail_offset
        
        if self._tail_side == "right":
            tail_points = [
                QtCore.QPointF(body_rect.right(), top_y + tail_h * 0.2),
                QtCore.QPointF(body_rect.right() + tail_w, top_y + tail_h * 0.5),
                QtCore.QPointF(body_rect.right(), top_y + tail_h * 0.8),
            ]
        else:
            tail_points = [
                QtCore.QPointF(body_rect.left(), top_y + tail_h * 0.2),
                QtCore.QPointF(body_rect.left() - tail_w, top_y + tail_h * 0.5),
                QtCore.QPointF(body_rect.left(), top_y + tail_h * 0.8),
            ]
        
        tail = QtGui.QPolygonF(tail_points)
        tail_path = QtGui.QPainterPath()
        tail_path.addPolygon(tail)
        
        return tail_path

    def _draw_shadow(self, painter: QtGui.QPainter, path: QtGui.QPainterPath):
        """繪製陰影"""
        shadow_path = QtGui.QPainterPath(path)
        transform = QtGui.QTransform()
        transform.translate(0, 2)
        shadow_path = transform.map(shadow_path)
        
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 60))
        painter.drawPath(shadow_path)

    def _draw_text(self, painter: QtGui.QPainter, body_rect: QtCore.QRect, text_color: QtGui.QColor):
        """繪製文字"""
        text_rect = QtCore.QRect(body_rect)
        text_rect.adjust(
            self._padding.left(), self._padding.top(),
            -self._padding.right(), -self._padding.bottom()
        )
        
        painter.setPen(text_color)
        painter.setFont(self._font)
        painter.drawText(
            text_rect, 
            QtCore.Qt.TextWordWrap | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, 
            self._text
        )