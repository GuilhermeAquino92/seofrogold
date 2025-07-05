"""
seofrog/parsers/links_parser.py
Parser especializado para links internos, externos e redirects
"""

import re
import time
import requests
from urllib.parse import urlparse, urljoin, urlunparse
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup, Tag
from seofrog.parsers.base import ParserMixin, SeverityLevel

class LinksParser(ParserMixin):
    """
    Parser especializado para análise completa de links
    Responsável por: links internos/externos, anchor text, redirects, link building
    """

    def __init__(self, enable_redirects: bool = True, redirect_timeout: int = 3):
        super().__init__()

        # Configurações de análise
        self.enable_redirects = enable_redirects
        self.redirect_timeout = redirect_timeout
        self.redirect_rate_limit = 0.1  # 100ms entre requests

        # Configurações de qualidade
        self.ideal_internal_links_ratio = 0.8  # 80% links internos
        self.max_links_per_100_words = 10

        # Armazenamento para exportação
        self.internal_redirect_links = []

    def parse(self, soup: BeautifulSoup, page_url: str, word_count: Optional[int] = None) -> Dict[str, Any]:
        all_links = soup.find_all('a')
        total_links = len(all_links)
        internal_links = []
        external_links = []

        parsed_page = urlparse(page_url)

        for tag in all_links:
            href = tag.get('href')
            anchor_text = tag.get_text(strip=True)
            if not href or href.startswith('javascript:') or href.startswith('#'):
                continue

            joined_url = urljoin(page_url, href)
            parsed_href = urlparse(joined_url)

            is_internal = parsed_page.netloc == parsed_href.netloc
            if is_internal:
                internal_links.append(joined_url)
            else:
                external_links.append(joined_url)

            # Verifica redirect se habilitado
            if self.enable_redirects and is_internal:
                try:
                    resolved_url, status_code = self._resolve_redirect(joined_url)
                    if resolved_url != joined_url and status_code in (301, 302):
                        criticidade = 'Alta' if self._is_non_canonical_redirect(joined_url, resolved_url) else 'Média'
                        sugestao = f"Atualizar link para {resolved_url}"
                        self.internal_redirect_links.append({
                            "From": page_url,
                            "To (Original)": joined_url,
                            "To (Final)": resolved_url,
                            "Anchor": anchor_text,
                            "Código": status_code,
                            "Criticidade": criticidade,
                            "Sugestão": sugestao
                        })
                    time.sleep(self.redirect_rate_limit)
                except Exception:
                    continue

        internal_ratio = len(internal_links) / total_links if total_links > 0 else 0
        links_per_100_words = total_links / (word_count / 100) if word_count else None

        return {
            'total_links': total_links,
            'internal_links': len(internal_links),
            'external_links': len(external_links),
            'internal_links_ratio': round(internal_ratio, 2),
            'links_per_100_words': round(links_per_100_words, 2) if links_per_100_words else None
        }

    def _resolve_redirect(self, url: str) -> (str, int):
        try:
            response = requests.head(url, allow_redirects=True, timeout=self.redirect_timeout)
            return response.url, response.status_code
        except requests.RequestException:
            return url, 0

    def _is_non_canonical_redirect(self, original: str, final: str) -> bool:
        # Detecta redirect por capitalização, trailing slash, parâmetros etc.
        o = urlparse(original)
        f = urlparse(final)

        return (
            o.scheme != f.scheme or
            o.netloc != f.netloc or
            o.path.rstrip('/') != f.path.rstrip('/') or
            o.query != f.query
        )
