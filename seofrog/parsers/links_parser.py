"""
seofrog/parsers/links_parser.py
Parser completo para links internos - REFATORADO + CORRIGIDO com compatibilidade total com aba "Internal"
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
    def __init__(self, enable_redirects: bool = True, redirect_timeout: int = 3):
        super().__init__()
        self.enable_redirects = enable_redirects
        self.redirect_timeout = redirect_timeout
        self.redirect_rate_limit = 0.1
        self.internal_redirect_links_by_url = defaultdict(list)
        self.internal_redirect_links = []
        self.all_internal_links_by_url = defaultdict(list)

        self.redirect_cache = create_redirect_cache("seofrog_cache", 24) if enable_redirects else None

    def parse(self, soup: BeautifulSoup, page_url: str, word_count: Optional[int] = None) -> Dict[str, Any]:
        all_links = soup.find_all('a')
        total_links = len(all_links)
        internal_links = []
        external_links = []
        internal_links_details = []
        parsed_page = urlparse(page_url)

        for tag in all_links:
            href = tag.get('href')
            if not href or href.startswith(('javascript:', '#')):
                continue
            try:
                joined_url = urljoin(page_url, href)
                parsed_href = urlparse(joined_url)
                is_internal = parsed_page.netloc == parsed_href.netloc
                if is_internal:
                    internal_links.append(joined_url)
                    link_data = self._extract_link_data(tag, page_url, joined_url)
                    internal_links_details.append(link_data)
                    self.all_internal_links_by_url[page_url].append(link_data)
                    if self.enable_redirects:
                        cache_hit = self._check_and_store_redirect(page_url, joined_url, link_data)
                        if not cache_hit:
                            time.sleep(self.redirect_rate_limit)
                else:
                    external_links.append(joined_url)
            except Exception as e:
                self.logger.debug(f"Erro processando link {href}: {e}")

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
        anchor_text = tag.get_text(strip=True)
        img = tag.find('img')
        alt_text = img.get('alt') if img and img.has_attr('alt') else ""
        target_attr = tag.get('target', '')
        rel_attr = ', '.join(tag.get('rel')) if tag.has_attr('rel') else ''
        xpath = self._generate_xpath(tag)
        return {
            'Type': 'Hyperlink',
            'From': from_url,
            'To Original': to_url,
            'To Final': to_url,
            'Anchor': anchor_text,
            'Alt Text': alt_text,
            'Follow': str(not ('nofollow' in rel_attr.lower())),
            'Target': target_attr,
            'Rel': rel_attr,
            'Status Code': '',
            'Status': '',
            'Redirected': 'False',
            'Link Path': xpath
        }

    def _check_and_store_redirect(self, page_url: str, link_url: str, link_data: Dict[str, str]) -> bool:
        cache_hit = False
        try:
            resolved_url, status_code = self._resolve(link_url)
            if self.redirect_cache and self.redirect_cache.was_hit():
                cache_hit = True

            link_data['Status Code'] = str(status_code)
            link_data['Status'] = self._get_status_text(status_code)
            link_data['To Final'] = resolved_url

            if status_code in (301, 302, 303, 307, 308):
                link_data['Redirected'] = 'True'
                criticidade = 'Média' if urls_are_equivalent(link_url, resolved_url) else 'Alta'
                redirect_data = {
                    'type': 'redirect',
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

    def _resolve(self, url: str) -> Tuple[str, int]:
        if self.redirect_cache:
            return self.redirect_cache.get_or_fetch(url, timeout=self.redirect_timeout)
        try:
            resp = requests.head(url, allow_redirects=True, timeout=self.redirect_timeout)
            if resp.status_code in (403, 405, 429):
                resp = requests.get(url, allow_redirects=True, timeout=self.redirect_timeout, stream=True)
                resp.close()
            return resp.url, resp.status_code
        except Exception:
            return url, 0

    def _get_status_text(self, status_code: int) -> str:
        return {
            200: 'OK', 301: 'Moved Permanently', 302: 'Found', 303: 'See Other',
            307: 'Temporary Redirect', 308: 'Permanent Redirect',
            404: 'Not Found', 403: 'Forbidden', 500: 'Internal Server Error', 0: 'Error'
        }.get(status_code, f'HTTP {status_code}')

    def _generate_xpath(self, tag: Tag) -> str:
        path = []
        current = tag
        while current and current.name and current.name != '[document]':
            if not current.parent:
                break
            siblings = [sib for sib in current.parent.find_all(current.name, recursive=False)]
            idx = siblings.index(current) + 1 if siblings else 1
            path.append(f"{current.name}[{idx}]")
            current = current.parent
            if len(path) > 15:
                break
        path.reverse()
        return '/' + '/'.join(path)

    def get_all_internal_links_for_export(self) -> List[Dict[str, str]]:
        result = []
        for links in self.all_internal_links_by_url.values():
            result.extend(links)
        return result

    def get_redirects_only_for_export(self) -> List[Dict[str, str]]:
        return [
            {
                'Type': 'Hyperlink',
                'From': r['from_url'],
                'To Original': r['to_original'],
                'To Final': r['to_final'],
                'Anchor': r['anchor_text'],
                'Alt Text': r['alt_text'],
                'Follow': str(r['follow']),
                'Target': r['target'],
                'Rel': r['rel'],
                'Status Code': str(r['status_code']),
                'Status': self._get_status_text(r['status_code']),
                'Redirected': 'True',
                'Criticidade': r['criticidade'],
                'Sugestão': r['sugestao'],
                'Link Path': r['link_path']
            }
            for r in self.internal_redirect_links
        ]
