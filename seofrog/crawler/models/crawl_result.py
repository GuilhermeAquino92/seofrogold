"""
CrawlResult data model
Modelo de dados para resultados de crawling
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class CrawlResult:
    """Resultado estruturado de um crawl individual"""
    url: str
    status_code: int
    final_url: str
    title: str = ""
    meta_description: str = ""
    h1_count: int = 0
    h2_count: int = 0
    internal_links: int = 0
    external_links: int = 0
    images_count: int = 0
    page_size: int = 0
    load_time: float = 0.0
    depth: int = 0
    crawl_timestamp: str = ""
    html_content: str = ""
    redirect_info: Dict = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.redirect_info is None:
            self.redirect_info = {}
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return asdict(self)
    
    def has_errors(self) -> bool:
        """Verifica se tem erros"""
        return len(self.errors) > 0
    
    def is_successful(self) -> bool:
        """Verifica se o crawl foi bem-sucedido"""
        return self.status_code == 200 and not self.has_errors()