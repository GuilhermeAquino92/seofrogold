"""
seofrog/parsers/social_parser.py
Parser modular para análise completa de Social Media Tags
Responsável por: Open Graph, Twitter Cards, Facebook específico, LinkedIn
"""

import re
import requests
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup, Tag
from .base import ParserMixin, SeverityLevel

class SocialParser(ParserMixin):
    """
    Parser especializado para análise completa de Social Media Tags
    Responsável por: Open Graph, Twitter Cards, Facebook meta, LinkedIn optimization
    """
    
    def __init__(self, validate_images: bool = False, image_timeout: int = 3):
        super().__init__()
        
        # Configurações de validação
        self.validate_images = validate_images  # Se deve validar URLs de imagem
        self.image_timeout = image_timeout      # Timeout para validação de imagem
        
        # Especificações de dimensões recomendadas
        self.image_specs = {
            'og': {
                'min_width': 1200,
                'min_height': 630,
                'aspect_ratio': 1.91,  # 1200:630
                'max_size_mb': 8
            },
            'twitter': {
                'min_width': 1024,
                'min_height': 512,
                'aspect_ratio': 2.0,   # 1024:512 para summary_large_image
                'max_size_mb': 5
            }
        }
        
        # Limites de texto recomendados por plataforma
        self.text_limits = {
            'og_title': {'min': 10, 'max': 60},
            'og_description': {'min': 50, 'max': 160},
            'twitter_title': {'min': 10, 'max': 70},
            'twitter_description': {'min': 50, 'max': 200}
        }
        
        # Tags obrigatórias por plataforma
        self.required_tags = {
            'facebook': ['og:title', 'og:description', 'og:image', 'og:url'],
            'twitter': ['twitter:card', 'twitter:title', 'twitter:description'],
            'linkedin': ['og:title', 'og:description', 'og:image']  # LinkedIn usa OG
        }
        
        # Tipos de Twitter Card válidos
        self.valid_twitter_cards = [
            'summary', 'summary_large_image', 'app', 'player'
        ]
    
    def parse(self, soup: BeautifulSoup, url: str = None, meta_title: str = None, meta_description: str = None) -> Dict[str, Any]:
        """
        Parse completo de análise de social media tags
        
        Args:
            soup: BeautifulSoup object da página
            url: URL da página (para validação de consistência)
            meta_title: Meta title da página (para comparação)
            meta_description: Meta description da página (para comparação)
            
        Returns:
            Dict com dados completos de social media
        """
        data = {}
        
        try:
            # Parse de cada tipo de social media tag
            self._parse_open_graph(soup, data)
            self._parse_twitter_cards(soup, data)
            self._parse_facebook_specific(soup, data)
            self._parse_other_social(soup, data)
            
            # Análise de qualidade e completude
            self._analyze_social_completeness(data)
            self._analyze_social_consistency(data, meta_title, meta_description)
            
            # Validação de imagens (se habilitado)
            if self.validate_images:
                self._validate_social_images(data)
            
            # Detecção de problemas
            self._detect_social_issues(data)
            
            # Severity scoring
            self._calculate_social_severity(data)
            
            # Log estatísticas
            errors = 1 if any(key.endswith('_error') for key in data.keys()) else 0
            self.log_parsing_stats('SocialParser', len(data), errors)
            
        except Exception as e:
            self.logger.error(f"Erro no parse de social media: {e}")
            data['social_parse_error'] = str(e)
            self.log_parsing_stats('SocialParser', len(data), 1)
        
        return data
    
    def _parse_open_graph(self, soup: BeautifulSoup, data: Dict):
        """
        Parse completo de Open Graph tags
        """
        # Encontra todas as tags OG
        og_tags = self.safe_find_all(soup, 'meta', {'property': re.compile(r'^og:', re.I)})
        
        data['og_tags_count'] = len(og_tags)
        data['og_tags_details'] = []
        
        # Parse individual de cada tag OG
        og_data = {}
        for tag in og_tags:
            property_name = self.safe_get_attribute(tag, 'property').lower()
            content = self.safe_get_attribute(tag, 'content')
            
            og_data[property_name] = content
            data['og_tags_details'].append({
                'property': property_name,
                'content': content[:100] + '...' if len(content) > 100 else content,
                'content_length': len(content)
            })
        
        # Tags específicas importantes
        data['og_title'] = og_data.get('og:title', '')
        data['og_description'] = og_data.get('og:description', '')
        data['og_image'] = og_data.get('og:image', '')
        data['og_url'] = og_data.get('og:url', '')
        data['og_type'] = og_data.get('og:type', '')
        data['og_site_name'] = og_data.get('og:site_name', '')
        data['og_locale'] = og_data.get('og:locale', '')
        
        # Análise de qualidade do conteúdo OG
        self._analyze_og_content_quality(data)
        
        # Múltiplas imagens OG
        og_images = [tag.get('content', '') for tag in og_tags 
                    if tag.get('property', '').lower() == 'og:image']
        data['og_images_count'] = len(og_images)
        data['og_images_list'] = og_images
    
    def _analyze_og_content_quality(self, data: Dict):
        """
        Analisa qualidade do conteúdo Open Graph
        """
        og_title = data.get('og_title', '')
        og_description = data.get('og_description', '')
        
        # Análise do título OG
        title_analysis = self.analyze_text_length(
            og_title,
            self.text_limits['og_title']['min'],
            self.text_limits['og_title']['max']
        )
        
        data['og_title_length'] = title_analysis['length']
        data['og_title_is_empty'] = title_analysis['is_empty']
        data['og_title_too_short'] = title_analysis['too_short']
        data['og_title_too_long'] = title_analysis['too_long']
        data['og_title_optimal'] = title_analysis['optimal']
        
        # Análise da descrição OG
        desc_analysis = self.analyze_text_length(
            og_description,
            self.text_limits['og_description']['min'],
            self.text_limits['og_description']['max']
        )
        
        data['og_description_length'] = desc_analysis['length']
        data['og_description_is_empty'] = desc_analysis['is_empty']
        data['og_description_too_short'] = desc_analysis['too_short']
        data['og_description_too_long'] = desc_analysis['too_long']
        data['og_description_optimal'] = desc_analysis['optimal']
        
        # Análise da imagem OG
        og_image = data.get('og_image', '')
        data['og_image_is_valid_url'] = self.is_valid_url(og_image)
        data['og_image_is_https'] = og_image.startswith('https://') if og_image else False
        data['og_image_is_relative'] = og_image and not og_image.startswith(('http://', 'https://'))
    
    def _parse_twitter_cards(self, soup: BeautifulSoup, data: Dict):
        """
        Parse completo de Twitter Cards
        """
        # Encontra todas as tags Twitter
        twitter_tags = self.safe_find_all(soup, 'meta', {'name': re.compile(r'^twitter:', re.I)})
        
        data['twitter_tags_count'] = len(twitter_tags)
        data['twitter_tags_details'] = []
        
        # Parse individual de cada tag Twitter
        twitter_data = {}
        for tag in twitter_tags:
            name = self.safe_get_attribute(tag, 'name').lower()
            content = self.safe_get_attribute(tag, 'content')
            
            twitter_data[name] = content
            data['twitter_tags_details'].append({
                'name': name,
                'content': content[:100] + '...' if len(content) > 100 else content,
                'content_length': len(content)
            })
        
        # Tags específicas importantes
        data['twitter_card'] = twitter_data.get('twitter:card', '')
        data['twitter_title'] = twitter_data.get('twitter:title', '')
        data['twitter_description'] = twitter_data.get('twitter:description', '')
        data['twitter_image'] = twitter_data.get('twitter:image', '')
        data['twitter_site'] = twitter_data.get('twitter:site', '')
        data['twitter_creator'] = twitter_data.get('twitter:creator', '')
        
        # Análise de qualidade do conteúdo Twitter
        self._analyze_twitter_content_quality(data)
    
    def _analyze_twitter_content_quality(self, data: Dict):
        """
        Analisa qualidade do conteúdo Twitter Cards
        """
        twitter_title = data.get('twitter_title', '')
        twitter_description = data.get('twitter_description', '')
        twitter_card = data.get('twitter_card', '')
        
        # Análise do título Twitter
        title_analysis = self.analyze_text_length(
            twitter_title,
            self.text_limits['twitter_title']['min'],
            self.text_limits['twitter_title']['max']
        )
        
        data['twitter_title_length'] = title_analysis['length']
        data['twitter_title_is_empty'] = title_analysis['is_empty']
        data['twitter_title_too_short'] = title_analysis['too_short']
        data['twitter_title_too_long'] = title_analysis['too_long']
        data['twitter_title_optimal'] = title_analysis['optimal']
        
        # Análise da descrição Twitter
        desc_analysis = self.analyze_text_length(
            twitter_description,
            self.text_limits['twitter_description']['min'],
            self.text_limits['twitter_description']['max']
        )
        
        data['twitter_description_length'] = desc_analysis['length']
        data['twitter_description_is_empty'] = desc_analysis['is_empty']
        data['twitter_description_too_short'] = desc_analysis['too_short']
        data['twitter_description_too_long'] = desc_analysis['too_long']
        data['twitter_description_optimal'] = desc_analysis['optimal']
        
        # Análise do tipo de card
        data['twitter_card_is_valid'] = twitter_card in self.valid_twitter_cards
        data['twitter_card_type'] = twitter_card
        
        # Análise da imagem Twitter
        twitter_image = data.get('twitter_image', '')
        data['twitter_image_is_valid_url'] = self.is_valid_url(twitter_image)
        data['twitter_image_is_https'] = twitter_image.startswith('https://') if twitter_image else False
        
        # Análise de handles (@)
        twitter_site = data.get('twitter_site', '')
        twitter_creator = data.get('twitter_creator', '')
        data['twitter_site_has_at'] = twitter_site.startswith('@') if twitter_site else False
        data['twitter_creator_has_at'] = twitter_creator.startswith('@') if twitter_creator else False
    
    def _parse_facebook_specific(self, soup: BeautifulSoup, data: Dict):
        """
        Parse de tags específicas do Facebook
        """
        # Facebook App ID
        fb_app_id = self.find_meta_by_property(soup, 'fb:app_id')
        data['fb_app_id'] = self.extract_meta_content(fb_app_id) if fb_app_id else ''
        
        # Facebook Pages
        fb_pages = self.find_meta_by_property(soup, 'fb:pages')
        data['fb_pages'] = self.extract_meta_content(fb_pages) if fb_pages else ''
        
        # Article tags (para artigos)
        article_tags = self.safe_find_all(soup, 'meta', {'property': re.compile(r'^article:', re.I)})
        data['article_tags_count'] = len(article_tags)
        
        article_data = {}
        for tag in article_tags:
            property_name = self.safe_get_attribute(tag, 'property').lower()
            content = self.safe_get_attribute(tag, 'content')
            article_data[property_name] = content
        
        data['article_author'] = article_data.get('article:author', '')
        data['article_published_time'] = article_data.get('article:published_time', '')
        data['article_modified_time'] = article_data.get('article:modified_time', '')
        data['article_section'] = article_data.get('article:section', '')
        data['article_tag'] = article_data.get('article:tag', '')
        
        # Análise de Article tags
        data['has_article_metadata'] = len(article_data) > 0
        data['article_has_author'] = bool(data['article_author'])
        data['article_has_publish_date'] = bool(data['article_published_time'])
    
    def _parse_other_social(self, soup: BeautifulSoup, data: Dict):
        """
        Parse de outras plataformas sociais (LinkedIn, Pinterest, etc.)
        """
        # LinkedIn usa principalmente OG tags, mas vamos verificar específicas
        
        # Pinterest
        pinterest_tags = self.safe_find_all(soup, 'meta', {'name': re.compile(r'^pinterest', re.I)})
        data['pinterest_tags_count'] = len(pinterest_tags)
        
        # WhatsApp (usa OG, mas pode ter customizações)
        # WhatsApp geralmente usa og:image, og:title, og:description
        
        # Telegram (usa OG também)
        
        # Para agora, focamos em OG + Twitter como principais
        data['supports_linkedin'] = data.get('og_tags_count', 0) >= 3  # Mínimo para LinkedIn
        data['supports_whatsapp'] = bool(data.get('og_image', ''))     # WhatsApp precisa de imagem
    
    def _analyze_social_completeness(self, data: Dict):
        """
        Analisa completude para cada plataforma social
        """
        # Completude Facebook/Meta (Open Graph)
        facebook_required = self.required_tags['facebook']
        facebook_present = 0
        
        for tag in facebook_required:
            field_name = tag.replace(':', '_')
            if data.get(field_name, ''):
                facebook_present += 1
        
        data['facebook_completeness'] = int((facebook_present / len(facebook_required)) * 100)
        data['facebook_required_missing'] = [tag for tag in facebook_required 
                                           if not data.get(tag.replace(':', '_'), '')]
        
        # Completude Twitter
        twitter_required = self.required_tags['twitter']
        twitter_present = 0
        
        for tag in twitter_required:
            field_name = tag.replace(':', '_')
            if data.get(field_name, ''):
                twitter_present += 1
        
        data['twitter_completeness'] = int((twitter_present / len(twitter_required)) * 100)
        data['twitter_required_missing'] = [tag for tag in twitter_required 
                                          if not data.get(tag.replace(':', '_'), '')]
        
        # Completude LinkedIn (usa OG)
        linkedin_required = self.required_tags['linkedin']
        linkedin_present = 0
        
        for tag in linkedin_required:
            field_name = tag.replace(':', '_')
            if data.get(field_name, ''):
                linkedin_present += 1
        
        data['linkedin_completeness'] = int((linkedin_present / len(linkedin_required)) * 100)
        
        # Score geral de completude social
        avg_completeness = (data['facebook_completeness'] + data['twitter_completeness'] + data['linkedin_completeness']) / 3
        data['social_completeness_score'] = int(avg_completeness)
    
    def _analyze_social_consistency(self, data: Dict, meta_title: str = None, meta_description: str = None):
        """
        Analisa consistência entre tags sociais e meta tags
        """
        consistency_issues = []
        consistency_score = 100
        
        # Consistência de título
        og_title = data.get('og_title', '')
        twitter_title = data.get('twitter_title', '')
        
        if meta_title:
            # OG title vs meta title
            if og_title and og_title != meta_title:
                title_similarity = self._calculate_text_similarity(og_title, meta_title)
                if title_similarity < 0.7:  # Menos de 70% similar
                    consistency_issues.append('og_title_differs_from_meta')
                    consistency_score -= 15
            
            # Twitter title vs meta title
            if twitter_title and twitter_title != meta_title:
                title_similarity = self._calculate_text_similarity(twitter_title, meta_title)
                if title_similarity < 0.7:
                    consistency_issues.append('twitter_title_differs_from_meta')
                    consistency_score -= 15
        
        # Consistência de descrição
        og_description = data.get('og_description', '')
        twitter_description = data.get('twitter_description', '')
        
        if meta_description:
            # OG description vs meta description
            if og_description and og_description != meta_description:
                desc_similarity = self._calculate_text_similarity(og_description, meta_description)
                if desc_similarity < 0.7:
                    consistency_issues.append('og_description_differs_from_meta')
                    consistency_score -= 15
            
            # Twitter description vs meta description
            if twitter_description and twitter_description != meta_description:
                desc_similarity = self._calculate_text_similarity(twitter_description, meta_description)
                if desc_similarity < 0.7:
                    consistency_issues.append('twitter_description_differs_from_meta')
                    consistency_score -= 15
        
        # Consistência entre plataformas sociais
        if og_title and twitter_title and og_title != twitter_title:
            consistency_issues.append('og_twitter_titles_differ')
            consistency_score -= 10
        
        if og_description and twitter_description and og_description != twitter_description:
            consistency_issues.append('og_twitter_descriptions_differ')
            consistency_score -= 10
        
        data['social_consistency_issues'] = consistency_issues
        data['social_consistency_score'] = max(0, consistency_score)
        data['social_consistency_issues_count'] = len(consistency_issues)
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calcula similaridade básica entre dois textos (0-1)
        """
        if not text1 or not text2:
            return 0.0
        
        # Normaliza textos
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _validate_social_images(self, data: Dict):
        """
        Valida URLs e dimensões de imagens sociais (opcional - pode ser lento)
        """
        # Valida imagem OG
        og_image = data.get('og_image', '')
        if og_image:
            og_validation = self._validate_image_url(og_image, 'og')
            data['og_image_validation'] = og_validation
            data['og_image_is_accessible'] = og_validation['is_accessible']
            data['og_image_meets_specs'] = og_validation['meets_specs']
        
        # Valida imagem Twitter
        twitter_image = data.get('twitter_image', '')
        if twitter_image:
            twitter_validation = self._validate_image_url(twitter_image, 'twitter')
            data['twitter_image_validation'] = twitter_validation
            data['twitter_image_is_accessible'] = twitter_validation['is_accessible']
            data['twitter_image_meets_specs'] = twitter_validation['meets_specs']
    
    def _validate_image_url(self, image_url: str, platform: str) -> Dict[str, Any]:
        """
        Valida uma URL de imagem específica
        """
        validation = {
            'is_accessible': False,
            'meets_specs': False,
            'width': 0,
            'height': 0,
            'size_mb': 0,
            'content_type': '',
            'error': ''
        }
        
        try:
            # HEAD request para verificar se existe
            response = requests.head(image_url, timeout=self.image_timeout, allow_redirects=True)
            
            if response.status_code == 200:
                validation['is_accessible'] = True
                validation['content_type'] = response.headers.get('content-type', '')
                
                # Tenta obter dimensões do Content-Length (estimativa)
                content_length = response.headers.get('content-length')
                if content_length:
                    validation['size_mb'] = int(content_length) / (1024 * 1024)
                
                # Verificação básica de specs (sem baixar a imagem completa)
                specs = self.image_specs.get(platform, {})
                max_size = specs.get('max_size_mb', 10)
                
                if validation['size_mb'] <= max_size:
                    validation['meets_specs'] = True
                
        except Exception as e:
            validation['error'] = str(e)
            self.logger.debug(f"Erro validando imagem {image_url}: {e}")
        
        return validation
    
    def _detect_social_issues(self, data: Dict):
        """
        Detecta problemas comuns de social media
        """
        issues = []
        
        # Problemas de completude
        facebook_completeness = data.get('facebook_completeness', 0)
        twitter_completeness = data.get('twitter_completeness', 0)
        
        if facebook_completeness < 75:
            issues.append('facebook_incompleto')
        
        if twitter_completeness < 75:
            issues.append('twitter_incompleto')
        
        # Problemas de qualidade de conteúdo
        if data.get('og_title_is_empty', True):
            issues.append('og_title_ausente')
        elif data.get('og_title_too_long', False):
            issues.append('og_title_muito_longo')
        
        if data.get('og_description_is_empty', True):
            issues.append('og_description_ausente')
        elif data.get('og_description_too_long', False):
            issues.append('og_description_muito_longa')
        
        # Problemas de imagem
        if not data.get('og_image', ''):
            issues.append('og_image_ausente')
        elif not data.get('og_image_is_https', True):
            issues.append('og_image_nao_https')
        
        # Problemas de Twitter
        if not data.get('twitter_card_is_valid', False):
            issues.append('twitter_card_invalido')
        
        # Problemas de consistência
        consistency_score = data.get('social_consistency_score', 100)
        if consistency_score < 70:
            issues.append('baixa_consistencia_social')
        
        # Validação de imagens (se habilitada)
        if self.validate_images:
            if data.get('og_image_is_accessible', True) == False:
                issues.append('og_image_inacessivel')
            
            if data.get('twitter_image_is_accessible', True) == False:
                issues.append('twitter_image_inacessivel')
        
        data['social_issues'] = issues
        data['social_issues_count'] = len(issues)
    
    def _calculate_social_severity(self, data: Dict):
        """
        Calcula severity score para problemas de social media
        """
        issues = data.get('social_issues', [])
        
        # Mapeia issues para chaves de severity
        severity_issues = []
        for issue in issues:
            if issue in ['og_title_ausente', 'og_description_ausente', 'og_image_ausente']:
                severity_issues.append('social_tags_ausentes')
            elif issue in ['facebook_incompleto', 'twitter_incompleto']:
                severity_issues.append('social_plataformas_incompletas')
            elif issue in ['baixa_consistencia_social', 'og_image_nao_https']:
                severity_issues.append('social_qualidade_baixa')
            else:
                severity_issues.append('social_otimizacao')
        
        # Calcula severidade geral
        data['social_severity_level'] = self.calculate_problem_severity(severity_issues)
        data['social_problems_keys'] = severity_issues
        data['social_problems_by_severity'] = self.categorize_problems_by_severity(severity_issues)
    
    # ==========================================
    # MÉTODOS DE ANÁLISE E RELATÓRIOS
    # ==========================================
    
    def get_social_summary(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera resumo da análise de social media
        """
        return {
            'og_tags_count': parsed_data.get('og_tags_count', 0),
            'twitter_tags_count': parsed_data.get('twitter_tags_count', 0),
            'facebook_completeness': parsed_data.get('facebook_completeness', 0),
            'twitter_completeness': parsed_data.get('twitter_completeness', 0),
            'linkedin_completeness': parsed_data.get('linkedin_completeness', 0),
            'social_completeness_score': parsed_data.get('social_completeness_score', 0),
            'social_consistency_score': parsed_data.get('social_consistency_score', 0),
            'social_severity_level': parsed_data.get('social_severity_level', SeverityLevel.BAIXA),
            'main_issues': parsed_data.get('social_issues', [])[:3],
            'supports_all_platforms': all([
                parsed_data.get('facebook_completeness', 0) >= 75,
                parsed_data.get('twitter_completeness', 0) >= 75,
                parsed_data.get('linkedin_completeness', 0) >= 75
            ])
        }
    
    def validate_social_best_practices(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida boas práticas de social media
        """
        validations = {}
        
        # Presença de tags básicas
        validations['has_og_tags'] = parsed_data.get('og_tags_count', 0) > 0
        validations['has_twitter_tags'] = parsed_data.get('twitter_tags_count', 0) > 0
        
        # Completude adequada
        validations['facebook_complete'] = parsed_data.get('facebook_completeness', 0) >= 75
        validations['twitter_complete'] = parsed_data.get('twitter_completeness', 0) >= 75
        validations['linkedin_ready'] = parsed_data.get('linkedin_completeness', 0) >= 75
        
        # Qualidade de conteúdo
        validations['og_content_quality'] = all([
            not parsed_data.get('og_title_is_empty', True),
            not parsed_data.get('og_description_is_empty', True),
            parsed_data.get('og_title_optimal', False),
            parsed_data.get('og_description_optimal', False)
        ])
        
        # Imagens adequadas
        validations['has_social_images'] = all([
            bool(parsed_data.get('og_image', '')),
            parsed_data.get('og_image_is_https', False)
        ])
        
        # Consistência
        validations['good_consistency'] = parsed_data.get('social_consistency_score', 0) >= 80
        
        # Sem problemas críticos
        validations['no_critical_issues'] = parsed_data.get('social_severity_level') != SeverityLevel.CRITICA
        
        # Score geral
        score_items = [
            validations['has_og_tags'],
            validations['has_twitter_tags'],
            validations['facebook_complete'],
            validations['twitter_complete'],
            validations['og_content_quality'],
            validations['has_social_images'],
            validations['good_consistency'],
            validations['no_critical_issues']
        ]
        
        validations['social_best_practices_score'] = int((sum(score_items) / len(score_items)) * 100)
        
        return validations

# ==========================================
# FUNÇÃO STANDALONE PARA TESTES
# ==========================================

def parse_social_elements(html_content: str, url: str = 'https://example.com', 
                         meta_title: str = None, meta_description: str = None,
                         validate_images: bool = False) -> Dict[str, Any]:
    """
    Função standalone para testar o SocialParser
    
    Args:
        html_content: HTML da página
        url: URL da página (para validação)
        meta_title: Meta title para comparação de consistência
        meta_description: Meta description para comparação de consistência
        validate_images: Se deve validar URLs de imagem (lento)
        
    Returns:
        Dict com dados de social media parseados
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'lxml')
    parser = SocialParser(validate_images=validate_images)
    
    # Parse básico
    data = parser.parse(soup, url, meta_title, meta_description)
    
    # Adiciona análises extras
    data.update(parser.get_social_summary(data))
    data.update(parser.validate_social_best_practices(data))
    
    return data

