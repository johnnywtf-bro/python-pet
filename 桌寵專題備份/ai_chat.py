# -*- coding: utf-8 -*-
"""
Doro Desktop Pet - AI聊天系統整合模組
修復異步調用問題
"""
import threading
import queue
import time
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from pathlib import Path
from PyQt5 import QtCore

# AI 依賴檢查
try:
    import ollama
    AI_DEPS_AVAILABLE = True
except ImportError:
    AI_DEPS_AVAILABLE = False

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MemoryItem:
    """記憶項目資料類別"""
    text: str
    timestamp: str
    memory_type: str = "short"  # "short" 或 "long"

class AIMemorySystem:
    def __init__(self, 
                 short_term_file="short_term_memory.json", 
                 long_term_file="long_term_memory.json",
                 prompt_file="test.json",
                 max_short_term_items=50,
                 chat_model="qwen2.5:7b"):
        
        # 使用絕對路徑，確保在任何位置都能找到檔案
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.short_term_file = os.path.join(self.base_path, short_term_file)
        self.long_term_file = os.path.join(self.base_path, long_term_file)
        self.prompt_file = os.path.join(self.base_path, prompt_file)
        
        self.max_short_term_items = max_short_term_items
        self.chat_model = chat_model
        
        # 載入記憶
        self.short_term_memory = self._load_json_file(self.short_term_file, [])
        self.long_term_memory = self._load_json_file(self.long_term_file, [])
        self.prompt_config = self._load_prompt_config()
        
        print("記憶系統初始化完成")
    
    def _load_json_file(self, filepath: str, default_value: any) -> any:
        """載入 JSON 檔案，如果檔案不存在則建立""" #如果test在就用，沒有用default
        try:
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(default_value, f, ensure_ascii=False, indent=2)
                return default_value
                
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"載入檔案失敗 {filepath}: {e}")
            return default_value
            
    def _save_json_file(self, filepath: str, data: any):
        """儲存資料到 JSON 檔案"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"儲存檔案失敗 {filepath}: {e}")
            
    def _load_prompt_config(self) -> Dict:
        """載入角色設定""" 
        default_config = { #最基礎的預設值，怕裂開，prompt_file是自訂用的，default_config是沒test.json時用的
            "character_name": "Doro",
            "character_prompt": "你是一隻可愛的桌寵，名字叫 Doro。你很活潑開朗，喜歡和人互動。",
            "system_prompt": "請用活潑可愛的語氣回答，句尾常常會加上「～」。回答要簡短，每次回應不要超過 30 個字。",
            "greeting": "人～你好！"
        }
        return self._load_json_file(self.prompt_file, default_config)
        
    def add_memory(self, text: str, memory_type: str = "short"):
        """新增記憶"""
        memory = {
            "text": text,
            "timestamp": str(datetime.now()),
            "memory_type": memory_type
        }
        
        if memory_type == "short":
            self.short_term_memory.append(memory)
            if len(self.short_term_memory) > self.max_short_term_items:
                self.short_term_memory.pop(0)
            self._save_json_file(self.short_term_file, self.short_term_memory)
        else:
            self.long_term_memory.append(memory)
            self._save_json_file(self.long_term_file, self.long_term_memory)
            
    def add_to_short_term_memory(self, text: str, role: str = "user", 
                                name: str = None, emotion: str = None,
                                action: str = None, thought: str = None):
        """向短期記憶添加內容（支持完整對話內容）"""
        memory_text = text
        if name:
            memory_text = f"[{name}] {memory_text}"
        if emotion:
            memory_text = f"{memory_text} (情緒: {emotion})"
        if action:
            memory_text = f"{memory_text} [動作: {action}]"
        if thought:
            memory_text = f"{memory_text} {{想法: {thought}}}"
            
        self.add_memory(memory_text, memory_type="short")
    
    def add_to_long_term_memory(self, text: str, role: str = "user",
                               name: str = None, emotion: str = None,
                               action: str = None, thought: str = None):
        """向長期記憶添加內容（支持完整對話內容）"""
        memory_text = text
        if name:
            memory_text = f"[{name}] {memory_text}"
        if emotion:
            memory_text = f"{memory_text} (情緒: {emotion})"
        if action:
            memory_text = f"{memory_text} [動作: {action}]"
        if thought:
            memory_text = f"{memory_text} {{想法: {thought}}}"
            
        self.add_memory(memory_text, memory_type="long")

    def stream_response(self, prompt: str) -> str:
        """同步串流處理回應 - 修復版本"""
        try:
            import ollama
            client = ollama.Client()
            response = ""
            
            # 建構完整的提示詞
            full_prompt = self._build_full_prompt(prompt)
            
            stream = client.chat(
                model=self.chat_model,
                messages=[{"role": "user", "content": full_prompt}],
                stream=True
            )
            
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    response += chunk['message']['content']
            
            # 儲存對話記錄
            self.add_to_short_term_memory(prompt, role="user")
            self.add_to_short_term_memory(response, role="assistant")
            
            return response
            
        except Exception as e:
            print(f"生成回應失敗: {e}")
            return "抱歉，我現在說不出話來..."
    
    def _build_full_prompt(self, user_input: str) -> str:
        """建構完整的提示詞"""
        try:
            # 取得角色設定
            character_prompt = self.prompt_config.get("character_prompt", "")
            system_prompt = self.prompt_config.get("system_prompt", "")
            
            # 取得最近的對話歷史
            recent_history = self.get_conversation_history(limit=3)
            
            # 組合提示詞
            full_prompt = f"""角色設定: {character_prompt}

