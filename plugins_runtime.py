from plugin_loader import load_plugins
from plugin_executor import FunctionExecutor

_executor = None

def get_executor():
    global _executor
    if _executor is None:
        _executor = FunctionExecutor(load_plugins())
    return _executor

def reload_plugins():
    global _executor
    _executor = FunctionExecutor(load_plugins())
    return _executor
