"""
seofrog/parsers/security_parser.py
Parser modular para análise completa de Segurança
Responsável por: Mixed Content, HTTPS, Security Headers, Vulnerabilidades
"""

import re
import requests
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List, Optional, Set
from bs4 import BeautifulSoup, Tag
from .base import ParserMixin, SeverityLevel

class SecurityParser(ParserMixin):
    """
    Parser especializado para análise completa de segurança
    Responsável por: Mixed Content, HTTPS, Security Headers, Vulnerabilidades
    """
    
    def __init__(self, check_external_resources: bool = False, timeout: int = 3):
        super().__init__()
        
        # Configurações
        self.check_external_resources = check_external_resources  # Se deve verificar recursos externos
        self.timeout = timeout
        
        # Recursos que causam Mixed Content
        self.mixed_content_tags = {
            'active': [  # Mixed Active Content (crítico)
                'script', 'iframe', 'object', 'embed'
            ],
            'passive': [  # Mixed Passive Content (warning)
                'img', 'audio', 'video', 'source'
            ]
        }
        
        # Atributos que podem conter URLs
        self.url_attributes = [
            'src', 'href', 'action', 'data', 'poster', 
            'background', 'cite', 'codebase', 'formaction'
        ]
        
        # Headers de segurança importantes
        self.security_headers = {
            'content-security-policy': 'CSP',
            'x-frame-options': 'X-Frame-Options',
            'x-content-type-options': 'X-Content-Type-Options',
            'x-xss-protection': 'X-XSS-Protection',
            'strict-transport-security': 'HSTS',
            'referrer-policy': 'Referrer-Policy',
            'permissions-policy': 'Permissions-Policy',
            'cross-origin-embedder-policy': 'COEP',
            'cross-origin-opener-policy': 'COOP',
            'cross-origin-resource-policy': 'CORP'
        }
        
        # Padrões de vulnerabilidades comuns
        self.vulnerability_patterns = {
            'inline_js': r'<script[^>]*>.*?</script>',
            'inline_css': r'<style[^>]*>.*?</style>',
            'eval_usage': r'eval\s*\(',
            'document_write': r'document\.write\s*\(',
            'inner_html': r'innerHTML\s*=',
            'external_js': r'<script[^>]+src=["\']https?://(?!(?:www\.)?{domain})',
            'http_forms': r'<form[^>]+action=["\']http://',
            'mailto_exposure': r'mailto:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            'ip_addresses': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'aws_keys': r'AKIA[0-9A-Z]{16}',
            'generic_api_keys': r'["\'][a-zA-Z0-9_-]{32,}["\']'
        }
        
        # CSP directives importantes
        self.important_csp_directives = [
            'default-src', 'script-src', 'style-src', 'img-src',
            'connect-src', 'font-src', 'object-src', 'media-src',
            'frame-src', 'worker-src', 'child-src', 'form-action',
            'frame-ancestors', 'base-uri', 'upgrade-insecure-requests'
        ]
    
    def parse(self, soup: BeautifulSoup, url: str = None, response_headers: Dict = None) -> Dict[str, Any]:
        """
        Parse completo de análise de segurança
        
        Args:
            soup: BeautifulSoup object da página
            url: URL da página atual
            response_headers: Headers de resposta HTTP (opcional)
            
        Returns:
            Dict com dados completos de segurança
        """
        data = {}
        
        try:
            # Informações básicas da página
            self._analyze_page_security_context(url, data)
            
            # Mixed Content Analysis
            self._analyze_mixed_content(soup, data, url)
            
            # Security Headers Analysis
            self._analyze_security_headers(soup, data, response_headers)
            
            # Content Security Policy
            self._analyze_csp(soup, data, response_headers)
            
            # Vulnerability Patterns
            self._analyze_vulnerability_patterns(soup, data)
            
            # External Resources Security
            self._analyze_external_resources(soup, data, url)
            
            # Form Security
            self._analyze_form_security(soup, data, url)
            
            # Cookie Security (via meta tags)
            self._analyze_cookie_security(soup, data)
            
            # Calculate overall security scores
            self._calculate_security_scores(data)
            
            # Detect security issues
            self._detect_security_issues(data)
            
            # Severity scoring
            self._calculate_security_severity(data)
            
            # Log estatísticas
            errors = 1 if any(key.endswith('_error') for key in data.keys()) else 0
            self.log_parsing_stats('SecurityParser', len(data), errors)
            
        except Exception as e:
            self.logger.error(f"Erro no parse de segurança: {e}")
            data['security_parse_error'] = str(e)
            self.log_parsing_stats('SecurityParser', len(data), 1)
        
        return data
    
    def _analyze_page_security_context(self, url: str, data: Dict):
        """
        Analisa contexto básico de segurança da página
        """
        if url:
            parsed_url = urlparse(url)
            data['page_protocol'] = parsed_url.scheme.lower()
            data['is_https_page'] = parsed_url.scheme.lower() == 'https'
            data['is_http_page'] = parsed_url.scheme.lower() == 'http'
            data['page_domain'] = parsed_url.netloc.lower()
            data['has_subdomain'] = len(parsed_url.netloc.split('.')) > 2
        else:
            data['page_protocol'] = 'unknown'
            data['is_https_page'] = False
            data['is_http_page'] = False
            data['page_domain'] = ''
            data['has_subdomain'] = False
    
    def _analyze_mixed_content(self, soup: BeautifulSoup, data: Dict, url: str):
        """
        Analisa problemas de Mixed Content (HTTPS page loading HTTP resources)
        """
        if not data.get('is_https_page', False):
            # Não há mixed content se a página não é HTTPS
            data['mixed_content_applicable'] = False
            data['active_mixed_content_count'] = 0
            data['passive_mixed_content_count'] = 0
            data['total_mixed_content_count'] = 0
            data['mixed_content_risk'] = 'N/A'
            return
        
        data['mixed_content_applicable'] = True
        active_mixed = []
        passive_mixed = []
        
        # Verifica recursos HTTP em página HTTPS
        all_elements = soup.find_all()
        
        for element in all_elements:
            tag_name = element.name.lower()
            
            # Verifica atributos que podem conter URLs
            for attr in self.url_attributes:
                if element.has_attr(attr):
                    resource_url = element.get(attr, '').strip()
                    
                    if resource_url.startswith('http://'):
                        mixed_item = {
                            'tag': tag_name,
                            'attribute': attr,
                            'url': resource_url,
                            'element_html': str(element)[:200]
                        }
                        
                        # Classifica como Active ou Passive Mixed Content
                        if tag_name in self.mixed_content_tags['active']:
                            active_mixed.append(mixed_item)
                        elif tag_name in self.mixed_content_tags['passive']:
                            passive_mixed.append(mixed_item)
                        else:
                            # Outros elementos são considerados passive
                            passive_mixed.append(mixed_item)
        
        # Verifica CSS inline para background-image HTTP
        style_elements = soup.find_all(attrs={'style': True})
        for element in style_elements:
            style_content = element.get('style', '')
            http_urls = re.findall(r'url\(["\']?(http://[^"\')\s]+)', style_content)
            for http_url in http_urls:
                passive_mixed.append({
                    'tag': element.name,
                    'attribute': 'style',
                    'url': http_url,
                    'element_html': str(element)[:200]
                })
        
        # Resultados
        data['active_mixed_content_count'] = len(active_mixed)
        data['passive_mixed_content_count'] = len(passive_mixed)
        data['total_mixed_content_count'] = len(active_mixed) + len(passive_mixed)
        data['active_mixed_content_details'] = active_mixed
        data['passive_mixed_content_details'] = passive_mixed
        
        # Risk assessment
        if len(active_mixed) > 0:
            data['mixed_content_risk'] = 'CRÍTICO'
        elif len(passive_mixed) > 5:
            data['mixed_content_risk'] = 'ALTO'
        elif len(passive_mixed) > 0:
            data['mixed_content_risk'] = 'MÉDIO'
        else:
            data['mixed_content_risk'] = 'BAIXO'
    
    def _analyze_security_headers(self, soup: BeautifulSoup, data: Dict, response_headers: Dict = None):
        """
        Analisa security headers (via meta tags e response headers)
        """
        found_headers = {}
        
        # 1. Via meta tags HTTP-EQUIV
        for header_name, display_name in self.security_headers.items():
            meta_tag = self.safe_find(soup, 'meta', {'http-equiv': re.compile(f'^{header_name}$', re.I)})
            if meta_tag:
                content = self.safe_get_attribute(meta_tag, 'content')
                found_headers[header_name] = {
                    'source': 'meta_tag',
                    'value': content,
                    'display_name': display_name
                }
        
        # 2. Via response headers (se fornecido)
        if response_headers:
            for header_name, display_name in self.security_headers.items():
                if header_name in response_headers:
                    found_headers[header_name] = {
                        'source': 'response_header',
                        'value': response_headers[header_name],
                        'display_name': display_name
                    }
        
        data['security_headers_found'] = found_headers
        data['security_headers_count'] = len(found_headers)
        
        # Análise específica de headers importantes
        data['has_csp'] = 'content-security-policy' in found_headers
        data['has_xframe_options'] = 'x-frame-options' in found_headers
        data['has_hsts'] = 'strict-transport-security' in found_headers
        data['has_content_type_options'] = 'x-content-type-options' in found_headers
        data['has_xss_protection'] = 'x-xss-protection' in found_headers
        
        # Qualidade dos headers
        self._analyze_header_quality(found_headers, data)
    
    def _analyze_header_quality(self, headers: Dict, data: Dict):
        """
        Analisa qualidade dos security headers encontrados
        """
        quality_issues = []
        
        # X-Frame-Options analysis
        if 'x-frame-options' in headers:
            xframe_value = headers['x-frame-options']['value'].upper()
            if xframe_value not in ['DENY', 'SAMEORIGIN']:
                quality_issues.append('xframe_options_weak')
        
        # X-Content-Type-Options analysis
        if 'x-content-type-options' in headers:
            content_type_value = headers['x-content-type-options']['value'].lower()
            if 'nosniff' not in content_type_value:
                quality_issues.append('content_type_options_weak')
        
        # HSTS analysis
        if 'strict-transport-security' in headers:
            hsts_value = headers['strict-transport-security']['value']
            max_age_match = re.search(r'max-age=(\d+)', hsts_value)
            if max_age_match:
                max_age = int(max_age_match.group(1))
                data['hsts_max_age'] = max_age
                if max_age < 31536000:  # < 1 year
                    quality_issues.append('hsts_max_age_low')
            else:
                quality_issues.append('hsts_no_max_age')
        
        data['security_headers_quality_issues'] = quality_issues
        data['security_headers_quality_score'] = max(0, 100 - (len(quality_issues) * 20))
    
    def _analyze_csp(self, soup: BeautifulSoup, data: Dict, response_headers: Dict = None):
        """
        Análise detalhada de Content Security Policy
        """
        csp_content = None
        csp_source = None
        
        # Busca CSP em meta tag
        csp_meta = self.safe_find(soup, 'meta', {'http-equiv': re.compile(r'^content-security-policy$', re.I)})
        if csp_meta:
            csp_content = self.safe_get_attribute(csp_meta, 'content')
            csp_source = 'meta_tag'
        
        # Busca CSP em response headers (priority)
        if response_headers and 'content-security-policy' in response_headers:
            csp_content = response_headers['content-security-policy']
            csp_source = 'response_header'
        
        if not csp_content:
            data['has_csp'] = False
            data['csp_score'] = 0
            data['csp_directives_count'] = 0
            return
        
        data['has_csp'] = True
        data['csp_content'] = csp_content
        data['csp_source'] = csp_source
        
        # Parse CSP directives
        directives = {}
        csp_parts = [part.strip() for part in csp_content.split(';') if part.strip()]
        
        for part in csp_parts:
            if ' ' in part:
                directive, sources = part.split(' ', 1)
                directives[directive.strip()] = sources.strip()
            else:
                directives[part.strip()] = ''
        
        data['csp_directives'] = directives
        data['csp_directives_count'] = len(directives)
        
        # Análise de qualidade do CSP
        self._analyze_csp_quality(directives, data)
    
    def _analyze_csp_quality(self, directives: Dict, data: Dict):
        """
        Analisa qualidade do CSP
        """
        csp_issues = []
        csp_score = 100
        
        # Verifica se tem default-src
        if 'default-src' not in directives:
            csp_issues.append('missing_default_src')
            csp_score -= 20
        
        # Verifica 'unsafe-inline' e 'unsafe-eval'
        unsafe_directives = []
        for directive, sources in directives.items():
            if "'unsafe-inline'" in sources:
                unsafe_directives.append(f"{directive}:unsafe-inline")
                csp_score -= 15
            if "'unsafe-eval'" in sources:
                unsafe_directives.append(f"{directive}:unsafe-eval")
                csp_score -= 20
        
        data['csp_unsafe_directives'] = unsafe_directives
        
        # Verifica wildcard usage
        wildcard_directives = []
        for directive, sources in directives.items():
            if '*' in sources and directive != 'img-src':  # img-src * é mais aceitável
                wildcard_directives.append(directive)
                csp_score -= 10
        
        data['csp_wildcard_directives'] = wildcard_directives
        
        # Verifica upgrade-insecure-requests
        data['csp_upgrades_insecure_requests'] = 'upgrade-insecure-requests' in directives
        
        # Important directives coverage
        important_coverage = sum(1 for directive in self.important_csp_directives if directive in directives)
        data['csp_important_directives_coverage'] = important_coverage
        data['csp_important_directives_percentage'] = (important_coverage / len(self.important_csp_directives)) * 100
        
        data['csp_issues'] = csp_issues
        data['csp_score'] = max(0, csp_score)
    
    def _analyze_vulnerability_patterns(self, soup: BeautifulSoup, data: Dict):
        """
        Analisa padrões de vulnerabilidades comuns
        """
        page_html = str(soup)
        vulnerabilities = {}
        
        for vuln_type, pattern in self.vulnerability_patterns.items():
            matches = re.findall(pattern, page_html, re.IGNORECASE | re.DOTALL)
            vulnerabilities[vuln_type] = {
                'count': len(matches),
                'found': len(matches) > 0,
                'samples': matches[:3] if matches else []  # Primeiros 3 matches
            }
        
        data['vulnerability_patterns'] = vulnerabilities
        
        # Contadores gerais
        data['inline_js_count'] = vulnerabilities['inline_js']['count']
        data['inline_css_count'] = vulnerabilities['inline_css']['count']
        data['has_eval_usage'] = vulnerabilities['eval_usage']['found']
        data['has_document_write'] = vulnerabilities['document_write']['found']
        data['exposed_emails_count'] = vulnerabilities['mailto_exposure']['count']
        data['exposed_ips_count'] = vulnerabilities['ip_addresses']['count']
        
        # Risk scoring
        high_risk_patterns = ['eval_usage', 'document_write', 'aws_keys', 'generic_api_keys']
        data['high_risk_vulnerabilities'] = sum(1 for pattern in high_risk_patterns 
                                               if vulnerabilities[pattern]['found'])
    
    def _analyze_external_resources(self, soup: BeautifulSoup, data: Dict, url: str):
        """
        Analisa segurança de recursos externos
        """
        if not url:
            return
        
        page_domain = urlparse(url).netloc.lower()
        external_resources = []
        
        # Scripts externos
        scripts = self.safe_find_all(soup, 'script', {'src': True})
        for script in scripts:
            src = self.safe_get_attribute(script, 'src')
            if src and self._is_external_resource(src, page_domain):
                external_resources.append({
                    'type': 'script',
                    'url': src,
                    'integrity': self.safe_get_attribute(script, 'integrity'),
                    'crossorigin': self.safe_get_attribute(script, 'crossorigin'),
                    'has_integrity': bool(script.get('integrity')),
                    'risk_level': 'high'  # Scripts externos são alto risco
                })
        
        # Links externos (CSS, etc)
        links = self.safe_find_all(soup, 'link', {'href': True})
        for link in links:
            href = self.safe_get_attribute(link, 'href')
            rel = self.safe_get_attribute(link, 'rel')
            if href and self._is_external_resource(href, page_domain):
                risk_level = 'high' if 'stylesheet' in rel else 'medium'
                external_resources.append({
                    'type': f"link:{rel}",
                    'url': href,
                    'integrity': self.safe_get_attribute(link, 'integrity'),
                    'crossorigin': self.safe_get_attribute(link, 'crossorigin'),
                    'has_integrity': bool(link.get('integrity')),
                    'risk_level': risk_level
                })
        
        data['external_resources'] = external_resources
        data['external_resources_count'] = len(external_resources)
        data['external_scripts_count'] = len([r for r in external_resources if r['type'] == 'script'])
        data['external_stylesheets_count'] = len([r for r in external_resources if 'stylesheet' in r['type']])
        
        # Security analysis
        resources_with_integrity = [r for r in external_resources if r['has_integrity']]
        data['external_resources_with_integrity'] = len(resources_with_integrity)
        data['external_resources_integrity_percentage'] = (
            len(resources_with_integrity) / len(external_resources) * 100 
            if external_resources else 100
        )
        
        high_risk_external = [r for r in external_resources if r['risk_level'] == 'high']
        data['high_risk_external_resources'] = len(high_risk_external)
    
    def _analyze_form_security(self, soup: BeautifulSoup, data: Dict, url: str):
        """
        Analisa segurança de formulários
        """
        forms = self.safe_find_all(soup, 'form')
        data['forms_count'] = len(forms)
        
        if not forms:
            return
        
        form_security_issues = []
        http_forms = 0
        forms_without_csrf = 0
        
        for form in forms:
            action = self.safe_get_attribute(form, 'action')
            method = self.safe_get_attribute(form, 'method').upper()
            
            # Forms com action HTTP
            if action and action.startswith('http://'):
                http_forms += 1
                form_security_issues.append('http_form_action')
            
            # Forms sem CSRF protection (heurística simples)
            csrf_inputs = form.find_all('input', {'name': re.compile(r'csrf|token|_token', re.I)})
            if method == 'POST' and not csrf_inputs:
                forms_without_csrf += 1
                form_security_issues.append('missing_csrf_protection')
        
        data['http_forms_count'] = http_forms
        data['forms_without_csrf_count'] = forms_without_csrf
        data['form_security_issues'] = list(set(form_security_issues))
        data['forms_security_score'] = max(0, 100 - (len(form_security_issues) * 25))
    
    def _analyze_cookie_security(self, soup: BeautifulSoup, data: Dict):
        """
        Analisa configurações de cookies via meta tags
        """
        # Busca meta tags relacionadas a cookies
        cookie_policy_meta = self.find_meta_by_name(soup, 'cookie-policy')
        if cookie_policy_meta:
            data['has_cookie_policy_meta'] = True
            data['cookie_policy_content'] = self.extract_meta_content(cookie_policy_meta)
        else:
            data['has_cookie_policy_meta'] = False
            data['cookie_policy_content'] = ''
        
        # Busca referências a cookies no JavaScript inline
        cookie_usage_patterns = [
            r'document\.cookie',
            r'localStorage\.',
            r'sessionStorage\.',
            r'setCookie\(',
            r'getCookie\('
        ]
        
        page_html = str(soup)
        cookie_usage = {}
        
        for pattern in cookie_usage_patterns:
            matches = re.findall(pattern, page_html, re.IGNORECASE)
            pattern_name = pattern.replace(r'\.', '_').replace(r'\(', '').replace('\\', '')
            cookie_usage[pattern_name] = len(matches)
        
        data['cookie_usage_patterns'] = cookie_usage
        data['uses_cookies'] = any(count > 0 for count in cookie_usage.values())
    
    def _calculate_security_scores(self, data: Dict):
        """
        Calcula scores gerais de segurança
        """
        # HTTPS Score
        https_score = 100 if data.get('is_https_page', False) else 0
        data['https_score'] = https_score
        
        # Mixed Content Score
        if data.get('mixed_content_applicable', False):
            active_mixed = data.get('active_mixed_content_count', 0)
            passive_mixed = data.get('passive_mixed_content_count', 0)
            
            if active_mixed > 0:
                mixed_content_score = 0  # Crítico
            elif passive_mixed > 5:
                mixed_content_score = 25  # Alto risco
            elif passive_mixed > 0:
                mixed_content_score = 60  # Médio risco
            else:
                mixed_content_score = 100  # Sem problemas
        else:
            mixed_content_score = 100 if data.get('is_https_page', False) else 50
        
        data['mixed_content_score'] = mixed_content_score
        
        # Security Headers Score
        headers_count = data.get('security_headers_count', 0)
        headers_score = min(100, (headers_count / 5) * 100)  # 5 headers principais
        data['security_headers_score'] = int(headers_score)
        
        # Vulnerability Score
        high_risk_vulns = data.get('high_risk_vulnerabilities', 0)
        inline_js = data.get('inline_js_count', 0)
        vuln_score = max(0, 100 - (high_risk_vulns * 30) - (min(inline_js, 5) * 5))
        data['vulnerability_score'] = vuln_score
        
        # External Resources Score
        external_integrity_pct = data.get('external_resources_integrity_percentage', 100)
        external_score = external_integrity_pct
        data['external_resources_score'] = int(external_score)
        
        # Overall Security Score
        scores = [
            https_score,
            mixed_content_score,
            data.get('security_headers_score', 0),
            data.get('csp_score', 0),
            vuln_score,
            external_score,
            data.get('forms_security_score', 100)
        ]
        
        data['overall_security_score'] = int(sum(scores) / len(scores))
    
    def _detect_security_issues(self, data: Dict):
        """
        Detecta problemas gerais de segurança
        """
        issues = []
        
        # Problemas críticos
        if not data.get('is_https_page', False):
            issues.append('pagina_nao_https')
        
        if data.get('active_mixed_content_count', 0) > 0:
            issues.append('mixed_content_ativo')
        
        if data.get('high_risk_vulnerabilities', 0) > 0:
            issues.append('vulnerabilidades_criticas')
        
        # Problemas altos
        if data.get('passive_mixed_content_count', 0) > 0:
            issues.append('mixed_content_passivo')
        
        if not data.get('has_csp', False):
            issues.append('csp_ausente')
        
        if data.get('external_scripts_count', 0) > 0 and data.get('external_resources_with_integrity', 0) == 0:
            issues.append('scripts_externos_sem_integridade')
        
        # Problemas médios
        if data.get('security_headers_count', 0) < 3:
            issues.append('poucos_security_headers')
        
        if data.get('inline_js_count', 0) > 5:
            issues.append('muito_javascript_inline')
        
        if data.get('http_forms_count', 0) > 0:
            issues.append('formularios_http')
        
        # Problemas baixos
        if data.get('forms_without_csrf_count', 0) > 0:
            issues.append('formularios_sem_csrf')
        
        if data.get('exposed_emails_count', 0) > 0:
            issues.append('emails_expostos')
        
        data['security_issues'] = issues
        data['security_issues_count'] = len(issues)
    
    def _calculate_security_severity(self, data: Dict):
        """
        Calcula severity score para problemas de segurança
        """
        issues = data.get('security_issues', [])
        
        # Mapeia issues para chaves de severity conhecidas
        severity_issues = []
        for issue in issues:
            if issue in ['pagina_nao_https', 'mixed_content_ativo', 'vulnerabilidades_criticas']:
                severity_issues.append('seguranca_critica')
            elif issue in ['mixed_content_passivo', 'csp_ausente', 'scripts_externos_sem_integridade']:
                severity_issues.append('seguranca_alta')
            elif issue in ['poucos_security_headers', 'muito_javascript_inline', 'formularios_http']:
                severity_issues.append('seguranca_media')
            else:
                severity_issues.append('seguranca_baixa')
        
        # Calcula severidade geral usando o sistema existente
        data['security_severity_level'] = self.calculate_problem_severity(severity_issues)
        data['security_problems_keys'] = severity_issues
        data['security_problems_by_severity'] = self.categorize_problems_by_severity(severity_issues)
    
    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================
    
    def _is_external_resource(self, resource_url: str, page_domain: str) -> bool:
        """
        Verifica se um recurso é externo ao domínio da página
        """
        if not resource_url or not page_domain:
            return False
        
        # URLs relativas são internas
        if not resource_url.startswith(('http://', 'https://')):
            return False
        
        try:
            resource_domain = urlparse(resource_url).netloc.lower()
            return resource_domain != page_domain
        except:
            return False
    
    def find_meta_by_name(self, soup: BeautifulSoup, name: str) -> Optional[Tag]:
        """Helper para encontrar meta tag por name"""
        return self.safe_find(soup, 'meta', {'name': re.compile(f'^{name}$', re.I)})
    
    def extract_meta_content(self, meta_tag: Tag) -> str:
        """Helper para extrair content de meta tag"""
        return self.safe_get_attribute(meta_tag, 'content')
    
    # ==========================================
    # MÉTODOS DE ANÁLISE E RELATÓRIOS
    # ==========================================
    
    def get_security_summary(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera resumo da análise de segurança
        """
        return {
            'is_https': parsed_data.get('is_https_page', False),
            'overall_security_score': parsed_data.get('overall_security_score', 0),
            'mixed_content_risk': parsed_data.get('mixed_content_risk', 'N/A'),
            'security_headers_count': parsed_data.get('security_headers_count', 0),
            'has_csp': parsed_data.get('has_csp', False),
            'vulnerability_score': parsed_data.get('vulnerability_score', 0),
            'external_resources_secure': parsed_data.get('external_resources_integrity_percentage', 0) >= 80,
            'security_severity_level': parsed_data.get('security_severity_level', SeverityLevel.BAIXA),
            'main_security_issues': parsed_data.get('security_issues', [])[:3],
            'critical_vulnerabilities': parsed_data.get('high_risk_vulnerabilities', 0),
            'forms_secure': parsed_data.get('forms_security_score', 100) >= 80
        }
    
    def validate_security_best_practices(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida boas práticas de segurança
        """
        validations = {}
        
        # HTTPS básico
        validations['uses_https'] = parsed_data.get('is_https_page', False)
        validations['no_mixed_content'] = parsed_data.get('total_mixed_content_count', 0) == 0
        
        # Security Headers
        validations['has_security_headers'] = parsed_data.get('security_headers_count', 0) >= 3
        validations['has_csp'] = parsed_data.get('has_csp', False)
        validations['good_csp_quality'] = parsed_data.get('csp_score', 0) >= 70
        
        # Vulnerabilidades
        validations['no_critical_vulnerabilities'] = parsed_data.get('high_risk_vulnerabilities', 0) == 0
        validations['limited_inline_js'] = parsed_data.get('inline_js_count', 0) <= 3
        
        # Recursos externos
        validations['external_resources_secure'] = parsed_data.get('external_resources_integrity_percentage', 0) >= 80
        
        # Forms
        validations['secure_forms'] = parsed_data.get('forms_security_score', 100) >= 80
        
        # Sem problemas críticos
        validations['no_critical_security_issues'] = parsed_data.get('security_severity_level') != SeverityLevel.CRITICA
        
        # Score geral
        score_items = [
            validations['uses_https'],
            validations['no_mixed_content'],
            validations['has_security_headers'],
            validations['has_csp'],
            validations['no_critical_vulnerabilities'],
            validations['limited_inline_js'],
            validations['external_resources_secure'],
            validations['secure_forms'],
            validations['no_critical_security_issues']
        ]
        
        validations['security_best_practices_score'] = int((sum(score_items) / len(score_items)) * 100)
        
        return validations

# ==========================================
# FUNÇÃO STANDALONE PARA TESTES
# ==========================================

def parse_security_elements(html_content: str, url: str = 'https://example.com', 
                           response_headers: Dict = None, 
                           check_external: bool = False) -> Dict[str, Any]:
    """
    Função standalone para testar o SecurityParser
    
    Args:
        html_content: HTML da página
        url: URL da página atual
        response_headers: Headers de resposta HTTP (opcional)
        check_external: Se deve verificar recursos externos (lento)
        
    Returns:
        Dict com dados de segurança parseados
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'lxml')
    parser = SecurityParser(check_external_resources=check_external)
    
    # Parse básico
    data = parser.parse(soup, url, response_headers)
    
    # Adiciona análises extras
    data.update(parser.get_security_summary(data))
    data.update(parser.validate_security_best_practices(data))
    
    return data

# ==========================================
# EXEMPLO DE USO E TESTE
# ==========================================

if __name__ == "__main__":
    # Teste com HTML com vários problemas de segurança
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teste de Segurança</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        
        <!-- Security headers via meta -->
        <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'">
        <meta http-equiv="X-Frame-Options" content="SAMEORIGIN">
        
        <!-- Problemas de Mixed Content (página HTTPS carregando HTTP) -->
        <script src="http://insecure-cdn.com/script.js"></script>
        <img src="http://example.com/image.jpg" alt="Imagem insegura">
        
        <!-- Scripts externos sem integrity -->
        <script src="https://external-cdn.com/jquery.js"></script>
        <script src="https://analytics.com/tracking.js" integrity="sha384-abc123" crossorigin="anonymous"></script>
        
        <!-- CSS externa -->
        <link rel="stylesheet" href="https://external-fonts.com/font.css">
    </head>
    <body>
        <h1>Página de Teste de Segurança</h1>
        
        <!-- JavaScript inline (vulnerabilidade) -->
        <script>
            eval('console.log("Dangerous eval usage")');
            document.write('<p>Dynamic content</p>');
            var userInput = prompt("Enter data:");
            document.getElementById('output').innerHTML = userInput;
        </script>
        
        <!-- Form inseguro -->
        <form method="POST" action="http://insecure-submit.com/process">
            <input type="text" name="username" required>
            <input type="password" name="password" required>
            <button type="submit">Login</button>
            <!-- Sem CSRF token -->
        </form>
        
        <!-- Emails expostos -->
        <p>Contato: <a href="mailto:admin@example.com">admin@example.com</a></p>
        <p>Suporte: contato@empresa.com.br</p>
        
        <!-- IP address exposure -->
        <p>Servidor: 192.168.1.100</p>
        
        <!-- Possível API key (fake) -->
        <script>
            var apiKey = "sk_live_1234567890abcdef1234567890abcdef";
        </script>
        
        <!-- CSS inline com background HTTP -->
        <div style="background-image: url('http://insecure.com/bg.jpg')">
            Conteúdo com background inseguro
        </div>
        
        <div id="output"></div>
    </body>
    </html>
    """
    
    # Headers de resposta simulados
    mock_headers = {
        'strict-transport-security': 'max-age=31536000; includeSubDomains',
        'x-content-type-options': 'nosniff'
    }
    
    # Parse com URL HTTPS para detectar mixed content
    result = parse_security_elements(
        test_html, 
        url='https://example.com/test', 
        response_headers=mock_headers
    )
    
    print("🔒 RESULTADO DO SECURITY PARSER:")
    print(f"   HTTPS Page: {result['is_https_page']}")
    print(f"   Overall Security Score: {result['overall_security_score']}/100")
    print(f"   Mixed Content Risk: {result['mixed_content_risk']}")
    print(f"   Active Mixed Content: {result['active_mixed_content_count']}")
    print(f"   Passive Mixed Content: {result['passive_mixed_content_count']}")
    print(f"   Security Headers: {result['security_headers_count']}")
    print(f"   Has CSP: {result['has_csp']} (Score: {result.get('csp_score', 0)}/100)")
    print(f"   High Risk Vulnerabilities: {result['high_risk_vulnerabilities']}")
    print(f"   Inline JS Count: {result['inline_js_count']}")
    print(f"   External Resources: {result['external_resources_count']}")
    print(f"   External with Integrity: {result['external_resources_with_integrity']}")
    print(f"   Forms Security Score: {result.get('forms_security_score', 100)}/100")
    print(f"   Security Severity: {result['security_severity_level']}")
    print(f"   Best Practices Score: {result['security_best_practices_score']}/100")
    
    if result['security_issues']:
        print(f"\n⚠️  Issues de Segurança:")
        for issue in result['security_issues']:
            print(f"      - {issue}")
    
    print(f"\n📊 SCORES DETALHADOS:")
    print(f"   HTTPS Score: {result['https_score']}/100")
    print(f"   Mixed Content Score: {result['mixed_content_score']}/100")
    print(f"   Security Headers Score: {result['security_headers_score']}/100")
    print(f"   Vulnerability Score: {result['vulnerability_score']}/100")
    print(f"   External Resources Score: {result['external_resources_score']}/100")
    
    if result.get('vulnerability_patterns'):
        print(f"\n🚨 PADRÕES DE VULNERABILIDADE:")
        for pattern, data in result['vulnerability_patterns'].items():
            if data['found']:
                print(f"   {pattern}: {data['count']} ocorrências")
    
    if result.get('security_headers_found'):
        print(f"\n🛡️  SECURITY HEADERS ENCONTRADOS:")
        for header, info in result['security_headers_found'].items():
            print(f"   {info['display_name']}: {info['source']}")