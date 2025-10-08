def route_input_to_plugin(user_text: str, executor: "FunctionExecutor"):
    name, _meta = executor.find_by_trigger(user_text)
    if not name:
        return None, None
    # 抽 URL（「分析網頁 https://...」）
    kwargs = {}
    for p in (user_text or "").split():
        if p.startswith("http://") or p.startswith("https://"):
            kwargs["url"] = p
            break
    return name, kwargs
