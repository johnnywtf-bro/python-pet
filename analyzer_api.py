# analyzer_api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import trafilatura
import re, os, json
from typing import Tuple, List, Optional
from urllib.parse import urlparse, unquote
from summarizer_plus import summarize_news_plus as _summarize_news
from summarizer_plus import summarize_article_plus as _summarize_article

# -------------- 小工具 --------------

def _pretty_url(url: str) -> str:
    """把超長網址轉成短標題：domain/path…"""
    if not url:
        return "(unknown)"
    try:
        p = urlparse(url)
        host = p.netloc or url
        if host.startswith("www."):
            host = host[4:]
        path = unquote(p.path or "/")
        if len(path) > 40:
            path = path[:40] + "…"
        return f"{host}{path}"
    except Exception:
        return url

def _sentences(txt: str):
    parts = re.split(r'(?<=[。！？!?.])\s+|\n+', (txt or "").strip())
    return [p.strip() for p in parts if p.strip()]

def _classify(url: str, title: str, text: str, mode: str) -> str:
    if mode in ("weather", "news", "article"):
        return mode
    low = f"{url} {title}".lower()
    if any(k in low for k in ["weather", "forecast", "天氣", "氣象"]):
        return "weather"
    if any(k in low for k in ["news", "breaking", "新聞"]):
        return "news"
    # 若正文出現明顯新聞關鍵詞也歸類新聞
    if re.search(r"(宣布|表示|指出|將於|發布|通過|上線|收購|合併)", text or ""):
        return "news"
    return "article"

def _summarize_weather(text: str) -> tuple[str, list[str]]:
    """產出：TL;DR + 要點（溫/體感/降雨/風/濕）"""
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    joined = " ".join(lines)

    def pick(pattern, default=""):
        m = re.search(pattern, joined)
        return m.group(1) if m else default

    now_temp = pick(r'(?:目前|現在)?\s*氣?溫[:：]?\s*(-?\d+)\s*°?C')
    feel     = pick(r'體感[:：]?\s*(-?\d+)\s*°?C')
    rain     = pick(r'(?:降雨(?:機率|機會)?[:：]?\s*)(\d{1,3})\s*%')
    wind     = pick(r'風速[:：]?\s*(\d{1,3})\s*(?:公里|km)/小時')
    humid    = pick(r'濕度[:：]?\s*(\d{1,3})\s*%')
    cond     = pick(r'(晴|多雲|陰|雨|雷雨|霧|雪)[^\s，。]*')

    pieces = []
    if cond: pieces.append(cond)
    if now_temp: pieces.append(f"{now_temp}°C")
    if feel: pieces.append(f"體感 {feel}°C")
    tldr = "，".join(pieces) if pieces else (lines[0] if lines else "天氣摘要")

    points = []
    if rain:  points.append(f"降雨：{rain}%")
    if wind:  points.append(f"風速：約 {wind} km/h")
    if humid: points.append(f"濕度：{humid}%")
    if rain and rain.isdigit() and int(rain) >= 40:
        points.append("建議：外出帶傘")
    if feel and now_temp:
        try:
            if abs(int(feel) - int(now_temp)) >= 3:
                points.append("體感與實際溫差較大，注意衣著")
        except Exception:
            pass

    summary = tldr + ("；" + "；".join(points) if points else "")
    return summary, points

# ===== 取代原本的 _summarize_news，放在 analyzer_api.py =====
import re, os, json
from typing import Tuple, List, Optional

