import os, requests
API_BASE = os.getenv("ANALYZE_API", "http://127.0.0.1:5005")

def summarize_page(url: str | None = None, text: str | None = None, mode: str = "auto"):
    if not url and not text:
        return {"error": "請提供 url 或 text 任一項"}
    try:
        r = requests.post(f"{API_BASE}/analyze",
                          json={"url": url or "", "title": "", "text": text or "", "mode": mode},
                          timeout=25)
        r.raise_for_status()
        data = r.json()
        return {
            "ok": True,
            "title": data.get("title") or (url or "（未命名）"),
            "kind": data.get("kind", "article"),
            "summary": data.get("summary", ""),
            "points": data.get("points") or []
        }
    except Exception as e:
        return {"error": f"呼叫 /analyze 失敗：{e}"}

def register():
    return {
        "name": "summarize_page",
        "version": "0.1.0",
        "description": "摘要當前網頁/新聞/文章",
        "triggers": ["分析網頁", "總結網頁", "新聞摘要", "天氣摘要", "summarize page"],
        "params_schema": {},
        "handler": summarize_page,
        "timeout_sec": 30,
    }
