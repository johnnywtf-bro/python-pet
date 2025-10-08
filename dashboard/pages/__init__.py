# dashboard/pages/__init__.py
"""
Dashboard Pages 模組
"""

try:
    from .page_status import StatusPage
    from .page_inventory import InventoryPage
    from .page_shop import ShopPage
    from .page_animations import AnimationsPage
    from .page_tasks import TasksPage
    
    __all__ = ['StatusPage', 'InventoryPage', 'ShopPage', 'AnimationsPage', 'TasksPage']
    
    print("✅ Dashboard Pages 模組載入成功")
    
except ImportError as e:
    print(f"⚠️  Dashboard Pages 模組部分載入失敗: {e}")
    __all__ = []
