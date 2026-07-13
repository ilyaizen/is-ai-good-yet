import importlib


def test_scraper_resolves_pipeline_utils_package():
    scraper = importlib.import_module("src.scraper")
    assert scraper.get_browser_context_options.__module__ == "utils.stealth_utils"