def _clean(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()

def _top_k_sents(text: str, k: int = 5) -> List[str]:
    sents = _sentences(text)
    if not sents:
        return []
    # 句子打分：包含關鍵動詞 + 含數字/日期 + 在前段
    verb_pat = r"(宣布|表示|指出|稱|称|決定|决定|批准|通過|通过|推出|簽署|签署|開放|开放|調整|调整|起訴|起诉|爆發|爆发|發生|发生|抗議|抗议|撤回|限制|開工|开工|改建|拆除)"
    score = []
    n = len(sents)
    for i, s in enumerate(sents):
        sc = 0
        if re.search(verb_pat, s): sc += 3
        if re.search(r"\d{4}年|\d{1,2}月\d{1,2}日|今天|今日|昨日|明日|本週|本月", s): sc += 2
        if re.search(r"\d", s): sc += 1
        sc += max(0, 3 - i)            # 越靠前分數越高
        sc -= (len(s) > 120) * 1       # 太長扣分
        score.append((sc, i, s))
    score.sort(key=lambda x: (-x[0], x[1]))
    sel = [s for _, _, s in score[:k]]
    # 去重，保持順序
    seen, out = set(), []
    for s in sel:
        cs = _clean(s)
        if cs and cs not in seen:
            seen.add(cs); out.append(cs)
    return out

def _who_from_text(text: str) -> str:
    # 在常見動詞前的名詞片段（機構/人物/群體）
    pats = [
        r'([^\s，。；：,“”\'\"]{2,20}?)(?:\s*表示|\s*指出|\s*宣布|\s*稱|称|決定|决定|批准|通過|通过)',
        r'(?:由|經|经|由於|由于|由)\s*([^\s，。；：,“”\'\"]{2,20})\s*(?:宣佈|宣布|表示|決定|决定)'
    ]
    for p in pats:
        m = re.search(p, text)
        if m: return _clean(m.group(1))
    # 後備：抓帶有明顯機構字尾的詞
    m = re.search(r'([^\s，。；：,“”\'\"]{2,20}(?:政府|部|局|院|會|会|委|司|公司|法院|警方|軍|军|教堂|教會|教会|修道院|學校|学校|基金會|媒体|媒體|居民|遊客|游客|開發商|开发商))', text)
    return _clean(m.group(1)) if m else ""

def _when_from_text(text: str) -> str:
    m = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日|\d{1,2}月\d{1,2}日|今日|今天|昨日|明日|近日|本週|本月)', text)
    return m.group(1) if m else ""

def _where_from_text(text: str) -> str:
    m = re.search(r'(?:在|於|于|位於|位于)\s*([^\s，。；：,“”\'\"]{2,20})', text)
    if m: return _clean(m.group(1))
    # 後備：含地點尾綴
    m = re.search(r'([^\s，。；：,“”\'\"]{2,20}(?:省|市|州|縣|县|區|区|鎮|镇|鄉|乡|島|岛|國|国|寺|修道院|山|廣場|广场|港|灣|湾))', text)
    return _clean(m.group(1)) if m else ""

def _what_from_text(text: str) -> str:
    m = re.search(r'(宣布|表示|指出|決定|决定|批准|通過|通过|推出|簽署|签署|開放|开放|調整|调整|起訴|起诉|爆發|爆发|發生|发生|抗議|抗议|改建|拆除|重建|規劃|规划)([^，。；：]{0,40})', text)
    if not m:
        return ""
    return _clean(m.group(1) + m.group(2))

def _impact_from_text(text: str) -> str:
    m = re.search(r'(影響|影响|引發|引发|導致|导致|意味|可能|將使|将使|恐將|恐将)([^，。；：]{0,40})', text)
    return _clean(m.group(1) + m.group(2)) if m else ""

# --- 可選：用本地 LLM 直接輸出 JSON，失敗再退回規則法 ---
def _summarize_news_llm(title: str, text: str) -> Optional[Tuple[str, List[str]]]:
    base = os.getenv("NEWS_LLM_BASE")      # 例如：http://127.0.0.1:1234/v1  (LM Studio) 或 http://localhost:11434/v1 (Ollama)
    if not base:
        return None
    model = os.getenv("NEWS_LLM_MODEL", "qwen2.5:7b")
    api_key = os.getenv("NEWS_LLM_API_KEY", "not-needed")
    import requests
    prompt = f"""你是中文新聞抽取器。請用繁體中文輸出 JSON（不要任何多餘文字），欄位：
summary: 3~5 句重點摘要；who, when, where, what, impact: 各用最短片語。
{{"summary":"...", "who":"...", "when":"...", "where":"...", "what":"...", "impact":"..."}}
標題：{title}
正文：{text[:8000]}"""
    try:
        r = requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages":[{"role":"user","content": prompt}],
                "temperature": 0.2
            },
            timeout=25
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        j = json.loads(content)
        pts = []
        if j.get("who"):    pts.append("主體：" + j["who"])
        if j.get("when"):   pts.append("時間：" + j["when"])
        if j.get("where"):  pts.append("地點：" + j["where"])
        if j.get("what"):   pts.append("事件：" + j["what"])
        if j.get("impact"): pts.append("影響：" + j["impact"])
        return j.get("summary",""), pts
    except Exception:
        return None

