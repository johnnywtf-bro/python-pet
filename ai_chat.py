"""
Doro Desktop Pet - AI聊天系統整合模組
修復異步調用問題並增加函數調用功能
整合 Ollama 和 Lemonade SDK 切換功能
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
from plugins_runtime import get_executor
from intent_router import route_input_to_plugin

# 整合新的 LLM 適配器
try:
    from llm_adapter import llm_adapter
    from llm_config import config_manager
    LLM_ADAPTER_AVAILABLE = True
except ImportError:
    print("新的 LLM 適配器不可用，使用舊版本")
    LLM_ADAPTER_AVAILABLE = False

try:
    from say import say 
except Exception:
    def say(x): print(x)

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

@dataclass
class FunctionCall:
    """函數調用結果"""
    function_name: str
    parameters: Dict
    should_execute: bool
    confidence: float

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
        """載入 JSON 檔案，如果檔案不存在則建立"""
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
        default_config = {
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
        """使用新的統一適配器生成回應"""
        try:
            # 如果有新的適配器系統，優先使用
            if LLM_ADAPTER_AVAILABLE:
                # 構建完整提示詞
                full_prompt = self._build_full_prompt(prompt)
                
                # 使用統一適配器
                result = llm_adapter.chat_completion(
                    messages=[{"role": "user", "content": full_prompt}],
                    temperature=0.3
                )
                
                if result["success"]:
                    response = result["content"]
                    
                    # 儲存對話記錄
                    self.add_to_short_term_memory(prompt, role="user")
                    self.add_to_short_term_memory(response, role="assistant")
                    
                    return response
                else:
                    print(f"LLM 適配器調用失敗: {result['error']}")
                    return "抱歉，我現在說不出話來..."
            
            else:
                # 使用舊版本的 ollama 直接調用
                import ollama
                client = ollama.Client()

                # 構建完整提示詞
                full_prompt = self._build_full_prompt(prompt)

                result = client.chat(
                    model=self.chat_model,
                    messages=[{"role": "user", "content": full_prompt}],
                    stream=False
                )

                response = result["message"]["content"]

                # 儲存對話記錄
                self.add_to_short_term_memory(prompt, role="user")
                self.add_to_short_term_memory(response, role="assistant")

                return response

        except Exception as e:
            print(f"生成回應失敗: {e}")
            return "抱歉，我現在說不出話來..."
    
    def _build_full_prompt(self, user_input: str) -> str:
        """構建完整的提示詞"""
        try:
            # 獲得角色設定
            character_prompt = self.prompt_config.get("character_prompt", "")
            system_prompt = self.prompt_config.get("system_prompt", "")
            
            # 獲得最近的對話歷史
            recent_history = self.get_conversation_history(limit=3)
            
            # 獲取當前模型信息（如果可用）
            current_model_info = ""
            if LLM_ADAPTER_AVAILABLE:
                try:
                    current_model = llm_adapter.get_current_model_info()
                    current_model_info = f"\n當前使用模型: {current_model['display_name']} ({current_model['provider']})"
                except:
                    pass
            
            # 組合提示詞
            full_prompt = f"""角色設定: {character_prompt}

回應要求: {system_prompt}{current_model_info}

最近對話:
{recent_history}

用戶說: {user_input}