回應規則: {system_prompt}

最近對話:
{recent_history}

用戶說: {user_input}

請回應:"""
            
            return full_prompt
            
        except Exception as e:
            print(f"建構提示詞失敗: {e}")
            return user_input
            
    def get_conversation_history(self, limit: int = 5) -> str:
        """取得對話歷史"""
        recent_memories = self.get_recent_memories(limit)
        return "\n".join(recent_memories) if recent_memories else ""
    
    def get_recent_memories(self, limit: int = 5) -> List[str]:
        """取得最近的記憶"""
        memories = self.short_term_memory[-limit:]
        return [m["text"] for m in memories]
        
    def search_memories(self, query: str) -> List[str]:
        """搜尋相關記憶（簡單文字匹配）"""
        results = []
        for memory in self.short_term_memory + self.long_term_memory:
            if query.lower() in memory["text"].lower():
                results.append(memory["text"])
        return results[:5]  # 返回最相關的前 5 筆

    def get_memory_stats(self) -> dict:
        """取得記憶統計"""
        return {
            "short_term_count": len(self.short_term_memory),
            "long_term_count": len(self.long_term_memory),
            "total_count": len(self.short_term_memory) + len(self.long_term_memory)
        }
    
    def clear_short_term_memory(self):
        """清除短期記憶"""
        self.short_term_memory = []
        self._save_json_file(self.short_term_file, self.short_term_memory)
    
    def backup_memories(self):
        """備份記憶"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(self.base_path, "memory_backup")
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        short_backup = os.path.join(backup_dir, f"short_term_{timestamp}.json")
        long_backup = os.path.join(backup_dir, f"long_term_{timestamp}.json")
        
        self._save_json_file(short_backup, self.short_term_memory)
        self._save_json_file(long_backup, self.long_term_memory)


