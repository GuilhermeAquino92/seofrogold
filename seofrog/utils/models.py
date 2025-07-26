"""
SEOFrog v0.3 - Models and Dataclasses
Modelos e estruturas de dados do crawler
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime

@dataclass
class CrawlResult:
    """Resultado estruturado completo de um crawl"""
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
    images_without_alt: int = 0
    page_size: int = 0
    load_time: float = 0.0
    depth: int = 0
    crawl_timestamp: str = ""
    redirect_info: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    
    # Campos SEO avançados
    meta_keywords: str = ""
    canonical_url: str = ""
    viewport_meta: str = ""
    charset_meta: str = ""
    
    # Security fields
    mixed_content_issues: int = 0
    csp_header: str = ""
    x_frame_options: str = ""
    
    # Performance
    total_resources: int = 0
    css_files: int = 0
    js_files: int = 0
    
    # Debug fields (para troubleshooting avançado)
    headers: Optional[Dict[str, str]] = None
    http_chain: Optional[List[str]] = None  # Para debug de redirect loops
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.redirect_info is None:
            self.redirect_info = {}
        if self.headers is None:
            self.headers = {}
        if self.http_chain is None:
            self.http_chain = []
        if not self.crawl_timestamp:
            self.crawl_timestamp = datetime.now().isoformat()
    
    def __repr__(self) -> str:
        """Representação para logs estruturados"""
        return f"<CrawlResult {self.status_code} {self.url[:50]}{'...' if len(self.url) > 50 else ''}>"
    
    def __str__(self) -> str:
        """String representation amigável"""
        status_emoji = "✅" if self.status_code == 200 else "❌"
        return f"{status_emoji} {self.status_code} | {self.title[:30] or 'No Title'} | {self.url}"
    
    def is_successful(self) -> bool:
        """Verifica se crawl foi bem-sucedido"""
        return 200 <= self.status_code < 300
    
    def has_seo_issues(self) -> bool:
        """Detecta problemas SEO básicos"""
        return (
            not self.title or 
            len(self.title) > 60 or 
            len(self.title) < 30 or
            not self.meta_description or
            self.h1_count == 0 or
            self.h1_count > 1
        )
    
    def get_redirect_summary(self) -> str:
        """Sumário do redirect para logs"""
        if not self.redirect_info or self.url == self.final_url:
            return "No redirect"
        
        redirect_type = self.redirect_info.get('type', 'unknown')
        return f"{redirect_type}: {self.url} → {self.final_url}"
    
    def get_export_data(self) -> Dict[str, Any]:
        """Retorna dados limpos para exportação (CSV/Excel/API)"""
        return {
            'url': self.url,
            'status_code': self.status_code,
            'final_url': self.final_url,
            'title': self.title,
            'meta_description': self.meta_description,
            'h1_count': self.h1_count,
            'h2_count': self.h2_count,
            'internal_links': self.internal_links,
            'external_links': self.external_links,
            'images_count': self.images_count,
            'images_without_alt': self.images_without_alt,
            'page_size': self.page_size,
            'load_time': self.load_time,
            'depth': self.depth,
            'crawl_timestamp': self.crawl_timestamp,
            'meta_keywords': self.meta_keywords,
            'canonical_url': self.canonical_url,
            'viewport_meta': self.viewport_meta,
            'charset_meta': self.charset_meta,
            'mixed_content_issues': self.mixed_content_issues,
            'csp_header': self.csp_header,
            'x_frame_options': self.x_frame_options,
            'total_resources': self.total_resources,
            'css_files': self.css_files,
            'js_files': self.js_files,
            'redirect_type': self.redirect_info.get('type', '') if self.redirect_info else '',
            'is_redirect': self.url != self.final_url,
            'has_errors': len(self.errors) > 0 if self.errors else False,
            'error_summary': '; '.join(self.errors) if self.errors else ''
        }
    
    def get_seo_data(self) -> Dict[str, Any]:
        """Retorna apenas dados SEO específicos"""
        return {
            'url': self.url,
            'title': self.title,
            'title_length': len(self.title) if self.title else 0,
            'meta_description': self.meta_description,
            'meta_description_length': len(self.meta_description) if self.meta_description else 0,
            'meta_keywords': self.meta_keywords,
            'canonical_url': self.canonical_url,
            'h1_count': self.h1_count,
            'h2_count': self.h2_count,
            'images_count': self.images_count,
            'images_without_alt': self.images_without_alt,
            'internal_links': self.internal_links,
            'external_links': self.external_links,
            'has_seo_issues': self.has_seo_issues(),
            'seo_score': self._calculate_seo_score()
        }
    
    def get_security_data(self) -> Dict[str, Any]:
        """Retorna apenas dados de segurança"""
        return {
            'url': self.url,
            'csp_header': self.csp_header,
            'x_frame_options': self.x_frame_options,
            'mixed_content_issues': self.mixed_content_issues,
            'has_security_headers': bool(self.csp_header or self.x_frame_options),
            'security_score': self._calculate_security_score()
        }
    
    def _calculate_seo_score(self) -> int:
        """Calcula score SEO básico (0-100)"""
        score = 100
        
        # Title issues
        if not self.title:
            score -= 25
        elif len(self.title) > 60 or len(self.title) < 30:
            score -= 10
        
        # Meta description issues  
        if not self.meta_description:
            score -= 20
        elif len(self.meta_description) > 160 or len(self.meta_description) < 120:
            score -= 5
        
        # H1 issues
        if self.h1_count == 0:
            score -= 15
        elif self.h1_count > 1:
            score -= 5
        
        # Images without ALT
        if self.images_count > 0 and self.images_without_alt > 0:
            score -= min(10, (self.images_without_alt / self.images_count) * 10)
        
        return max(0, int(score))
    
    def _calculate_security_score(self) -> int:
        """Calcula score de segurança básico (0-100)"""
        score = 0
        
        if self.csp_header:
            score += 40
        if self.x_frame_options:
            score += 30
        if self.mixed_content_issues == 0:
            score += 30
        
        return min(100, int(score))

@dataclass
class CrawlConfig:
    """Configuração completa do crawler"""
    max_urls: int = 1000
    max_depth: int = 3
    max_workers: int = 10
    delay: float = 0.5
    timeout: int = 30
    max_redirects: int = 10
    respect_robots: bool = True
    follow_redirects: bool = True
    crawl_images: bool = False
    crawl_css: bool = False
    crawl_js: bool = False
    crawl_pdf: bool = False
    user_agent: str = "SEOFrog/0.3 Enterprise"
    retry_attempts: int = 2
    output_dir: str = "./crawl_output"
    export_format: str = "xlsx"
    log_level: str = "INFO"
    auto_save_interval: int = 100
    
    def validate(self, cli_safe: bool = False) -> Union[bool, Tuple[bool, str]]:
        """
        Valida configuração
        
        Args:
            cli_safe: Se True, retorna (bool, str) em vez de raise exception
            
        Returns:
            bool se cli_safe=False, ou (bool, error_message) se cli_safe=True
        """
        errors = []
        
        if self.max_urls <= 0:
            errors.append("max_urls deve ser > 0")
        if self.max_depth < 0:
            errors.append("max_depth deve ser >= 0")
        if self.max_workers <= 0:
            errors.append("max_workers deve ser > 0")
        if self.delay < 0:
            errors.append("delay deve ser >= 0")
        if self.timeout <= 0:
            errors.append("timeout deve ser > 0")
        if self.export_format not in ['csv', 'xlsx']:
            errors.append("export_format deve ser 'csv' ou 'xlsx'")
        
        if errors:
            error_msg = "; ".join(errors)
            if cli_safe:
                return False, error_msg
            else:
                raise ValueError(error_msg)
        
        return True if cli_safe else True
    
    def __repr__(self) -> str:
        """Representação para debug"""
        return f"<CrawlConfig max_urls={self.max_urls} workers={self.max_workers} depth={self.max_depth}>"
    
    def get_summary(self) -> str:
        """Sumário da configuração para logs"""
        return f"{self.max_urls:,} URLs, depth {self.max_depth}, {self.max_workers} workers, delay {self.delay}s"
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return asdict(self)

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def create_crawl_result(url: str, status_code: int, **kwargs) -> CrawlResult:
    """Factory function para criar CrawlResult"""
    return CrawlResult(
        url=url,
        status_code=status_code,
        final_url=kwargs.get('final_url', url),
        **kwargs
    )

def create_error_result(url: str, error_message: str, depth: int = 0) -> CrawlResult:
    """Factory function para criar resultado de erro"""
    return CrawlResult(
        url=url,
        status_code=0,
        final_url=url,
        depth=depth,
        errors=[error_message],
        crawl_timestamp=datetime.now().isoformat()
    )

def create_result_from_export_data(export_data: Dict[str, Any]) -> CrawlResult:
    """Factory function para recriar CrawlResult a partir de dados exportados"""
    
    # Extrai campos básicos
    result = CrawlResult(
        url=export_data.get('url', ''),
        status_code=export_data.get('status_code', 0),
        final_url=export_data.get('final_url', ''),
        title=export_data.get('title', ''),
        meta_description=export_data.get('meta_description', ''),
        h1_count=export_data.get('h1_count', 0),
        h2_count=export_data.get('h2_count', 0),
        internal_links=export_data.get('internal_links', 0),
        external_links=export_data.get('external_links', 0),
        images_count=export_data.get('images_count', 0),
        images_without_alt=export_data.get('images_without_alt', 0),
        page_size=export_data.get('page_size', 0),
        load_time=export_data.get('load_time', 0.0),
        depth=export_data.get('depth', 0),
        crawl_timestamp=export_data.get('crawl_timestamp', ''),
        meta_keywords=export_data.get('meta_keywords', ''),
        canonical_url=export_data.get('canonical_url', ''),
        viewport_meta=export_data.get('viewport_meta', ''),
        charset_meta=export_data.get('charset_meta', ''),
        mixed_content_issues=export_data.get('mixed_content_issues', 0),
        csp_header=export_data.get('csp_header', ''),
        x_frame_options=export_data.get('x_frame_options', ''),
        total_resources=export_data.get('total_resources', 0),
        css_files=export_data.get('css_files', 0),
        js_files=export_data.get('js_files', 0)
    )
    
    # Reconstrói redirect_info se necessário
    if export_data.get('redirect_type'):
        result.redirect_info = {
            'type': export_data.get('redirect_type', ''),
            'is_redirect': export_data.get('is_redirect', False)
        }
    
    # Reconstrói errors se necessário
    if export_data.get('error_summary'):
        result.errors = export_data.get('error_summary', '').split('; ')
    
    return result