請回應:"""
            
            return full_prompt
            
        except Exception as e:
            print(f"構建提示詞失敗: {e}")
            return user_input
            
    def get_conversation_history(self, limit: int = 5) -> str:
        """獲得對話歷史"""
        recent_memories = self.get_recent_memories(limit)
        return "\n".join(recent_memories) if recent_memories else ""
    
    def get_recent_memories(self, limit: int = 5) -> List[str]:
        """獲得最近的記憶"""
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
        """獲得記憶統計"""
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


class IntentRecognizer:
    """意圖識別器"""
    
    def __init__(self):
        # 定義意圖模式和對應的函數
        self.intent_patterns = {
            "calculator": {
                "patterns": [
                    r'.*[\d\+\-\*/\(\)\.]+.*',
                    r'.*計算.*',
                    r'.*算.*',
                    r'.*等於.*',
                    r'.*多少.*'
                ],
                "keywords": ["計算", "算", "等於", "數學", "加", "減", "乘", "除", "多少", "+", "-", "*", "/", "×", "÷"],
                "function": "calculate",
                "confidence_threshold": 0.5
            },
            "weather": {
                "patterns": [
                    r'.*天氣.*',
                    r'.*看看天氣.*',
                    r'.*查天氣.*',
                    r'.*天氣怎麼樣',
                    r'.*今天.*天氣',
                    r'.*明天.*天氣',
                    r'.*最近.*天氣',
                    r'.*天氣.*如何',
                    r'.*下雨.*嗎',
                    r'.*溫度.*',
                    r'.*天氣.*資訊',
                    r'.*告訴我.*天氣'
                ],
                "keywords": ["天氣", "看看天氣", "查天氣", "下雨", "溫度", "晴天", "陰天", "氣溫", "今天", "明天", "最近"],
                "function": "get_weather",
                "confidence_threshold": 0.5
            },
            "open_calculator": {
                "patterns": [
                    r".*打開.*計算.*",      # 打開計算機/計算器
                    r".*開啟.*計算.*",      # 開啟計算機/計算器  
                    r".*開.*計算.*",        # 開計算機/計算器
                    r".*計算機.*",          # 直接說計算機
                    r".*計算器.*",          # 直接說計算器
                    r".*calc.*",           # 英文 calc
                    r".*calculator.*"      # 英文 calculator
                ],
                "keywords": [
                    "打開計算機", "開啟計算機", "計算機", "計算器", 
                    "打開計算器", "開啟計算器", "開計算機", "開計算器",
                    "系統計算機", "電腦計算機", "calc", "calculator"
                ],
                "function": "open_calculator",
                "confidence_threshold": 0.4
            },
            # 新增：模型切換相關意圖
            "switch_model": {
                "patterns": [
                    r".*切換.*模型.*",
                    r".*換.*模型.*",
                    r".*模型.*切換.*",
                    r".*改用.*模型.*",
                    r".*使用.*模型.*",
                    r".*改變.*AI.*",
                    r".*更換.*LLM.*"
                ],
                "keywords": ["切換模型", "換模型", "模型切換", "改用模型", "使用模型", "切換AI", "換AI", "LLM", "ollama", "lemonade"],
                "function": "switch_model",
                "confidence_threshold": 0.6
            },
            "show_models": {
                "patterns": [
                    r".*有.*哪些.*模型.*",
                    r".*模型.*列表.*",
                    r".*顯示.*模型.*",
                    r".*查看.*模型.*",
                    r".*可用.*模型.*",
                    r".*當前.*模型.*"
                ],
                "keywords": ["哪些模型", "模型列表", "顯示模型", "查看模型", "可用模型", "當前模型", "現在用", "目前用"],
                "function": "show_models",
                "confidence_threshold": 0.5
            }
        }

    
    def recognize_intent(self, text: str) -> Optional[FunctionCall]:
        """識別用戶意圖並返回函數調用"""
        original_text = text
        text_lower = text.lower()
        
        print(f"[調試] 正在分析文本: '{text}'")
        
        # 特別處理計算機相關的請求
        if any(keyword in text for keyword in ["計算機", "計算器", "calc"]):
            print(f"[調試] 檢測到計算機關鍵詞")
        
        for intent_name, intent_config in self.intent_patterns.items():
            confidence = self._calculate_confidence(text_lower, intent_config)
            print(f"[調試] {intent_name} 信心度: {confidence}")
            
            if confidence >= intent_config["confidence_threshold"]:
                parameters = self._extract_parameters(original_text, intent_name)
                print(f"[調試] 提取的參數: {parameters}")
                
                # 對於 open_calculator 和其他功能，不需要參數也可以執行
                if intent_name in ["open_calculator", "weather", "show_models"] or parameters:
                    print(f"[調試] 準備執行函數調用: {intent_config['function']}")
                    return FunctionCall(
                        function_name=intent_config["function"],
                        parameters=parameters if parameters else {},
                        should_execute=True,
                        confidence=confidence
                    )
        
        print("[調試] 未識別到任何意圖")
        return None
    
    def _calculate_confidence(self, text: str, intent_config: Dict) -> float:
        """計算意圖匹配信心度"""
        pattern_score = 0
        keyword_score = 0
        math_score = 0
        
        # 對天氣功能，不需要數學表達式檢查
        if intent_config["function"] == "calculate" and self._contains_math_expression(text):
            math_score = 0.8
            print(f"[調試] 發現數學表達式，得分: {math_score}")
        
        # 檢查正則模式匹配
        for pattern in intent_config["patterns"]:
            if re.search(pattern, text):
                if intent_config["function"] == "get_weather":
                    pattern_score = max(pattern_score, 0.8)
                elif intent_config["function"] == "open_calculator":
                    pattern_score = max(pattern_score, 0.9)  # 計算機模式給高分
                elif intent_config["function"] in ["switch_model", "show_models"]:
                    pattern_score = max(pattern_score, 0.8)
                else:
                    pattern_score = max(pattern_score, 0.6)
                print(f"[調試] 模式匹配: {pattern} -> 得分: {pattern_score}")
        
        # 檢查關鍵字匹配
        keywords_found = 0
        for keyword in intent_config["keywords"]:
            if keyword in text:
                keywords_found += 1
                print(f"[調試] 找到關鍵字: {keyword}")
        
        if keywords_found > 0:
            if intent_config["function"] == "get_weather":
                keyword_score = min(keywords_found / len(intent_config["keywords"]) * 3, 0.9)
            elif intent_config["function"] == "open_calculator":
                keyword_score = min(keywords_found / len(intent_config["keywords"]) * 4, 0.95)  # 計算機關鍵字給高權重
            elif intent_config["function"] in ["switch_model", "show_models"]:
                keyword_score = min(keywords_found / len(intent_config["keywords"]) * 3, 0.9)
            else:
                keyword_score = min(keywords_found / len(intent_config["keywords"]) * 2, 0.7)
        
        final_score = max(pattern_score, keyword_score, math_score)
        print(f"[調試] 最終得分: 模式={pattern_score}, 關鍵字={keyword_score}, 數學={math_score}, 總分={final_score}")
        
        return final_score
    
    def _contains_math_expression(self, text: str) -> bool:
        """檢查文本是否包含數學表達式"""
        # 尋找數字和運算符的組合
        math_patterns = [
            r'\d+\s*[\+\-\*/]\s*\d+',  # 基本運算：數字 運算符 數字
            r'\d+\s*[×÷]\s*\d+',      # 中文運算符
            r'\d+\s*/\s*\d+',         # 除法
            r'\d+\s*\*\s*\d+',        # 乘法
            r'\d+\s*\+\s*\d+',        # 加法
            r'\d+\s*-\s*\d+',         # 減法
        ]
        
        for pattern in math_patterns:
            if re.search(pattern, text):
                print(f"[調試] 匹配數學模式: {pattern}")
                return True
        
        return False
    
    def _extract_parameters(self, text: str, intent_name: str) -> Dict:
        """從文本中提取參數"""
        if intent_name == "calculator":
            return self._extract_math_expression(text)
        elif intent_name == "weather":
            return self._extract_weather_params(text)
        elif intent_name == "switch_model":
            return self._extract_model_params(text)
        return {}
    
    def _extract_math_expression(self, text: str) -> Dict:
        """提取數學表達式 - 改進版"""
        print(f"[調試] 開始提取數學表達式: {text}")
        
        # 處理中文數學符號
        processed_text = text.replace("乘", "*").replace("除", "/")
        processed_text = processed_text.replace("加", "+").replace("減", "-")
        processed_text = processed_text.replace("×", "*").replace("÷", "/")
        processed_text = processed_text.replace("X", "*").replace("x", "*")  # 常見的乘法表示
        
        print(f"[調試] 處理後文本: {processed_text}")
        
        # 更精確的數學表達式模式
        patterns = [
            r'[\d\+\-\*/\(\)\.\s]+(?=\s*[是等於多少嗎？])',  # 帶結尾詞的表達式
            r'[\d\+\-\*/\(\)\.]+',  # 純數學表達式
            r'\d+[\+\-\*/]\d+',     # 簡單運算
            r'\d+\s*[\+\-\*/]\s*\d+(?:\s*[\+\-\*/]\s*\d+)*',  # 多項運算
        ]
        
        best_expression = ""
        
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, processed_text)
            print(f"[調試] 模式 {i+1} 匹配結果: {matches}")
            
            if matches:
                # 選擇最長且最像數學表達式的匹配
                for match in matches:
                    cleaned_match = match.strip()
                    if len(cleaned_match) > len(best_expression) and self._is_valid_math_expression(cleaned_match):
                        best_expression = cleaned_match
        
        if best_expression:
            print(f"[調試] 最佳表達式: {best_expression}")
            return {"expression": best_expression}
        
        print("[調試] 未找到有效的數學表達式")
        return {}
    
    def _is_valid_math_expression(self, expression: str) -> bool:
        """驗證數學表達式是否有效"""
        try:
            # 簡單驗證：確保包含數字和運算符
            if not re.search(r'\d', expression):  # 必須包含數字
                return False
            if not re.search(r'[\+\-\*/]', expression):  # 必須包含運算符
                return False
            
            # 嘗試編譯表達式（不執行）
            compile(expression.replace(' ', ''), '<string>', 'eval')
            return True
        except:
            return False
        
    def _extract_weather_params(self, text: str) -> Dict:
        """提取天氣查詢參數"""
        params = {}
        
        # 提取時間
        if "今天" in text:
            params["when"] = "today"
        elif "明天" in text:
            params["when"] = "tomorrow"
        elif "最近" in text:
            params["when"] = "recent"
        else:
            params["when"] = "current"
        
        # 可以擴展提取地點等其他參數
        return params
    
    def _extract_model_params(self, text: str) -> Dict:
        """提取模型切換參數 - NPU 優先邏輯"""
        params = {}
        
        # 檢查是否指定了特定的提供商
        if "ollama" in text.lower():
            params["provider"] = "ollama"
        elif "lemonade" in text.lower() or "npu" in text.lower():
            params["provider"] = "lemonade"
        else:
            # 沒有明確指定時，預設優先選擇 NPU
            params["provider_preference"] = "npu_first"
        
        # 檢查是否指定了模型大小
        if "7b" in text.lower():
            params["size"] = "7b"
        elif "1.5b" in text.lower():
            params["size"] = "1.5b"
        else:
            # 沒有明確指定時，預設選擇 7B 模型
            params["size_preference"] = "7b_first"
            
        return params

class FunctionExecutor:
    """函數執行器"""
    
    def __init__(self, pet_instance):
        self.pet = pet_instance
        self.functions = {
            "calculate": self._execute_calculator,
            "get_weather": self._execute_weather_query,
            "open_calculator": self._execute_open_calculator,
            "switch_model": self._execute_switch_model,
            "show_models": self._execute_show_models,
        }
    
    def execute_function(self, function_call: FunctionCall) -> str:
        """執行函數調用"""
        print(f"[調試] 開始執行函數: {function_call.function_name}")
        
        if function_call.function_name in self.functions:
            try:
                result = self.functions[function_call.function_name](function_call.parameters)
                print(f"[調試] 函數執行成功: {result}")
                return result
            except Exception as e:
                print(f"[調試] 函數執行失敗: {e}")
                import traceback
                traceback.print_exc()
                return f"執行 {function_call.function_name} 時發生錯誤：{str(e)}"
        else:
            print(f"[調試] 未知函數: {function_call.function_name}")
            return f"未知的函數：{function_call.function_name}"
    
    def _execute_calculator(self, params: Dict) -> str:
        """執行計算器功能"""
        expression = params.get("expression", "")
        if not expression:
            return "沒有找到要計算的表達式"
        
        # 調用計算器助手
        if hasattr(self.pet, 'calculator_helper'):
            self.pet.calculator_helper.calculate_with_system_calculator(expression)
            return f"正在為你計算 {expression}，請查看計算器窗口"
        else:
            return "計算器功能不可用"
        
    def _execute_weather_query(self, params: Dict) -> str:
        """執行天氣查詢功能"""
        when = params.get("when", "current")
        print(f"[調試] 天氣查詢 - 時間: {when}")
        
        # 調用天氣功能
        if hasattr(self.pet, 'open_weather'):
            self.pet.open_weather()
            return f"正在為你打開天氣資訊頁面"
        else:
            return "天氣查詢功能不可用"
        
    def _execute_open_calculator(self, params: Dict) -> str:
        """打開系統計算機 - 加強版本"""
        print(f"[調試] 執行 _execute_open_calculator，參數: {params}")
        
        try:
            import subprocess
            import os
            
            # 直接嘗試打開 Windows 計算機
            print("[調試] 嘗試打開 calc.exe")
            subprocess.Popen(['calc.exe'])
            
            # 在桌寵中顯示確認訊息
            if hasattr(self.pet, "ai_speak"):
                print("[調試] 調用 ai_speak")
                self.pet.ai_speak("人～計算機已經打開囉～", "happy")
            
            print("[調試] 計算機打開成功")
            return "系統計算機已成功打開"
            
        except FileNotFoundError as e:
            print(f"[調試] calc.exe 未找到: {e}")
            try:
                # 嘗試其他可能的計算機程式
                subprocess.Popen(['calculator.exe'])
                if hasattr(self.pet, "ai_speak"):
                    self.pet.ai_speak("人～計算機已經打開囉～", "happy")
                return "系統計算機已成功打開"
            except Exception as e2:
                print(f"[調試] 所有計算機程式都失敗: {e2}")
                error_msg = f"找不到計算機程式: {str(e)}"
                if hasattr(self.pet, "ai_speak"):
                    self.pet.ai_speak(f"嗚嗚...找不到計算機程式", "sad")
                return error_msg
                
        except Exception as e:
            print(f"[調試] 其他錯誤: {e}")
            error_msg = f"打開計算機失敗：{str(e)}"
            if hasattr(self.pet, "ai_speak"):
                self.pet.ai_speak(f"嗚嗚...計算機打不開: {str(e)}", "sad")
            return error_msg
    
    def _execute_switch_model(self, params: Dict) -> str:
        """執行模型切換功能 - NPU 優先邏輯"""
        print(f"[調試] 執行模型切換，參數: {params}")
        
        if not LLM_ADAPTER_AVAILABLE:
            return "模型切換功能不可用，請確保已安裝新的 LLM 適配器"
        
        try:
            provider = params.get("provider")
            size = params.get("size")
            provider_preference = params.get("provider_preference")
            size_preference = params.get("size_preference")
            
            target_model = None
            
            # 根據參數選擇模型，NPU 優先
            if provider == "ollama":
                if size == "1.5b":
                    target_model = "qwen2.5:1.5b"
                else:
                    target_model = "qwen2.5:7b"
            elif provider == "lemonade":
                if size == "1.5b":
                    target_model = "Qwen-2.5-1.5B-Instruct-NPU"
                else:
                    target_model = "Qwen-2.5-7B-Instruct-NPU"
            elif provider_preference == "npu_first":
                # 智能選擇：NPU 優先，按大小偏好
                if size_preference == "7b_first" or size == "7b":
                    # 優先嘗試 NPU 7B -> NPU 1.5B -> Ollama 7B -> Ollama 1.5B
                    candidate_models = [
                        "Qwen-2.5-7B-Instruct-NPU",
                        "Qwen-2.5-1.5B-Instruct-NPU", 
                        "qwen2.5:7b",
                        "qwen2.5:1.5b"
                    ]
                else:
                    # 優先嘗試 NPU 1.5B -> NPU 7B -> Ollama 1.5B -> Ollama 7B
                    candidate_models = [
                        "Qwen-2.5-1.5B-Instruct-NPU",
                        "Qwen-2.5-7B-Instruct-NPU",
                        "qwen2.5:1.5b", 
                        "qwen2.5:7b"
                    ]
                
                # 嘗試按優先級順序切換到第一個可用的模型
                for candidate in candidate_models:
                    if llm_adapter.switch_model(candidate):
                        current_model = llm_adapter.get_current_model_info()
                        if hasattr(self.pet, "ai_speak"):
                            if current_model['provider'] == 'lemonade':
                                self.pet.ai_speak(f"人～已經切換到高效的 NPU 模型 {current_model['display_name']} 囉～", "happy")
                            else:
                                self.pet.ai_speak(f"人～NPU 模型不可用，已切換到備用的 {current_model['display_name']} 囉～", "happy")
                        return f"已成功切換到模型: {current_model['display_name']}"
                
                # 如果都失敗了
                if hasattr(self.pet, "ai_speak"):
                    self.pet.ai_speak("嗚嗚...所有模型都不可用", "sad")
                return "所有候選模型都不可用，請檢查服務狀態"
            else:
                # 沒有指定具體模型，打開選擇界面
                self._open_model_selector()
                return "已打開模型選擇界面，請選擇你想要的模型"
            
            # 執行指定的模型切換
            if target_model:
                success = llm_adapter.switch_model(target_model)
                if success:
                    current_model = llm_adapter.get_current_model_info()
                    if hasattr(self.pet, "ai_speak"):
                        if current_model['provider'] == 'lemonade':
                            self.pet.ai_speak(f"人～已經切換到高效的 NPU 模型 {current_model['display_name']} 囉～", "happy")
                        else:
                            self.pet.ai_speak(f"人～已經切換到 {current_model['display_name']} 囉～", "happy")
                    return f"已成功切換到模型: {current_model['display_name']}"
                else:
                    if hasattr(self.pet, "ai_speak"):
                        self.pet.ai_speak("嗚嗚...模型切換失敗了", "sad")
                    return "模型切換失敗，請檢查模型是否可用"
                
        except Exception as e:
            print(f"[調試] 模型切換錯誤: {e}")
            if hasattr(self.pet, "ai_speak"):
                self.pet.ai_speak(f"嗚嗚...出錯了: {str(e)}", "sad")
            return f"模型切換出錯: {str(e)}"
    
    def _execute_show_models(self, params: Dict) -> str:
        """顯示可用模型信息"""
        print(f"[調試] 顯示模型信息，參數: {params}")
        
        if not LLM_ADAPTER_AVAILABLE:
            return "模型信息功能不可用，請確保已安裝新的 LLM 適配器"
        
        try:
            current_model = llm_adapter.get_current_model_info()
            models = llm_adapter.get_available_models()
            
            # 構建回應信息
            response = f"當前使用: {current_model['display_name']} ({current_model['provider'].upper()})\n\n"
            response += "可用模型:\n"
            
            ollama_models = [m for m in models if m['provider'] == 'ollama']
            lemonade_models = [m for m in models if m['provider'] == 'lemonade']
            
            if ollama_models:
                response += "🐋 Ollama 模型:\n"
                for model in ollama_models:
                    status = " (當前)" if model['is_current'] else ""
                    response += f"  • {model['display_name']}{status}\n"
                response += "\n"
            
            if lemonade_models:
                response += "🍋 Lemonade 模型:\n"
                for model in lemonade_models:
                    status = " (當前)" if model['is_current'] else ""
                    response += f"  • {model['display_name']}{status}\n"
            
            # 在 GUI 中顯示完整信息
            if hasattr(self.pet, 'show_info_dialog'):
                from PyQt5 import QtWidgets
                QtWidgets.QMessageBox.information(None, "🤖 模型信息", response)
            
            # 桌寵簡短回應
            if hasattr(self.pet, "ai_speak"):
                self.pet.ai_speak(f"人～目前用的是 {current_model['display_name']}，詳細信息已顯示～", "happy")
            
            return f"當前模型: {current_model['display_name']}"
            
        except Exception as e:
            print(f"[調試] 顯示模型信息錯誤: {e}")
            if hasattr(self.pet, "ai_speak"):
                self.pet.ai_speak(f"嗚嗚...無法獲取模型信息: {str(e)}", "sad")
            return f"獲取模型信息失敗: {str(e)}"
    
    def _open_model_selector(self):
        """打開模型選擇器界面"""
        try:
            from model_selector_ui import ModelSelectorDialog
            from PyQt5 import QtWidgets
            
            # 創建並顯示模型選擇對話框
            dialog = ModelSelectorDialog()
            
            def on_model_changed(model_name):
                if hasattr(self.pet, "ai_speak"):
                    self.pet.ai_speak(f"人～已經切換到新模型囉～", "happy")
            
            dialog.model_changed.connect(on_model_changed)
            dialog.show()
            
        except ImportError:
            print("模型選擇器界面不可用")
        except Exception as e:
            print(f"打開模型選擇器失敗: {e}")

class DoroAIChat:
    """Doro AI 聊天整合類 - 增強版"""
    
    def __init__(self, pet_instance=None):
        self.pet = pet_instance
        self.ai_memory = None
        self.response_queue = queue.Queue()
        self.is_thinking = False
        
        # 新增：函數調用組件
        self.intent_recognizer = IntentRecognizer()
        self.function_executor = FunctionExecutor(pet_instance)
        self.plugin_executor = get_executor()
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
                if not AI_DEPS_AVAILABLE and not LLM_ADAPTER_AVAILABLE:
                    print("AI 依賴不可用")
                    if self.pet:
                        self.pet.hide_thinking()
                        self.pet.ai_speak("人...Doro還沒學會聰明的說話呢～", "sad")
                    return
                
                # 使用 test.json 作為配置檔案，但不自動選擇模型
                self.ai_memory = AIMemorySystem(
                    prompt_file="test.json",
                    chat_model="qwen2.5:7b"  # 使用保守的預設值
                )
                
                # 顯示當前配置的模型信息（不強制切換）
                if LLM_ADAPTER_AVAILABLE:
                    try:
                        current_model = llm_adapter.get_current_model_info()
                        print(f"當前配置模型: {current_model['display_name']} ({current_model['provider']})")
                        
                        # 檢查模型是否真正可用，但不自動切換
                        from llm_config import config_manager
                        is_available = config_manager._is_model_service_available(
                            config_manager.available_models.get(current_model['name'])
                        )
                        
                        if is_available:
                            print(f"✅ 模型服務可用")
                        else:
                            print(f"⚠️  模型服務不可用，可能需要手動選擇其他模型")
                                
                    except Exception as e:
                        print(f"模型狀態檢查失敗: {e}")
                        pass
                
                print("Doro AI 系統初始化完成！")
                
                if self.pet:
                    self.pet.hide_thinking()
                    # 顯示啟動訊息
                    startup_msg = self.ai_memory.prompt_config.get(
                        "startup_message", 
                        "人！Doro 跑過來了～要陪我一起玩嗎？"
                    )
                    
                    # 如果有新適配器，添加模型信息並優先顯示 NPU
                    if LLM_ADAPTER_AVAILABLE:
                        try:
                            current_model = llm_adapter.get_current_model_info()
                            if current_model['provider'] == 'lemonade':
                                startup_msg += f"\n（我現在用的是高效的 NPU 模型 {current_model['display_name']} 哦～）"
                            else:
                                startup_msg += f"\n（我現在用的是 {current_model['display_name']}）"
                        except:
                            pass
                    
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
        return self.ai_memory is not None and (AI_DEPS_AVAILABLE or LLM_ADAPTER_AVAILABLE)
    
    def chat_with_ai(self, user_input: str):
        """與 AI 進行對話 - 增強版本（支援函數調用）"""
        if not self.is_ai_ready():
            if self.pet:
                self.pet.ai_speak("人...Doro 還在學習中，等等再來找我玩吧～", "think")
            return
        
        if self.is_thinking:
            if self.pet:
                self.pet.ai_speak("人～等等，Doro 還在想上一個問題呢！", "think")
            return
        
        # === Plugins: 路由並嘗試攔截（改：有 points 時開完整視窗） ===
        name, kw = route_input_to_plugin(user_input, self.plugin_executor)
        if name:
            result = self.plugin_executor.call(name, **(kw or {}))
            if result.get("error"):
                if self.pet:
                    self.pet.ai_speak("（插件）" + result["error"], "sad")
                else:
                    say("（插件）" + result["error"])
                return

            title   = result.get("title","")
            kind    = result.get("kind","")
            summary = result.get("summary","")
            points  = result.get("points") or []

            preview = summary[:180] + ("…" if len(summary) > 180 else "")
            # 泡泡：短預覽
            if self.pet:
                self.pet.ai_speak(f"《{title}》{kind} 摘要：\n{preview}", "think")
            else:
                say(f"《{title}》{kind} 摘要：\n{preview}")

            # 完整視窗
            if self.pet and (summary or points):
                from PyQt5 import QtWidgets
                full = f"《{title}》\n\n{summary}\n\n" + "\n".join(f"• {p}" for p in points)
                QtWidgets.QMessageBox.information(None, "分析結果", full)

            return

        # === 若沒命中插件，繼續原本流程（意圖識別與 LLM） ===

        # 首先識別意圖
        function_call = self.intent_recognizer.recognize_intent(user_input)
        
        if function_call and function_call.should_execute:
            # 執行函數並生成增強回應
            self._handle_function_call(user_input, function_call)
        else:
            # 沒有識別到特殊意圖，使用原有的聊天功能
            self._original_chat_with_ai(user_input)
    
    def _handle_function_call(self, user_input: str, function_call: FunctionCall):
        """處理函數調用"""
        # 開始思考
        self.is_thinking = True
        if self.pet:
            self.pet.show_thinking()
        
        def process_function_call():
            try:
                # 執行函數
                function_result = self.function_executor.execute_function(function_call)
                
                # 構造特殊提示詞
                enhanced_prompt = f"""
