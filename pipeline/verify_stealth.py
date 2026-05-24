
from playwright_stealth import stealth
import inspect
print("is coro:", inspect.iscoroutinefunction(stealth.stealth_async))
print("sig:", inspect.signature(stealth.stealth_async))
