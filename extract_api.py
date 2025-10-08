# extract_api.py
"""
Agent 提取 API - 用於接收 Godot 世界的 Agent 資料並啟動桌寵
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import pathlib
from typing import Optional, Dict

# Inbox 檔案位置
INBOX = pathlib.Path.home() / ".deskpet" / "inbox.json"

class ExtractRequest(BaseModel):
    """Agent 提取請求的資料結構"""
    agent_id: int
    name: str
    state: Optional[Dict] = None
    position: Optional[Dict] = None
    time: Optional[str] = None
    memory: Optional[str] = None

class ExtractResponse(BaseModel):
    """提取回應"""
    ok: bool
    message: str
    error: Optional[str] = None

def setup_extract_routes(app: FastAPI):
    """設置提取相關的路由"""
    
    @app.post("/extract", response_model=ExtractResponse)
    async def extract_agent(req: ExtractRequest):
        """接收 Godot 發送的 Agent 資料並保存到 inbox"""
        try:
            # 確保 inbox 目錄存在
            INBOX.parent.mkdir(parents=True, exist_ok=True)
            
            # 準備要寫入的資料
            inbox_data = {
                "from_world": True,
                "agent_id": req.agent_id,
                "name": req.name,
                "state": req.state or {},
                "position": req.position or {},
                "time": req.time or "",
                "memory": req.memory or "",
            }
            
            # 寫入 inbox
            with open(INBOX, "w", encoding="utf-8") as f:
                json.dump(inbox_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Agent '{req.name}' (ID: {req.agent_id}) 已提取到 inbox")
            
            return ExtractResponse(
                ok=True,
                message=f"Agent '{req.name}' 已成功提取"
            )
            
        except Exception as e:
            print(f"❌ 提取失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/extract/status")
    async def check_extract_status():
        """檢查是否有待處理的 Agent 資料"""
        if INBOX.exists():
            try:
                with open(INBOX, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {
                    "has_pending": True,
                    "agent_name": data.get("name", "Unknown"),
                    "agent_id": data.get("agent_id", 0)
                }
            except Exception:
                pass
        
        return {"has_pending": False}