class DoroAIChat:
    """Doro AI 聊天整合類"""
    
    def __init__(self, pet_instance=None):
        self.pet = pet_instance
        self.ai_memory = None
        self.response_queue = queue.Queue()
        self.is_thinking = False
        
        # 在背景初始化 AI 系統
        self._initialize_ai_system()
    
    def _initialize_ai_system(self):
        """在背景初始化 AI 系統"""
        def init_ai():
            try:
                print("正在初始化 Doro AI 系統...")
                if self.pet:
                    self.pet.show_thinking()
                
                # 檢查 AI 依賴
                if not AI_DEPS_AVAILABLE:
                    print("AI 依賴不可用")
                    if self.pet:
                        self.pet.hide_thinking()
                        self.pet.ai_speak("人...Doro還沒學會聰明的說話呢～", "sad")
                    return
                
                # 使用 test.json 作為配置檔案
                self.ai_memory = AIMemorySystem(
                    prompt_file="test.json",
                    chat_model="qwen2.5:7b"
                )
                
                print("Doro AI 系統初始化完成！")
                
                if self.pet:
                    self.pet.hide_thinking()
                    # 顯示啟動訊息
                    startup_msg = self.ai_memory.prompt_config.get(
                        "startup_message", 
                        "人！Doro 跑過來了～要陪我一起玩嗎？"
                    )
                    self.pet.ai_speak(startup_msg, "happy")
                
            except Exception as e:
                print(f"AI 系統初始化失敗: {e}")
                if self.pet:
                    self.pet.hide_thinking()
                    self.pet.ai_speak("嗚...AI 系統啟動失敗了", "sad")
                    import traceback
                    traceback.print_exc()
        
        # 在背景執行緒中初始化
        init_thread = threading.Thread(target=init_ai, daemon=True)
        init_thread.start()
    
    def is_ai_ready(self) -> bool:
        """檢查 AI 系統是否準備就緒"""
        return self.ai_memory is not None and AI_DEPS_AVAILABLE
    
    def chat_with_ai(self, user_input: str):
        """與 AI 進行對話 - 修復版本"""
        if not self.is_ai_ready():
            if self.pet:
                self.pet.ai_speak("人...Doro 還在學習中，等等再來找我玩吧～", "think")
            return
        
        if self.is_thinking:
            if self.pet:
                self.pet.ai_speak("人～等等，Doro 還在想上一個問題呢！", "think")
            return
        
        # 開始思考
        self.is_thinking = True
        if self.pet:
            self.pet.show_thinking()
        
        # 在背景處理 AI 回應
        def process_ai_response():
            try:
                # 直接調用同步版本的 stream_response
                response = self.ai_memory.stream_response(user_input)
                
                # 將回應放入佇列
                self.response_queue.put(('success', response))
                
            except Exception as e:
                print(f"AI 處理失敗: {e}")
                self.response_queue.put(('error', str(e)))
        
        # 啟動處理執行緒
        response_thread = threading.Thread(target=process_ai_response, daemon=True)
        response_thread.start()
        
        # 啟動計時器檢查回應
        self._start_response_timer()
    
    def _start_response_timer(self):
        """啟動計時器檢查 AI 回應"""
        def check_response():
            try:
                result_type, result_data = self.response_queue.get_nowait()
                self.is_thinking = False
                if self.pet:
                    self.pet.hide_thinking()
                    
                if result_type == 'success':
                    self.pet.ai_speak(result_data)
                elif result_type == 'error':
                    self.pet.ai_speak(f"嗚嗚...出錯了: {result_data}", "sad")
                    
            except queue.Empty:
                if self.is_thinking:
                    # 繼續檢查
                    QtCore.QTimer.singleShot(500, check_response)
                else:
                    if self.pet:
                        self.pet.hide_thinking()
                        self.pet.ai_speak("人...Doro 想太久了，腦袋打結了", "think")
            except Exception as e:
                self.is_thinking = False
                if self.pet:
                    self.pet.hide_thinking()
                    self.pet.ai_speak(f"處理出錯了: {e}", "sad")

        # 第一次啟動
        QtCore.QTimer.singleShot(500, check_response)
    
    def get_ai_stats(self) -> dict:
        """獲得 AI 系統統計資訊"""
        if not self.is_ai_ready():
            return {"status": "not_ready"}
        
        try:
            stats = self.ai_memory.get_memory_stats()
            stats["status"] = "ready"
            stats["character_name"] = self.ai_memory.prompt_config.get("character_name", "Doro")
            return stats
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def clear_ai_memory(self):
        """清除 AI 記憶"""
        if not self.is_ai_ready():
            if self.pet:
                self.pet.ai_speak("人...還沒準備好呢", "think")
            return
        
        try:
            self.ai_memory.clear_short_term_memory()
            if self.pet:
                clear_msg = self.ai_memory.prompt_config.get(
                    "greeting_after_clear", 
                    "Doro 又來到你身邊了～我們可以重新開始玩耍！"
                )
                self.pet.ai_speak(clear_msg, "happy")
        except Exception as e:
            if self.pet:
                self.pet.ai_speak(f"清除記憶失敗: {e}", "sad")
    
    def backup_ai_memories(self):
        """備份 AI 記憶"""
        if not self.is_ai_ready():
            if self.pet:
                self.pet.ai_speak("人...還沒準備好呢", "think")
            return
        
        try:
            self.ai_memory.backup_memories()
            if self.pet:
                self.pet.ai_speak("記憶已經安全備份了！", "happy")
        except Exception as e:
            if self.pet:
                self.pet.ai_speak(f"備份失敗: {e}", "sad")
    
    def get_character_info(self) -> dict:
        """獲得角色資訊"""
        if not self.is_ai_ready():
            return {"name": "Doro", "status": "loading"}
        
        config = self.ai_memory.prompt_config
        return {
            "name": config.get("character_name", "Doro"),
            "greeting": config.get("greeting", "人～你好！"),
            "system_prompt": config.get("system_prompt", ""),
            "status": "ready"
        }