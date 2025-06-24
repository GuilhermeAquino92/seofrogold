"""
seofrog/parsers/seo_parser.py
SEO Parser Enterprise do SEOFrog v0.2 - VERSÃO COMPLETA COM MIXED CONTENT + LINKS MELHORADOS
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from seofrog.utils.logger import get_logger
from seofrog.core.exceptions import ParseException

class SEOParser:
    """Parser enterprise para dados SEO completos"""
    
    def __init__(self):
        self.logger = get_logger('SEOParser')
    
    def parse_page(self, url: str, response: requests.Response) -> Dict[str, Any]:
        """
        Parse completo de página para dados SEO enterprise
        
        Args:
            url: URL da página
            response: Response object do requests
            
        Returns:
            Dict com todos os dados SEO extraídos
        """
        
        data = {
            'url': url,
            'status_code': response.status_code,
            'content_type': response.headers.get('content-type', ''),
            'content_length': len(response.content),
            'response_time': response.elapsed.total_seconds(),
            'final_url': response.url,
            'crawl_timestamp': datetime.now().isoformat()
        }
        
        # Se não é HTML, retorna dados básicos
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            data['content_type_category'] = self._categorize_content_type(content_type)
            return data
        
        try:
            soup = BeautifulSoup(response.content, 'lxml')
            
            # === BASIC SEO ELEMENTS ===
            self._parse_title(soup, data)
            self._parse_meta_description(soup, data)
            self._parse_meta_keywords(soup, data)
            self._parse_canonical(soup, data, url)
            self._parse_meta_robots(soup, data)
            
            # === HEADINGS ===
            self._parse_headings(soup, data)
            
            # === LINKS - VERSÃO MELHORADA ===
            self._parse_links(soup, data, url)
            
            # === IMAGES ===
            self._parse_images(soup, data)
            
            # === CONTENT ANALYSIS ===
            self._parse_content(soup, data)
            
            # === STRUCTURED DATA ===
            self._parse_schema_markup(soup, data)
            
            # === SOCIAL MEDIA ===
            self._parse_social_tags(soup, data)
            
            # === TECHNICAL SEO ===
            self._parse_technical_elements(soup, data)
            
            # === INTERNATIONAL SEO ===
            self._parse_hreflang(soup, data)
            
            # === MIXED CONTENT DETECTION ===
            self._parse_mixed_content(soup, data, url)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Erro parseando {url}: {e}")
            data['parse_error'] = str(e)
            return data
    
    def _categorize_content_type(self, content_type: str) -> str:
        """Categoriza tipo de conteúdo"""
        if 'image/' in content_type:
            return 'image'
        elif 'text/css' in content_type:
            return 'css'
        elif 'javascript' in content_type or 'text/js' in content_type:
            return 'javascript'
        elif 'application/pdf' in content_type:
            return 'pdf'
        elif 'application/json' in content_type:
            return 'json'
        elif 'text/xml' in content_type or 'application/xml' in content_type:
            return 'xml'
        else:
            return 'other'
    
    def _parse_title(self, soup: BeautifulSoup, data: Dict):
        """Parse do title tag"""
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text().strip()
            data['title'] = title_text
            data['title_length'] = len(title_text)
            
            # Análise de qualidade do título
            data['title_words'] = len(title_text.split())
            data['title_has_brand'] = self._detect_brand_in_title(title_text)
        else:
            data['title'] = ''
            data['title_length'] = 0
            data['title_words'] = 0
            data['title_has_brand'] = False
    
    def _detect_brand_in_title(self, title: str) -> bool:
        """Detecta se título contém marca/brand"""
        # Heurística simples: procura por separadores comuns de brand
        brand_separators = [' | ', ' - ', ' :: ', ' • ']
        return any(sep in title for sep in brand_separators)
    
    def _parse_meta_description(self, soup: BeautifulSoup, data: Dict):
        """Parse da meta description"""
        meta_desc = soup.find('meta', attrs={'name': re.compile(r'^description$', re.I)})
        if meta_desc:
            desc_text = meta_desc.get('content', '').strip()
            data['meta_description'] = desc_text
            data['meta_description_length'] = len(desc_text)
        else:
            data['meta_description'] = ''
            data['meta_description_length'] = 0
    
    def _parse_meta_keywords(self, soup: BeautifulSoup, data: Dict):
        """Parse das meta keywords"""
        meta_keywords = soup.find('meta', attrs={'name': re.compile(r'^keywords$', re.I)})
        if meta_keywords:
            data['meta_keywords'] = meta_keywords.get('content', '').strip()
        else:
            data['meta_keywords'] = ''
    
    def _parse_canonical(self, soup: BeautifulSoup, data: Dict, url: str):
        """Parse da canonical URL"""
        canonical = soup.find('link', attrs={'rel': re.compile(r'^canonical$', re.I)})
        if canonical:
            canonical_url = canonical.get('href', '').strip()
            data['canonical_url'] = canonical_url
            data['canonical_is_self'] = canonical_url == url
        else:
            data['canonical_url'] = ''
            data['canonical_is_self'] = False
    
    def _parse_meta_robots(self, soup: BeautifulSoup, data: Dict):
        """Parse da meta robots"""
        meta_robots = soup.find('meta', attrs={'name': re.compile(r'^robots$', re.I)})
        if meta_robots:
            robots_content = meta_robots.get('content', '').strip().lower()
            data['meta_robots'] = robots_content
            data['meta_robots_noindex'] = 'noindex' in robots_content
            data['meta_robots_nofollow'] = 'nofollow' in robots_content
        else:
            data['meta_robots'] = ''
            data['meta_robots_noindex'] = False
            data['meta_robots_nofollow'] = False
    
    def _parse_headings(self, soup: BeautifulSoup, data: Dict):
        """Parse de todas as headings H1-H6 + detecção de headings vazias e escondidas"""
        for i in range(1, 7):
            headings = soup.find_all(f'h{i}')
            data[f'h{i}_count'] = len(headings)
            
            if i == 1 and headings:
                data['h1_text'] = headings[0].get_text().strip()
                data['h1_length'] = len(data['h1_text'])
            elif i == 1:
                data['h1_text'] = ''
                data['h1_length'] = 0
        
        # === DETECÇÃO DE HEADINGS VAZIAS E ESCONDIDAS ===
        empty_headings = []
        hidden_headings = []
        
        for level in range(1, 7):
            headings = soup.find_all(f'h{level}')
            
            for heading in headings:
                heading_text = heading.get_text().strip()
                heading_html = str(heading)
                
                # Verifica se está vazia
                is_empty = self._is_empty_heading(heading_text)
                
                # Verifica se está escondida por CSS
                is_hidden = self._is_hidden_by_css(heading)
                
                if is_empty:
                    empty_headings.append({
                        'level': f'H{level}',
                        'text': heading_text,
                        'html': heading_html[:200],  # Primeiros 200 chars
                        'reason': self._get_empty_reason(heading_text, heading_html)
                    })
                
                if is_hidden:
                    hidden_headings.append({
                        'level': f'H{level}',
                        'text': heading_text,
                        'html': heading_html[:200],
                        'css_issue': self._get_css_hiding_method(heading)
                    })
        
        # Adiciona aos dados
        data['empty_headings_count'] = len(empty_headings)
        data['hidden_headings_count'] = len(hidden_headings)
        data['empty_headings_details'] = empty_headings
        data['hidden_headings_details'] = hidden_headings
        
        # Cria resumo textual para CSV
        if empty_headings:
            data['empty_headings_summary'] = '; '.join([f"{h['level']}: {h['reason']}" for h in empty_headings])
        else:
            data['empty_headings_summary'] = ''
            
        if hidden_headings:
            data['hidden_headings_summary'] = '; '.join([f"{h['level']}: {h['css_issue']}" for h in hidden_headings])
        else:
            data['hidden_headings_summary'] = ''
    
    def _is_empty_heading(self, text: str) -> bool:
        """Verifica se heading está vazia (apenas casos realmente vazios)"""
        if not text:
            return True
        
        # Remove espaços em branco
        clean_text = text.replace('\n', '').replace('\t', '').replace('\r', '').strip()
        
        # Verifica apenas os 3 casos principais
        empty_patterns = [
            '',        # Completamente vazio
            '&nbsp;',  # Non-breaking space HTML
            '\u00a0',  # Non-breaking space Unicode
        ]
        
        # Verifica se é só espaços em branco
        if len(clean_text) == 0:
            return True
            
        return clean_text in empty_patterns
    
    def _get_empty_reason(self, text: str, html: str) -> str:
        """Identifica o motivo da heading estar vazia (simplificado)"""
        if not text:
            return "Completamente vazia"
        
        clean_text = text.strip()
        
        if '&nbsp;' in html:
            return "Contém &nbsp;"
        elif clean_text == '\u00a0':
            return "Non-breaking space"
        elif len(clean_text) == 0:
            return "Só espaços em branco"
        else:
            return "Vazia"
    
    def _is_hidden_by_css(self, heading) -> bool:
        """Verifica se heading está escondida por CSS"""
        style = heading.get('style', '').lower()
        class_attr = heading.get('class', [])
        
        # Verifica CSS inline
        css_hiding_patterns = [
            'display:none',
            'display: none',
            'visibility:hidden',
            'visibility: hidden',
            'opacity:0',
            'opacity: 0',
            'color:white',
            'color: white',
            'color:#fff',
            'color: #fff',
            'color:#ffffff',
            'color: #ffffff',
            'text-indent:-9999',
            'text-indent: -9999',
            'left:-9999',
            'left: -9999',
            'position:absolute;left:-9999',
            'font-size:0',
            'font-size: 0',
            'height:0',
            'height: 0',
            'width:0',
            'width: 0'
        ]
        
        # Verifica style inline
        for pattern in css_hiding_patterns:
            if pattern in style.replace(' ', ''):
                return True
        
        # Verifica classes suspeitas
        if isinstance(class_attr, list):
            suspicious_classes = [
                'hidden', 'hide', 'invisible', 'screen-reader-only',
                'sr-only', 'visuallyhidden', 'visually-hidden',
                'seo-hidden', 'seo-text', 'white-text'
            ]
            
            for cls in class_attr:
                if any(suspicious in cls.lower() for suspicious in suspicious_classes):
                    return True
        
        return False
    
    def _get_css_hiding_method(self, heading) -> str:
        """Identifica o método CSS usado para esconder"""
        style = heading.get('style', '').lower()
        class_attr = heading.get('class', [])
        
        # Verifica método específico
        if 'display:none' in style or 'display: none' in style:
            return "display: none"
        elif 'visibility:hidden' in style or 'visibility: hidden' in style:
            return "visibility: hidden"
        elif 'opacity:0' in style or 'opacity: 0' in style:
            return "opacity: 0"
        elif any(color in style for color in ['color:white', 'color: white', 'color:#fff', 'color: #fff']):
            return "color: white"
        elif 'text-indent:-9999' in style or 'text-indent: -9999' in style:
            return "text-indent: -9999px"
        elif 'left:-9999' in style or 'left: -9999' in style:
            return "position: absolute; left: -9999px"
        elif 'font-size:0' in style or 'font-size: 0' in style:
            return "font-size: 0"
        elif any(size in style for size in ['height:0', 'height: 0', 'width:0', 'width: 0']):
            return "height/width: 0"
        elif isinstance(class_attr, list):
            for cls in class_attr:
                if 'hidden' in cls.lower():
                    return f"class: {cls}"
                elif any(word in cls.lower() for word in ['sr-only', 'screen-reader']):
                    return f"screen-reader class: {cls}"
        
        return "CSS escondido (método desconhecido)"
    
    def _parse_links(self, soup: BeautifulSoup, data: Dict, url: str):
        """
        Parse de todos os links - VERSÃO MELHORADA COMPLETA
        Agora captura lista completa de links internos com resolução de redirects
        """
        all_links = soup.find_all('a', href=True)
        internal_links = []
        external_links = []
        internal_links_detailed = []  # NOVO: Lista detalhada para análise de redirects
        
        parsed_base = urlparse(url)
        
        for link in all_links:
            href = link.get('href', '').strip()
            if not href or href.startswith('#'):
                continue
            
            full_url = urljoin(url, href)
            parsed_link = urlparse(full_url)
            
            # Captura anchor text e atributos
            anchor_text = link.get_text().strip()
            link_title = link.get('title', '').strip()
            link_classes = ' '.join(link.get('class', []))
            
            if parsed_link.netloc == parsed_base.netloc:
                internal_links.append(full_url)
                
                # NOVO: Resolve redirect para o link interno (com rate limiting)
                redirect_info = self._resolve_internal_link_redirect(full_url)
                
                # NOVO: Armazena informações detalhadas do link interno
                internal_links_detailed.append({
                    'url': full_url,
                    'final_url': redirect_info['final_url'],
                    'status_code': redirect_info['status_code'],
                    'has_redirect': redirect_info['has_redirect'],
                    'redirect_type': redirect_info['redirect_type'],
                    'href': href,  # href original (pode ser relativo)
                    'anchor': anchor_text,
                    'title': link_title,
                    'classes': link_classes,
                    'is_relative': not href.startswith(('http://', 'https://')),
                    'has_anchor': bool(anchor_text),
                    'tag_html': str(link)[:200],  # Primeiros 200 chars da tag
                    'response_time': redirect_info.get('response_time', 0)
                })
            elif parsed_link.netloc and parsed_link.netloc != parsed_base.netloc:
                external_links.append(full_url)
        
        # Dados tradicionais (mantém compatibilidade)
        data['internal_links_count'] = len(internal_links)
        data['external_links_count'] = len(external_links)
        data['total_links_count'] = len(all_links)
        data['links_without_anchor'] = len([link for link in all_links if not link.get_text().strip()])
        
        # NOVO: Dados detalhados para análise de redirects
        data['internal_links_detailed'] = internal_links_detailed
        data['internal_redirects_count'] = len([link for link in internal_links_detailed if link['has_redirect']])
        
        # NOVO: Estatísticas de redirects por tipo
        redirect_types = {}
        for link in internal_links_detailed:
            if link['has_redirect']:
                redirect_type = link['redirect_type']
                redirect_types[redirect_type] = redirect_types.get(redirect_type, 0) + 1
        
        data['internal_redirect_types'] = redirect_types

    def _resolve_internal_link_redirect(self, url: str) -> dict:
        """
        Resolve redirecionamentos para um link interno específico
        Usa HEAD request para eficiência com rate limiting
        
        Args:
            url: URL do link interno para verificar
            
        Returns:
            dict: Informações do redirect
        """
        try:
            # Rate limiting: pequeno delay para não sobrecarregar servidor
            time.sleep(0.1)
            
            # Configura session com timeout curto para não impactar performance
            session = requests.Session()
            session.verify = False  # Mesma config do HTTPEngine
            
            # Headers similares ao crawler principal
            session.headers.update({
                'User-Agent': 'SEOFrog/0.2 (+https://seofrog.com/bot)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            })
            
            # Usa HEAD para ser mais eficiente
            start_time = time.time()
            response = session.head(
                url, 
                timeout=3,  # Timeout ainda menor
                allow_redirects=False
            )
            response_time = time.time() - start_time
            
            # Verifica se há redirecionamento
            if response.status_code in [301, 302, 303, 307, 308]:
                location = response.headers.get('location', '')
                if location:
                    final_url = urljoin(url, location)
                    redirect_type = self._classify_redirect_type(url, final_url)
                    
                    return {
                        'final_url': final_url,
                        'status_code': response.status_code,
                        'has_redirect': True,
                        'redirect_type': redirect_type,
                        'response_time': response_time
                    }
            
            # Sem redirecionamento
            return {
                'final_url': url,
                'status_code': response.status_code,
                'has_redirect': False,
                'redirect_type': 'None',
                'response_time': response_time
            }
            
        except Exception as e:
            # Em caso de erro, assume sem redirect
            self.logger.debug(f"Erro verificando redirect para {url}: {e}")
            return {
                'final_url': url,
                'status_code': 0,
                'has_redirect': False,
                'redirect_type': 'Error',
                'response_time': 0,
                'error': str(e)
            }

    def _classify_redirect_type(self, original_url: str, final_url: str) -> str:
        """
        Classifica o tipo de redirecionamento para análise
        
        Args:
            original_url: URL original do link
            final_url: URL final após redirect
            
        Returns:
            str: Tipo do redirecionamento
        """
        try:
            parsed_orig = urlparse(original_url)
            parsed_final = urlparse(final_url)
            
            # HTTP -> HTTPS
            if parsed_orig.scheme == 'http' and parsed_final.scheme == 'https':
                return 'HTTP_to_HTTPS'
            
            # HTTPS -> HTTP (problemático)
            if parsed_orig.scheme == 'https' and parsed_final.scheme == 'http':
                return 'HTTPS_to_HTTP'
            
            # Capitalização no path
            if (parsed_orig.netloc.lower() == parsed_final.netloc.lower() and 
                parsed_orig.path != parsed_final.path and 
                parsed_orig.path.lower() == parsed_final.path.lower()):
                return 'Case_Change'
            
            # Trailing slash
            if (parsed_orig.netloc == parsed_final.netloc and 
                (parsed_orig.path.rstrip('/') == parsed_final.path.rstrip('/')) and
                parsed_orig.path != parsed_final.path):
                return 'Trailing_Slash'
            
            # Query string
            if (parsed_orig.netloc == parsed_final.netloc and 
                parsed_orig.path == parsed_final.path and 
                parsed_orig.query != parsed_final.query):
                return 'Query_String'
            
            # WWW differences
            if (parsed_orig.path == parsed_final.path and
                ('www.' in parsed_orig.netloc) != ('www.' in parsed_final.netloc)):
                return 'WWW_Redirect'
            
            # Path redirect (mudança de estrutura)
            if (parsed_orig.netloc == parsed_final.netloc and 
                parsed_orig.path != parsed_final.path):
                return 'Path_Change'
            
            # Domain redirect (mudança de domínio)
            if parsed_orig.netloc != parsed_final.netloc:
                return 'Domain_Change'
            
            return 'Other'
            
        except Exception:
            return 'Unknown'
    
    def _parse_images(self, soup: BeautifulSoup, data: Dict):
        """Parse de todas as imagens"""
        images = soup.find_all('img')
        data['images_count'] = len(images)
        data['images_without_alt'] = len([img for img in images if not img.get('alt')])
        data['images_without_src'] = len([img for img in images if not img.get('src')])
        
        # Tamanhos de imagem especificados
        images_with_dimensions = len([img for img in images if img.get('width') and img.get('height')])
        data['images_with_dimensions'] = images_with_dimensions
    
    def _parse_content(self, soup: BeautifulSoup, data: Dict):
        """Parse do conteúdo da página"""
        # Remove scripts e styles do texto
        for script in soup(["script", "style"]):
            script.decompose()
        
        text_content = soup.get_text()
        words = re.findall(r'\b\w+\b', text_content)
        
        data['word_count'] = len(words)
        data['character_count'] = len(text_content)
        data['text_ratio'] = len(text_content.strip()) / len(soup.prettify()) if len(soup.prettify()) > 0 else 0
    
    def _parse_schema_markup(self, soup: BeautifulSoup, data: Dict):
        """Parse de structured data / schema markup"""
        # JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        data['schema_json_ld_count'] = len(json_ld_scripts)
        
        # Microdata
        microdata_items = soup.find_all(attrs={'itemscope': True})
        data['schema_microdata_count'] = len(microdata_items)
        
        # RDFa
        rdfa_items = soup.find_all(attrs={'typeof': True})
        data['schema_rdfa_count'] = len(rdfa_items)
        
        data['schema_total_count'] = data['schema_json_ld_count'] + data['schema_microdata_count'] + data['schema_rdfa_count']
    
    def _parse_social_tags(self, soup: BeautifulSoup, data: Dict):
        """Parse de Open Graph e Twitter Cards"""
        # Open Graph
        og_tags = soup.find_all('meta', attrs={'property': re.compile(r'^og:', re.I)})
        data['og_tags_count'] = len(og_tags)
        
        # Twitter Cards
        twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:', re.I)})
        data['twitter_tags_count'] = len(twitter_tags)
        
        # Tags específicas importantes
        og_title = soup.find('meta', attrs={'property': re.compile(r'^og:title$', re.I)})
        data['og_title'] = og_title.get('content', '').strip() if og_title else ''
        
        og_description = soup.find('meta', attrs={'property': re.compile(r'^og:description$', re.I)})
        data['og_description'] = og_description.get('content', '').strip() if og_description else ''
    
    def _parse_technical_elements(self, soup: BeautifulSoup, data: Dict):
        """Parse de elementos técnicos"""
        # Viewport
        viewport = soup.find('meta', attrs={'name': re.compile(r'^viewport$', re.I)})
        data['has_viewport'] = viewport is not None
        data['viewport_content'] = viewport.get('content', '').strip() if viewport else ''
        
        # Charset
        charset_meta = soup.find('meta', charset=True) or soup.find('meta', attrs={'http-equiv': re.compile(r'^content-type$', re.I)})
        data['has_charset'] = charset_meta is not None
        
        # Favicon
        favicon = soup.find('link', attrs={'rel': re.compile(r'icon', re.I)})
        data['has_favicon'] = favicon is not None
        
        # AMP
        amp_html = soup.find('html', attrs={'amp': True}) or soup.find('html', attrs={'⚡': True})
        data['is_amp'] = amp_html is not None
    
    def _parse_hreflang(self, soup: BeautifulSoup, data: Dict):
        """Parse de hreflang tags"""
        hreflang_tags = soup.find_all('link', attrs={'rel': re.compile(r'^alternate$', re.I), 'hreflang': True})
        data['hreflang_count'] = len(hreflang_tags)
        
        if hreflang_tags:
            hreflang_list = []
            for tag in hreflang_tags:
                hreflang_list.append({
                    'hreflang': tag.get('hreflang', ''),
                    'href': tag.get('href', '')
                })
            data['hreflang_languages'] = [tag['hreflang'] for tag in hreflang_list]
        else:
            data['hreflang_languages'] = []
    
    def _parse_mixed_content(self, soup: BeautifulSoup, data: Dict, url: str):
        """
        Parse de Mixed Content - detecta recursos HTTP em páginas HTTPS
        """
        try:
            # Só analisa se a página atual é HTTPS
            if not url.startswith('https://'):
                data['is_https_page'] = False
                data['mixed_content_risk'] = 'N/A - Página HTTP'
                return
            
            data['is_https_page'] = True
            
            # Contadores de mixed content
            active_mixed_content = []
            passive_mixed_content = []
            
            # === ACTIVE MIXED CONTENT (CRÍTICO) ===
            
            # Scripts HTTP
            scripts = soup.find_all('script', src=True)
            for script in scripts:
                src = script.get('src', '').strip()
                if src.startswith('http://'):
                    active_mixed_content.append({
                        'type': 'script',
                        'url': src,
                        'tag': str(script)[:200]
                    })
            
            # Stylesheets HTTP
            stylesheets = soup.find_all('link', rel='stylesheet', href=True)
            for link in stylesheets:
                href = link.get('href', '').strip()
                if href.startswith('http://'):
                    active_mixed_content.append({
                        'type': 'stylesheet',
                        'url': href,
                        'tag': str(link)[:200]
                    })
            
            # Iframes HTTP
            iframes = soup.find_all('iframe', src=True)
            for iframe in iframes:
                src = iframe.get('src', '').strip()
                if src.startswith('http://'):
                    active_mixed_content.append({
                        'type': 'iframe',
                        'url': src,
                        'tag': str(iframe)[:200]
                    })
            
            # Objects e Embeds HTTP
            objects = soup.find_all(['object', 'embed'], ['data', 'src'])
            for obj in objects:
                src = obj.get('data') or obj.get('src', '')
                if src.startswith('http://'):
                    active_mixed_content.append({
                        'type': obj.name,
                        'url': src,
                        'tag': str(obj)[:200]
                    })
            
            # === PASSIVE MIXED CONTENT (AVISO) ===
            
            # Imagens HTTP
            images = soup.find_all('img', src=True)
            for img in images:
                src = img.get('src', '').strip()
                if src.startswith('http://'):
                    passive_mixed_content.append({
                        'type': 'image',
                        'url': src,
                        'alt': img.get('alt', ''),
                        'tag': str(img)[:200]
                    })
            
            # Áudio e Vídeo HTTP
            media = soup.find_all(['audio', 'video', 'source'], src=True)
            for medium in media:
                src = medium.get('src', '').strip()
                if src.startswith('http://'):
                    passive_mixed_content.append({
                        'type': medium.name,
                        'url': src,
                        'tag': str(medium)[:200]
                    })
            
            # === OUTRAS FONTES DE MIXED CONTENT ===
            
            # Links HTTP
            http_links = []
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '').strip()
                if href.startswith('http://'):
                    http_links.append({
                        'url': href,
                        'text': link.get_text().strip()[:100],
                        'tag': str(link)[:200]
                    })
            
            # Forms com action HTTP
            http_forms = []
            forms = soup.find_all('form', action=True)
            for form in forms:
                action = form.get('action', '').strip()
                if action.startswith('http://'):
                    http_forms.append({
                        'action': action,
                        'method': form.get('method', 'GET').upper(),
                        'tag': str(form)[:200]
                    })
            
            # === RESULTADOS CONSOLIDADOS ===
            
            # Contadores
            data['active_mixed_content_count'] = len(active_mixed_content)
            data['passive_mixed_content_count'] = len(passive_mixed_content)
            data['total_mixed_content_count'] = len(active_mixed_content) + len(passive_mixed_content)
            data['http_links_count'] = len(http_links)
            data['http_forms_count'] = len(http_forms)
            
            # Detalhes completos
            data['active_mixed_content_details'] = active_mixed_content
            data['passive_mixed_content_details'] = passive_mixed_content
            data['http_links_details'] = http_links
            data['http_forms_details'] = http_forms
            
            # Resumos para CSV
            if active_mixed_content:
                active_summary = []
                for item in active_mixed_content:
                    active_summary.append(f"{item['type']}: {item['url']}")
                data['active_mixed_content_summary'] = '; '.join(active_summary)
            else:
                data['active_mixed_content_summary'] = ''
            
            if passive_mixed_content:
                passive_summary = []
                for item in passive_mixed_content:
                    passive_summary.append(f"{item['type']}: {item['url']}")
                data['passive_mixed_content_summary'] = '; '.join(passive_summary)
            else:
                data['passive_mixed_content_summary'] = ''
            
            # Análise de risco
            if active_mixed_content:
                data['mixed_content_risk'] = 'CRÍTICO - Active Mixed Content'
            elif passive_mixed_content:
                data['mixed_content_risk'] = 'MÉDIO - Passive Mixed Content'
            elif http_links or http_forms:
                data['mixed_content_risk'] = 'BAIXO - Links/Forms HTTP'
            else:
                data['mixed_content_risk'] = 'SEGURO - Sem Mixed Content'
            
            # URLs e domínios problemáticos
            all_http_urls = set()
            for item in active_mixed_content + passive_mixed_content:
                all_http_urls.add(item['url'])
            data['unique_http_resources'] = len(all_http_urls)
            
            http_domains = set()
            for http_url in all_http_urls:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(http_url).netloc
                    if domain:
                        http_domains.add(domain)
                except:
                    pass
            
            data['http_domains_count'] = len(http_domains)
            data['http_domains_list'] = list(http_domains)
            
        except Exception as e:
            self.logger.error(f"Erro parseando mixed content: {e}")
            data['mixed_content_error'] = str(e)