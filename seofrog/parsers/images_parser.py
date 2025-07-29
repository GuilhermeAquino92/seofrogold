"""
seofrog/parsers/images_parser.py
Parser modular para análise completa de imagens
Responsável por: ALT text, SRC, dimensões, lazy loading, formatos
"""

import re
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List
from bs4 import BeautifulSoup, Tag
from .base import ParserMixin, SeverityLevel

class ImagesParser(ParserMixin):
    """
    Parser especializado para análise completa de imagens
    Responsável por: ALT text, SRC, dimensões, lazy loading, acessibilidade
    """
    
    def __init__(self):
        super().__init__()
        
        # Configurações para análise de imagens
        self.ideal_alt_min_length = 5      # Mínimo para ALT text útil
        self.ideal_alt_max_length = 125    # Máximo recomendado para ALT text
        self.max_images_per_100_words = 10 # Máximo de imagens por 100 palavras
        
        # Formatos de imagem suportados
        self.image_formats = [
            'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 
            'bmp', 'tiff', 'avif', 'ico'
        ]
        
        # Palavras que indicam imagem decorativa
        self.decorative_keywords = [
            'decoration', 'border', 'spacer', 'bullet', 
            'arrow', 'divider', 'background', 'pattern'
        ]
        
        # Atributos de lazy loading
        self.lazy_loading_attributes = [
            'loading', 'data-src', 'data-lazy', 'data-original',
            'data-srcset', 'data-bg', 'lazy'
        ]
    
    def parse(self, soup: BeautifulSoup, word_count: int = None) -> Dict[str, Any]:
        """
        Parse completo de análise de imagens
        
        Args:
            soup: BeautifulSoup object da página
            word_count: Word count da página (do content_parser, opcional)
            
        Returns:
            Dict com dados completos de imagens
        """
        data = {}
        
        try:
            # Parse básico de todas as imagens
            images = self._find_all_images(soup)
            
            try:
                self._analyze_basic_image_metrics(images, data)
            except ZeroDivisionError:
                self.logger.error("Division by zero in _analyze_basic_image_metrics")
                raise
            
            # Análise detalhada de cada imagem
            try:
                image_details = self._analyze_individual_images(images, soup)
                data['images_details'] = image_details
            except ZeroDivisionError:
                self.logger.error("Division by zero in _analyze_individual_images")
                raise
            
            # Análise de problemas de ALT text
            try:
                self._analyze_alt_text_issues(image_details, data)
            except ZeroDivisionError:
                self.logger.error("Division by zero in _analyze_alt_text_issues")
                raise
            
            # Análise de problemas de SRC
            try:
                self._analyze_src_issues(image_details, data)
            except ZeroDivisionError:
                self.logger.error("Division by zero in _analyze_src_issues")
                raise
            
            # Análise de dimensões e atributos
            try:
                self._analyze_dimensions_and_attributes(image_details, data)
            except ZeroDivisionError:
                self.logger.error("Division by zero in _analyze_dimensions_and_attributes")
                raise
            
            # Análise de lazy loading
            try:
                self._analyze_lazy_loading(image_details, data)
            except ZeroDivisionError:
                self.logger.error("Division by zero in _analyze_lazy_loading")
                raise
            
            # Análise de densidade de imagens (se word_count disponível)
            if word_count:
                try:
                    self._analyze_image_density(data, word_count)
                except ZeroDivisionError:
                    self.logger.error("Division by zero in _analyze_image_density")
                    raise
            
            # Detecção de problemas gerais
            try:
                self._detect_image_issues(data)
            except ZeroDivisionError:
                self.logger.error("Division by zero in _detect_image_issues")
                raise
            
            # Severity scoring
            try:
                self._calculate_images_severity(data)
            except ZeroDivisionError:
                self.logger.error("Division by zero in _calculate_images_severity")
                raise
            
            # Log estatísticas
            errors = 1 if any(key.endswith('_error') for key in data.keys()) else 0
            self.log_parsing_stats('ImagesParser', len(data), errors)
            
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            # Special logging for division by zero to help debug
            if 'division by zero' in error_msg.lower():
                self.logger.error(f"DIVISION BY ZERO in ImagesParser - word_count: {word_count}, error: {error_msg}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
            else:
                self.logger.error(f"Erro no parse de imagens: {error_msg}")
            data['images_parse_error'] = error_msg
            self.log_parsing_stats('ImagesParser', len(data), 1)
        
        return data
    
    def _find_all_images(self, soup: BeautifulSoup) -> List[Tag]:
        """
        Encontra todas as imagens na página (incluindo lazy loading)
        """
        # Imagens tradicionais
        traditional_images = self.safe_find_all(soup, 'img')
        
        # Imagens em outros elementos (CSS background, etc.)
        css_background_images = []
        try:
            # Busca elementos com style="background-image"
            elements_with_bg = soup.find_all(attrs={'style': re.compile(r'background-image', re.I)})
            css_background_images.extend(elements_with_bg)
        except Exception as e:
            self.logger.debug(f"Erro buscando background images: {e}")
        
        return traditional_images  # Por enquanto, foca em <img> tags
    
    def _analyze_basic_image_metrics(self, images: List[Tag], data: Dict):
        """
        Análise básica de métricas de imagens
        """
        total_images = len(images)
        data['images_count'] = total_images
        
        if total_images == 0:
            # Sem imagens
            data['images_without_alt'] = 0
            data['images_without_src'] = 0
            data['images_with_empty_alt'] = 0
            data['images_with_dimensions'] = 0
            data['images_with_lazy_loading'] = 0
            return
        
        # Contadores básicos
        without_alt = 0
        without_src = 0
        empty_alt = 0
        with_dimensions = 0
        with_lazy_loading = 0
        
        for img in images:
            # ALT text
            alt_text = self.safe_get_attribute(img, 'alt')
            if not alt_text:
                without_alt += 1
            elif not alt_text.strip():
                empty_alt += 1
            
            # SRC
            src = self.safe_get_attribute(img, 'src')
            if not src:
                without_src += 1
            
            # Dimensões
            width = self.safe_get_attribute(img, 'width')
            height = self.safe_get_attribute(img, 'height')
            if width and height:
                with_dimensions += 1
            
            # Lazy loading
            if self._has_lazy_loading(img):
                with_lazy_loading += 1
        
        # Armazena métricas
        data['images_without_alt'] = without_alt
        data['images_without_src'] = without_src
        data['images_with_empty_alt'] = empty_alt
        data['images_with_dimensions'] = with_dimensions
        data['images_with_lazy_loading'] = with_lazy_loading
        
        # Percentuais
        data['images_alt_coverage'] = ((total_images - without_alt) / total_images * 100) if total_images > 0 else 0
        data['images_src_coverage'] = ((total_images - without_src) / total_images * 100) if total_images > 0 else 0
        data['images_dimensions_coverage'] = (with_dimensions / total_images * 100) if total_images > 0 else 0
        data['images_lazy_loading_coverage'] = (with_lazy_loading / total_images * 100) if total_images > 0 else 0
    
    def _analyze_individual_images(self, images: List[Tag], soup: BeautifulSoup) -> List[Dict]:
        """
        Análise detalhada de cada imagem individual
        """
        image_details = []
        
        for i, img in enumerate(images):
            detail = {
                'index': i + 1,
                'tag_html': str(img).encode('utf-8', errors='replace').decode('utf-8')[:200],  # Primeiros 200 chars da tag
            }
            
            # Atributos básicos
            detail['src'] = self.safe_get_attribute(img, 'src')
            detail['alt'] = self.safe_get_attribute(img, 'alt')
            detail['title'] = self.safe_get_attribute(img, 'title')
            detail['width'] = self.safe_get_attribute(img, 'width')
            detail['height'] = self.safe_get_attribute(img, 'height')
            detail['class'] = ' '.join(img.get('class', []))
            
            # Análise do ALT text
            self._analyze_individual_alt_text(detail)
            
            # Análise do SRC
            self._analyze_individual_src(detail)
            
            # Análise de dimensões
            self._analyze_individual_dimensions(detail)
            
            # Análise de lazy loading
            detail['has_lazy_loading'] = self._has_lazy_loading(img)
            detail['lazy_loading_method'] = self._get_lazy_loading_method(img)
            
            # Análise de formato
            self._analyze_image_format(detail)
            
            # Análise de acessibilidade
            self._analyze_accessibility(detail, img)
            
            image_details.append(detail)
        
        return image_details
    
    def _analyze_individual_alt_text(self, detail: Dict):
        """
        Análise detalhada do ALT text de uma imagem
        """
        alt_text = detail.get('alt', '')
        
        # Básico
        detail['has_alt'] = alt_text is not None
        detail['alt_is_empty'] = not bool(alt_text.strip()) if alt_text else True
        detail['alt_length'] = len(alt_text) if alt_text else 0
        
        if alt_text:
            alt_clean = alt_text.strip()
            
            # Análise de qualidade
            detail['alt_too_short'] = 0 < len(alt_clean) < self.ideal_alt_min_length
            detail['alt_too_long'] = len(alt_clean) > self.ideal_alt_max_length
            detail['alt_optimal_length'] = self.ideal_alt_min_length <= len(alt_clean) <= self.ideal_alt_max_length
            
            # Detecta ALT text problemático
            detail['alt_is_filename'] = self._is_filename_alt(alt_clean)
            detail['alt_is_generic'] = self._is_generic_alt(alt_clean)
            detail['alt_is_decorative_keyword'] = any(keyword in alt_clean.lower() for keyword in self.decorative_keywords)
            
            # Word count do ALT
            alt_words = len(alt_clean.split()) if alt_clean else 0
            detail['alt_word_count'] = alt_words
            detail['alt_has_multiple_words'] = alt_words > 1
        else:
            detail['alt_too_short'] = False
            detail['alt_too_long'] = False
            detail['alt_optimal_length'] = False
            detail['alt_is_filename'] = False
            detail['alt_is_generic'] = False
            detail['alt_is_decorative_keyword'] = False
            detail['alt_word_count'] = 0
            detail['alt_has_multiple_words'] = False
    
    def _analyze_individual_src(self, detail: Dict):
        """
        Análise detalhada do SRC de uma imagem
        """
        src = detail.get('src', '')
        
        # Básico
        detail['has_src'] = bool(src)
        detail['src_is_valid_url'] = self.is_valid_url(src) if src else False
        
        if src:
            # Análise de URL
            detail['src_is_relative'] = not src.startswith(('http://', 'https://'))
            detail['src_is_data_uri'] = src.startswith('data:')
            detail['src_is_external'] = self._is_external_image(src)
            
            # Análise de path/filename
            try:
                parsed_url = urlparse(src)
                path = parsed_url.path
                detail['src_filename'] = path.split('/')[-1] if '/' in path else path
                detail['src_has_query_params'] = bool(parsed_url.query)
            except:
                detail['src_filename'] = ''
                detail['src_has_query_params'] = False
        else:
            detail['src_is_relative'] = False
            detail['src_is_data_uri'] = False
            detail['src_is_external'] = False
            detail['src_filename'] = ''
            detail['src_has_query_params'] = False
    
    def _analyze_individual_dimensions(self, detail: Dict):
        """
        Análise de dimensões de uma imagem
        """
        width = detail.get('width', '')
        height = detail.get('height', '')
        
        # Verificação de dimensões especificadas
        detail['has_width'] = bool(width)
        detail['has_height'] = bool(height)
        detail['has_both_dimensions'] = bool(width and height)
        
        # Análise de valores de dimensões
        if width and height:
            try:
                width_val = int(width) if width.isdigit() else 0
                height_val = int(height) if height.isdigit() else 0
                
                detail['width_value'] = width_val
                detail['height_value'] = height_val
                detail['aspect_ratio'] = round(width_val / height_val, 2) if height_val > 0 else 0
                detail['is_large_image'] = width_val > 1200 or height_val > 800
                detail['is_small_image'] = width_val < 100 and height_val < 100
            except:
                detail['width_value'] = 0
                detail['height_value'] = 0
                detail['aspect_ratio'] = 0
                detail['is_large_image'] = False
                detail['is_small_image'] = False
        else:
            detail['width_value'] = 0
            detail['height_value'] = 0
            detail['aspect_ratio'] = 0
            detail['is_large_image'] = False
            detail['is_small_image'] = False
    
    def _analyze_image_format(self, detail: Dict):
        """
        Análise do formato da imagem baseado no SRC
        """
        src = detail.get('src', '')
        src_filename = detail.get('src_filename', '')
        
        # Extrai extensão
        if src_filename and '.' in src_filename:
            extension = src_filename.split('.')[-1].lower()
            detail['image_format'] = extension
            detail['is_supported_format'] = extension in self.image_formats
            detail['is_modern_format'] = extension in ['webp', 'avif', 'svg']
            detail['is_legacy_format'] = extension in ['gif', 'bmp']
        else:
            detail['image_format'] = 'unknown'
            detail['is_supported_format'] = False
            detail['is_modern_format'] = False
            detail['is_legacy_format'] = False
    
    def _analyze_accessibility(self, detail: Dict, img: Tag):
        """
        Análise de acessibilidade da imagem
        """
        # Verifica se imagem é decorativa (ALT vazio propositalmente)
        alt_text = detail.get('alt', '')
        detail['is_decorative'] = alt_text == ''  # ALT vazio (não None) indica decorativa
        
        # Verifica role
        role = self.safe_get_attribute(img, 'role')
        detail['has_role'] = bool(role)
        detail['role'] = role
        
        # Verifica aria-hidden
        aria_hidden = self.safe_get_attribute(img, 'aria-hidden')
        detail['is_aria_hidden'] = aria_hidden == 'true'
        
        # Verifica aria-label
        aria_label = self.safe_get_attribute(img, 'aria-label')
        detail['has_aria_label'] = bool(aria_label)
        detail['aria_label'] = aria_label
        
        # Score de acessibilidade
        accessibility_score = 0
        if detail['has_alt'] and not detail['alt_is_empty']:
            accessibility_score += 40
        if detail['alt_optimal_length']:
            accessibility_score += 20
        if detail['has_both_dimensions']:
            accessibility_score += 20
        if detail.get('alt_has_multiple_words'):
            accessibility_score += 10
        if not detail.get('alt_is_generic'):
            accessibility_score += 10
        
        detail['accessibility_score'] = accessibility_score
        detail['is_accessible'] = accessibility_score >= 60
    
    def _analyze_alt_text_issues(self, image_details: List[Dict], data: Dict):
        """
        Análise de problemas de ALT text em todas as imagens
        """
        alt_issues = []
        
        for img in image_details:
            if not img['has_alt']:
                alt_issues.append({
                    'index': img['index'],
                    'issue': 'missing_alt',
                    'severity': 'alta',
                    'description': 'Imagem sem atributo ALT'
                })
            elif img['alt_is_empty'] and not img['is_decorative']:
                alt_issues.append({
                    'index': img['index'],
                    'issue': 'empty_alt',
                    'severity': 'alta',
                    'description': 'ALT text vazio (pode ser decorativa?)'
                })
            elif img['alt_too_short']:
                alt_issues.append({
                    'index': img['index'],
                    'issue': 'alt_too_short',
                    'severity': 'media',
                    'description': f'ALT muito curto ({img["alt_length"]} chars)'
                })
            elif img['alt_too_long']:
                alt_issues.append({
                    'index': img['index'],
                    'issue': 'alt_too_long',
                    'severity': 'media',
                    'description': f'ALT muito longo ({img["alt_length"]} chars)'
                })
            elif img['alt_is_filename']:
                alt_issues.append({
                    'index': img['index'],
                    'issue': 'alt_is_filename',
                    'severity': 'alta',
                    'description': 'ALT text é nome de arquivo'
                })
            elif img['alt_is_generic']:
                alt_issues.append({
                    'index': img['index'],
                    'issue': 'alt_is_generic',
                    'severity': 'media',
                    'description': 'ALT text genérico/inútil'
                })
        
        data['alt_text_issues'] = alt_issues
        data['alt_text_issues_count'] = len(alt_issues)
    
    def _analyze_src_issues(self, image_details: List[Dict], data: Dict):
        """
        Análise de problemas de SRC em todas as imagens
        """
        src_issues = []
        
        for img in image_details:
            if not img['has_src']:
                src_issues.append({
                    'index': img['index'],
                    'issue': 'missing_src',
                    'severity': 'critica',
                    'description': 'Imagem sem atributo SRC'
                })
            elif not img['src_is_valid_url'] and not img['src_is_data_uri']:
                src_issues.append({
                    'index': img['index'],
                    'issue': 'invalid_src',
                    'severity': 'alta',
                    'description': 'SRC com URL inválida'
                })
        
        data['src_issues'] = src_issues
        data['src_issues_count'] = len(src_issues)
    
    def _analyze_dimensions_and_attributes(self, image_details: List[Dict], data: Dict):
        """
        Análise de dimensões e outros atributos
        """
        # Contadores de dimensões
        large_images = sum(1 for img in image_details if img.get('is_large_image', False))
        small_images = sum(1 for img in image_details if img.get('is_small_image', False))
        modern_formats = sum(1 for img in image_details if img.get('is_modern_format', False))
        
        data['images_large_count'] = large_images
        data['images_small_count'] = small_images
        data['images_modern_format_count'] = modern_formats
        data['images_modern_format_percentage'] = (modern_formats / len(image_details) * 100) if image_details and len(image_details) > 0 else 0
    
    def _analyze_lazy_loading(self, image_details: List[Dict], data: Dict):
        """
        Análise de lazy loading
        """
        lazy_loading_methods = {}
        
        for img in image_details:
            method = img.get('lazy_loading_method')
            if method and method != 'none':
                lazy_loading_methods[method] = lazy_loading_methods.get(method, 0) + 1
        
        data['lazy_loading_methods'] = lazy_loading_methods
        data['lazy_loading_total_methods'] = len(lazy_loading_methods)
    
    def _analyze_image_density(self, data: Dict, word_count: int):
        """
        Análise de densidade de imagens (imagens por 100 palavras)
        """
        images_count = data.get('images_count', 0)
        
        if word_count > 0:
            density = (images_count / word_count) * 100
            data['image_density_per_100_words'] = round(density, 2)
            data['image_density_source'] = 'real'
            data['image_density_optimal'] = density <= self.max_images_per_100_words
        else:
            data['image_density_per_100_words'] = 0
            data['image_density_source'] = 'no_content'
            data['image_density_optimal'] = True
    
    def _detect_image_issues(self, data: Dict):
        """
        Detecta problemas gerais de imagens
        """
        issues = []
        
        # Problemas de ALT text
        if data.get('images_without_alt', 0) > 0:
            issues.append('imagens_sem_alt')
        
        if data.get('images_with_empty_alt', 0) > 0:
            issues.append('imagens_alt_vazio')
        
        # Problemas de SRC
        if data.get('images_without_src', 0) > 0:
            issues.append('imagens_sem_src')
        
        # Problemas de dimensões
        if data.get('images_with_dimensions', 0) == 0 and data.get('images_count', 0) > 0:
            issues.append('imagens_sem_dimensoes')
        
        # Densidade muito alta
        if data.get('image_density_per_100_words', 0) > self.max_images_per_100_words:
            issues.append('densidade_imagens_alta')
        
        # Muitas imagens grandes
        images_count = data.get('images_count', 0)
        if images_count > 0:
            large_percentage = (data.get('images_large_count', 0) / images_count) * 100
            if large_percentage > 50:
                issues.append('muitas_imagens_grandes')
        
        # Poucos formatos modernos
        modern_percentage = data.get('images_modern_format_percentage', 0)
        if modern_percentage < 25 and data.get('images_count', 0) > 5:
            issues.append('poucos_formatos_modernos')
        
        data['image_issues'] = issues
        data['image_issues_count'] = len(issues)
    
    def _calculate_images_severity(self, data: Dict):
        """
        Calcula severity score para problemas de imagens
        """
        issues = data.get('image_issues', [])
        
        # Mapeia issues para chaves de severity
        severity_issues = []
        for issue in issues:
            if issue == 'imagens_sem_src':
                severity_issues.append('imagens_sem_src')
            elif issue in ['imagens_sem_alt', 'imagens_alt_vazio']:
                severity_issues.append('imagens_sem_alt')
            elif issue in ['imagens_sem_dimensoes', 'muitas_imagens_grandes']:
                severity_issues.append('imagens_problemas_tecnicos')
            else:
                severity_issues.append('imagens_otimizacao')
        
        # Calcula severidade geral
        data['images_severity_level'] = self.calculate_problem_severity(severity_issues)
        data['images_problems_keys'] = severity_issues
        data['images_problems_by_severity'] = self.categorize_problems_by_severity(severity_issues)
    
    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================
    
    def _has_lazy_loading(self, img: Tag) -> bool:
        """Verifica se imagem tem lazy loading"""
        for attr in self.lazy_loading_attributes:
            if img.has_attr(attr):
                return True
        return False
    
    def _get_lazy_loading_method(self, img: Tag) -> str:
        """Identifica método de lazy loading usado"""
        for attr in self.lazy_loading_attributes:
            if img.has_attr(attr):
                return attr
        return 'none'
    
    def _is_filename_alt(self, alt_text: str) -> bool:
        """Verifica se ALT text é um nome de arquivo"""
        alt_lower = alt_text.lower()
        
        # Padrões de filename
        filename_patterns = [
            r'\.(jpg|jpeg|png|gif|svg|webp|bmp)$',  # Extensões de imagem
            r'^img_?\d+',                           # img001, img_001
            r'^image_?\d+',                         # image001, image_001
            r'^dsc_?\d+',                           # DSC001 (câmeras)
            r'^[a-z0-9_-]+\.(jpg|jpeg|png|gif)$'   # filename.ext
        ]
        
        return any(re.search(pattern, alt_lower) for pattern in filename_patterns)
    
    def _is_generic_alt(self, alt_text: str) -> bool:
        """Verifica se ALT text é genérico/inútil"""
        alt_lower = alt_text.lower().strip()
        
        generic_alts = [
            'image', 'img', 'picture', 'photo', 'logo', 'icon',
            'imagem', 'foto', 'figura', 'ilustração',
            'click here', 'read more', 'learn more',
            'banner', 'advertisement', 'ad'
        ]
        
        return alt_lower in generic_alts
    
    def _is_external_image(self, src: str) -> bool:
        """Verifica se imagem é externa (CDN, outros domínios)"""
        if not src or src.startswith('data:'):
            return False
        
        # CDNs e domínios externos comuns
        external_domains = [
            'cdn.', 'images.', 'static.', 'assets.',
            'amazonaws.com', 'cloudfront.net', 'googleapis.com',
            'imgur.com', 'flickr.com', 'unsplash.com'
        ]
        
        return any(domain in src.lower() for domain in external_domains)
    
    # ==========================================
    # MÉTODOS DE ANÁLISE E RELATÓRIOS
    # ==========================================
    
    def get_images_summary(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera resumo da análise de imagens
        
        Args:
            parsed_data: Dados já parseados
            
        Returns:
            Dict com resumo de análise
        """
        images_count = parsed_data.get('images_count', 0)
        issues_count = parsed_data.get('image_issues_count', 0)
        
        return {
            'images_count': images_count,
            'alt_coverage': parsed_data.get('images_alt_coverage', 0),
            'accessibility_ready': issues_count <= 1 and parsed_data.get('images_alt_coverage', 0) >= 90,
            'images_severity_level': parsed_data.get('images_severity_level', SeverityLevel.BAIXA),
            'main_issues': parsed_data.get('image_issues', [])[:3],
            'modern_format_usage': parsed_data.get('images_modern_format_percentage', 0),
            'lazy_loading_usage': parsed_data.get('images_lazy_loading_coverage', 0),
            'image_density': parsed_data.get('image_density_per_100_words', 0)
        }
    
    def validate_images_best_practices(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida boas práticas de imagens
        
        Args:
            parsed_data: Dados parseados
            
        Returns:
            Dict com validações
        """
        validations = {}
        
        images_count = parsed_data.get('images_count', 0)
        
        if images_count == 0:
            # Sem imagens - score neutro
            validations['images_best_practices_score'] = 50
            return validations
        
        # ALT text adequado
        alt_coverage = parsed_data.get('images_alt_coverage', 0)
        validations['good_alt_coverage'] = alt_coverage >= 90
        validations['excellent_alt_coverage'] = alt_coverage >= 95
        
        # SRC adequado
        src_coverage = parsed_data.get('images_src_coverage', 0)
        validations['good_src_coverage'] = src_coverage >= 95
        
        # Dimensões especificadas
        dimensions_coverage = parsed_data.get('images_dimensions_coverage', 0)
        validations['good_dimensions_coverage'] = dimensions_coverage >= 70
        
        # Densidade adequada
        density = parsed_data.get('image_density_per_100_words', 0)
        validations['optimal_image_density'] = density <= self.max_images_per_100_words
        
        # Uso de formatos modernos
        modern_format_usage = parsed_data.get('images_modern_format_percentage', 0)
        validations['uses_modern_formats'] = modern_format_usage >= 25
        
        # Lazy loading
        lazy_loading_usage = parsed_data.get('images_lazy_loading_coverage', 0)
        validations['uses_lazy_loading'] = lazy_loading_usage >= 50
        
        # Sem problemas críticos
        validations['no_critical_issues'] = parsed_data.get('images_severity_level') != SeverityLevel.CRITICA
        
        # Score geral
        score_items = [
            validations['good_alt_coverage'],
            validations['good_src_coverage'],
            validations['good_dimensions_coverage'],
            validations['optimal_image_density'],
            validations['uses_modern_formats'],
            validations['no_critical_issues']
        ]
        
        validations['images_best_practices_score'] = int((sum(score_items) / len(score_items)) * 100) if score_items else 0
        
        return validations
    
    def update_with_word_count(self, parsed_data: Dict[str, Any], word_count: int) -> Dict[str, Any]:
        """
        Atualiza dados parseados com word count real (para usar após content_parser)
        
        Args:
            parsed_data: Dados já parseados
            word_count: Word count real da página
            
        Returns:
            Dict com densidade real calculada
        """
        self._analyze_image_density(parsed_data, word_count)
        
        # Recalcula validações com densidade real
        validations = self.validate_images_best_practices(parsed_data)
        parsed_data.update(validations)
        
        return parsed_data

# ==========================================
# FUNÇÃO STANDALONE PARA TESTES
# ==========================================

def parse_images_elements(html_content: str, word_count: int = None) -> Dict[str, Any]:
    """
    Função standalone para testar o ImagesParser
    
    Args:
        html_content: HTML da página
        word_count: Word count da página (opcional)
        
    Returns:
        Dict com dados de imagens parseados
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'lxml')
    parser = ImagesParser()
    
    # Parse básico
    data = parser.parse(soup, word_count)
    
    # Adiciona análises extras
    data.update(parser.get_images_summary(data))
    data.update(parser.validate_images_best_practices(data))
    
    return data

# ==========================================
# EXEMPLO DE USO E TESTE
# ==========================================

if __name__ == "__main__":
    # Teste com HTML com diversos tipos de imagens
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teste de Imagens</title>
    </head>
    <body>
        <h1>Galeria de Teste</h1>
        
        <!-- Imagem com ALT adequado -->
        <img src="https://example.com/produto.jpg" alt="Smartphone Samsung Galaxy com tela de 6.1 polegadas" width="300" height="200">
        
        <!-- Imagem sem ALT (problema) -->
        <img src="/images/banner.png" width="800" height="200">
        
        <!-- Imagem com ALT vazio (decorativa) -->
        <img src="/images/divider.gif" alt="" width="100%" height="1">
        
        <!-- Imagem com ALT muito curto -->
        <img src="photo.jpg" alt="foto" width="150" height="100">
        
        <!-- Imagem com ALT muito longo -->
        <img src="camera.jpg" alt="Esta é uma fotografia extremamente detalhada de uma câmera profissional digital DSLR de alta resolução com lente intercambiável, corpo em magnésio, múltiplos botões de controle e display LCD na parte traseira, ideal para fotógrafos profissionais que precisam de qualidade excepcional em suas imagens" width="250" height="150">
        
        <!-- Imagem com nome de arquivo como ALT -->
        <img src="img_001.jpg" alt="img_001.jpg" width="200" height="150">
        
        <!-- Imagem sem SRC (problema crítico) -->
        <img alt="Imagem sem source" width="100" height="100">
        
        <!-- Imagem com lazy loading -->
        <img src="placeholder.jpg" data-src="real-image.jpg" alt="Imagem com lazy loading" loading="lazy" width="300" height="200">
        
        <!-- Imagem moderna WebP -->
        <img src="modern-image.webp" alt="Imagem em formato WebP moderno" width="400" height="300">
        
        <!-- Imagem grande -->
        <img src="huge-banner.jpg" alt="Banner principal da página" width="1920" height="1080">
        
    </body>
    </html>
    """
    
    # Parse com word count simulado
    word_count = 150  # Simula 150 palavras na página
    result = parse_images_elements(test_html, word_count)
    
    print("🔍 RESULTADO DO IMAGES PARSER:")
    print(f"   Images Count: {result['images_count']}")
    print(f"   Images without ALT: {result['images_without_alt']}")
    print(f"   Images without SRC: {result['images_without_src']}")
    print(f"   Images with empty ALT: {result['images_with_empty_alt']}")
    print(f"   Images with dimensions: {result['images_with_dimensions']}")
    print(f"   Images with lazy loading: {result['images_with_lazy_loading']}")
    print(f"   ALT Coverage: {result['images_alt_coverage']:.1f}%")
    print(f"   SRC Coverage: {result['images_src_coverage']:.1f}%")
    print(f"   Modern Format Usage: {result['images_modern_format_percentage']:.1f}%")
    print(f"   Image Density: {result['image_density_per_100_words']:.1f} per 100 words")
    print(f"   Accessibility Ready: {result['accessibility_ready']}")
    print(f"   Images Severity: {result['images_severity_level']}")
    print(f"   Best Practices Score: {result['images_best_practices_score']}/100")
    
    if result['image_issues']:
        print(f"   Issues encontradas:")
        for issue in result['image_issues']:
            print(f"      - {issue}")
    
    if result['alt_text_issues']:
        print(f"   ALT text issues:")
        for issue in result['alt_text_issues'][:5]:  # Primeiros 5
            print(f"      - Img {issue['index']}: {issue['description']}")
    
    if result['src_issues']:
        print(f"   SRC issues:")
        for issue in result['src_issues']:
            print(f"      - Img {issue['index']}: {issue['description']}")