from playwright_stealth.stealth import Stealth  # type: ignore
import inspect

# Inspect the Stealth class and its methods
print("=== Playwright Stealth Inspection ===")

# Create a Stealth instance to inspect
stealth = Stealth()

print("Stealth class signature:")
print(inspect.signature(Stealth.__init__))

print("\nAvailable methods:")
for attr in dir(stealth):
    if not attr.startswith('_') and callable(getattr(stealth, attr)):
        obj = getattr(stealth, attr)
        try:
            sig = inspect.signature(obj)
            print(f"  {attr}{sig}")
        except Exception as e:
            print(f"  {attr}: {type(obj)} (signature unavailable: {e})")

print("\nKey async method for applying stealth:")
print(f"apply_stealth_async signature: {inspect.signature(stealth.apply_stealth_async)}")
print(f"Is coroutine function: {inspect.iscoroutinefunction(stealth.apply_stealth_async)}")

print("\nConfiguration options (showing first 10):")
config_attrs = [attr for attr in dir(stealth) if not attr.startswith('_') and not callable(getattr(stealth, attr))]
for attr in config_attrs[:10]:
    value = getattr(stealth, attr)
    print(f"  {attr}: {value}")

print(f"\n... and {len(config_attrs) - 10} more configuration options")

print("\n=== Usage Example ===")
print("from playwright_stealth.stealth import Stealth  # type: ignore")
print("from playwright.async_api import async_playwright")
print("")
print("async with async_playwright() as p:")
print("    browser = await p.chromium.launch()")
print("    context = await browser.new_context()")
print("    page = await context.new_page()")
print("    ")
print("    # Apply stealth")
print("    stealth = Stealth()")
print("    await stealth.apply_stealth_async(page)")
print("    ")
print("    # Now the page is stealthed!")