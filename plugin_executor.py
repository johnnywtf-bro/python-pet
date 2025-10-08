import concurrent.futures

class FunctionExecutor:
    def __init__(self, plugins_registry, logger=print):
        self.logger = logger
        self.plugins = plugins_registry
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    def find_by_trigger(self, text: str):
        t = (text or "").lower()
        for name, meta in self.plugins.items():
            for trig in meta.get("triggers", []):
                if trig.lower() in t:
                    return name, meta
        return None, None

    def call(self, name: str, **kwargs):
        meta = self.plugins.get(name)
        if not meta:
            return {"error": f"未知插件：{name}"}
        handler = meta["handler"]
        timeout = meta.get("timeout_sec", 30)
        fut = self.pool.submit(handler, **kwargs)
        try:
            return fut.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return {"error": f"執行逾時（{timeout}s）"}
        except Exception as e:
            return {"error": f"執行失敗：{e}"}
