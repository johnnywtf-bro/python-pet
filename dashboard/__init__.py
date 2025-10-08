# dashboard/__init__.py
"""
Dashboard 模組
"""

try:
    from .main_dashboard import DashboardWindow
    from .event_bus import bus
    from .models import DB
    
    # 導入頁面模組
    from .pages.page_status import StatusPage
    from .pages.page_inventory import InventoryPage
    from .pages.page_shop import ShopPage
    from .pages.page_animations import AnimationsPage
    from .pages.page_tasks import TasksPage
    
    __all__ = [
        'DashboardWindow', 'bus', 'DB',
        'StatusPage', 'InventoryPage', 'ShopPage', 'AnimationsPage', 'TasksPage'
    ]
    
    print("✅ Dashboard 模組載入成功")
    
except ImportError as e:
    print(f"⚠️  Dashboard 模組部分載入失敗: {e}")
    
    # 嘗試載入核心組件
    try:
        from .main_dashboard import DashboardWindow
        from .event_bus import bus
        __all__ = ['DashboardWindow', 'bus']
        print("✅ Dashboard 核心組件載入成功")
    except ImportError as e2:
        print(f"❌ Dashboard 核心組件載入失敗: {e2}")
        __all__ = []
