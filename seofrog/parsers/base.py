"""
seofrog/parsers/base.py
Helpers comuns e ParserMixin para todos os parsers modulares
"""

import re
from typing import Dict, Any, Optional, List, Union
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin
from seofrog.utils.logger import get_logger

class ParserMixin:
    """
    Mixin com métodos utilitários comuns para todos os parsers
    Fornece helpers seguros e padronizados
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    # ==========================================
    # HELPERS DE BUSCA SEGUROS
    # ==========================================
    
    def safe_find(self, soup: BeautifulSoup, tag: str, attrs: Dict = None) -> Optional[Tag]:
        """
        Find seguro que não quebra e loga erros
        
        Args:
            soup: BeautifulSoup object
            tag: Nome da tag
            attrs: Atributos para buscar
            
        Returns:
            Tag encontrada ou None
        """
        try:
            return soup.find(tag, attrs or {})
        except Exception as e:
            self.logger.debug(f"Erro no find({tag}, {attrs}): {e}")
            return None
    
    def safe_find_all(self, soup: BeautifulSoup, tag: str, attrs: Dict = None) -> List[Tag]:
        """
        Find_all seguro que retorna lista vazia em caso de erro
        
        Args:
            soup: BeautifulSoup object
            tag: Nome da tag
            attrs: Atributos para buscar
            
        Returns:
            Lista de tags encontradas (vazia se erro)
        """
        try:
            return soup.find_all(tag, attrs or {})
        except Exception as e:
            self.logger.debug(f"Erro no find_all({tag}, {attrs}): {e}")
            return []
    
    def safe_get_attribute(self, element: Tag, attr: str, default: str = '') -> str:
        """
        Extrai atributo de forma segura
        
        Args:
            element: Elemento BeautifulSoup
            attr: Nome do atributo
            default: Valor padrão se não encontrar
            
        Returns:
            Valor do atributo ou padrão
        """
        try:
            if element and hasattr(element, 'get'):
                return element.get(attr, default).strip()
            return default
        except Exception as e:
            self.logger.debug(f"Erro extraindo atributo {attr}: {e}")
            return default
    
    # ==========================================
    # HELPERS DE TEXTO
    # ==========================================
    
    def clean_text(self, text: Union[str, Tag, None]) -> str:
        """
        Limpa texto removendo espaços extras e quebras de linha
        
        Args:
            text: Texto, tag BeautifulSoup ou None
            
        Returns:
            Texto limpo ou string vazia
        """
        try:
            if text is None:
                return ''
            
            # Se é uma tag BeautifulSoup, extrai o texto
            if hasattr(text, 'get_text'):
                text = text.get_text()
            
            # Converte para string se necessário
            text = str(text)
            
            # Remove espaços extras, tabs, quebras de linha
            cleaned = re.sub(r'\s+', ' ', text.strip())
            
            return cleaned
            
        except Exception as e:
            self.logger.debug(f"Erro limpando texto: {e}")
            return ''
    
    def extract_text_safe(self, element: Tag) -> str:
        """
        Extrai texto de elemento de forma segura
        
        Args:
            element: Elemento BeautifulSoup
            
        Returns:
            Texto extraído e limpo
        """
        try:
            if element and hasattr(element, 'get_text'):
                return self.clean_text(element.get_text())
            return ''
        except Exception as e:
            self.logger.debug(f"Erro extraindo texto: {e}")
            return ''
    
    # ==========================================
    # HELPERS DE URL
    # ==========================================
    
    def extract_domain(self, url: str) -> str:
        """
        Extrai domínio da URL de forma segura
        
        Args:
            url: URL para extrair domínio
            
        Returns:
            Domínio ou string vazia
        """
        try:
            if not url:
                return ''
            parsed = urlparse(url.strip())
            return parsed.netloc.lower()
        except Exception as e:
            self.logger.debug(f"Erro extraindo domínio de {url}: {e}")
            return ''
    
    def is_same_domain(self, url1: str, url2: str) -> bool:
        """
        Verifica se duas URLs são do mesmo domínio
        
        Args:
            url1: Primeira URL
            url2: Segunda URL
            
        Returns:
            True se mesmo domínio
        """
        try:
            domain1 = self.extract_domain(url1)
            domain2 = self.extract_domain(url2)
            return domain1 == domain2 and domain1 != ''
        except Exception as e:
            self.logger.debug(f"Erro comparando domínios: {e}")
            return False
    
    def resolve_url(self, base_url: str, href: str) -> str:
        """
        Resolve URL relativa para absoluta
        
        Args:
            base_url: URL base da página
            href: href que pode ser relativo
            
        Returns:
            URL absoluta ou href original se erro
        """
        try:
            if not href:
                return ''
            
            # Se já é absoluta, retorna como está
            if href.startswith(('http://', 'https://')):
                return href.strip()
            
            # Resolve relativa
            return urljoin(base_url, href).strip()
            
        except Exception as e:
            self.logger.debug(f"Erro resolvendo URL {href}: {e}")
            return href
    
    # ==========================================
    # HELPERS DE VALIDAÇÃO
    # ==========================================
    
    def is_valid_url(self, url: str) -> bool:
        """
        Valida se string é URL válida
        
        Args:
            url: String para validar
            
        Returns:
            True se URL válida
        """
        try:
            if not url or not isinstance(url, str):
                return False
            
            parsed = urlparse(url.strip())
            return bool(parsed.scheme and parsed.netloc)
            
        except Exception:
            return False
    
    def is_empty_text(self, text: str) -> bool:
        """
        Verifica se texto está vazio (incluindo apenas espaços/HTML entities)
        
        Args:
            text: Texto para verificar
            
        Returns:
            True se texto vazio
        """
        if not text:
            return True
        
        # Remove espaços e entities comuns
        cleaned = text.strip()
        cleaned = cleaned.replace('&nbsp;', '').replace('\u00a0', '')
        cleaned = re.sub(r'\s+', '', cleaned)
        
        return len(cleaned) == 0
    
    # ==========================================
    # HELPERS DE ANÁLISE SEO
    # ==========================================
    
    def analyze_text_length(self, text: str, min_length: int, max_length: int) -> Dict[str, Any]:
        """
        Analisa comprimento de texto para validações SEO
        
        Args:
            text: Texto para analisar
            min_length: Comprimento mínimo recomendado
            max_length: Comprimento máximo recomendado
            
        Returns:
            Dict com análise de comprimento
        """
        length = len(text) if text else 0
        
        return {
            'length': length,
            'is_empty': length == 0,
            'too_short': 0 < length < min_length,
            'too_long': length > max_length,
            'optimal': min_length <= length <= max_length,
            'word_count': len(text.split()) if text else 0
        }
    
    def detect_brand_pattern(self, text: str, separators: List[str] = None) -> bool:
        """
        Detecta padrões de brand em texto (títulos, etc.)
        
        Args:
            text: Texto para analisar
            separators: Lista de separadores de brand
            
        Returns:
            True se detecta padrão de brand
        """
        if not text:
            return False
        
        if separators is None:
            separators = [' | ', ' - ', ' :: ', ' • ', ' » ', ' / ']
        
        return any(sep in text for sep in separators)
    
    # ==========================================
    # HELPERS DE ATRIBUTOS META
    # ==========================================
    
    def find_meta_by_name(self, soup: BeautifulSoup, name: str, case_sensitive: bool = False) -> Optional[Tag]:
        """
        Busca meta tag por name de forma segura
        
        Args:
            soup: BeautifulSoup object
            name: Nome da meta tag
            case_sensitive: Se deve ser case sensitive
            
        Returns:
            Meta tag encontrada ou None
        """
        try:
            if case_sensitive:
                return soup.find('meta', attrs={'name': name})
            else:
                return soup.find('meta', attrs={'name': re.compile(f'^{re.escape(name)}$', re.I)})
        except Exception as e:
            self.logger.debug(f"Erro buscando meta name='{name}': {e}")
            return None
    
    def find_meta_by_property(self, soup: BeautifulSoup, property_name: str, case_sensitive: bool = False) -> Optional[Tag]:
        """
        Busca meta tag por property de forma segura
        
        Args:
            soup: BeautifulSoup object
            property_name: Nome da property
            case_sensitive: Se deve ser case sensitive
            
        Returns:
            Meta tag encontrada ou None
        """
        try:
            if case_sensitive:
                return soup.find('meta', attrs={'property': property_name})
            else:
                return soup.find('meta', attrs={'property': re.compile(f'^{re.escape(property_name)}$', re.I)})
        except Exception as e:
            self.logger.debug(f"Erro buscando meta property='{property_name}': {e}")
            return None
    
    def extract_meta_content(self, meta_tag: Tag) -> str:
        """
        Extrai content de meta tag de forma segura
        
        Args:
            meta_tag: Meta tag
            
        Returns:
            Conteúdo da meta tag ou string vazia
        """
        return self.safe_get_attribute(meta_tag, 'content')
    
    # ==========================================
    # HELPERS DE LOGGING
    # ==========================================
    
    def log_parsing_stats(self, parser_name: str, fields_extracted: int, errors: int = 0):
        """
        Log padronizado de estatísticas de parsing
        
        Args:
            parser_name: Nome do parser
            fields_extracted: Número de campos extraídos
            errors: Número de erros encontrados
        """
        if errors > 0:
            self.logger.warning(f"{parser_name}: {fields_extracted} campos extraídos, {errors} erros")
        else:
            self.logger.debug(f"{parser_name}: {fields_extracted} campos extraídos com sucesso")
    
    # ==========================================
    # HELPERS PARA DETECÇÃO DE ELEMENTOS ESCONDIDOS
    # ==========================================
    
    def is_hidden_by_css(self, element: Tag) -> bool:
        """
        Verifica se elemento está escondido por CSS usando padrões centralizados
        
        Args:
            element: Tag do elemento
            
        Returns:
            bool: True se escondido por CSS
        """
        if not element:
            return False
        
        # Verifica style inline
        style = self.safe_get_attribute(element, 'style').lower()
        
        # Verifica padrões CSS de esconder
        for pattern in CSS_HIDING_PATTERNS:
            if pattern in style.replace(' ', ''):
                return True
        
        # Verifica classes suspeitas
        class_attr = element.get('class', [])
        if isinstance(class_attr, list):
            for cls in class_attr:
                if any(suspicious in cls.lower() for suspicious in SUSPICIOUS_CSS_CLASSES):
                    return True
        
        return False
    
    def get_css_hiding_method(self, element: Tag) -> str:
        """
        Identifica o método CSS usado para esconder usando padrões centralizados
        
        Args:
            element: Tag do elemento
            
        Returns:
            str: Método CSS identificado
        """
        if not element:
            return "Desconhecido"
        
        style = self.safe_get_attribute(element, 'style').lower()
        class_attr = element.get('class', [])
        
        # Verifica métodos específicos inline
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
        
        # Verifica classes suspeitas
        if isinstance(class_attr, list):
            for cls in class_attr:
                if any(suspicious in cls.lower() for suspicious in SUSPICIOUS_CSS_CLASSES):
                    return f"class: {cls}"
        
        return "CSS escondido (método desconhecido)"
    
    # ==========================================
    # HELPERS PARA SEVERITY SCORING
    # ==========================================
    
    def calculate_problem_severity(self, problems: List[str]) -> str:
        """
        Calcula severidade geral baseada na lista de problemas
        
        Args:
            problems: Lista de chaves de problemas (ex: ['sem_h1', 'headings_escondidas'])
            
        Returns:
            str: Nível de severidade geral
        """
        if not problems:
            return SeverityLevel.BAIXA
        
        severities = []
        for problem in problems:
            severity = PROBLEM_SEVERITY_MAP.get(problem, SeverityLevel.BAIXA)
            severities.append(severity)
        
        # Retorna a severidade mais alta encontrada
        if SeverityLevel.CRITICA in severities:
            return SeverityLevel.CRITICA
        elif SeverityLevel.ALTA in severities:
            return SeverityLevel.ALTA
        elif SeverityLevel.MEDIA in severities:
            return SeverityLevel.MEDIA
        else:
            return SeverityLevel.BAIXA
    
    def categorize_problems_by_severity(self, problems: List[str]) -> Dict[str, List[str]]:
        """
        Categoriza problemas por nível de severidade
        
        Args:
            problems: Lista de chaves de problemas
            
        Returns:
            Dict com problemas categorizados por severidade
        """
        categorized = {
            SeverityLevel.CRITICA: [],
            SeverityLevel.ALTA: [],
            SeverityLevel.MEDIA: [],
            SeverityLevel.BAIXA: []
        }
        
        for problem in problems:
            severity = PROBLEM_SEVERITY_MAP.get(problem, SeverityLevel.BAIXA)
            categorized[severity].append(problem)
        
        return categorized

# ==========================================
# CLASSES AUXILIARES
# ==========================================

class ParseResult:
    """
    Classe para encapsular resultados de parsing com metadados
    """
    
    def __init__(self, data: Dict[str, Any], parser_name: str):
        self.data = data
        self.parser_name = parser_name
        self.fields_count = len(data)
        self.has_errors = any(key.endswith('_error') for key in data.keys())
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo do resultado do parsing"""
        return {
            'parser': self.parser_name,
            'fields_extracted': self.fields_count,
            'has_errors': self.has_errors,
            'error_fields': [k for k in self.data.keys() if k.endswith('_error')]
        }