# ==========================================
# EXEMPLO DE USO E TESTE
# ==========================================

if __name__ == "__main__":
    # Teste com HTML com diversas tags sociais
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Título da Página | Minha Empresa</title>
        <meta name="description" content="Esta é a meta description da página para SEO.">
        
        <!-- Open Graph completo -->
        <meta property="og:title" content="Título Otimizado para Facebook">
        <meta property="og:description" content="Descrição otimizada para compartilhamento no Facebook e outras redes sociais.">
        <meta property="og:image" content="https://example.com/og-image.jpg">
        <meta property="og:url" content="https://example.com/pagina">
        <meta property="og:type" content="article">
        <meta property="og:site_name" content="Minha Empresa">
        <meta property="og:locale" content="pt_BR">
        
        <!-- Twitter Cards -->
        <meta name="twitter:card" content="summary_large_image">
        <meta name="twitter:site" content="@minhaempresa">
        <meta name="twitter:creator" content="@autor">
        <meta name="twitter:title" content="Título para Twitter">
        <meta name="twitter:description" content="Descrição especial para Twitter com mais caracteres permitidos do que Facebook.">
        <meta name="twitter:image" content="https://example.com/twitter-image.jpg">
        
        <!-- Facebook específico -->
        <meta property="fb:app_id" content="123456789012345">
        <meta property="fb:pages" content="987654321098765">
        
        <!-- Article tags -->
        <meta property="article:author" content="https://facebook.com/autor">
        <meta property="article:published_time" content="2024-01-15T10:30:00Z">
        <meta property="article:modified_time" content="2024-01-16T14:45:00Z">
        <meta property="article:section" content="Tecnologia">
        <meta property="article:tag" content="SEO">
        
        <!-- Tags com problemas -->
        <meta property="og:image" content="http://example.com/insecure-image.jpg">
        <meta name="twitter:title" content="Título muito longo para Twitter que vai passar do limite recomendado de 70 caracteres e pode ser truncado">
        
    </head>
    <body>
        <h1>Conteúdo da Página</h1>
        <p>Artigo sobre otimização para redes sociais.</p>
    </body>
    </html>
    """
    
    # Parse (SEM validação de imagem para teste rápido)
    meta_title = "Título da Página | Minha Empresa"
    meta_description = "Esta é a meta description da página para SEO."
    
    result = parse_social_elements(
        test_html, 
        url="https://example.com/pagina",
        meta_title=meta_title,
        meta_description=meta_description,
        validate_images=False  # Desabilitado para teste rápido
    )
    
    print("🔍 RESULTADO DO SOCIAL PARSER:")
    print(f"   OG Tags: {result['og_tags_count']}")
    print(f"   Twitter Tags: {result['twitter_tags_count']}")
    print(f"   Article Tags: {result.get('article_tags_count', 0)}")
    print(f"   Facebook Completeness: {result['facebook_completeness']}%")
    print(f"   Twitter Completeness: {result['twitter_completeness']}%")
    print(f"   LinkedIn Completeness: {result['linkedin_completeness']}%")
    print(f"   Social Completeness Score: {result['social_completeness_score']}%")
    print(f"   Social Consistency Score: {result['social_consistency_score']}%")
    print(f"   Best Practices Score: {result['social_best_practices_score']}/100")
    print(f"   Social Severity: {result['social_severity_level']}")
    print(f"   Supports All Platforms: {result['supports_all_platforms']}")
    
    print(f"\n📱 PLATAFORMAS:")
    print(f"   Facebook Ready: {result['facebook_complete']}")
    print(f"   Twitter Ready: {result['twitter_complete']}")
    print(f"   LinkedIn Ready: {result['linkedin_ready']}")
    
    print(f"\n📊 QUALIDADE DE CONTEÚDO:")
    print(f"   OG Title: '{result.get('og_title', '')}' ({result.get('og_title_length', 0)} chars)")
    print(f"   OG Description: '{result.get('og_description', '')[:50]}...' ({result.get('og_description_length', 0)} chars)")
    print(f"   Twitter Card: {result.get('twitter_card', 'N/A')}")
    print(f"   OG Image HTTPS: {result.get('og_image_is_https', False)}")
    
    if result['social_issues']:
        print(f"\n⚠️  Issues encontradas:")
        for issue in result['social_issues']:
            print(f"      - {issue}")
    
    if result.get('social_consistency_issues'):
        print(f"\n🔄 Problemas de Consistência:")
        for issue in result['social_consistency_issues']:
            print(f"      - {issue}")
    
    if result.get('facebook_required_missing'):
        print(f"\n❌ Facebook - Tags Obrigatórias Ausentes:")
        for tag in result['facebook_required_missing']:
            print(f"      - {tag}")