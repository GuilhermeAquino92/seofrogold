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
    
    # Campos adicionais para compatibilidade com parsers modulares
    meta_keywords: str = ""
    canonical_url: str = ""
    robots_meta: str = ""
    h1: str = ""
    headings: List = None
    charset: str = ""
    content_type: str = ""
    server: str = ""
    response_headers: Dict = None
    og_data: Dict = None
    twitter_data: Dict = None
    schema_org: List = None
    images: List = None
    image_count: int = 0
    security_headers: Dict = None
    mixed_content: List = None
    word_count: int = 0
    text_content: str = ""
    links_internal: List = None
    links_external: List = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.redirect_info is None:
            self.redirect_info = {}
        if self.headings is None:
            self.headings = []
        if self.response_headers is None:
            self.response_headers = {}
        if self.og_data is None:
            self.og_data = {}
        if self.twitter_data is None:
            self.twitter_data = {}
        if self.schema_org is None:
            self.schema_org = []
        if self.images is None:
            self.images = []
        if self.security_headers is None:
            self.security_headers = {}
        if self.mixed_content is None:
            self.mixed_content = []
        if self.links_internal is None:
            self.links_internal = []
        if self.links_external is None:
            self.links_external = []
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return asdict(self)
    
    def has_errors(self) -> bool:
        """Verifica se tem erros"""
        return len(self.errors) > 0
    
    def is_successful(self) -> bool:
        """Verifica se o crawl foi bem-sucedido"""
        return self.status_code == 200 and not self.has_errors()