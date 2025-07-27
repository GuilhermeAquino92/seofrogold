"""
Simple Page Parser
Parser simples para extração básica de dados da página
"""

from urllib.parse import urlparse, urljoin
from datetime import datetime
import logging

from ..models.crawl_result import CrawlResult
from .redirect_classifier import RedirectClassifier


class SimplePageParser:
    """
    📄 Parser simples para extração básica de dados da página
    Substituto temporário até integração com parsers modulares existentes
    """
    
    def __init__(self):
        self.redirect_classifier = RedirectClassifier()
        self.logger = logging.getLogger('SimplePageParser')
    
    def parse_response(self, response, original_url: str, depth: int) -> CrawlResult:
        """
        Parseia response HTTP para CrawlResult (sem BeautifulSoup)
        """
        result = CrawlResult(
            url=original_url,
            status_code=response.status_code,
            final_url=str(response.url),
            depth=depth,
            crawl_timestamp=datetime.now().isoformat()
        )
        
        # Parse básico do conteúdo HTML sem BeautifulSoup
        if response.status_code == 200 and self._is_html_content(response):
            try:
                self._extract_page_data_simple(response.text, result, original_url)
            except Exception as e:
                result.errors.append(f"Parse error: {str(e)}")
                self.logger.warning(f"Error parsing {original_url}: {e}")
        
        # Classificação de redirect
        if original_url != str(response.url):
            # Simula chain de status codes (simplificado)
            status_chain = [response.status_code] if response.status_code != 200 else [301]
            result.redirect_info = self.redirect_classifier.classify_redirect(
                original_url, str(response.url), status_chain
            )
        
        # Page size
        if hasattr(response, 'content'):
            result.page_size = len(response.content)
        elif hasattr(response, 'text'):
            result.page_size = len(response.text.encode('utf-8'))
        
        return result
    
    def _is_html_content(self, response) -> bool:
        """Verifica se o conteúdo é HTML"""
        # Try both lowercase and title case for compatibility
        content_type = response.headers.get('content-type', '') or response.headers.get('Content-Type', '')
        content_type = content_type.lower()
        return 'text/html' in content_type
    
    def _extract_page_data_simple(self, html_text: str, result: CrawlResult, original_url: str):
        """Extrai dados da página usando regex simples (sem BeautifulSoup)"""
        import re
        
        # Salva HTML content para análise DOM posterior
        result.html_content = html_text
        
        # Title - busca simples
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html_text, re.IGNORECASE | re.DOTALL)
        result.title = title_match.group(1).strip() if title_match else ""
        
        # Meta description
        meta_desc_match = re.search(
            r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', 
            html_text, re.IGNORECASE
        )
        if not meta_desc_match:
            meta_desc_match = re.search(
                r'<meta[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']', 
                html_text, re.IGNORECASE
            )
        result.meta_description = meta_desc_match.group(1).strip() if meta_desc_match else ""
        
        # Headings - conta ocorrências
        result.h1_count = len(re.findall(r'<h1[^>]*>', html_text, re.IGNORECASE))
        result.h2_count = len(re.findall(r'<h2[^>]*>', html_text, re.IGNORECASE))
        
        # Links - extração simples
        self._extract_links_simple(html_text, result, original_url)
        
        # Images - conta tags img
        result.images_count = len(re.findall(r'<img[^>]*>', html_text, re.IGNORECASE))
    
    def _extract_links_simple(self, html_text: str, result: CrawlResult, original_url: str):
        """Extrai e classifica links da página usando regex"""
        import re
        
        domain = urlparse(original_url).netloc
        internal_links = 0
        external_links = 0
        
        # Find all href attributes
        href_pattern = r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>'
        hrefs = re.findall(href_pattern, html_text, re.IGNORECASE)
        
        for href in hrefs:
            href = href.strip()
            
            # Skip empty hrefs, mailto, tel, etc.
            if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                continue
            
            try:
                # Resolve absolute URL
                if href.startswith('http'):
                    absolute_url = href
                else:
                    absolute_url = urljoin(original_url, href)
                
                link_domain = urlparse(absolute_url).netloc
                
                if link_domain == domain:
                    internal_links += 1
                elif link_domain:  # External link with valid domain
                    external_links += 1
                    
            except Exception as e:
                self.logger.debug(f"Error processing link {href}: {e}")
                continue
        
        result.internal_links = internal_links
        result.external_links = external_links
    
    def _create_basic_result(self, response, original_url: str, depth: int, errors: list) -> CrawlResult:
        """Cria resultado básico quando parsing completo falha"""
        return CrawlResult(
            url=original_url,
            status_code=response.status_code,
            final_url=str(response.url),
            depth=depth,
            crawl_timestamp=datetime.now().isoformat(),
            errors=errors,
            page_size=len(response.content) if hasattr(response, 'content') else 0
        )
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do parser"""
        return {
            'redirect_stats': self.redirect_classifier.get_stats()
        }