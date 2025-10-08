# plugins/translate_text.py
import os, requests

def translate_text(text: str, target_lang: str = "zh-TW"):
    # Ollama API 位置
    base = os.getenv("TRANS_API_BASE", "http://127.0.0.1:11434/v1")
    # 這裡指定 Ollama 已經拉好的模型
    model = os.getenv("TRANS_MODEL", "qwen2.5:7b")
    api_key = os.getenv("TRANS_API_KEY", "not-needed")  # Ollama 不需要 key
    if not text:
        return {"error": "請提供要翻譯的文字"}

    try:
        prompt = f"請將以下內容翻譯成 {target_lang}：\n{text}"

        r = requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,  # "qwen2.5:7b"
                "messages":[{"role":"user","content": prompt}],
                "temperature": 0.2
            },
            timeout=25
        )

        r.raise_for_status()
        translated = r.json()["choices"][0]["message"]["content"].strip()
        return {"ok": True, "original": text, "translated": translated}
    except Exception as e:
        return {"error": f"翻譯失敗：{e}"}

def register():
    return {
        "name": "translate_text",
        "version": "0.1.0",
        "description": "本地翻譯功能（依賴 LLM API）",
        "triggers": ["翻譯", "translate", "翻譯一下"],
        "params_schema": {"text": str, "target_lang": str},
        "handler": translate_text,
        "timeout_sec": 30,
    }