def _summarize_news(title: str, text: str) -> Tuple[str, List[str]]:
    """優先 LLM（若設置 NEWS_LLM_BASE），否則使用加強版規則法。"""
    # 1) 嘗試 LLM JSON
    r = _summarize_news_llm(title, text)
    if r:
        return r

    # 2) 規則法
    sents = _top_k_sents(text, k=5)
    summary = " ".join(sents) if sents else "（沒有可用的新聞內容）"

    # 用全文來抽 5W1H（較準）；抽不到再用摘要兜底
    base = text if len(text) > 200 else summary
    who  = _who_from_text(base)   or "（未知）"
    when = _when_from_text(base)  or "（未明）"
    where= _where_from_text(base) or "（未明）"
    what = _what_from_text(base)  or "（未明）"
    impact = _impact_from_text(base)

    points = [f"主體：{who}", f"時間：{when}", f"地點：{where}", f"事件：{what}"]
    if impact:
        points.append(f"影響：{impact}")

    return summary, points


def _rendered_text_by_playwright(url: str) -> str:
    """（可選）用 Playwright 抓取渲染後文字；若未安裝/失敗則回空字串"""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=20000)
            page.wait_for_load_state("networkidle")
            txt = page.inner_text("body")
            browser.close()
            return txt
    except Exception:
        return ""

# -------------- FastAPI --------------

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 正式可改白名單
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeReq(BaseModel):
    url: str | None = None
    title: str | None = None
    text: str | None = None
    mode: str = "auto"  # 可強制指定 weather/news/article

class AnalyzeResp(BaseModel):
    title: str
    kind: str
    summary: str
    points: list[str] | None = None

@app.post("/analyze", response_model=AnalyzeResp)
def analyze(payload: AnalyzeReq):
    title = (payload.title or "").strip()
    text  = (payload.text  or "").strip()
    url   = (payload.url   or "").strip()

    # 1) 內容擷取（先 trafilatura；若太短且有 URL，再用 Playwright 回退）
    if (not text) and url:
        try:
            downloaded = trafilatura.fetch_url(url) or ""
            text = trafilatura.extract(downloaded, include_comments=False) or ""
        except Exception:
            text = ""
        if not title:
            title = _pretty_url(url)

    if len(text) < 200 and url:
        rendered = _rendered_text_by_playwright(url)
        if len(rendered) > len(text):
            text = rendered

    # 若仍然沒有文字，回基本訊息
    if not text:
        kind = _classify(url, title, "", payload.mode)
        return AnalyzeResp(
            title=title or _pretty_url(url) or "(無標題)",
            kind=kind,
            summary="（沒有取得任何文字）",
            points=None
        )

    # 2) 類型判斷
    kind = _classify(url, title, text, payload.mode)

    # 3) 產生摘要
    if kind == "weather":
        summary, points = _summarize_weather(text)
    elif kind == "news":
        summary, points = _summarize_news(title or _pretty_url(url), text)
    else:
        trimmed = text.replace("\n\n", "\n").strip()
        summary = trimmed[:600] + ("..." if len(trimmed) > 600 else "")
        points = None

    return AnalyzeResp(
        title=title or _pretty_url(url) or "(無標題)",
        kind=kind,
        summary=summary,
        points=points
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5005)
try:
    from summarizer_plus import summarize_news_plus as _summarize_news
    from summarizer_plus import summarize_article_plus as _summarize_article
    print("[analyzer_api] using summarizer_plus")
except Exception as e:
    print("[analyzer_api] summarizer_plus not available:", e)