# ==========================================
# UTILITÁRIOS GLOBAIS
# ==========================================

def merge_parse_results(*results: ParseResult) -> Dict[str, Any]:
    """
    Merge múltiplos resultados de parsing
    
    Args:
        *results: Resultados de diferentes parsers
        
    Returns:
        Dict consolidado com todos os dados
    """
    merged_data = {}
    
    for result in results:
        merged_data.update(result.data)
    
    return merged_data

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """
    Valida se campos obrigatórios estão presentes
    
    Args:
        data: Dados parseados
        required_fields: Lista de campos obrigatórios
        
    Returns:
        Lista de campos faltantes
    """
    return [field for field in required_fields if field not in data or data[field] is None]

# ==========================================
# CONSTANTES ÚTEIS
# ==========================================

# Separadores comuns para detecção de brand
BRAND_SEPARATORS = [' | ', ' - ', ' :: ', ' • ', ' » ', ' / ', ' ~ ']

# Limits recomendados para elementos SEO
SEO_LIMITS = {
    'title': {'min': 30, 'max': 60},
    'meta_description': {'min': 120, 'max': 160},
    'h1': {'min': 10, 'max': 70},
    'meta_keywords': {'max': 255}  # Legado
}

# User agents suspeitos para detecção
SUSPICIOUS_USER_AGENTS = [
    'seo', 'crawler', 'spider', 'bot', 'scraper'
]