用戶說：{user_input}

我已經幫用戶執行了 {function_call.function_name} 功能。
執行結果：{function_result}

請以 Doro 的角色回應用戶：
1. 確認已經幫用戶執行了相關功能
2. 保持 Doro 可愛呆萌的語氣
3. 用「人～」稱呼用戶
4. 如果是計算功能，提醒查看計算器窗口
5. 如果是模型切換功能，確認切換結果
"""
                
                # 生成 AI 回應
                response = self.ai_memory.stream_response(enhanced_prompt)
                
                # 將回應放入佇列
                self.response_queue.put(('success', response))
                
            except Exception as e:
                print(f"函數調用處理失敗: {e}")
                self.response_queue.put(('error', str(e)))
        
        # 啟動處理執行緒
        response_thread = threading.Thread(target=process_function_call, daemon=True)
        response_thread.start()
        
        # 啟動計時器檢查回應
        self._start_response_timer()
    
    def _original_chat_with_ai(self, user_input: str):
        """原有的聊天方法"""
        # 開始思考
        self.is_thinking = True
        if self.pet:
            self.pet.show_thinking()
        
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
    
    # 新增：模型管理相關方法
    def switch_model(self, model_name: str) -> bool:
        """切換使用的模型"""
        if not LLM_ADAPTER_AVAILABLE:
            if self.pet:
                self.pet.ai_speak("人...模型切換功能還沒準備好呢～", "sad")
            return False
        
        try:
            success = llm_adapter.switch_model(model_name)
            if success:
                current_model = llm_adapter.get_current_model_info()
                if self.pet:
                    self.pet.ai_speak(f"人～我已經切換到 {current_model['display_name']} 了！", "happy")
                return True
            else:
                if self.pet:
                    self.pet.ai_speak("嗚嗚...切換失敗了", "sad")
                return False
        except Exception as e:
            if self.pet:
                self.pet.ai_speak(f"切換出錯了: {str(e)}", "sad")
            return False
    
    def get_available_models(self) -> List[Dict]:
        """獲取可用模型列表"""
        if not LLM_ADAPTER_AVAILABLE:
            return []
        
        try:
            return llm_adapter.get_available_models()
        except:
            return []
    
    def get_current_model_info(self) -> Dict:
        """獲取當前模型信息"""
        if not LLM_ADAPTER_AVAILABLE:
            return {"name": "未知", "display_name": "舊版模式", "provider": "ollama"}
        
        try:
            return llm_adapter.get_current_model_info()
        except:
            return {"name": "未知", "display_name": "獲取失敗", "provider": "未知"}
    
    def test_model_connection(self) -> Dict:
        """測試當前模型連接"""
        if not LLM_ADAPTER_AVAILABLE:
            return {"success": False, "error": "新適配器不可用"}
        
        try:
            return llm_adapter.test_model_connection()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_ai_stats(self) -> dict:
        """獲得 AI 系統統計資訊"""
        if not self.is_ai_ready():
            return {"status": "not_ready"}
        
        try:
            stats = self.ai_memory.get_memory_stats()
            stats["status"] = "ready"
            stats["character_name"] = self.ai_memory.prompt_config.get("character_name", "Doro")
            stats["function_calling_enabled"] = True
            stats["llm_adapter_available"] = LLM_ADAPTER_AVAILABLE
            
            # 添加當前模型信息
            if LLM_ADAPTER_AVAILABLE:
                try:
                    current_model = self.get_current_model_info()
                    stats["current_model"] = current_model
                    stats["available_models_count"] = len(self.get_available_models())
                except:
                    pass
            
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
        info = {
            "name": config.get("character_name", "Doro"),
            "greeting": config.get("greeting", "人～你好！"),
            "system_prompt": config.get("system_prompt", ""),
            "status": "ready",
            "function_calling": True,
            "llm_adapter": LLM_ADAPTER_AVAILABLE
        }
        
        # 添加當前模型信息
        if LLM_ADAPTER_AVAILABLE:
            try:
                current_model = self.get_current_model_info()
                info["current_model"] = current_model
            except:
                pass
        
        return info