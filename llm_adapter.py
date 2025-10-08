# llm_adapter.py
# -*- coding: utf-8 -*-
"""
統一 LLM API 適配器
支援 Ollama 和 Lemonade SDK 的統一接口
"""

from typing import Dict, List, Optional, Iterator
from llm_config import config_manager, ModelConfig

class LLMAdapter:
    """統一的 LLM API 適配器"""
    
    def __init__(self):
        self.config_manager = config_manager
    
    def chat_completion(self, messages: List[Dict], model: Optional[str] = None, 
                       temperature: float = 0.3, max_tokens: Optional[int] = None,
                       stream: bool = False) -> Dict:
        """
        統一的聊天完成接口
        
        Args:
            messages: 對話消息列表
            model: 模型名稱，如果為 None 則使用當前配置的模型
            temperature: 溫度參數
            max_tokens: 最大令牌數
            stream: 是否使用流式輸出
            
        Returns:
            統一格式的響應字典
        """
        try:
            if model:
                # 臨時使用指定模型
                if not self.config_manager.is_model_available(model):
                    raise ValueError(f"模型 {model} 不可用")
                model_config = self.config_manager.available_models[model]
            else:
                # 使用當前配置的模型
                model_config = self.config_manager.get_current_model_config()
            
            if model_config.provider == "ollama":
                return self._ollama_chat(messages, model_config, temperature, max_tokens, stream)
            elif model_config.provider == "lemonade":
                return self._lemonade_chat(messages, model_config, temperature, max_tokens, stream)
            else:
                raise ValueError(f"不支援的提供商: {model_config.provider}")
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": f"調用 LLM API 失敗: {e}"
            }
    
    def _ollama_chat(self, messages: List[Dict], model_config: ModelConfig, 
                    temperature: float, max_tokens: Optional[int], stream: bool) -> Dict:
        """Ollama API 調用"""
        try:
            if stream:
                # 使用 ollama 原生客戶端進行流式調用
                import ollama
                client = ollama.Client()
                
                def stream_generator():
                    for chunk in client.chat(
                        model=model_config.name,
                        messages=messages,
                        stream=True,
                        options={
                            "temperature": temperature,
                            "num_predict": max_tokens or -1
                        }
                    ):
                        if chunk.get('message', {}).get('content'):
                            yield chunk['message']['content']
                
                return {
                    "success": True,
                    "stream": stream_generator(),
                    "model": model_config.name,
                    "provider": "ollama"
                }
            else:
                # 非流式調用
                import ollama
                client = ollama.Client()
                
                result = client.chat(
                    model=model_config.name,
                    messages=messages,
                    stream=False,
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens or -1
                    }
                )
                
                return {
                    "success": True,
                    "content": result["message"]["content"],
                    "model": model_config.name,
                    "provider": "ollama",
                    "usage": result.get("usage", {})
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Ollama API 錯誤: {str(e)}",
                "content": f"Ollama 調用失敗: {e}"
            }
    
    def _lemonade_chat(self, messages: List[Dict], model_config: ModelConfig,
                      temperature: float, max_tokens: Optional[int], stream: bool) -> Dict:
        """Lemonade SDK API 調用"""
        try:
            from openai import OpenAI
            
            client = OpenAI(
                base_url=model_config.api_base,
                api_key=model_config.api_key
            )
            
            # 構建請求參數
            params = {
                "model": model_config.name,
                "messages": messages,
                "temperature": temperature,
                "stream": stream
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            if stream:
                # 流式調用
                def stream_generator():
                    completion = client.chat.completions.create(**params)
                    for chunk in completion:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content:
                            yield delta.content
                
                return {
                    "success": True,
                    "stream": stream_generator(),
                    "model": model_config.name,
                    "provider": "lemonade"
                }
            else:
                # 非流式調用
                completion = client.chat.completions.create(**params)
                
                return {
                    "success": True,
                    "content": completion.choices[0].message.content,
                    "model": model_config.name,
                    "provider": "lemonade",
                    "usage": {
                        "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
                        "completion_tokens": completion.usage.completion_tokens if completion.usage else 0,
                        "total_tokens": completion.usage.total_tokens if completion.usage else 0
                    } if hasattr(completion, 'usage') and completion.usage else {}
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Lemonade API 錯誤: {str(e)}",
                "content": f"Lemonade 調用失敗: {e}"
            }
    
    def get_available_models(self) -> List[Dict]:
        """獲取可用模型列表"""
        models = []
        for model_config in self.config_manager.get_all_models():
            models.append({
                "name": model_config.name,
                "display_name": model_config.display_name,
                "provider": model_config.provider,
                "is_current": model_config.name == self.config_manager.current_model
            })
        return models
    
    def switch_model(self, model_name: str) -> bool:
        """切換當前使用的模型"""
        return self.config_manager.switch_model(model_name)
    
    def get_current_model_info(self) -> Dict:
        """獲取當前模型信息"""
        model_config = self.config_manager.get_current_model_config()
        return {
            "name": model_config.name,
            "display_name": model_config.display_name,
            "provider": model_config.provider,
            "api_base": model_config.api_base
        }
    
    def test_model_connection(self, model_name: Optional[str] = None) -> Dict:
        """測試模型連接"""
        try:
            if model_name:
                if not self.config_manager.is_model_available(model_name):
                    return {"success": False, "error": f"模型 {model_name} 不存在"}
                model_config = self.config_manager.available_models[model_name]
            else:
                model_config = self.config_manager.get_current_model_config()
            
            # 發送測試消息
            test_messages = [{"role": "user", "content": "你好"}]
            result = self.chat_completion(
                messages=test_messages,
                model=model_config.name,
                temperature=0.1
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"模型 {model_config.display_name} 連接正常",
                    "response_preview": result["content"][:50] + "..." if len(result["content"]) > 50 else result["content"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"連接測試失敗: {str(e)}"
            }

# 全局適配器實例
llm_adapter = LLMAdapter()