"""
SEOFrog v0.3 - Utilities Package
"""

from .models import CrawlResult, CrawlConfig, create_crawl_result, create_error_result, create_result_from_export_data

__all__ = [
    'CrawlResult',
    'CrawlConfig', 
    'create_crawl_result',
    'create_error_result',
    'create_result_from_export_data',
]
