"""
seofrog/core/exceptions.py
Sistema de exceções enterprise do SEOFrog
"""

from typing import Optional, Dict, Any

class SEOFrogException(Exception):
    """Base exception para SEOFrog"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message

class ConfigException(SEOFrogException):
    """Erro de configuração"""
    pass

class CrawlException(SEOFrogException):
    """Erro durante crawling"""
    
    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None, **kwargs):
        details = {'url': url, 'status_code': status_code}
        details.update(kwargs)
        super().__init__(message, details)

class NetworkException(SEOFrogException):
    """Erro de rede"""
    
    def __init__(self, message: str, url: Optional[str] = None, retry_count: int = 0, **kwargs):
        details = {'url': url, 'retry_count': retry_count}
        details.update(kwargs)
        super().__init__(message, details)

class ParseException(SEOFrogException):
    """Erro durante parsing"""
    
    def __init__(self, message: str, url: Optional[str] = None, parser_type: Optional[str] = None, **kwargs):
        details = {'url': url, 'parser_type': parser_type}
        details.update(kwargs)
        super().__init__(message, details)

class ExportException(SEOFrogException):
    """Erro durante export"""
    
    def __init__(self, message: str, filename: Optional[str] = None, format_type: Optional[str] = None, **kwargs):
        details = {'filename': filename, 'format_type': format_type}
        details.update(kwargs)
        super().__init__(message, details)

class ValidationException(SEOFrogException):
    """Erro de validação"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        details = {'field': field, 'value': value}
        details.update(kwargs)
        super().__init__(message, details)

class RobotsException(SEOFrogException):
    """Erro relacionado a robots.txt"""
    
    def __init__(self, message: str, robots_url: Optional[str] = None, **kwargs):
        details = {'robots_url': robots_url}
        details.update(kwargs)
        super().__init__(message, details)

class SitemapException(SEOFrogException):
    """Erro relacionado a sitemap.xml"""
    
    def __init__(self, message: str, sitemap_url: Optional[str] = None, **kwargs):
        details = {'sitemap_url': sitemap_url}
        details.update(kwargs)
        super().__init__(message, details)

class MemoryException(SEOFrogException):
    """Erro de memória/recursos"""
    
    def __init__(self, message: str, memory_usage: Optional[int] = None, limit: Optional[int] = None, **kwargs):
        details = {'memory_usage_mb': memory_usage, 'limit_mb': limit}
        details.update(kwargs)
        super().__init__(message, details)

class URLException(SEOFrogException):
    """Erro relacionado a URLs"""
    
    def __init__(self, message: str, url: Optional[str] = None, **kwargs):
        details = {'url': url}
        details.update(kwargs)
        super().__init__(message, details)

# === HELPER FUNCTIONS ===

def handle_exception(func):
    """Decorator para handling padrão de exceções"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SEOFrogException:
            raise  # Re-raise SEOFrog exceptions
        except Exception as e:
            # Convert generic exceptions to SEOFrogException
            raise SEOFrogException(f"Unexpected error in {func.__name__}: {str(e)}")
    return wrapper