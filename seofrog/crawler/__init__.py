"""
SEOFrog Modular Crawler System
Crawler modularizado para melhor organização e manutenibilidade
"""

from .core.crawler_factory import CrawlerFactory, CrawlerConfig, create_crawler, quick_crawl
from .models.crawl_result import CrawlResult

__version__ = "0.4.0"
__all__ = ["CrawlerFactory", "CrawlerConfig", "CrawlResult", "create_crawler", "quick_crawl"]