# Extensions de arquivos não-HTML
NON_HTML_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.zip', '.rar', '.tar', '.gz', '.mp3', '.mp4', '.avi'
]

# ==========================================
# CSS PATTERNS PARA DETECÇÃO DE ELEMENTOS ESCONDIDOS
# ==========================================

# Padrões CSS para detectar elementos escondidos (reutilizável entre parsers)
CSS_HIDING_PATTERNS = [
    'display:none', 'display: none',
    'visibility:hidden', 'visibility: hidden', 
    'opacity:0', 'opacity: 0',
    'color:white', 'color: white', 'color:#fff', 'color: #fff',
    'color:#ffffff', 'color: #ffffff',
    'text-indent:-9999', 'text-indent: -9999',
    'left:-9999', 'left: -9999',
    'position:absolute;left:-9999',
    'font-size:0', 'font-size: 0',
    'height:0', 'height: 0',
    'width:0', 'width: 0'
]

# Classes CSS suspeitas (SEO spam)
SUSPICIOUS_CSS_CLASSES = [
    'hidden', 'hide', 'invisible', 'screen-reader-only',
    'sr-only', 'visuallyhidden', 'visually-hidden',
    'seo-hidden', 'seo-text', 'white-text', 'ghost-text'
]

# ==========================================
# SEVERITY LEVELS PARA PROBLEMAS SEO
# ==========================================

