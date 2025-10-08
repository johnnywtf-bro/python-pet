# dashboard/event_bus.py
from PyQt5.QtCore import QObject, pyqtSignal

class Bus(QObject):
    stats_changed = pyqtSignal(dict)          # 飽食/好感/等級變動
    item_used     = pyqtSignal(int)           # 使用物品 item_id
    coins_changed = pyqtSignal(int)           # 金幣
    anim_toggled  = pyqtSignal(str, bool)     # 動畫啟停
    log_added     = pyqtSignal(str, str)      # icon, text
    play_anim     = pyqtSignal(str)

bus = Bus()
