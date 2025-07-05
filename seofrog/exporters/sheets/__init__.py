"""
seofrog/exporters/sheets/__init__.py
Módulo de sheets especializadas para export Excel - VERSÃO COMPLETA COM REDIRECTS
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
from .links_internos_redirect import LinksInternosRedirectSheet  # 🆕 Aba "Internal"

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
    LinksInternosRedirectSheet, # 12. 🆕 Aba "Internal" (links com redirects)
    AnaliseTecnicaSheet,        # 13. Análise técnica final
]

# Sheets por categoria de importância
CRITICAL_SHEETS = [
    ErrosHttpSheet,             # Status HTTP críticos
    H1H2AusentesSheet,          # H1/H2 ausentes
    ProblemasTitulosSheet,      # Títulos ausentes
    LinksInternosRedirectSheet, # Links internos (redirects)
]

SEO_SHEETS = [
    ProblemasTitulosSheet,      # Títulos
    ProblemasMetaSheet,         # Meta descriptions
    ProblemasHeadingsSheet,     # Estrutura de headings
    H1H2AusentesSheet,          # H1/H2 específicos
    LinksInternosRedirectSheet, # Links internos (equity)
]

TECHNICAL_SHEETS = [
    ProblemasTecnicosSheet,     # Canonical, viewport, etc.
    ProblemasPerformanceSheet,  # Performance
    MixedContentSheet,          # HTTPS/HTTP
    LinksInternosRedirectSheet, # Links internos (redirects técnicos)
    AnaliseTecnicaSheet,        # Análise técnica geral
]

# Export das classes principais
__all__ = [
    'BaseSheet',
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
    'LinksInternosRedirectSheet',  # 🆕 Aba "Internal"
    'AnaliseTecnicaSheet',
    'ALL_SHEETS',
    'CRITICAL_SHEETS',
    'SEO_SHEETS',
    'TECHNICAL_SHEETS'
]