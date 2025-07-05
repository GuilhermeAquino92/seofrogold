"""
PATCH 1: seofrog/parsers/links_parser.py
Corrige estrutura de dados para redirects por URL
"""

import re
import time
import requests
from urllib.parse import urlparse, urljoin, urlunparse
from typing import Dict, Any, List, Optional
from collections import defaultdict
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

        # ✅ CORREÇÃO PRINCIPAL: Armazenamento por URL em vez de lista global
        self.internal_redirect_links_by_url = defaultdict(list)
        self.internal_redirect_links = []  # Mantido para compatibilidade

    def parse(self, soup: BeautifulSoup, page_url: str, word_count: Optional[int] = None) -> Dict[str, Any]:
        """
        Parse principal com correções de robustez
        """
        all_links = soup.find_all('a')
        total_links = len(all_links)
        internal_links = []
        external_links = []
        internal_links_details = []  # ✅ NOVO: Detalhes de links internos

        parsed_page = urlparse(page_url)

        for tag in all_links:
            href = tag.get('href')
            anchor_text = str(tag.get_text(strip=True) or '')  # ✅ Blindagem contra None
            
            if not href or href.startswith('javascript:') or href.startswith('#'):
                continue

            try:
                joined_url = urljoin(page_url, href)
                parsed_href = urlparse(joined_url)

                is_internal = parsed_page.netloc == parsed_href.netloc
                
                if is_internal:
                    internal_links.append(joined_url)
                    
                    # ✅ NOVO: Coleta detalhes de todos os links internos
                    link_details = {
                        'from_url': page_url,
                        'to_url': joined_url,
                        'anchor_text': anchor_text,
                        'alt_text': str(tag.get('alt', '') or ''),
                        'title_attr': str(tag.get('title', '') or ''),
                        'follow': not ('nofollow' in str(tag.get('rel', '')).lower()),
                        'target': str(tag.get('target', '') or ''),
                        'rel': str(tag.get('rel', '') or ''),
                        'link_path': self._get_element_path(tag)
                    }
                    internal_links_details.append(link_details)
                    
                    # Verifica redirect se habilitado
                    if self.enable_redirects:
                        self._check_and_store_redirect(page_url, joined_url, anchor_text, tag)
                        
                else:
                    external_links.append(joined_url)
                    
            except Exception as e:
                self.logger.debug(f"Erro processando link {href}: {e}")
                continue

        internal_ratio = len(internal_links) / total_links if total_links > 0 else 0
        links_per_100_words = total_links / (word_count / 100) if word_count else None

        # ✅ Log informativo
        if internal_links:
            self.logger.debug(f"Encontrados {len(internal_links)} links internos em {page_url}")
        
        redirects_for_this_url = self.internal_redirect_links_by_url.get(page_url, [])
        if redirects_for_this_url:
            self.logger.info(f"🔄 {len(redirects_for_this_url)} redirects detectados em {page_url}")

        return {
            'total_links': total_links,
            'internal_links': len(internal_links),
            'external_links': len(external_links),
            'internal_links_ratio': round(internal_ratio, 2),
            'links_per_100_words': round(links_per_100_words, 2) if links_per_100_words else None,
            'internal_links_details': internal_links_details,  # ✅ NOVO: Detalhes dos links
            'internal_redirects_for_this_url': redirects_for_this_url  # ✅ NOVO: Redirects específicos desta URL
        }

    def _check_and_store_redirect(self, page_url: str, link_url: str, anchor_text: str, tag):
        """
        ✅ NOVO: Verifica redirect e armazena por URL de origem
        """
        try:
            resolved_url, status_code = self._resolve_redirect(link_url)
            
            if resolved_url != link_url and status_code in (301, 302, 303, 307, 308):
                criticidade = 'Alta' if self._is_non_canonical_redirect(link_url, resolved_url) else 'Média'
                
                # ✅ Estrutura normalizada e validada
                redirect_data = {
                    'from_url': page_url,
                    'to_original': link_url,
                    'to_final': resolved_url,
                    'anchor_text': str(anchor_text or ''),
                    'alt_text': str(tag.get('alt', '') or ''),
                    'follow': not ('nofollow' in str(tag.get('rel', '')).lower()),
                    'target': str(tag.get('target', '') or ''),
                    'rel': str(tag.get('rel', '') or ''),
                    'status_code': status_code,
                    'criticidade': criticidade,
                    'link_path': self._get_element_path(tag),
                    'sugestao': f"Atualizar link para {resolved_url}"
                }
                
                # ✅ Validação: só adiciona se campos obrigatórios existem
                required_fields = ['from_url', 'to_original', 'to_final', 'status_code']
                if all(redirect_data.get(field) for field in required_fields):
                    # Armazena por URL de origem
                    self.internal_redirect_links_by_url[page_url].append(redirect_data)
                    # Mantém compatibilidade com versão antiga
                    self.internal_redirect_links.append(redirect_data)
                    
                    self.logger.debug(f"Redirect armazenado: {link_url} → {resolved_url} ({status_code})")
                else:
                    self.logger.warning(f"Redirect malformado ignorado: {redirect_data}")
                    
            time.sleep(self.redirect_rate_limit)
            
        except Exception as e:
            self.logger.debug(f"Erro verificando redirect {link_url}: {e}")

    def _get_element_path(self, element) -> str:
        """
        ✅ NOVO: Gera path DOM do elemento
        """
        try:
            path_parts = []
            current = element
            
            while current and current.name:
                # Calcula posição entre irmãos do mesmo tipo
                siblings = [sibling for sibling in current.parent.find_all(current.name, recursive=False) if sibling.name == current.name]
                position = siblings.index(current) + 1 if len(siblings) > 1 else 1
                
                if position > 1:
                    path_parts.append(f"{current.name}[{position}]")
                else:
                    path_parts.append(current.name)
                    
                current = current.parent
                
                # Limita profundidade para evitar paths muito longos
                if len(path_parts) > 10:
                    break
            
            # Inverte para ficar do root para o elemento
            path_parts.reverse()
            return "/" + "/".join(path_parts) if path_parts else "/unknown"
            
        except Exception:
            return "/body/div[1]/section/div/a[1]"  # Fallback genérico

    def _resolve_redirect(self, url: str) -> tuple:
        """
        Resolve redirect com timeout e tratamento de erro melhorado
        """
        try:
            response = requests.head(
                url, 
                allow_redirects=True, 
                timeout=self.redirect_timeout,
                headers={'User-Agent': 'SEOFrog/0.2 (+https://seofrog.com/bot)'}
            )
            return response.url, response.status_code
        except requests.RequestException as e:
            self.logger.debug(f"Erro resolvendo redirect {url}: {e}")
            return url, 0

    def _is_non_canonical_redirect(self, original: str, final: str) -> bool:
        """
        Detecta redirect por capitalização, trailing slash, parâmetros etc.
        """
        try:
            o = urlparse(original)
            f = urlparse(final)

            return (
                o.scheme != f.scheme or
                o.netloc != f.netloc or
                o.path.rstrip('/') != f.path.rstrip('/') or
                o.query != f.query
            )
        except Exception:
            return True  # Em caso de erro, assume que é não-canônico
    
    def get_redirects_for_url(self, url: str) -> List[Dict[str, Any]]:
        """
        ✅ NOVO: Método público para obter redirects de uma URL específica
        """
        return self.internal_redirect_links_by_url.get(url, [])
    
    def get_total_redirects_count(self) -> int:
        """
        ✅ NOVO: Retorna total de redirects encontrados
        """
        return sum(len(redirects) for redirects in self.internal_redirect_links_by_url.values())
    
    def log_redirect_summary(self):
        """
        ✅ NOVO: Log resumo dos redirects encontrados
        """
        total_redirects = self.get_total_redirects_count()
        total_urls_with_redirects = len(self.internal_redirect_links_by_url)
        
        if total_redirects > 0:
            self.logger.info(f"🔄 Resumo redirects: {total_redirects} redirects em {total_urls_with_redirects} URLs")
        else:
            self.logger.info("✅ Nenhum link interno com redirect encontrado")