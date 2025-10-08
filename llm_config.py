# llm_config.py
# -*- coding: utf-8 -*-
"""
LLM 配置管理模組
支援 Ollama 和 Lemonade SDK 之間的切換
"""

import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ModelConfig:
    """模型配置類"""
    name: str
    display_name: str
    provider: str  # "ollama" or "lemonade"
    api_base: str
    api_key: str
    
class LLMConfigManager:
    """LLM 配置管理器"""
    
    def __init__(self):
        self.config_file = "llm_config.json"
        self.current_provider = "lemonade"  # 預設優先使用 lemonade 
        # 動態檢測並設定默認模型
        self.current_model = self._detect_best_available_model()
        
        # 更新的模型配置 - 匹配所有可能的模型名稱變體
        self.available_models = {
            # Lemonade SDK 模型 - CPU 版本
            "Qwen2.5-0.5B-Instruct-CPU": ModelConfig(
                name="Qwen2.5-0.5B-Instruct-CPU",
                display_name="Qwen 2.5 0.5B CPU (Lemonade)",
                provider="lemonade",
                api_base="http://localhost:8000/api/v1",
                api_key="lemonade"
            ),
            
            # NPU 版本 - 多種可能的命名變體
            "Qwen-2.5-7B-Instruct-NPU": ModelConfig(
                name="Qwen-2.5-7B-Instruct-NPU",
                display_name="Qwen 2.5 7B NPU (Lemonade) [推薦]",
                provider="lemonade",
                api_base="http://localhost:8000/api/v1",
                api_key="lemonade"
            ),
            "Qwen2.5-7B-Instruct-NPU": ModelConfig(
                name="Qwen2.5-7B-Instruct-NPU",
                display_name="Qwen2.5 7B NPU (Lemonade) [推薦]",
                provider="lemonade",
                api_base="http://localhost:8000/api/v1",
                api_key="lemonade"
            ),
            "Qwen-2.5-1.5B-Instruct-NPU": ModelConfig(
                name="Qwen-2.5-1.5B-Instruct-NPU",
                display_name="Qwen 2.5 1.5B NPU (Lemonade) [快速]", 
                provider="lemonade",
                api_base="http://localhost:8000/api/v1",
                api_key="lemonade"
            ),
            "Qwen2.5-1.5B-Instruct-NPU": ModelConfig(
                name="Qwen2.5-1.5B-Instruct-NPU",
                display_name="Qwen2.5 1.5B NPU (Lemonade) [快速]", 
                provider="lemonade",
                api_base="http://localhost:8000/api/v1",
                api_key="lemonade"
            ),
            
            # Ollama 模型 (備用)
            "qwen2.5:7b": ModelConfig(
                name="qwen2.5:7b",
                display_name="Qwen 2.5 7B (Ollama) [備用]",
                provider="ollama",
                api_base="http://127.0.0.1:11434/v1",
                api_key="not-needed"
            ),
            "qwen2.5:1.5b": ModelConfig(
                name="qwen2.5:1.5b", 
                display_name="Qwen 2.5 1.5B (Ollama) [備用]",
                provider="ollama",
                api_base="http://127.0.0.1:11434/v1",
                api_key="not-needed"
            )
        }
        
        self._load_config()
    
    def _load_config(self):
        """載入配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.current_provider = config.get("current_provider", "lemonade")
                    # 如果配置中的模型不存在，使用實際可用的模型
                    config_model = config.get("current_model", "Qwen2.5-0.5B-Instruct-CPU")
                    if config_model in self.available_models:
                        self.current_model = config_model
                    else:
                        self.current_model = "Qwen2.5-0.5B-Instruct-CPU"  # 使用實際可用的
        except Exception as e:
            print(f"載入配置失敗，使用預設值: {e}")
    
    def _save_config(self):
        """保存配置文件"""
        try:
            config = {
                "current_provider": self.current_provider,
                "current_model": self.current_model
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失敗: {e}")
    
    def get_current_model_config(self) -> ModelConfig:
        """獲取當前模型配置 - 智能選擇可用模型"""
        # 優先嘗試當前配置的模型
        if self.current_model in self.available_models:
            preferred_config = self.available_models[self.current_model]
            
            # 檢查該模型是否真正可用
            if self._is_model_service_available(preferred_config):
                return preferred_config
            else:
                print(f"警告：首選模型 {preferred_config.display_name} 服務不可用，正在尋找備用模型...")
        
        # 更新優先級順序 - NPU 優先，並包含所有變體
        priority_models = [
            "Qwen-2.5-7B-Instruct-NPU",      # NPU 7B 帶破折號
            "Qwen2.5-7B-Instruct-NPU",       # NPU 7B 無破折號
            "Qwen-2.5-1.5B-Instruct-NPU",    # NPU 1.5B 帶破折號  
            "Qwen2.5-1.5B-Instruct-NPU",     # NPU 1.5B 無破折號
            "Qwen2.5-0.5B-Instruct-CPU",     # CPU 0.5B
            "qwen2.5:7b",                     # Ollama 7B
            "qwen2.5:1.5b"                    # Ollama 1.5B
        ]
        
        for model_name in priority_models:
            if model_name in self.available_models:
                config = self.available_models[model_name]
                if self._is_model_service_available(config):
                    # 只有在真正可用時才切換
                    old_model = self.current_model
                    self.current_model = model_name
                    self.current_provider = config.provider
                    self._save_config()
                    print(f"自動切換: {old_model} -> {config.display_name}")
                    return config
                else:
                    print(f"跳過不可用的模型: {config.display_name}")
        
        # 如果都不可用，返回預設配置但發出警告
        print("嚴重警告：沒有找到任何可用的模型服務！")
        fallback = self.available_models.get("Qwen2.5-0.5B-Instruct-CPU", 
                                           list(self.available_models.values())[0])
        print(f"使用後備配置: {fallback.display_name}（但服務可能不可用）")
        return fallback
    
    def _is_model_service_available(self, model_config: ModelConfig) -> bool:
        """檢查特定模型服務是否可用 - 修復健康檢查問題"""
        try:
            import requests
            
            if model_config.provider == "lemonade":
                # 檢查 Lemonade 服務 - 跳過健康檢查，直接檢查模型列表
                try:
                    # 直接檢查模型列表 API，跳過不存在的 /health 端點
                    models_response = requests.get(
                        "http://localhost:8000/api/v1/models", 
                        timeout=3,
                        headers={"Authorization": f"Bearer {model_config.api_key}"}
                    )
                    if models_response.status_code == 200:
                        models_data = models_response.json()
                        if isinstance(models_data, dict) and 'data' in models_data:
                            available_models = [m.get('id', '') for m in models_data['data']]
                            model_available = model_config.name in available_models
                            print(f"{'✅' if model_available else '❌'} 模型 {model_config.name} {'可用' if model_available else '不在模型列表中'}")
                            if not model_available:
                                print(f"可用模型: {available_models}")
                            return model_available
                        return True  # API 可用但格式不明，假設可用
                    else:
                        print(f"❌ Lemonade 模型列表 API 返回 {models_response.status_code}")
                        return False
                except Exception as e:
                    print(f"❌ Lemonade 服務連接失敗: {e}")
                    return False
                        
            elif model_config.provider == "ollama":
                # 檢查 Ollama 服務
                try:
                    # 檢查服務版本
                    response = requests.get("http://127.0.0.1:11434/api/version", timeout=3)
                    if response.status_code == 200:
                        print(f"✅ Ollama 服務可用")
                        
                        # 檢查特定模型是否已拉取
                        try:
                            tags_response = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
                            if tags_response.status_code == 200:
                                tags_data = tags_response.json()
                                if isinstance(tags_data, dict) and 'models' in tags_data:
                                    available_models = [m.get('name', '') for m in tags_data['models']]
                                    # Ollama 模型名稱可能有標籤，需要模糊匹配
                                    model_available = any(model_config.name in model_name for model_name in available_models)
                                    print(f"{'✅' if model_available else '❌'} 模型 {model_config.name} {'已拉取' if model_available else '未拉取'}")
                                    if not model_available:
                                        print(f"可用模型: {available_models}")
                                    return model_available
                                return True  # API 可用但格式不明，假設可用
                            else:
                                print(f"❌ Ollama 模型列表 API 返回 {tags_response.status_code}")
                                return False
                        except Exception as e:
                            print(f"⚠️ Ollama 模型列表檢查失敗: {e}")
                            return True  # 服務可用，假設基本可用
                    else:
                        print(f"❌ Ollama 服務檢查失敗: {response.status_code}")
                        return False
                except Exception as e:
                    print(f"❌ Ollama 服務連接失敗: {e}")
                    return False
                    
            return False
            
        except Exception as e:
            print(f"❌ 模型服務檢查異常: {e}")
            return False
    
    def switch_model(self, model_name: str) -> bool:
        """切換模型"""
        if model_name in self.available_models:
            self.current_model = model_name
            model_config = self.available_models[model_name]
            self.current_provider = model_config.provider
            self._save_config()
            print(f"已切換到模型: {model_config.display_name}")
            return True
        else:
            print(f"找不到模型: {model_name}")
            return False
    
    def get_models_by_provider(self, provider: str) -> List[ModelConfig]:
        """根據提供商獲取模型列表"""
        return [model for model in self.available_models.values() 
                if model.provider == provider]
    
    def get_all_models(self) -> List[ModelConfig]:
        """獲取所有可用模型"""
        return list(self.available_models.values())
    
    def add_custom_model(self, name: str, display_name: str, provider: str, 
                        api_base: str, api_key: str):
        """添加自定義模型"""
        self.available_models[name] = ModelConfig(
            name=name,
            display_name=display_name,
            provider=provider,
            api_base=api_base,
            api_key=api_key
        )
        self._save_config()
    
    def is_model_available(self, model_name: str) -> bool:
        """檢查模型是否可用"""
        return model_name in self.available_models
    
    def get_provider_status(self) -> Dict[str, str]:
        """獲取各提供商狀態"""
        status = {}
        
        # 檢查 Ollama
        try:
            import requests
            response = requests.get("http://127.0.0.1:11434/api/version", timeout=3)
            status["ollama"] = "可用" if response.status_code == 200 else "不可用"
        except:
            status["ollama"] = "不可用"
        
        # 檢查 Lemonade - 修復健康檢查
        try:
            import requests
            # 直接檢查模型列表而不是健康端點
            response = requests.get("http://localhost:8000/api/v1/models", timeout=3)
            status["lemonade"] = "可用" if response.status_code == 200 else "不可用"
        except:
            # 如果模型列表也失敗，嘗試 OpenAI 客戶端
            try:
                from openai import OpenAI
                client = OpenAI(base_url="http://localhost:8000/api/v1", api_key="lemonade")
                models = client.models.list()
                status["lemonade"] = "可用"
            except:
                status["lemonade"] = "不可用"
        
        return status

    def _detect_best_available_model(self) -> str:
        """動態檢測最佳可用模型"""
        try:
            import requests
            # 獲取實際可用的模型列表
            response = requests.get("http://localhost:8000/api/v1/models", timeout=3)
            if response.status_code == 200:
                models_data = response.json()
                if isinstance(models_data, dict) and 'data' in models_data:
                    available_model_ids = [m.get('id', '') for m in models_data['data']]
                    print(f"檢測到的可用模型: {available_model_ids}")
                    
                    # 按優先級檢查，NPU 模型優先
                    priority_check = [
                        "Qwen-2.5-7B-Instruct-NPU",
                        "Qwen2.5-7B-Instruct-NPU", 
                        "Qwen-2.5-1.5B-Instruct-NPU",
                        "Qwen2.5-1.5B-Instruct-NPU",
                        "Qwen2.5-0.5B-Instruct-CPU"
                    ]
                    
                    for model_name in priority_check:
                        if model_name in available_model_ids:
                            print(f"選擇最佳模型: {model_name}")
                            return model_name
                    
                    # 如果沒有匹配的，使用第一個可用的
                    if available_model_ids:
                        selected = available_model_ids[0]
                        print(f"使用第一個可用模型: {selected}")
                        return selected
        except Exception as e:
            print(f"自動檢測模型失敗: {e}")
        
        # 默認返回
        return "Qwen-2.5-7B-Instruct-NPU"

# 全局配置管理器實例
config_manager = LLMConfigManager()