"""
seofrog/parsers/links_parser.py
Parser modular para análise completa de links
Responsável por: links internos/externos, anchor text, redirects, link equity
"""

import re
import time
import requests
from urllib.parse import urlparse, urljoin, urlunparse
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup, Tag
from .base import ParserMixin, SeverityLevel

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
        self.max_links_per_100_words = 5       # Máximo de links por 100 palavras
        self.min_anchor_length = 2             # Mínimo para anchor text útil
        self.max_anchor_length = 100           # Máximo para anchor text
        
        # Padrões de anchor text problemático
        self.generic_anchors = [
            'click here', 'clique aqui', 'read more', 'leia mais',
            'more info', 'saiba mais', 'here', 'aqui', 'link',
            'this', 'este', 'página', 'page', 'site', 'website'
        ]
        
        # Tipos de links para ignorar na análise
        self.ignore_link_patterns = [
            r'^#',                    # Anchors internos
            r'^javascript:',          # JavaScript links
            r'^mailto:',              # Email links
            r'^tel:',                 # Telephone links
            r'^ftp:',                 # FTP links
            r'^file:',                # File links
        ]
    
    def parse(self, soup: BeautifulSoup, page_url: str, word_count: int = None) -> Dict[str, Any]:
        """
        Parse completo de análise de links
        
        Args:
            soup: BeautifulSoup object da página
            page_url: URL da página atual (para determinar links internos)
            word_count: Word count da página (do content_parser, opcional)
            
        Returns:
            Dict com dados completos de links
        """
        data = {}
        
        try:
            # Encontra todos os links
            all_links = self._find_all_links(soup)
            
            # Análise básica de links
            self._analyze_basic_link_metrics(all_links, page_url, data)
            
            # Análise detalhada de cada link
            link_details = self._analyze_individual_links(all_links, page_url)
            data['links_details'] = link_details
            
            # Análise de anchor text
            self._analyze_anchor_text_quality(link_details, data)
            
            # Análise de links internos (com redirects se habilitado)
            if self.enable_redirects:
                self._analyze_internal_redirects(link_details, data)
            
            # Análise de link density (se word_count disponível)
            if word_count:
                self._analyze_link_density(data, word_count)
            
            # Análise de distribuição de links
            self._analyze_link_distribution(link_details, data)
            
            # Detecção de problemas de links
            self._detect_link_issues(data)
            
            # Severity scoring
            self._calculate_links_severity(data)
            
            # Log estatísticas
            errors = 1 if any(key.endswith('_error') for key in data.keys()) else 0
            self.log_parsing_stats('LinksParser', len(data), errors)
            
        except Exception as e:
            self.logger.error(f"Erro no parse de links: {e}")
            data['links_parse_error'] = str(e)
            self.log_parsing_stats('LinksParser', len(data), 1)
        
        return data
    
    def _find_all_links(self, soup: BeautifulSoup) -> List[Tag]:
        """
        Encontra todos os links válidos na página
        """
        all_links = self.safe_find_all(soup, 'a')
        
        # Filtra links válidos (com href)
        valid_links = []
        for link in all_links:
            href = self.safe_get_attribute(link, 'href')
            if href and not self._should_ignore_link(href):
                valid_links.append(link)
        
        return valid_links
    
    def _should_ignore_link(self, href: str) -> bool:
        """
        Verifica se link deve ser ignorado na análise
        """
        href_lower = href.lower()
        
        for pattern in self.ignore_link_patterns:
            if re.match(pattern, href_lower):
                return True
        
        return False
    
    def _analyze_basic_link_metrics(self, links: List[Tag], page_url: str, data: Dict):
        """
        Análise básica de métricas de links
        """
        total_links = len(links)
        data['total_links_count'] = total_links
        
        if total_links == 0:
            # Sem links
            data['internal_links_count'] = 0
            data['external_links_count'] = 0
            data['links_without_anchor'] = 0
            data['internal_links_ratio'] = 0
            data['external_links_ratio'] = 0
            return
        
        # Separa links internos vs externos
        base_domain = self.extract_domain(page_url)
        internal_count = 0
        external_count = 0
        without_anchor_count = 0
        
        for link in links:
            href = self.safe_get_attribute(link, 'href')
            anchor_text = self.extract_text_safe(link)
            
            # Resolve URL completa
            full_url = self.resolve_url(page_url, href)
            link_domain = self.extract_domain(full_url)
            
            # Classifica como interno ou externo
            if link_domain == base_domain or not link_domain:
                internal_count += 1
            else:
                external_count += 1
            
            # Verifica anchor text
            if not anchor_text.strip():
                without_anchor_count += 1
        
        # Armazena métricas
        data['internal_links_count'] = internal_count
        data['external_links_count'] = external_count
        data['links_without_anchor'] = without_anchor_count
        
        # Ratios
        data['internal_links_ratio'] = internal_count / total_links if total_links > 0 else 0
        data['external_links_ratio'] = external_count / total_links if total_links > 0 else 0
        data['links_with_anchor_ratio'] = (total_links - without_anchor_count) / total_links if total_links > 0 else 0
    
    def _analyze_individual_links(self, links: List[Tag], page_url: str) -> List[Dict]:
        """
        Análise detalhada de cada link individual
        """
        link_details = []
        base_domain = self.extract_domain(page_url)
        
        for i, link in enumerate(links):
            detail = {
                'index': i + 1,
                'tag_html': str(link)[:200],
            }
            
            # Atributos básicos
            href = self.safe_get_attribute(link, 'href')
            detail['href'] = href
            detail['anchor_text'] = self.extract_text_safe(link)
            detail['title'] = self.safe_get_attribute(link, 'title')
            detail['target'] = self.safe_get_attribute(link, 'target')
            detail['rel'] = self.safe_get_attribute(link, 'rel')
            detail['class'] = ' '.join(link.get('class', []))
            
            # URL analysis
            full_url = self.resolve_url(page_url, href)
            detail['full_url'] = full_url
            detail['is_relative'] = not href.startswith(('http://', 'https://'))
            detail['is_valid_url'] = self.is_valid_url(full_url)
            
            # Classificação interno/externo
            link_domain = self.extract_domain(full_url)
            detail['domain'] = link_domain
            detail['is_internal'] = link_domain == base_domain or not link_domain
            detail['is_external'] = not detail['is_internal'] and bool(link_domain)
            
            # Análise de anchor text
            self._analyze_individual_anchor_text(detail)
            
            # Análise de atributos de link
            self._analyze_link_attributes(detail)
            
            # Análise de SEO attributes
            self._analyze_seo_attributes(detail)
            
            link_details.append(detail)
        
        return link_details
    
    def _analyze_individual_anchor_text(self, detail: Dict):
        """
        Análise detalhada do anchor text de um link
        """
        anchor_text = detail.get('anchor_text', '')
        
        # Básico
        detail['has_anchor_text'] = bool(anchor_text.strip())
        detail['anchor_length'] = len(anchor_text)
        detail['anchor_word_count'] = len(anchor_text.split()) if anchor_text else 0
        
        if anchor_text:
            anchor_clean = anchor_text.strip().lower()
            
            # Análise de qualidade
            detail['anchor_too_short'] = 0 < len(anchor_clean) < self.min_anchor_length
            detail['anchor_too_long'] = len(anchor_clean) > self.max_anchor_length
            detail['anchor_optimal_length'] = self.min_anchor_length <= len(anchor_clean) <= self.max_anchor_length
            
            # Detecta anchor text problemático
            detail['anchor_is_generic'] = anchor_clean in self.generic_anchors
            detail['anchor_is_url'] = self._is_anchor_url(anchor_clean)
            detail['anchor_is_repetitive'] = self._is_anchor_repetitive(anchor_clean)
            
            # Análise de keywords
            detail['anchor_has_keywords'] = self._has_seo_keywords(anchor_clean)
            detail['anchor_is_branded'] = self._is_branded_anchor(anchor_clean)
        else:
            detail['anchor_too_short'] = False
            detail['anchor_too_long'] = False
            detail['anchor_optimal_length'] = False
            detail['anchor_is_generic'] = False
            detail['anchor_is_url'] = False
            detail['anchor_is_repetitive'] = False
            detail['anchor_has_keywords'] = False
            detail['anchor_is_branded'] = False
    
    def _analyze_link_attributes(self, detail: Dict):
        """
        Análise de atributos do link
        """
        target = detail.get('target', '')
        rel = detail.get('rel', '')
        
        # Target analysis
        detail['opens_new_window'] = target == '_blank'
        detail['opens_new_tab'] = target in ['_blank', '_top', '_parent']
        
        # Rel analysis
        rel_values = rel.lower().split() if rel else []
        detail['is_nofollow'] = 'nofollow' in rel_values
        detail['is_sponsored'] = 'sponsored' in rel_values
        detail['is_ugc'] = 'ugc' in rel_values
        detail['has_noopener'] = 'noopener' in rel_values
        detail['has_noreferrer'] = 'noreferrer' in rel_values
        
        # Security analysis
        detail['is_secure_external'] = (
            detail['is_external'] and 
            detail['opens_new_window'] and 
            (detail['has_noopener'] or detail['has_noreferrer'])
        )
    
    def _analyze_seo_attributes(self, detail: Dict):
        """
        Análise de atributos SEO do link
        """
        # Link equity
        detail['passes_link_equity'] = not detail['is_nofollow']
        
        # External link best practices
        if detail['is_external']:
            detail['follows_external_best_practices'] = (
                detail['is_nofollow'] or 
                detail['is_sponsored'] or 
                detail['is_ugc']
            )
        else:
            detail['follows_external_best_practices'] = True
        
        # Internal link optimization
        if detail['is_internal']:
            detail['is_optimized_internal'] = (
                detail['has_anchor_text'] and 
                detail['anchor_optimal_length'] and 
                not detail['anchor_is_generic'] and
                detail['passes_link_equity']
            )
        else:
            detail['is_optimized_internal'] = False
    
    def _analyze_anchor_text_quality(self, link_details: List[Dict], data: Dict):
        """
        Análise de qualidade geral dos anchor texts
        """
        if not link_details:
            data['anchor_quality_score'] = 0
            return
        
        # Contadores de qualidade
        generic_anchors = sum(1 for link in link_details if link.get('anchor_is_generic', False))
        url_anchors = sum(1 for link in link_details if link.get('anchor_is_url', False))
        empty_anchors = sum(1 for link in link_details if not link.get('has_anchor_text', False))
        optimal_anchors = sum(1 for link in link_details if link.get('anchor_optimal_length', False))
        
        total_links = len(link_details)
        
        # Métricas
        data['generic_anchors_count'] = generic_anchors
        data['url_anchors_count'] = url_anchors
        data['empty_anchors_count'] = empty_anchors
        data['optimal_anchors_count'] = optimal_anchors
        
        # Percentuais
        data['generic_anchors_percentage'] = (generic_anchors / total_links * 100) if total_links > 0 else 0
        data['optimal_anchors_percentage'] = (optimal_anchors / total_links * 100) if total_links > 0 else 0
        
        # Score de qualidade geral (0-100)
        quality_score = 100
        quality_score -= (generic_anchors / total_links * 30)  # -30% por generic
        quality_score -= (url_anchors / total_links * 20)      # -20% por URLs
        quality_score -= (empty_anchors / total_links * 40)    # -40% por vazios
        
        data['anchor_quality_score'] = max(0, int(quality_score))
    
    def _analyze_internal_redirects(self, link_details: List[Dict], data: Dict):
        """
        Análise de redirects em links internos (opcional - pode ser lento)
        """
        if not self.enable_redirects:
            data['internal_redirects_analyzed'] = False
            return
        
        internal_links = [link for link in link_details if link.get('is_internal', False)]
        
        if not internal_links:
            data['internal_redirects_analyzed'] = False
            return
        
        self.logger.info(f"Analisando redirects em {len(internal_links)} links internos...")
        
        redirects_found = 0
        redirect_details = []
        
        for link in internal_links:
            full_url = link.get('full_url', '')
            if not full_url:
                continue
            
            # Rate limiting
            time.sleep(self.redirect_rate_limit)
            
            # Analisa redirect
            redirect_info = self._check_link_redirect(full_url)
            
            if redirect_info['has_redirect']:
                redirects_found += 1
                redirect_details.append({
                    'original_url': full_url,
                    'final_url': redirect_info['final_url'],
                    'status_code': redirect_info['status_code'],
                    'redirect_type': redirect_info['redirect_type'],
                    'response_time': redirect_info['response_time'],
                    'anchor_text': link.get('anchor_text', '')
                })
            
            # Atualiza dados do link
            link.update({
                'redirect_final_url': redirect_info['final_url'],
                'redirect_status_code': redirect_info['status_code'],
                'redirect_has_redirect': redirect_info['has_redirect'],
                'redirect_type': redirect_info['redirect_type'],
                'redirect_response_time': redirect_info.get('response_time', 0)
            })
        
        # Armazena resultados
        data['internal_redirects_analyzed'] = True
        data['internal_redirects_count'] = redirects_found
        data['internal_redirects_details'] = redirect_details
        data['internal_redirects_percentage'] = (redirects_found / len(internal_links) * 100) if internal_links else 0
    
    def _analyze_link_density(self, data: Dict, word_count: int):
        """
        Análise de densidade de links (links por 100 palavras)
        """
        total_links = data.get('total_links_count', 0)
        
        if word_count > 0:
            density = (total_links / word_count) * 100
            data['link_density_per_100_words'] = round(density, 2)
            data['link_density_source'] = 'real'
            data['link_density_optimal'] = density <= self.max_links_per_100_words
        else:
            data['link_density_per_100_words'] = 0
            data['link_density_source'] = 'no_content'
            data['link_density_optimal'] = True
    
    def _analyze_link_distribution(self, link_details: List[Dict], data: Dict):
        """
        Análise da distribuição de links na página
        """
        if not link_details:
            return
        
        # Análise de domínios externos
        external_domains = set()
        for link in link_details:
            if link.get('is_external', False):
                domain = link.get('domain', '')
                if domain:
                    external_domains.add(domain)
        
        data['unique_external_domains'] = len(external_domains)
        data['external_domains_list'] = list(external_domains)
        
        # Análise de tipos de links
        follow_links = sum(1 for link in link_details if link.get('passes_link_equity', False))
        nofollow_links = sum(1 for link in link_details if link.get('is_nofollow', False))
        external_secure = sum(1 for link in link_details if link.get('is_secure_external', False))
        
        data['follow_links_count'] = follow_links
        data['nofollow_links_count'] = nofollow_links
        data['secure_external_links_count'] = external_secure
        
        # Ratios
        total_links = len(link_details)
        data['follow_links_ratio'] = follow_links / total_links if total_links > 0 else 0
        data['nofollow_links_ratio'] = nofollow_links / total_links if total_links > 0 else 0
    
    def _detect_link_issues(self, data: Dict):
        """
        Detecta problemas gerais de links
        """
        issues = []
        
        # Problemas de anchor text
        if data.get('generic_anchors_count', 0) > 0:
            issues.append('anchors_genericos')
        
        if data.get('empty_anchors_count', 0) > 0:
            issues.append('anchors_vazios')
        
        # Problemas de densidade
        if data.get('link_density_per_100_words', 0) > self.max_links_per_100_words:
            issues.append('densidade_links_alta')
        
        # Problemas de distribuição
        internal_ratio = data.get('internal_links_ratio', 0)
        if internal_ratio < 0.5:  # Menos de 50% links internos
            issues.append('poucos_links_internos')
        
        # Problemas de redirects (se analisados)
        if data.get('internal_redirects_analyzed', False):
            redirect_percentage = data.get('internal_redirects_percentage', 0)
            if redirect_percentage > 20:  # Mais de 20% com redirect
                issues.append('muitos_redirects_internos')
        
        # Problemas de segurança
        total_external = data.get('external_links_count', 0)
        secure_external = data.get('secure_external_links_count', 0)
        if total_external > 0 and (secure_external / total_external) < 0.8:
            issues.append('links_externos_inseguros')
        
        data['link_issues'] = issues
        data['link_issues_count'] = len(issues)
    
    def _calculate_links_severity(self, data: Dict):
        """
        Calcula severity score para problemas de links
        """
        issues = data.get('link_issues', [])
        
        # Mapeia issues para chaves de severity
        severity_issues = []
        for issue in issues:
            if issue in ['anchors_vazios', 'muitos_redirects_internos']:
                severity_issues.append('links_problemas_seo')
            elif issue in ['densidade_links_alta', 'anchors_genericos']:
                severity_issues.append('links_qualidade_baixa')
            elif issue in ['poucos_links_internos', 'links_externos_inseguros']:
                severity_issues.append('links_estrutura_ruim')
        
        # Calcula severidade geral
        data['links_severity_level'] = self.calculate_problem_severity(severity_issues)
        data['links_problems_keys'] = severity_issues
        data['links_problems_by_severity'] = self.categorize_problems_by_severity(severity_issues)
    
    def _check_link_redirect(self, url: str) -> Dict[str, Any]:
        """
        Verifica se link tem redirect (com rate limiting)
        """
        try:
            start_time = time.time()
            
            # Configura session
            session = requests.Session()
            session.verify = False
            session.headers.update({
                'User-Agent': 'SEOFrog/0.2 (+https://seofrog.com/bot)'
            })
            
            # HEAD request para eficiência
            response = session.head(
                url,
                timeout=self.redirect_timeout,
                allow_redirects=False
            )
            response_time = time.time() - start_time
            
            # Verifica redirect
            if response.status_code in [301, 302, 303, 307, 308]:
                location = response.headers.get('location', '')
                if location:
                    final_url = urljoin(url, location)
                    redirect_type = self._classify_redirect_type(url, final_url, response.status_code)
                    
                    return {
                        'final_url': final_url,
                        'status_code': response.status_code,
                        'has_redirect': True,
                        'redirect_type': redirect_type,
                        'response_time': response_time
                    }
            
            # Sem redirect
            return {
                'final_url': url,
                'status_code': response.status_code,
                'has_redirect': False,
                'redirect_type': 'none',
                'response_time': response_time
            }
            
        except Exception as e:
            self.logger.debug(f"Erro verificando redirect para {url}: {e}")
            return {
                'final_url': url,
                'status_code': 0,
                'has_redirect': False,
                'redirect_type': 'error',
                'response_time': 0,
                'error': str(e)
            }
    
    def _classify_redirect_type(self, original_url: str, final_url: str, status_code: int) -> str:
        """
        Classifica tipo de redirect para análise
        """
        try:
            parsed_orig = urlparse(original_url)
            parsed_final = urlparse(final_url)
            
            # HTTP -> HTTPS
            if parsed_orig.scheme == 'http' and parsed_final.scheme == 'https':
                return 'http_to_https'
            
            # HTTPS -> HTTP (problemático)
            if parsed_orig.scheme == 'https' and parsed_final.scheme == 'http':
                return 'https_to_http'
            
            # WWW redirect
            if ('www.' in parsed_orig.netloc) != ('www.' in parsed_final.netloc):
                return 'www_redirect'
            
            # Trailing slash
            if (parsed_orig.path.rstrip('/') == parsed_final.path.rstrip('/') and
                parsed_orig.path != parsed_final.path):
                return 'trailing_slash'
            
            # Permanent vs temporary
            if status_code == 301:
                return 'permanent_301'
            elif status_code == 302:
                return 'temporary_302'
            else:
                return f'redirect_{status_code}'
            
        except Exception:
            return 'unknown'
    
    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================
    
    def _is_anchor_url(self, anchor_text: str) -> bool:
        """Verifica se anchor text é uma URL"""
        return bool(re.match(r'https?://', anchor_text) or 
                   re.match(r'www\.', anchor_text) or
                   '.' in anchor_text and len(anchor_text.split('.')) >= 2)
    
    def _is_anchor_repetitive(self, anchor_text: str) -> bool:
        """Verifica se anchor text é repetitivo"""
        words = anchor_text.split()
        if len(words) <= 2:
            return False
        
        # Verifica se mesmo palavra repetida
        unique_words = set(words)
        return len(unique_words) / len(words) < 0.5
    
    def _has_seo_keywords(self, anchor_text: str) -> bool:
        """Verifica se anchor text tem palavras-chave SEO"""
        # Heurística: mais de 2 palavras e não genérico
        words = anchor_text.split()
        return len(words) >= 2 and anchor_text not in self.generic_anchors
    
    def _is_branded_anchor(self, anchor_text: str) -> bool:
        """Verifica se anchor text contém marca/brand"""
        # Heurística: palavras capitalizadas que podem ser marca
        words = anchor_text.split()
        capitalized_words = [w for w in words if w and w[0].isupper()]
        return len(capitalized_words) >= 1
    
    # ==========================================
    # MÉTODOS DE ANÁLISE E RELATÓRIOS
    # ==========================================
    
    def get_links_summary(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera resumo da análise de links
        """
        return {
            'total_links': parsed_data.get('total_links_count', 0),
            'internal_links_ratio': parsed_data.get('internal_links_ratio', 0),
            'external_links_ratio': parsed_data.get('external_links_ratio', 0),
            'anchor_quality_score': parsed_data.get('anchor_quality_score', 0),
            'link_density': parsed_data.get('link_density_per_100_words', 0),
            'links_severity_level': parsed_data.get('links_severity_level', SeverityLevel.BAIXA),
            'main_issues': parsed_data.get('link_issues', [])[:3],
            'redirects_found': parsed_data.get('internal_redirects_count', 0),
            'unique_external_domains': parsed_data.get('unique_external_domains', 0)
        }
    
    def validate_links_best_practices(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida boas práticas de links
        """
        validations = {}
        
        total_links = parsed_data.get('total_links_count', 0)
        
        if total_links == 0:
            validations['links_best_practices_score'] = 50
            return validations
        
        # Distribuição adequada
        internal_ratio = parsed_data.get('internal_links_ratio', 0)
        validations['good_internal_ratio'] = internal_ratio >= 0.6
        
        # Qualidade de anchor text
        anchor_score = parsed_data.get('anchor_quality_score', 0)
        validations['good_anchor_quality'] = anchor_score >= 70
        
        # Densidade adequada
        density = parsed_data.get('link_density_per_100_words', 0)
        validations['optimal_link_density'] = density <= self.max_links_per_100_words
        
        # Sem redirects excessivos
        redirect_percentage = parsed_data.get('internal_redirects_percentage', 0)
        validations['low_redirect_rate'] = redirect_percentage <= 10
        
        # Links externos seguros
        total_external = parsed_data.get('external_links_count', 0)
        secure_external = parsed_data.get('secure_external_links_count', 0)
        if total_external > 0:
            validations['secure_external_links'] = (secure_external / total_external) >= 0.8
        else:
            validations['secure_external_links'] = True
        
        # Sem problemas críticos
        validations['no_critical_issues'] = parsed_data.get('links_severity_level') != SeverityLevel.CRITICA
        
        # Score geral
        score_items = [
            validations['good_internal_ratio'],
            validations['good_anchor_quality'],
            validations['optimal_link_density'],
            validations['low_redirect_rate'],
            validations['secure_external_links'],
            validations['no_critical_issues']
        ]
        
        validations['links_best_practices_score'] = int((sum(score_items) / len(score_items)) * 100)
        
        return validations
    
    def update_with_word_count(self, parsed_data: Dict[str, Any], word_count: int) -> Dict[str, Any]:
        """
        Atualiza dados parseados com word count real
        """
        self._analyze_link_density(parsed_data, word_count)
        
        # Recalcula validações
        validations = self.validate_links_best_practices(parsed_data)
        parsed_data.update(validations)
        
        return parsed_data

# ==========================================
# FUNÇÃO STANDALONE PARA TESTES
# ==========================================

def parse_links_elements(html_content: str, page_url: str = 'https://example.com', 
                         word_count: int = None, enable_redirects: bool = False) -> Dict[str, Any]:
    """
    Função standalone para testar o LinksParser
    
    Args:
        html_content: HTML da página
        page_url: URL da página atual
        word_count: Word count da página (opcional)
        enable_redirects: Se deve verificar redirects (lento)
        
    Returns:
        Dict com dados de links parseados
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'lxml')
    parser = LinksParser(enable_redirects=enable_redirects)
    
    # Parse básico
    data = parser.parse(soup, page_url, word_count)
    
    # Adiciona análises extras
    data.update(parser.get_links_summary(data))
    data.update(parser.validate_links_best_practices(data))
    
    return data

# ==========================================
# EXEMPLO DE USO E TESTE
# ==========================================

if __name__ == "__main__":
    # Teste com HTML com diversos tipos de links
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teste de Links</title>
    </head>
    <body>
        <h1>Página de Teste</h1>
        
        <!-- Links internos bons -->
        <p>Confira nossos <a href="/produtos">produtos em destaque</a> e 
        <a href="/sobre">saiba mais sobre nossa empresa</a>.</p>
        
        <!-- Links internos com problemas -->
        <p><a href="/categoria">clique aqui</a> para ver categorias.</p>
        <p><a href="/blog/artigo-seo">aqui</a> tem mais informações.</p>
        
        <!-- Link sem anchor text -->
        <a href="/contato"></a>
        
        <!-- Links externos -->
        <p>Visite o <a href="https://google.com" target="_blank" rel="noopener nofollow">Google</a> 
        para pesquisar mais informações.</p>
        
        <!-- Link externo inseguro -->
        <p>Acesse <a href="https://example.org" target="_blank">este site externo</a>.</p>
        
        <!-- Link com anchor text de URL -->
        <p>Acesse <a href="https://wikipedia.org">https://wikipedia.org</a> para mais detalhes.</p>
        
        <!-- Links internos com diferentes tipos -->
        <a href="#secao1">Seção 1</a>
        <a href="javascript:void(0)">Funcionalidade JS</a>
        <a href="mailto:contato@example.com">contato@example.com</a>
        
        <!-- Links com rel diferentes -->
        <a href="https://partner.com" rel="sponsored">Parceiro Patrocinado</a>
        <a href="https://forum.com/post" rel="ugc nofollow">Post do Usuário</a>
        
        <!-- Links relativos -->
        <a href="../categoria/produto-1">Produto 1</a>
        <a href="./subcategoria/item">Item da Subcategoria</a>
        
    </body>
    </html>
    """
    
    # Parse com word count simulado (SEM redirects para teste rápido)
    word_count = 120  # Simula 120 palavras na página
    result = parse_links_elements(test_html, 'https://example.com/pagina', word_count, enable_redirects=False)
    
    print("🔍 RESULTADO DO LINKS PARSER:")
    print(f"   Total Links: {result['total_links_count']}")
    print(f"   Internal Links: {result['internal_links_count']} ({result['internal_links_ratio']:.1%})")
    print(f"   External Links: {result['external_links_count']} ({result['external_links_ratio']:.1%})")
    print(f"   Links without Anchor: {result['links_without_anchor']}")
    print(f"   Generic Anchors: {result['generic_anchors_count']}")
    print(f"   URL Anchors: {result['url_anchors_count']}")
    print(f"   Anchor Quality Score: {result['anchor_quality_score']}/100")
    print(f"   Link Density: {result['link_density_per_100_words']:.1f} per 100 words")
    print(f"   Follow Links: {result['follow_links_count']}")
    print(f"   NoFollow Links: {result['nofollow_links_count']}")
    print(f"   Unique External Domains: {result['unique_external_domains']}")
    print(f"   Links Severity: {result['links_severity_level']}")
    print(f"   Best Practices Score: {result['links_best_practices_score']}/100")
    
    if result['link_issues']:
        print(f"   Issues encontradas:")
        for issue in result['link_issues']:
            print(f"      - {issue}")
    
    if result.get('internal_redirects_analyzed'):
        print(f"   Internal Redirects: {result['internal_redirects_count']} ({result['internal_redirects_percentage']:.1f}%)")
    else:
        print(f"   Internal Redirects: Análise desabilitada (enable_redirects=False)")
    
    print(f"   External Domains: {result.get('external_domains_list', [])}")