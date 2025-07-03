"""
seofrog/parsers/technical_parser.py
Parser modular para análise completa de elementos técnicos SEO
Responsável por: viewport, charset, favicon, AMP, lang, DOCTYPE, performance hints
"""

import re
import requests
import time
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List, Optional, Set
from bs4 import BeautifulSoup, Tag, Doctype
from .base import ParserMixin, SeverityLevel

class TechnicalParser(ParserMixin):
    """
    Parser especializado para análise completa de elementos técnicos SEO
    Responsável por: viewport, charset, favicon, AMP, lang, DOCTYPE, performance, security
    """
    
    def __init__(self):
        super().__init__()
        
        # Viewports recomendados
        self.recommended_viewports = [
            'width=device-width, initial-scale=1',
            'width=device-width, initial-scale=1.0',
            'width=device-width,initial-scale=1',
            'width=device-width,initial-scale=1.0'
        ]
        
        # Charsets válidos
        self.valid_charsets = [
            'utf-8', 'utf8', 'iso-8859-1', 'windows-1252'
        ]
        
        # Formatos de favicon
        self.favicon_formats = {
            'ico': {'sizes': ['16x16', '32x32', '48x48'], 'type': 'image/x-icon'},
            'png': {'sizes': ['16x16', '32x32', '96x96', '192x192'], 'type': 'image/png'},
            'svg': {'sizes': ['any'], 'type': 'image/svg+xml'},
            'apple-touch-icon': {'sizes': ['180x180', '152x152', '144x144'], 'type': 'image/png'}
        }
        
        # Performance hints válidos
        self.performance_hints = [
            'dns-prefetch', 'preconnect', 'prefetch', 'preload', 
            'prerender', 'modulepreload'
        ]
        
        # Códigos de idioma válidos (amostra)
        self.valid_lang_codes = {
            'pt', 'pt-br', 'pt-pt', 'en', 'en-us', 'en-gb', 
            'es', 'es-es', 'es-mx', 'fr', 'fr-fr', 'de', 'de-de',
            'it', 'it-it', 'ja', 'ja-jp', 'ko', 'ko-kr', 'zh', 
            'zh-cn', 'zh-tw', 'ru', 'ru-ru', 'ar', 'ar-sa'
        }
        
        # Meta robots válidos
        self.valid_robots_directives = [
            'index', 'noindex', 'follow', 'nofollow', 'archive', 
            'noarchive', 'snippet', 'nosnippet', 'imageindex', 
            'noimageindex', 'translate', 'notranslate', 'none', 'all'
        ]
        
        # 🆕 CONFIGURAÇÃO PARA DETECÇÃO DE REDIRECTS
        self.enable_redirect_detection = True
        self.redirect_timeout = 5
        self.redirect_delay = 0.05
        self.max_redirects_check = 100
    
    def parse(self, soup: BeautifulSoup, url: str = None) -> Dict[str, Any]:
        """
        Parse completo de análise de elementos técnicos
        
        Args:
            soup: BeautifulSoup object da página
            url: URL da página (para validação de links relativos)
            
        Returns:
            Dict com dados completos de elementos técnicos
        """
        data = {}
        
        try:
            # Parse de cada categoria técnica
            self._parse_doctype(soup, data)
            self._parse_html_lang(soup, data)
            self._parse_charset(soup, data)
            self._parse_viewport(soup, data)
            self._parse_favicon(soup, data, url)
            self._parse_amp_detection(soup, data)
            self._parse_meta_robots_advanced(soup, data)
            self._parse_performance_hints(soup, data, url)
            self._parse_security_headers(soup, data)
            self._parse_html_structure(soup, data)

            # 🆕 DETECÇÃO DE REDIRECTS
            if url and self.enable_redirect_detection:
                redirect_data = self.check_internal_redirects(soup, url)
                data.update(redirect_data)

            # Análise de qualidade técnica
            self._analyze_technical_quality(data)
            self._analyze_mobile_optimization(data)
            self._analyze_performance_optimization(data)

            # Detecção de problemas
            self._detect_technical_issues(data)

            # Severity scoring
            self._calculate_technical_severity(data)

            # Log estatísticas
            errors = 1 if any(key.endswith('_error') for key in data.keys()) else 0
            self.log_parsing_stats('TechnicalParser', len(data), errors)

        except Exception as e:
            self.logger.error(f"Erro no parse técnico: {e}")
            data['technical_parse_error'] = str(e)
            self.log_parsing_stats('TechnicalParser', len(data), 1)

        return data

    def check_internal_redirects(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Detecta redirects em links internos da página"""
        redirect_data = {
            'redirects_found': [],
            'redirects_count': 0,
            'redirects_by_code': {},
            'redirects_errors': []
        }

        if not self.enable_redirect_detection:
            return redirect_data

        try:
            # Encontra todos os links internos
            internal_links = self._extract_internal_links(soup, base_url)

            if not internal_links:
                return redirect_data

            # Limita quantidade para não sobrecarregar
            links_to_check = internal_links[:self.max_redirects_check]

            self.logger.info(f"🔄 Verificando redirects em {len(links_to_check)} links internos de {base_url}...")

            for link_url in links_to_check:
                try:
                    redirect_info = self._check_single_redirect(link_url)

                    if redirect_info['has_redirect']:
                        redirect_data['redirects_found'].append({
                            'source_url': base_url,
                            'link_url': link_url,
                            'final_url': redirect_info['final_url'],
                            'status_code': redirect_info['status_code'],
                            'redirect_chain': redirect_info.get('redirect_chain', [])
                        })

                        # Log do redirect encontrado
                        self.logger.info(f"🔄 REDIRECT detectado: {link_url} → {redirect_info['final_url']} ({redirect_info['status_code']})")

                    # Rate limiting
                    time.sleep(self.redirect_delay)

                except Exception as e:
                    redirect_data['redirects_errors'].append({
                        'url': link_url,
                        'error': str(e)
                    })

            # Estatísticas finais
            redirect_data['redirects_count'] = len(redirect_data['redirects_found'])

            # Contagem por código de status
            status_codes = {}
            for redirect in redirect_data['redirects_found']:
                code = redirect['status_code']
                status_codes[code] = status_codes.get(code, 0) + 1
            redirect_data['redirects_by_code'] = status_codes

            if redirect_data['redirects_count'] > 0:
                self.logger.info(f"✅ Encontrados {redirect_data['redirects_count']} redirects em {base_url}")

        except Exception as e:
            self.logger.error(f"Erro na detecção de redirects: {e}")
            redirect_data['redirects_errors'].append({'error': str(e)})

        return redirect_data

    def _extract_internal_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extrai todos os links internos da página"""
        base_domain = urlparse(base_url).netloc
        internal_links = []

        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()

            if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                continue

            # Converte para URL absoluta
            absolute_url = urljoin(base_url, href)
            parsed = urlparse(absolute_url)
            
            # Só links do mesmo domínio
            if parsed.netloc == base_domain:
                internal_links.append(absolute_url)

        # Remove duplicatas
        return list(set(internal_links))

    def _check_single_redirect(self, url: str) -> Dict[str, Any]:
        """Verifica se uma URL específica tem redirect"""
        redirect_info = {
            'has_redirect': False,
            'final_url': url,
            'status_code': None,
            'redirect_chain': []
        }

        try:
            # Faz HEAD request para verificar redirect sem baixar conteúdo
            response = requests.head(
                url,
                allow_redirects=True,
                timeout=self.redirect_timeout,
                headers={'User-Agent': 'SEOFrog/1.0 (Redirect Detection)'},
                verify=False  # Ignora SSL como no crawler principal
            )

            redirect_info['status_code'] = response.status_code
            redirect_info['final_url'] = response.url

            # Verifica se houve redirect (URL mudou)
            if response.url != url:
                redirect_info['has_redirect'] = True

        except requests.RequestException as e:
            self.logger.debug(f"Erro verificando redirect {url}: {e}")
            redirect_info['error'] = str(e)

        return redirect_info

    def _parse_doctype(self, soup: BeautifulSoup, data: Dict):
        """
        Parse e validação do DOCTYPE
        """
        doctype_found = False
        doctype_valid = False
        doctype_string = ''

        # Procura pelo DOCTYPE no BeautifulSoup
        for item in soup.contents:
            if isinstance(item, Doctype):
                doctype_found = True
                doctype_string = str(item).strip()

                # Valida se é HTML5 (recomendado)
                if doctype_string.lower() == 'html':
                    doctype_valid = True
                    data['doctype_type'] = 'HTML5'
                elif 'html 4' in doctype_string.lower():
                    data['doctype_type'] = 'HTML4'
                elif 'xhtml' in doctype_string.lower():
                    data['doctype_type'] = 'XHTML'
                else:
                    data['doctype_type'] = 'Unknown'

                break

        data['has_doctype'] = doctype_found
        data['doctype_valid'] = doctype_valid
        data['doctype_string'] = doctype_string
        data['is_html5'] = doctype_valid and data.get('doctype_type') == 'HTML5'

    def _parse_html_lang(self, soup: BeautifulSoup, data: Dict):
        """
        Parse do atributo lang no HTML
        """
        html_tag = soup.find('html')

        if html_tag:
            lang_attr = self.safe_get_attribute(html_tag, 'lang')

            data['has_html_lang'] = bool(lang_attr)
            data['html_lang'] = lang_attr
            data['html_lang_valid'] = lang_attr.lower() in self.valid_lang_codes if lang_attr else False

            # Análise adicional do lang
            if lang_attr:
                data['html_lang_is_generic'] = lang_attr.lower() in ['en', 'pt', 'es']  # Muito genérico
                data['html_lang_has_country'] = '-' in lang_attr  # ex: pt-BR, en-US
            else:
                data['html_lang_is_generic'] = False
                data['html_lang_has_country'] = False
        else:
            data['has_html_lang'] = False
            data['html_lang'] = ''
            data['html_lang_valid'] = False
            data['html_lang_is_generic'] = False
            data['html_lang_has_country'] = False

    def _parse_charset(self, soup: BeautifulSoup, data: Dict):
        """
        Parse completo da declaração de charset
        """
        charset_found = False
        charset_value = ''
        charset_method = ''
        charset_valid = False
        charset_position = 0

        # Método 1: HTML5 <meta charset="utf-8">
        charset_meta = self.safe_find(soup, 'meta', {'charset': True})
        if charset_meta:
            charset_found = True
            charset_value = self.safe_get_attribute(charset_meta, 'charset').lower()
            charset_method = 'html5'
            charset_position = self._get_element_position(soup, charset_meta)
        else:
            # Método 2: HTML4 <meta http-equiv="content-type" content="text/html; charset=utf-8">
            content_type_meta = self.safe_find(soup, 'meta', {'http-equiv': re.compile(r'^content-type$', re.I)})
            if content_type_meta:
                content = self.safe_get_attribute(content_type_meta, 'content')
                charset_match = re.search(r'charset=([^;]+)', content, re.I)
                if charset_match:
                    charset_found = True
                    charset_value = charset_match.group(1).strip().lower()
                    charset_method = 'html4'
                    charset_position = self._get_element_position(soup, content_type_meta)

        # Validação do charset
        if charset_value:
            charset_valid = charset_value in self.valid_charsets

        data['has_charset'] = charset_found
        data['charset_value'] = charset_value
        data['charset_method'] = charset_method
        data['charset_valid'] = charset_valid
        data['charset_is_utf8'] = charset_value == 'utf-8'
        data['charset_position'] = charset_position
        data['charset_early_declaration'] = charset_position < 10  # Dentro dos primeiros 10 elementos

    def _parse_viewport(self, soup: BeautifulSoup, data: Dict):
        """
        Parse completo do viewport para mobile optimization
        """
        viewport_meta = self.safe_find(soup, 'meta', {'name': re.compile(r'^viewport$', re.I)})
        
        if viewport_meta:
            viewport_content = self.safe_get_attribute(viewport_meta, 'content')

            data['has_viewport'] = True
            data['viewport_content'] = viewport_content

            # Análise detalhada do viewport
            self._analyze_viewport_content(viewport_content, data)
        else:
            data['has_viewport'] = False
            data['viewport_content'] = ''
            data['viewport_mobile_optimized'] = False
            data['viewport_issues'] = ['viewport_missing']

    def _analyze_viewport_content(self, viewport_content: str, data: Dict):
        """
        Analisa o conteúdo do viewport em detalhes
        """
        if not viewport_content:
            data['viewport_mobile_optimized'] = False
            data['viewport_issues'] = ['viewport_empty']
            return

        viewport_lower = viewport_content.lower().replace(' ', '')
        issues = []

        # Verifica se é um dos recomendados
        viewport_clean = viewport_content.replace(' ', '').lower()
        is_recommended = any(rec.replace(' ', '').lower() == viewport_clean
                           for rec in self.recommended_viewports)

        data['viewport_is_recommended'] = is_recommended

        # Análise de componentes específicos
        data['viewport_has_width_device'] = 'width=device-width' in viewport_lower
        data['viewport_has_initial_scale'] = 'initial-scale' in viewport_lower

        # Extrai valores específicos
        if 'initial-scale=' in viewport_lower:
            scale_match = re.search(r'initial-scale=([0-9.]+)', viewport_lower)
            if scale_match:
                initial_scale = float(scale_match.group(1))
                data['viewport_initial_scale'] = initial_scale
                data['viewport_scale_optimal'] = initial_scale == 1.0

                if initial_scale < 1.0:
                    issues.append('initial_scale_too_small')
                elif initial_scale > 1.0:
                    issues.append('initial_scale_too_large')
            else:
                data['viewport_initial_scale'] = None
                data['viewport_scale_optimal'] = False

        # Verifica user-scalable
        data['viewport_user_scalable'] = 'user-scalable=no' not in viewport_lower
        if 'user-scalable=no' in viewport_lower:
            issues.append('user_scaling_disabled')  # Pode ser problema de acessibilidade

        # Verifica maximum-scale
        if 'maximum-scale=' in viewport_lower:
            max_scale_match = re.search(r'maximum-scale=([0-9.]+)', viewport_lower)
            if max_scale_match:
                max_scale = float(max_scale_match.group(1))
                data['viewport_maximum_scale'] = max_scale
                if max_scale < 1.0:
                    issues.append('maximum_scale_too_restrictive')

        # Verifica width específico (não device-width)
        if 'width=' in viewport_lower and 'width=device-width' not in viewport_lower:
            width_match = re.search(r'width=(\d+)', viewport_lower)
            if width_match:
                issues.append('fixed_width_instead_of_device')

        # Score geral de mobile optimization
        mobile_factors = [
            data.get('viewport_has_width_device', False),
            data.get('viewport_has_initial_scale', False),
            data.get('viewport_scale_optimal', False),
            data.get('viewport_user_scalable', True),  # True é melhor
            len(issues) == 0
        ]

        data['viewport_mobile_optimized'] = sum(mobile_factors) >= 3
        data['viewport_issues'] = issues
        data['viewport_mobile_score'] = int((sum(mobile_factors) / len(mobile_factors)) * 100)

    def _parse_favicon(self, soup: BeautifulSoup, data: Dict, url: str = None):
        """
        Parse completo de favicons (múltiplos formatos e tamanhos)
        """
        # Encontra todos os links relacionados a favicon
        favicon_links = self.safe_find_all(soup, 'link', {'rel': re.compile(r'icon|shortcut|apple-touch', re.I)})

        data['favicon_links_count'] = len(favicon_links)
        data['favicon_details'] = []

        if not favicon_links:
            data['has_favicon'] = False
            data['favicon_formats'] = []
            data['favicon_coverage_score'] = 0
            return

        data['has_favicon'] = True

        favicon_formats = set()
        favicon_sizes = set()

        for link in favicon_links:
            rel = self.safe_get_attribute(link, 'rel').lower()
            href = self.safe_get_attribute(link, 'href')
            sizes = self.safe_get_attribute(link, 'sizes')
            type_attr = self.safe_get_attribute(link, 'type')

            # Resolve URL completa
            if url and href:
                full_href = urljoin(url, href) if not href.startswith('http') else href
            else:
                full_href = href

            # Determina formato
            favicon_format = self._determine_favicon_format(rel, href, type_attr)
            if favicon_format:
                favicon_formats.add(favicon_format)

            # Coleta tamanhos
            if sizes and sizes.lower() != 'any':
                sizes_list = [s.strip() for s in sizes.split(',')]
                favicon_sizes.update(sizes_list)

            favicon_details = {
                'rel': rel,
                'href': href,
                'full_href': full_href,
                'sizes': sizes,
                'type': type_attr,
                'format': favicon_format,
                'is_valid_url': self.is_valid_url(full_href) if full_href else False
            }
            data['favicon_details'].append(favicon_details)

        data['favicon_formats'] = list(favicon_formats)
        data['favicon_sizes'] = list(favicon_sizes)

        # Análise de cobertura
        self._analyze_favicon_coverage(data)
    
    def _determine_favicon_format(self, rel: str, href: str, type_attr: str) -> str:
        """
        Determina o formato do favicon baseado em rel, href e type
        """
        rel_lower = rel.lower()

        if 'apple-touch' in rel_lower:
            return 'apple-touch-icon'
        elif type_attr and 'svg' in type_attr.lower():
            return 'svg'
        elif href:
            href_lower = href.lower()
            if href_lower.endswith('.ico'):
                return 'ico'
            elif href_lower.endswith('.png'):
                return 'png'
            elif href_lower.endswith('.svg'):
                return 'svg'
            elif href_lower.endswith('.gif'):
                return 'gif'

        return 'unknown'

    def _analyze_favicon_coverage(self, data: Dict):
        """
        Analisa cobertura de favicon para diferentes dispositivos
        """
        formats = set(data.get('favicon_formats', []))
        sizes = set(data.get('favicon_sizes', []))

        coverage_factors = []

        # Tem formato básico
        coverage_factors.append('ico' in formats or 'png' in formats)

        # Tem formato moderno
        coverage_factors.append('svg' in formats)

        # Tem Apple touch icon
        coverage_factors.append('apple-touch-icon' in formats)

        # Tem múltiplos tamanhos
        coverage_factors.append(len(sizes) >= 2)
        
        # Tem tamanhos adequados
        has_small = any(size in sizes for size in ['16x16', '32x32'])
        has_large = any(size in sizes for size in ['192x192', '180x180'])
        coverage_factors.append(has_small and has_large)

        data['favicon_coverage_score'] = int((sum(coverage_factors) / len(coverage_factors)) * 100)
        data['favicon_has_modern_formats'] = 'svg' in formats
        data['favicon_has_apple_touch'] = 'apple-touch-icon' in formats
        data['favicon_has_multiple_sizes'] = len(sizes) >= 2

    def _parse_amp_detection(self, soup: BeautifulSoup, data: Dict):
        """
        Detecção completa de páginas AMP
        """
        # Método 1: atributo amp ou ⚡ na tag html
        html_tag = soup.find('html')
        is_amp_html = False

        if html_tag:
            is_amp_html = (html_tag.has_attr('amp') or
                          html_tag.has_attr('⚡') or
                          html_tag.has_attr('data-ampdevmode'))

        # Método 2: meta tags AMP
        amp_canonical = self.safe_find(soup, 'link', {'rel': 'amphtml'})
        canonical_amp = self.safe_find(soup, 'link', {'rel': 'canonical'})

        # Método 3: scripts AMP
        amp_scripts = self.safe_find_all(soup, 'script', {'src': re.compile(r'ampproject\.org', re.I)})
        amp_runtime = self.safe_find(soup, 'script', {'src': re.compile(r'v0\.js', re.I)})

        data['is_amp'] = is_amp_html
        data['has_amp_canonical'] = amp_canonical is not None
        data['has_canonical_amp'] = canonical_amp is not None
        data['amp_scripts_count'] = len(amp_scripts)
        data['has_amp_runtime'] = amp_runtime is not None

        # Análise detalhada AMP
        if is_amp_html:
            data['amp_type'] = 'amp_page'
            data['amp_validation_required'] = True
        elif amp_canonical:
            data['amp_type'] = 'has_amp_version'
            data['amp_canonical_url'] = self.safe_get_attribute(amp_canonical, 'href')
        else:
            data['amp_type'] = 'no_amp'
            data['amp_validation_required'] = False

    def _parse_meta_robots_advanced(self, soup: BeautifulSoup, data: Dict):
        """
        Parse avançado de meta robots e diretivas de crawling
        """
        # Meta robots padrão
        meta_robots = self.find_meta_by_name(soup, 'robots')

        if meta_robots:
            robots_content = self.extract_meta_content(meta_robots).lower()
            data['meta_robots'] = robots_content

            # Parse individual de diretivas
            directives = [d.strip() for d in robots_content.split(',')]
            data['meta_robots_directives'] = directives

            # Análise de diretivas específicas
            self._analyze_robots_directives(directives, data)
        else:
            data['meta_robots'] = ''
            data['meta_robots_directives'] = []
            data['robots_allows_indexing'] = True  # Default
            data['robots_allows_following'] = True  # Default

        # Meta robots específicos por bot
        self._parse_bot_specific_robots(soup, data)

        # Meta refresh (pode impactar SEO)
        meta_refresh = self.find_meta_by_name(soup, 'refresh') or self.safe_find(soup, 'meta', {'http-equiv': re.compile(r'^refresh$', re.I)})
        if meta_refresh:
            refresh_content = self.extract_meta_content(meta_refresh)
            data['has_meta_refresh'] = True
            data['meta_refresh_content'] = refresh_content
            data['meta_refresh_delay'] = self._extract_refresh_delay(refresh_content)
        else:
            data['has_meta_refresh'] = False
            data['meta_refresh_content'] = ''
            data['meta_refresh_delay'] = 0

    def _analyze_robots_directives(self, directives: List[str], data: Dict):
        """
        Analisa diretivas específicas do meta robots
        """
        # Diretivas principais
        data['robots_noindex'] = 'noindex' in directives or 'none' in directives
        data['robots_nofollow'] = 'nofollow' in directives or 'none' in directives
        data['robots_noarchive'] = 'noarchive' in directives
        data['robots_nosnippet'] = 'nosnippet' in directives
        data['robots_noimageindex'] = 'noimageindex' in directives
        data['robots_notranslate'] = 'notranslate' in directives

        # Estados resultantes
        data['robots_allows_indexing'] = not data['robots_noindex']
        data['robots_allows_following'] = not data['robots_nofollow']
        
        # Verifica diretivas inválidas
        valid_directives = set(self.valid_robots_directives)
        invalid_directives = [d for d in directives if d not in valid_directives and d]
        data['robots_invalid_directives'] = invalid_directives
        data['robots_has_invalid_directives'] = len(invalid_directives) > 0

    def _parse_bot_specific_robots(self, soup: BeautifulSoup, data: Dict):
        """
        Parse de meta robots específicos por bot
        """
        bot_robots = {}

        # Bots comuns
        bots = ['googlebot', 'bingbot', 'slurp', 'duckduckbot', 'baiduspider', 'yandexbot']

        for bot in bots:
            bot_meta = self.find_meta_by_name(soup, bot)
            if bot_meta:
                bot_content = self.extract_meta_content(bot_meta)
                bot_robots[bot] = bot_content

        data['bot_specific_robots'] = bot_robots
        data['has_bot_specific_robots'] = len(bot_robots) > 0

    def _parse_performance_hints(self, soup: BeautifulSoup, data: Dict, url: str = None):
        """
        Parse de performance hints (dns-prefetch, preload, etc.)
        """
        performance_links = []
        hint_counts = {}

        for hint in self.performance_hints:
            links = self.safe_find_all(soup, 'link', {'rel': hint})
            hint_counts[hint] = len(links)

            for link in links:
                href = self.safe_get_attribute(link, 'href')
                as_attr = self.safe_get_attribute(link, 'as')
                type_attr = self.safe_get_attribute(link, 'type')

                performance_links.append({
                    'rel': hint,
                    'href': href,
                    'as': as_attr,
                    'type': type_attr,
                    'is_external': self._is_external_domain(href, url) if url else False
                })

        data['performance_hints_count'] = len(performance_links)
        data['performance_hints_details'] = performance_links
        data['performance_hints_by_type'] = hint_counts

        # Análise de performance optimization
        data['uses_dns_prefetch'] = hint_counts.get('dns-prefetch', 0) > 0
        data['uses_preconnect'] = hint_counts.get('preconnect', 0) > 0
        data['uses_preload'] = hint_counts.get('preload', 0) > 0
        data['performance_optimized'] = sum([
            data['uses_dns_prefetch'],
            data['uses_preconnect'],
            data['uses_preload']
        ]) >= 2

    def _parse_security_headers(self, soup: BeautifulSoup, data: Dict):
        """
        Parse de headers de segurança via meta tags
        """
        # Content Security Policy
        csp_meta = self.safe_find(soup, 'meta', {'http-equiv': re.compile(r'^content-security-policy$', re.I)})
        if csp_meta:
            csp_content = self.safe_get_attribute(csp_meta, 'content')
            data['has_csp_meta'] = True
            data['csp_meta_content'] = csp_content
        else:
            data['has_csp_meta'] = False
            data['csp_meta_content'] = ''

        # X-Frame-Options
        xframe_meta = self.safe_find(soup, 'meta', {'http-equiv': re.compile(r'^x-frame-options$', re.I)})
        if xframe_meta:
            xframe_content = self.safe_get_attribute(xframe_meta, 'content')
            data['has_xframe_meta'] = True
            data['xframe_meta_content'] = xframe_content
        else:
            data['has_xframe_meta'] = False
            data['xframe_meta_content'] = ''

        # Referrer Policy
        referrer_meta = self.find_meta_by_name(soup, 'referrer')
        if referrer_meta:
            referrer_content = self.extract_meta_content(referrer_meta)
            data['has_referrer_policy'] = True
            data['referrer_policy_content'] = referrer_content
        else:
            data['has_referrer_policy'] = False
            data['referrer_policy_content'] = ''

        data['security_headers_count'] = sum([
            data['has_csp_meta'],
            data['has_xframe_meta'],
            data['has_referrer_policy']
        ])

    def _parse_html_structure(self, soup: BeautifulSoup, data: Dict):
        """
        Parse da estrutura básica do HTML
        """
        # Tags obrigatórias
        data['has_html_tag'] = soup.find('html') is not None
        data['has_head_tag'] = soup.find('head') is not None
        data['has_body_tag'] = soup.find('body') is not None
        data['has_title_tag'] = soup.find('title') is not None

        # Estrutura básica válida
        required_structure = [
            data['has_html_tag'],
            data['has_head_tag'],
            data['has_body_tag'],
            data['has_title_tag']
        ]

        data['html_structure_valid'] = all(required_structure)
        data['html_structure_score'] = int((sum(required_structure) / len(required_structure)) * 100)

    def _analyze_technical_quality(self, data: Dict):
        """
        Analisa qualidade técnica geral
        """
        quality_factors = [
            data.get('doctype_valid', False),
            data.get('has_html_lang', False),
            data.get('charset_is_utf8', False),
            data.get('has_viewport', False),
            data.get('has_favicon', False),
            data.get('html_structure_valid', False),
            data.get('robots_allows_indexing', True),
            not data.get('has_meta_refresh', False)  # Refresh é problemático
        ]
        
        data['technical_quality_score'] = int((sum(quality_factors) / len(quality_factors)) * 100)
        data['technical_standards_compliant'] = sum(quality_factors) >= 6

    def _analyze_mobile_optimization(self, data: Dict):
        """
        Analisa otimização para mobile
        """
        mobile_factors = [
            data.get('has_viewport', False),
            data.get('viewport_mobile_optimized', False),
            data.get('favicon_has_apple_touch', False),
            data.get('html_lang_valid', False)
        ]

        data['mobile_optimization_score'] = int((sum(mobile_factors) / len(mobile_factors)) * 100)
        data['mobile_ready'] = sum(mobile_factors) >= 3

    def _analyze_performance_optimization(self, data: Dict):
        """
        Analisa otimização de performance
        """
        performance_factors = [
            data.get('charset_early_declaration', False),
            data.get('uses_dns_prefetch', False),
            data.get('uses_preconnect', False),
            data.get('uses_preload', False),
            not data.get('has_meta_refresh', False)
        ]
        
        data['performance_optimization_score'] = int((sum(performance_factors) / len(performance_factors)) * 100)
        data['performance_optimized'] = sum(performance_factors) >= 3

    def _detect_technical_issues(self, data: Dict):
        """
        Detecta problemas técnicos comuns
        """
        issues = []

        # Problemas críticos
        if not data.get('has_doctype', False):
            issues.append('doctype_ausente')
        elif not data.get('doctype_valid', False):
            issues.append('doctype_invalido')
        
        if not data.get('has_charset', False):
            issues.append('charset_ausente')
        elif not data.get('charset_is_utf8', False):
            issues.append('charset_nao_utf8')

        # Problemas de mobile
        if not data.get('has_viewport', False):
            issues.append('viewport_ausente')
        elif not data.get('viewport_mobile_optimized', False):
            issues.append('viewport_nao_otimizado')

        # Problemas de estrutura
        if not data.get('html_structure_valid', False):
            issues.append('estrutura_html_invalida')

        if not data.get('has_html_lang', False):
            issues.append('lang_ausente')
        elif not data.get('html_lang_valid', False):
            issues.append('lang_invalido')

        # Problemas de SEO
        if data.get('robots_noindex', False):
            issues.append('pagina_bloqueada_indexacao')
        
        if data.get('has_meta_refresh', False):
            issues.append('meta_refresh_presente')

        # Problemas de performance
        if not data.get('charset_early_declaration', False):
            issues.append('charset_declaracao_tardia')
        
        data['technical_issues'] = issues
        data['technical_issues_count'] = len(issues)

    def _calculate_technical_severity(self, data: Dict):
        """
        Calcula severity score para problemas técnicos
        """
        issues = data.get('technical_issues', [])

        # Mapeia issues para chaves de severity
        severity_issues = []
        for issue in issues:
            if issue in ['doctype_ausente', 'charset_ausente', 'estrutura_html_invalida']:
                severity_issues.append('html_estrutura_critica')
            elif issue in ['viewport_ausente', 'viewport_nao_otimizado']:
                severity_issues.append('mobile_nao_otimizado')
            elif issue in ['pagina_bloqueada_indexacao', 'meta_refresh_presente']:
                severity_issues.append('seo_tecnico_problematico')
            else:
                severity_issues.append('tecnico_nao_otimizado')
        
        # Calcula severidade geral
        data['technical_severity_level'] = self.calculate_problem_severity(severity_issues)
        data['technical_problems_keys'] = severity_issues
        data['technical_problems_by_severity'] = self.categorize_problems_by_severity(severity_issues)

    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================

    def _get_element_position(self, soup: BeautifulSoup, element: Tag) -> int:
        """
        Obtém a posição de um elemento no head (para charset)
        """
        try:
            head_tag = soup.find('head')
            if head_tag and element:
                head_children = [child for child in head_tag.children if hasattr(child, 'name')]
                return head_children.index(element) + 1
        except:
            pass
        return 999  # Posição muito alta se não conseguir determinar

    def _extract_refresh_delay(self, refresh_content: str) -> int:
        """
        Extrai delay do meta refresh
        """
        try:
            # Formato: "5; url=http://example.com" ou apenas "5"
            delay_match = re.search(r'^(\d+)', refresh_content.strip())
            if delay_match:
                return int(delay_match.group(1))
        except:
            pass
        return 0
    
    def _is_external_domain(self, href: str, base_url: str) -> bool:
        """
        Verifica se href é de domínio externo
        """
        if not href or not base_url:
            return False

        try:
            if not href.startswith('http'):
                return False  # Relativo = interno

            href_domain = urlparse(href).netloc
            base_domain = urlparse(base_url).netloc

            return href_domain != base_domain
        except:
            return False

    # ==========================================
    # MÉTODOS DE ANÁLISE E RELATÓRIOS
    # ==========================================

    def get_technical_summary(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera resumo da análise técnica
        """
        return {
            'technical_quality_score': parsed_data.get('technical_quality_score', 0),
            'mobile_optimization_score': parsed_data.get('mobile_optimization_score', 0),
            'performance_optimization_score': parsed_data.get('performance_optimization_score', 0),
            'is_html5': parsed_data.get('is_html5', False),
            'mobile_ready': parsed_data.get('mobile_ready', False),
            'performance_optimized': parsed_data.get('performance_optimized', False),
            'technical_severity_level': parsed_data.get('technical_severity_level', SeverityLevel.BAIXA),
            'main_issues': parsed_data.get('technical_issues', [])[:3],
            'has_critical_issues': any(issue in parsed_data.get('technical_issues', [])
                                     for issue in ['doctype_ausente', 'charset_ausente', 'viewport_ausente']),
            'favicon_coverage': parsed_data.get('favicon_coverage_score', 0),
            'security_headers_count': parsed_data.get('security_headers_count', 0)
        }

    def validate_technical_best_practices(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida boas práticas técnicas
        """
        validations = {}

        # HTML5 e estrutura
        validations['uses_html5'] = parsed_data.get('is_html5', False)
        validations['valid_html_structure'] = parsed_data.get('html_structure_valid', False)
        validations['has_proper_charset'] = parsed_data.get('charset_is_utf8', False)
        validations['early_charset_declaration'] = parsed_data.get('charset_early_declaration', False)

        # Internacionalização
        validations['has_language_declaration'] = parsed_data.get('has_html_lang', False)
        validations['valid_language_code'] = parsed_data.get('html_lang_valid', False)

        # Mobile optimization
        validations['mobile_viewport'] = parsed_data.get('has_viewport', False)
        validations['mobile_optimized_viewport'] = parsed_data.get('viewport_mobile_optimized', False)
        validations['mobile_ready'] = parsed_data.get('mobile_ready', False)

        # Icons e branding
        validations['has_favicon'] = parsed_data.get('has_favicon', False)
        validations['good_favicon_coverage'] = parsed_data.get('favicon_coverage_score', 0) >= 70

        # Performance
        validations['uses_performance_hints'] = parsed_data.get('performance_hints_count', 0) > 0
        validations['performance_optimized'] = parsed_data.get('performance_optimized', False)
        
        # SEO técnico
        validations['indexing_allowed'] = parsed_data.get('robots_allows_indexing', True)
        validations['no_meta_refresh'] = not parsed_data.get('has_meta_refresh', False)

        # Sem problemas críticos
        validations['no_critical_technical_issues'] = parsed_data.get('technical_severity_level') != SeverityLevel.CRITICA   

        # Score geral
        score_items = [
            validations['uses_html5'],
            validations['valid_html_structure'],
            validations['has_proper_charset'],
            validations['has_language_declaration'],
            validations['mobile_viewport'],
            validations['mobile_optimized_viewport'],
            validations['has_favicon'],
            validations['indexing_allowed'],
            validations['no_meta_refresh'],
            validations['no_critical_technical_issues']
        ]

        validations['technical_best_practices_score'] = int((sum(score_items) / len(score_items)) * 100)

        return validations


# ==========================================
# FUNÇÃO STANDALONE PARA TESTES
# ==========================================

def parse_technical_elements(html_content: str, url: str = 'https://example.com') -> Dict[str, Any]:
    """
    Função standalone para testar o TechnicalParser
    
    Args:
        html_content: HTML da página
        url: URL da página (para validação de links)
        
    Returns:
        Dict com dados técnicos parseados
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'lxml')
    parser = TechnicalParser()
    
    # Parse básico
    data = parser.parse(soup, url)
    
    # Adiciona análises extras
    data.update(parser.get_technical_summary(data))
    data.update(parser.validate_technical_best_practices(data))
    
    return data


# ==========================================
# EXEMPLO DE USO E TESTE
# ==========================================

if __name__ == "__main__":
    # Teste com HTML com diversos elementos técnicos
    test_html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Página de Teste Técnico</title>
        
        <!-- Favicons múltiplos -->
        <link rel="icon" type="image/x-icon" href="/favicon.ico">
        <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
        <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
        <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
        <link rel="icon" type="image/svg+xml" href="/favicon.svg">
        
        <!-- Performance hints -->
        <link rel="dns-prefetch" href="//fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link rel="preload" href="/critical.css" as="style">
        
        <!-- Meta robots -->
        <meta name="robots" content="index, follow, max-snippet:-1">
        <meta name="googlebot" content="index, follow, max-image-preview:large">
        
        <!-- Security headers -->
        <meta http-equiv="X-Frame-Options" content="DENY">
        <meta name="referrer" content="strict-origin-when-cross-origin">
        
        <!-- Problemas intencionais para teste -->
        <meta http-equiv="refresh" content="30; url=/nova-pagina">
        
    </head>
    <body>
        <h1>Página com Elementos Técnicos</h1>
        <p>Esta página tem diversos elementos técnicos para testar o parser.</p>
    </body>
    </html>
    """
    
    # Parse e resultado
    result = parse_technical_elements(test_html)
    
    print("🔍 RESULTADO DO TECHNICAL PARSER:")
    print(f"   DOCTYPE: {result.get('doctype_type', 'N/A')} (HTML5: {result['is_html5']})")
    print(f"   Charset: {result.get('charset_value', 'N/A')} (UTF-8: {result.get('charset_is_utf8', False)})")
    print(f"   Language: {result.get('html_lang', 'N/A')} (Valid: {result.get('html_lang_valid', False)})")
    print(f"   Viewport: {result.get('viewport_content', 'N/A')}")
    print(f"   Mobile Optimized: {result.get('mobile_ready', False)} ({result.get('mobile_optimization_score', 0)}%)")       
    print(f"   Favicon Coverage: {result.get('favicon_coverage_score', 0)}% ({result.get('favicon_links_count', 0)} links)") 
    print(f"   Performance Hints: {result.get('performance_hints_count', 0)} encontrados")
    print(f"   Security Headers: {result.get('security_headers_count', 0)} encontrados")

    print(f"\n📊 SCORES:")
    print(f"   Technical Quality: {result['technical_quality_score']}/100")
    print(f"   Mobile Optimization: {result['mobile_optimization_score']}/100")
    print(f"   Performance Optimization: {result['performance_optimization_score']}/100")
    print(f"   Best Practices: {result['technical_best_practices_score']}/100")
    print(f"   Technical Severity: {result['technical_severity_level']}")

    print(f"\n🚀 STATUS:")
    print(f"   Standards Compliant: {result.get('technical_standards_compliant', False)}")
    print(f"   Mobile Ready: {result['mobile_ready']}")
    print(f"   Performance Optimized: {result['performance_optimized']}")
    print(f"   Critical Issues: {result['has_critical_issues']}")

    if result['technical_issues']:
        print(f"\n⚠️  Issues encontradas:")
        for issue in result['technical_issues']:
            print(f"      - {issue}")

    print(f"\n🔧 DETALHES TÉCNICOS:")
    print(f"   Favicon Formats: {result.get('favicon_formats', [])}")
    print(f"   Performance Hints: {result.get('performance_hints_by_type', {})}")
    print(f"   Viewport Issues: {result.get('viewport_issues', [])}")
    print(f"   Meta Refresh: {result.get('has_meta_refresh', False)} (Delay: {result.get('meta_refresh_delay', 0)}s)")       

    if result.get('bot_specific_robots'):
        print(f"   Bot-specific robots: {result['bot_specific_robots']}")