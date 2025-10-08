import importlib.util, inspect
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent / "plugins"

def load_plugins(logger=print):
    registry = {}
    for py in PLUGIN_DIR.glob("*.py"):
        if py.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(py.stem, py)
            mod = importlib.util.module_from_spec(spec)  # type: ignore
            assert spec and spec.loader
            spec.loader.exec_module(mod)                # type: ignore

            if not hasattr(mod, "register") or not inspect.isfunction(mod.register):
                logger(f"[plugin] {py.name} 無 register()，略過")
                continue

            meta = mod.register()
            name = meta.get("name", py.stem)
            handler = meta.get("handler")
            if not callable(handler):
                logger(f"[plugin] {name} handler 非可呼叫，略過")
                continue

            registry[name] = {**meta, "module": mod}
            logger(f"[plugin] 載入：{name} v{meta.get('version','?')}")
        except Exception as e:
            logger(f"[plugin] 失敗 {py.name} → {e}")
    return registry
