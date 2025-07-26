"""
Redirect Classifier for SEO Analysis
Classificador de Redirects para Análise SEO
"""

from enum import Enum
from urllib.parse import urlparse
from typing import Dict, List, Any
from dataclasses import dataclass, field


class RedirectType(Enum):
    """Tipos de redirect para classificação SEO"""
    HTTP_TO_HTTPS = "HTTP_to_HTTPS"
    HTTPS_TO_HTTP = "HTTPS_to_HTTP"  # Problema grave!
    WWW_TO_NONWWW = "WWW_to_NonWWW"
    NONWWW_TO_WWW = "NonWWW_to_WWW"
    PATH_REDIRECT = "Path_Redirect"
    DOMAIN_REDIRECT = "Domain_Redirect"
    SELF_REDIRECT = "Self_Redirect"  # Redundante


@dataclass
class RedirectInfo:
    """Informações completas sobre um redirect"""
    original_url: str
    final_url: str
    status_code: int
    redirect_type: RedirectType
    chain_length: int
    response_time: float = 0.0
    is_redirect: bool = field(default=False)
    has_issues: bool = field(default=False)
    seo_impact: str = field(default="LOW")
    
    def __post_init__(self):
        self.is_redirect = self.status_code in (301, 302, 303, 307, 308)
        self._analyze_seo_impact()
    
    def _analyze_seo_impact(self):
        """Analisa impacto SEO do redirect"""
        if not self.is_redirect:
            self.seo_impact = "NONE"
            return
            
        if self.redirect_type == RedirectType.HTTPS_TO_HTTP:
            self.seo_impact = "CRITICAL"
            self.has_issues = True
        elif self.redirect_type == RedirectType.SELF_REDIRECT:
            self.seo_impact = "HIGH"  # Redundante
            self.has_issues = True
        elif self.chain_length > 3:
            self.seo_impact = "HIGH"  # Chain muito longa
            self.has_issues = True
        elif self.redirect_type in [RedirectType.HTTP_TO_HTTPS, RedirectType.WWW_TO_NONWWW]:
            self.seo_impact = "LOW"  # Redirects comuns e bons
        else:
            self.seo_impact = "MEDIUM"


class RedirectClassifier:
    """
    🔄 Classificador de Redirects para Análise SEO
    
    Analisa e classifica redirects HTTP para identificar:
    - Tipos de redirect (HTTP->HTTPS, WWW, domínio, path)
    - Impacto SEO (LOW, MEDIUM, HIGH, CRITICAL)
    - Chains de redirect e suas implicações
    """
    
    def __init__(self):
        self.stats = {
            'redirects_classified': 0,
            'by_type': {},
            'by_impact': {}
        }
    
    def classify_redirect(self, original_url: str, final_url: str, status_chain: List[int]) -> Dict[str, Any]:
        """
        Classifica um redirect e retorna informações detalhadas
        
        Args:
            original_url: URL original da requisição
            final_url: URL final após todos os redirects
            status_chain: Lista de status codes da chain de redirect
            
        Returns:
            Dict com informações de classificação do redirect
        """
        # Determina status code principal
        main_status = status_chain[0] if status_chain else 200
        
        # Classifica tipo de redirect
        redirect_type = self._classify_redirect_type(original_url, final_url)
        
        # Cria RedirectInfo
        redirect_info = RedirectInfo(
            original_url=original_url,
            final_url=final_url,
            status_code=main_status,
            redirect_type=redirect_type,
            chain_length=len(status_chain)
        )
        
        # Atualiza estatísticas
        self._update_stats(redirect_info)
        
        # Retorna como dict para compatibilidade
        return {
            'type': redirect_type.value,
            'is_clean': redirect_info.seo_impact in ['LOW', 'NONE'],
            'is_external': redirect_type == RedirectType.DOMAIN_REDIRECT,
            'chain_length': redirect_info.chain_length,
            'seo_impact': redirect_info.seo_impact,
            'has_issues': redirect_info.has_issues,
            'status_codes': status_chain,
            'original_url': original_url,
            'final_url': final_url
        }
    
    def _classify_redirect_type(self, original_url: str, final_url: str) -> RedirectType:
        """
        Classifica o tipo específico de redirect
        """
        if original_url == final_url:
            return RedirectType.SELF_REDIRECT
        
        orig_parsed = urlparse(original_url)
        final_parsed = urlparse(final_url)
        
        # HTTP -> HTTPS (bom)
        if orig_parsed.scheme == 'http' and final_parsed.scheme == 'https':
            return RedirectType.HTTP_TO_HTTPS
        
        # HTTPS -> HTTP (muito ruim!)
        if orig_parsed.scheme == 'https' and final_parsed.scheme == 'http':
            return RedirectType.HTTPS_TO_HTTP
        
        # Redirects de WWW
        orig_has_www = orig_parsed.netloc.startswith('www.')
        final_has_www = final_parsed.netloc.startswith('www.')
        
        if orig_has_www and not final_has_www:
            return RedirectType.WWW_TO_NONWWW
        elif not orig_has_www and final_has_www:
            return RedirectType.NONWWW_TO_WWW
        
        # Domínios diferentes
        if orig_parsed.netloc != final_parsed.netloc:
            return RedirectType.DOMAIN_REDIRECT
        
        # Mesmo domínio, paths diferentes
        return RedirectType.PATH_REDIRECT
        
    def _update_stats(self, redirect_info: RedirectInfo):
        """Atualiza estatísticas internas"""
        self.stats['redirects_classified'] += 1
        
        # Por tipo
        type_name = redirect_info.redirect_type.value
        self.stats['by_type'][type_name] = self.stats['by_type'].get(type_name, 0) + 1
        
        # Por impacto
        impact = redirect_info.seo_impact
        self.stats['by_impact'][impact] = self.stats['by_impact'].get(impact, 0) + 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de classificação"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reseta estatísticas"""
        self.stats = {
            'redirects_classified': 0,
            'by_type': {},
            'by_impact': {}
        }