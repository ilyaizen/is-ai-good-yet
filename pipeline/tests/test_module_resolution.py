import importlib
from pathlib import Path


def test_scraper_resolves_pipeline_utils_package():
    scraper = importlib.import_module("src.scraper")
    utils_path = Path(scraper.get_browser_context_options.__module__.replace(".", "/"))

    assert str(utils_path) == "utils/stealth_utils"