class SeverityLevel:
    """Níveis de severidade para problemas SEO"""
    BAIXA = 'baixa'
    MEDIA = 'média'  
    ALTA = 'alta'
    CRITICA = 'crítica'

# Mapping de problemas para severidade
PROBLEM_SEVERITY_MAP = {
    # Problemas críticos
    'sem_h1': SeverityLevel.CRITICA,
    'multiplos_h1': SeverityLevel.CRITICA,
    'h1_vazio': SeverityLevel.CRITICA,
    'headings_escondidas': SeverityLevel.CRITICA,
    'title_ausente': SeverityLevel.CRITICA,
    'meta_description_ausente': SeverityLevel.CRITICA,
    'thin_content_critico': SeverityLevel.CRITICA,
    'imagens_sem_src': SeverityLevel.CRITICA,
    
    # Problemas altos
    'h1_muito_curto': SeverityLevel.ALTA,
    'h1_muito_longo': SeverityLevel.ALTA,
    'headings_vazias': SeverityLevel.ALTA,
    'estrutura_hierarquica_invalida': SeverityLevel.ALTA,
    'title_muito_longo': SeverityLevel.ALTA,
    'canonical_ausente': SeverityLevel.ALTA,
    'thin_content': SeverityLevel.ALTA,
    'qualidade_conteudo_baixa': SeverityLevel.ALTA,
    'imagens_sem_alt': SeverityLevel.ALTA,
    'imagens_problemas_tecnicos': SeverityLevel.ALTA,
    'links_problemas_seo': SeverityLevel.ALTA,
    
    # Problemas médios
    'sem_h2': SeverityLevel.MEDIA,
    'title_muito_curto': SeverityLevel.MEDIA,
    'meta_description_muito_longa': SeverityLevel.MEDIA,
    'canonical_cross_domain': SeverityLevel.MEDIA,
    'content_muito_longo': SeverityLevel.MEDIA,
    'estrutura_conteudo_ruim': SeverityLevel.MEDIA,
    'imagens_otimizacao': SeverityLevel.MEDIA,
    'links_qualidade_baixa': SeverityLevel.MEDIA,
    'links_estrutura_ruim': SeverityLevel.MEDIA,
    
    # Problemas baixos
    'densidade_headings_baixa': SeverityLevel.BAIXA,
    'meta_keywords_ausente': SeverityLevel.BAIXA,
    'title_sem_brand': SeverityLevel.BAIXA,
}