"""Multi-strategy content extraction with fallback support."""

from .base import ScraperStrategy
from .trafilatura_scraper import TrafilaturaScraper
from .newspaper_scraper import NewspaperScraper
from .archive_scraper import ArchiveScraper

from .simple_scraper import SimpleScraper

# Optional Selenium-based scraper (requires undetected-chromedriver)
try:
    from .selenium_archive import SeleniumArchiveScraper, SELENIUM_AVAILABLE
except ImportError:
    SeleniumArchiveScraper = None  # type: ignore
    SELENIUM_AVAILABLE = False

__all__ = [
    "ScraperStrategy",
    "TrafilaturaScraper",
    "NewspaperScraper",
    "SimpleScraper",
    "ArchiveScraper",
    "SeleniumArchiveScraper",
    "SELENIUM_AVAILABLE",
]

