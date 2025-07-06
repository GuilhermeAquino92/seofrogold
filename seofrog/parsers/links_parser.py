"""
seofrog/parsers/links_parser.py
Parser completo para links internos - REFATORAÇÃO 100% com todas as melhorias
"""

import re
import time
import requests
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from bs4 import BeautifulSoup, Tag
from seofrog.parsers.base import ParserMixin
from seofrog.utils.redirect_cache import create_redirect_cache
from seofrog.utils.url_normalizer import urls_are_equivalent


class LinksParser(ParserMixin):
    """Parser para análise completa de links internos com todas as otimizações"""

    def __init__(self, enable_redirects: bool = True, redirect_timeout: int = 3):
        super().__init__()
        
        self.enable_redirects = enable_redirects
        self.redirect_timeout = redirect_timeout
        self.redirect_rate_limit = 0.1
        
        self.internal_redirect_links_by_url = defaultdict(list)
        self.internal_redirect_links = []
        self.all_internal_links_by_url = defaultdict(list)  # NOVO: todos os links
        
        if enable_redirects:
            self.redirect_cache = create_redirect_cache(
                cache_dir="seofrog_cache",
                ttl_hours=24,
            )
        else:
            self.redirect_cache = None

    def parse(self, soup: BeautifulSoup, page_url: str, word_count: Optional[int] = None) -> Dict[str, Any]:
        """Parse principal com features completas e otimizadas"""
        
        all_links = soup.find_all('a')
        total_links = len(all_links)
        internal_links = []
        external_links = []
        internal_links_details = []

        parsed_page = urlparse(page_url)

        for tag in all_links:
            href = tag.get('href')
            
            if not href or href.startswith('javascript:') or href.startswith('#'):
                continue

            try:
                joined_url = urljoin(page_url, href)
                parsed_href = urlparse(joined_url)
                is_internal = parsed_page.netloc == parsed_href.netloc
                
                if is_internal:
                    internal_links.append(joined_url)
                    
                    # Extrai dados completos do link
                    link_data = self._extract_link_data(tag, page_url, joined_url)
                    internal_links_details.append(link_data)
                    
                    # Armazena TODOS os links internos (não só redirects)
                    self.all_internal_links_by_url[page_url].append(link_data)
                    
                    # Verifica redirect se habilitado
                    if self.enable_redirects:
                        cache_hit = self._check_and_store_redirect(page_url, joined_url, link_data, tag)
                        
                        # MELHORIA 3: Sleep apenas se não foi cache hit
                        if not cache_hit:
                            time.sleep(self.redirect_rate_limit)
                        
                else:
                    external_links.append(joined_url)
                    
            except Exception as e:
                self.logger.debug(f"Erro processando link {href}: {e}")
                continue

        internal_ratio = len(internal_links) / total_links if total_links > 0 else 0
        links_per_100_words = total_links / (word_count / 100) if word_count else None

        redirects_for_this_url = self.internal_redirect_links_by_url.get(page_url, [])

        return {
            'total_links': total_links,
            'internal_links': len(internal_links),
            'external_links': len(external_links),
            'internal_links_ratio': round(internal_ratio, 2),
            'links_per_100_words': round(links_per_100_words, 2) if links_per_100_words else None,
            'internal_links_details': internal_links_details,
            'internal_redirects_for_this_url': redirects_for_this_url
        }

    def _extract_link_data(self, tag: Tag, from_url: str, to_url: str) -> Dict[str, str]:
        """Extrai dados completos do link para aba Internal"""
        
        # FEATURE 1: Anchor Text real (conteúdo visível)
        anchor_text = tag.get_text(strip=True)
        
        # FEATURE 2: Alt Text da imagem contida no link
        img = tag.find('img')
        alt_text = img.get('alt') if img and img.has_attr('alt') else ""
        
        # FEATURE 3: Target e Rel completos
        target_attr = tag.get('target', '')
        rel_attr = ', '.join(tag.get('rel')) if tag.has_attr('rel') else ''
        
        # FEATURE 4: XPath real do link no DOM
        xpath = self._generate_xpath(tag)
        
        # FEATURE 5: Normalizar campos vazios como string
        return {
            'Type': 'Hyperlink',
            'From': str(from_url),
            'To Original': str(to_url),  # MELHORIA 5: URL original do HTML
            'To Final': str(to_url),     # MELHORIA 5: URL final após redirect
            'Anchor': str(anchor_text),
            'Alt Text': str(alt_text),
            'Follow': str(not ('nofollow' in rel_attr.lower())),
            'Target': str(target_attr),
            'Rel': str(rel_attr),
            'Status Code': '',
            'Status': '',
            'Redirected': 'False',       # MELHORIA 2: Flag de redirect
            'Link Path': str(xpath)
        }

    def _generate_xpath(self, tag: Tag) -> str:
        """Gera XPath real do elemento no DOM"""
        try:
            path = []
            current = tag
            
            while current and current.name and current.name != '[document]':
                if current.parent is None:
                    break
                    
                siblings = [sibling for sibling in current.parent.find_all(current.name, recursive=False) 
                           if sibling.name == current.name]
                
                if len(siblings) > 1:
                    try:
                        index = siblings.index(current) + 1
                        path.append(f"{current.name}[{index}]")
                    except ValueError:
                        path.append(f"{current.name}[1]")
                else:
                    path.append(current.name)
                    
                current = current.parent
                
                if len(path) > 15:
                    break
            
            path.reverse()
            return '/' + '/'.join(path) if path else '/html/body/a[1]'
            
        except Exception:
            return '/html/body/a[1]'

    def _check_and_store_redirect(self, page_url: str, link_url: str, link_data: Dict[str, str], tag: Tag) -> bool:
        """
        Verifica redirect e atualiza dados do link
        Returns: True se foi cache hit, False se fez requisição
        """
        cache_hit = False
        
        try:
            if self.redirect_cache:
                # Verifica se já está no cache antes de fazer requisição
                cache_key = self.redirect_cache._normalize_url_for_cache(link_url)
                cached_result = self.redirect_cache._get_from_cache(cache_key)
                
                if cached_result:
                    cache_hit = True
                    resolved_url, status_code = cached_result[0], cached_result[1]
                else:
                    resolved_url, status_code = self.redirect_cache.get_or_fetch(
                        link_url,
                        timeout=self.redirect_timeout
                    )
            else:
                resolved_url, status_code = self._resolve_redirect_with_fallback(link_url)
            
            # Atualiza dados do link com status
            link_data['Status Code'] = str(status_code)
            link_data['Status'] = self._get_status_text(status_code)
            link_data['To Final'] = str(resolved_url)
            
            # CORREÇÃO: Registra TODOS os redirects reais, usa normalização só para criticidade
            if status_code in (301, 302, 303, 307, 308):
                # MELHORIA 2: Marca como redirecionado
                link_data['Redirected'] = 'True'
                
                # MELHORIA 1: Usa normalização apenas para classificar criticidade
                criticidade = 'Média' if urls_are_equivalent(link_url, resolved_url) else 'Alta'
                
                redirect_data = {
                    'from_url': page_url,
                    'to_original': link_url,
                    'to_final': resolved_url,
                    'anchor_text': link_data['Anchor'],
                    'alt_text': link_data['Alt Text'],
                    'follow': link_data['Follow'] == 'True',
                    'target': link_data['Target'],
                    'rel': link_data['Rel'],
                    'status_code': status_code,
                    'criticidade': criticidade,
                    'link_path': link_data['Link Path'],
                    'sugestao': f"Atualizar link para {resolved_url}"
                }
                
                self.internal_redirect_links_by_url[page_url].append(redirect_data)
                self.internal_redirect_links.append(redirect_data)
                
        except Exception as e:
            self.logger.debug(f"Erro verificando redirect {link_url}: {e}")
            link_data['Status Code'] = '0'
            link_data['Status'] = 'Error'
            
        return cache_hit

    def _resolve_redirect_with_fallback(self, url: str) -> Tuple[str, int]:
        """
        MELHORIA 6: Resolve redirect com fallback GET se HEAD falhar
        """
        try:
            # Tenta HEAD primeiro
            response = requests.head(
                url, 
                allow_redirects=True, 
                timeout=self.redirect_timeout,
                headers={'User-Agent': 'SEOFrog/0.2.1 (+https://seofrog.com/bot)'}
            )
            
            # Se HEAD bloqueado, tenta GET com stream
            if response.status_code in [403, 405, 429]:
                self.logger.debug(f"HEAD bloqueado para {url}, tentando GET")
                response = requests.get(
                    url,
                    allow_redirects=True,
                    timeout=self.redirect_timeout,
                    stream=True,  # Não baixa o corpo
                    headers={'User-Agent': 'SEOFrog/0.2.1 (+https://seofrog.com/bot)'}
                )
                response.close()  # Fecha conexão imediatamente
            
            return response.url, response.status_code
            
        except requests.RequestException:
            return url, 0

    def _get_status_text(self, status_code: int) -> str:
        """Converte código de status para texto"""
        status_map = {
            200: 'OK',
            301: 'Moved Permanently',
            302: 'Found',
            303: 'See Other',
            307: 'Temporary Redirect',
            308: 'Permanent Redirect',
            404: 'Not Found',
            403: 'Forbidden',
            500: 'Internal Server Error',
            0: 'Error'
        }
        return status_map.get(status_code, f'HTTP {status_code}')

    def _is_non_canonical_redirect(self, original: str, final: str) -> bool:
        """Detecta redirect por capitalização, trailing slash, etc."""
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
            return True

    def get_redirects_for_url(self, url: str) -> List[Dict[str, Any]]:
        """Obtém redirects de uma URL específica"""
        return self.internal_redirect_links_by_url.get(url, [])
    
    def get_total_redirects_count(self) -> int:
        """Retorna total de redirects encontrados"""
        return sum(len(redirects) for redirects in self.internal_redirect_links_by_url.values())
    
    def get_all_internal_links_for_export(self) -> List[Dict[str, str]]:
        """
        MELHORIA 4: Retorna TODOS os links internos (redirects + não-redirects)
        """
        all_internal_links = []
        
        for page_url, links in self.all_internal_links_by_url.items():
            for link in links:
                # Formato otimizado para aba Internal
                link_export = {
                    'Type': str(link.get('Type', 'Hyperlink')),
                    'From': str(link.get('From', '')),
                    'To Original': str(link.get('To Original', '')),
                    'To Final': str(link.get('To Final', '')),
                    'Anchor': str(link.get('Anchor', '')),
                    'Alt Text': str(link.get('Alt Text', '')),
                    'Follow': str(link.get('Follow', 'True')),
                    'Target': str(link.get('Target', '')),
                    'Rel': str(link.get('Rel', '')),
                    'Status Code': str(link.get('Status Code', '')),
                    'Status': str(link.get('Status', '')),
                    'Redirected': str(link.get('Redirected', 'False')),
                    'Link Path': str(link.get('Link Path', ''))
                }
                all_internal_links.append(link_export)
        
        return all_internal_links

    def get_redirects_only_for_export(self) -> List[Dict[str, str]]:
        """
        MELHORIA 4: Retorna apenas links que redirecionam (para aba separada)
        """
        redirect_links = []
        
        for url_redirects in self.internal_redirect_links_by_url.values():
            for redirect in url_redirects:
                link_export = {
                    'Type': 'Hyperlink',
                    'From': str(redirect.get('from_url', '')),
                    'To Original': str(redirect.get('to_original', '')),
                    'To Final': str(redirect.get('to_final', '')),
                    'Anchor': str(redirect.get('anchor_text', '')),
                    'Alt Text': str(redirect.get('alt_text', '')),
                    'Follow': str(redirect.get('follow', True)),
                    'Target': str(redirect.get('target', '')),
                    'Rel': str(redirect.get('rel', '')),
                    'Status Code': str(redirect.get('status_code', '')),
                    'Status': self._get_status_text(redirect.get('status_code', 0)),
                    'Redirected': 'True',
                    'Criticidade': str(redirect.get('criticidade', '')),
                    'Sugestão': str(redirect.get('sugestao', '')),
                    'Link Path': str(redirect.get('link_path', ''))
                }
                redirect_links.append(link_export)
        
        return redirect_links

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas completas do parser"""
        total_internal_links = sum(len(links) for links in self.all_internal_links_by_url.values())
        total_redirects = self.get_total_redirects_count()
        redirect_percentage = (total_redirects / total_internal_links * 100) if total_internal_links > 0 else 0
        
        stats = {
            'total_internal_links': total_internal_links,
            'total_redirects': total_redirects,
            'redirect_percentage': round(redirect_percentage, 2),
            'pages_with_redirects': len(self.internal_redirect_links_by_url),
            'pages_with_links': len(self.all_internal_links_by_url)
        }
        
        # Adiciona stats do cache se disponível
        if self.redirect_cache:
            cache_stats = self.redirect_cache.get_stats()
            stats.update({
                'cache_hit_rate': cache_stats.get('hit_rate_percent', 0),
                'cache_size': cache_stats.get('cache_size', 0),
                'head_fallbacks': cache_stats.get('head_fallbacks', 0)
            })
        
        return stats

    def log_cache_summary(self):
        """Log resumo das estatísticas do cache"""
        if not self.redirect_cache:
            return
        
        stats = self.redirect_cache.get_stats()
        
        if stats.get('cache_hits', 0) + stats.get('cache_misses', 0) > 0:
            self.logger.info(
                f"📊 RedirectCache: "
                f"{stats['cache_hits']} hits, "
                f"{stats['cache_misses']} misses, "
                f"{stats['hit_rate_percent']}% hit rate, "
                f"{stats['cache_size']} entries"
            )
            
            # Log fallbacks se relevantes
            if stats.get('head_fallbacks', 0) > 0:
                self.logger.info(f"🔄 HEAD fallbacks: {stats['head_fallbacks']} (sites bloqueando HEAD)")

    def log_final_summary(self):
        """Log resumo final das estatísticas"""
        stats = self.get_stats()
        
        self.logger.info(f"📊 Links Parser Summary:")
        self.logger.info(f"   - {stats['total_internal_links']} links internos processados")
        self.logger.info(f"   - {stats['total_redirects']} redirects detectados ({stats['redirect_percentage']}%)")
        self.logger.info(f"   - {stats['pages_with_redirects']} páginas com redirects")
        
        if self.redirect_cache:
            self.logger.info(f"   - Cache hit rate: {stats.get('cache_hit_rate', 0)}%")

    def clear_redirect_cache(self):
        """Limpa cache de redirects"""
        if self.redirect_cache:
            self.redirect_cache.clear_cache()

    def close(self):
        """Fecha recursos"""
        if self.redirect_cache:
            self.redirect_cache.close()