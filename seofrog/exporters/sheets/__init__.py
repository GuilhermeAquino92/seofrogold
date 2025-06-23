"""
seofrog/exporters/sheets/__init__.py
Módulo de sheets especializadas para export Excel - VERSÃO COMPLETA
"""

from .base_sheet import BaseSheet

# Import todas as sheets especializadas
from .dados_completos import DadosCompletosSheet
from .resumo_executivo import ResumoExecutivoSheet
from .erros_http import ErrosHttpSheet
from .problemas_titulos import ProblemasTitulosSheet
from .problemas_meta import ProblemasMetaSheet
from .problemas_headings import ProblemasHeadingsSheet
from .h1_h2_ausentes import H1H2AusentesSheet
from .problemas_imagens import ProblemasImagensSheet
from .problemas_tecnicos import ProblemasTecnicosSheet
from .problemas_performance import ProblemasPerformanceSheet
from .mixed_content import MixedContentSheet
from .analise_tecnica import AnaliseTecnicaSheet

# Lista de todas as sheets disponíveis (na ordem correta)
ALL_SHEETS = [
    DadosCompletosSheet,        # 1. Dados principais
    ResumoExecutivoSheet,       # 2. KPIs e estatísticas
    ErrosHttpSheet,             # 3. Status HTTP != 200
    ProblemasTitulosSheet,      # 4. Títulos problemáticos  
    ProblemasMetaSheet,         # 5. Meta descriptions problemáticas
    ProblemasHeadingsSheet,     # 6. Problemas de headings gerais
    H1H2AusentesSheet,          # 7. H1/H2 ausentes (crítico)
    ProblemasImagensSheet,      # 8. Imagens sem ALT/SRC
    ProblemasTecnicosSheet,     # 9. Canonical, viewport, charset
    ProblemasPerformanceSheet,  # 10. Páginas lentas/pesadas
    MixedContentSheet,          # 11. Problemas HTTPS/HTTP
    AnaliseTecnicaSheet,        # 12. Análise técnica final
]

# Sheets por categoria de importância
CRITICAL_SHEETS = [
    ErrosHttpSheet,             # Status HTTP críticos
    H1H2AusentesSheet,          # H1/H2 ausentes
    ProblemasTitulosSheet,      # Títulos ausentes
]

SEO_SHEETS = [
    ProblemasTitulosSheet,      # Títulos
    ProblemasMetaSheet,         # Meta descriptions
    ProblemasHeadingsSheet,     # Estrutura de headings
    H1H2AusentesSheet,          # H1/H2 específicos
]

TECHNICAL_SHEETS = [
    ProblemasTecnicosSheet,     # Canonical, viewport, etc.
    ProblemasPerformanceSheet,  # Velocidade e tamanho
    MixedContentSheet,          # Segurança HTTPS
    AnaliseTecnicaSheet,        # Análise final
]

CONTENT_SHEETS = [
    ProblemasImagensSheet,      # Problemas de imagens
    ProblemasHeadingsSheet,     # Estrutura de conteúdo
]

UX_SHEETS = [
    ProblemasPerformanceSheet,  # Performance impacta UX
    ErrosHttpSheet,             # Erros HTTP quebram UX
    ProblemasTecnicosSheet,     # Viewport impacta mobile
]

# Função auxiliar para obter sheets por categoria
def get_sheets_by_category(category: str) -> list:
    """
    Retorna lista de sheets por categoria
    
    Args:
        category: 'critical', 'seo', 'technical', 'content', 'ux', 'all'
        
    Returns:
        Lista de classes de sheets
    """
    categories = {
        'critical': CRITICAL_SHEETS,
        'seo': SEO_SHEETS,
        'technical': TECHNICAL_SHEETS,
        'content': CONTENT_SHEETS,
        'ux': UX_SHEETS,
        'all': ALL_SHEETS
    }
    
    return categories.get(category.lower(), ALL_SHEETS)

# Função para verificar se todas as sheets estão disponíveis
def check_sheets_integrity() -> dict:
    """
    Verifica se todas as sheets podem ser instanciadas
    
    Returns:
        Dict com status de cada sheet
    """
    results = {}
    
    for sheet_class in ALL_SHEETS:
        try:
            sheet_instance = sheet_class()
            sheet_name = sheet_instance.get_sheet_name()
            results[sheet_class.__name__] = {
                'status': 'OK',
                'sheet_name': sheet_name,
                'error': None
            }
        except Exception as e:
            results[sheet_class.__name__] = {
                'status': 'ERROR',
                'sheet_name': sheet_class.__name__,
                'error': str(e)
            }
    
    return results

__all__ = [
    # Classe base
    'BaseSheet',
    
    # Sheets individuais
    'DadosCompletosSheet',
    'ResumoExecutivoSheet',
    'ErrosHttpSheet',
    'ProblemasTitulosSheet',
    'ProblemasMetaSheet',
    'ProblemasHeadingsSheet',
    'H1H2AusentesSheet',
    'ProblemasImagensSheet',
    'ProblemasTecnicosSheet',
    'ProblemasPerformanceSheet',
    'MixedContentSheet',
    'AnaliseTecnicaSheet',
    
    # Listas de sheets por categoria
    'ALL_SHEETS',
    'CRITICAL_SHEETS',
    'SEO_SHEETS',
    'TECHNICAL_SHEETS',
    'CONTENT_SHEETS',
    'UX_SHEETS',
    
    # Funções auxiliares
    'get_sheets_by_category',
    'check_sheets_integrity'
]