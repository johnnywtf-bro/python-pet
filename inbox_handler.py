# inbox_handler.py
"""
Inbox 處理模組 - 桌寵啟動時讀取並處理從 Godot 世界提取的 Agent 資料
"""
import json
import pathlib
from typing import Optional, Dict
from datetime import datetime

# Inbox 檔案位置（與 extract_api.py 保持一致）
INBOX = pathlib.Path.home() / ".deskpet" / "inbox.json"


class InboxData:
    """Inbox 資料結構"""
    def __init__(self, data: Dict):
        self.from_world = data.get("from_world", False)
        self.agent_id = data.get("agent_id", 0)
        self.name = data.get("name", "Unknown")
        self.state = data.get("state", {})
        self.position = data.get("position", {})
        self.time = data.get("time", "")
        self.memory = data.get("memory", "")
        self.extracted_at = data.get("extracted_at", "")


def read_inbox() -> Optional[InboxData]:
    """
    讀取 inbox 檔案
    
    返回:
        InboxData: 如果有資料則返回，否則返回 None
    """
    if not INBOX.exists():
        return None
    
    try:
        with open(INBOX, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 讀取後立即刪除（防止重複處理）
        INBOX.unlink(missing_ok=True)
        print(f"✅ 已讀取並清除 inbox: {data.get('name', 'Unknown')}")
        
        return InboxData(data)
    
    except Exception as e:
        print(f"❌ 讀取 inbox 失敗: {e}")
        return None


def bootstrap_memory_from_inbox(ai_chat_instance):
    """從 inbox 啟動記憶系統"""
    print("=" * 50)
    print("🔍 [DEBUG] bootstrap_memory_from_inbox 開始執行")
    print("=" * 50)
    
    # 讀取 inbox
    inbox_data = read_inbox()
    
    if not inbox_data:
        print("📭 Inbox 為空，正常啟動")
        return
    
    print(f"✅ 成功讀取 inbox: {inbox_data.name}")
    
    if not inbox_data.from_world:
        print("⚠️ Inbox 資料格式不正確")
        return
    
    print(f"🌍 檢測到從世界提取的 Agent: {inbox_data.name}")
    
    # 檢查 AI 系統是否就緒
    is_ready = ai_chat_instance.is_ai_ready()
    print(f"🔍 [DEBUG] AI 系統就緒狀態: {is_ready}")
    
    if not is_ready:
        print("⚠️ AI 系統尚未就緒，無法處理 inbox")
        return
    
    try:
        memory = ai_chat_instance.ai_memory
        
        # 1. 添加基本提取資訊到短期記憶
        extract_note = f"我剛從一個叫做「世界」的地方被提取出來。我的名字是 {inbox_data.name}。"
        memory.add_to_short_term_memory(extract_note, role="system")
        print(f"💭 已添加提取記憶")
        
        # 2. 添加位置資訊（如果有）
        if inbox_data.position:
            x = inbox_data.position.get("x", 0)
            y = inbox_data.position.get("y", 0)
            position_note = f"在世界裡，我最後的位置是 ({x:.1f}, {y:.1f})。"
            memory.add_to_short_term_memory(position_note, role="system")
            print(f"📍 已添加位置記憶: ({x:.1f}, {y:.1f})")
        
        # 3. 添加時間資訊（如果有）
        if inbox_data.time:
            time_note = f"在世界裡的時間是: {inbox_data.time}。"
            memory.add_to_short_term_memory(time_note, role="system")
            print(f"⏰ 已添加時間記憶")
        
        # 4. 添加狀態資訊（如果有）
        if inbox_data.state:
            state_json = json.dumps(inbox_data.state, ensure_ascii=False)
            state_note = f"我在世界裡的狀態資料: {state_json}"
            memory.add_to_short_term_memory(state_note, role="system")
            print(f"📊 已添加狀態記憶")
        
        # 5. 添加額外記憶（如果有）
        if inbox_data.memory:
            memory_note = f"我在世界裡的記憶: {inbox_data.memory}"
            memory.add_to_short_term_memory(memory_note, role="system")
            print(f"🧠 已添加世界記憶")
        
        # 6. 讓桌寵說話（如果有 pet 實例）
        if hasattr(ai_chat_instance, 'pet') and ai_chat_instance.pet:
            greeting = f"人～我從另一個世界來的！我叫 {inbox_data.name}。"
            if inbox_data.memory:
                greeting += f"\n我還記得...{inbox_data.memory[:50]}..."
            
            ai_chat_instance.pet.ai_speak(greeting, "happy")
            print(f"💬 桌寵已問候")
        
        print("✅ Inbox 資料已成功整合到記憶系統")
        
    except Exception as e:
        print(f"❌ 整合 inbox 資料失敗: {e}")
        import traceback
        traceback.print_exc()


def check_inbox_exists() -> bool:
    """檢查 inbox 是否存在"""
    return INBOX.exists()


def clear_inbox():
    """清空 inbox（測試用）"""
    if INBOX.exists():
        INBOX.unlink()
        print("🗑️ Inbox 已清空")
        return True
    return False