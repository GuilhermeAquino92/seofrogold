"""
Redirect Classifier
Classificador de redirects SEO-aware baseado no crawler_old
"""

from urllib.parse import urlparse
from typing import List, Dict, Optional


def classify_redirect_type(original_url: str, final_url: str) -> str:
    """
    Classifica o tipo de redirect para análise SEO
    Baseado no método _classify_redirect_type do crawler_old
    
    Args:
        original_url: URL original solicitada
        final_url: URL final após redirects
        
    Returns:
        String descrevendo o tipo de redirect
    """
    try:
        parsed_orig = urlparse(original_url)
        parsed_final = urlparse(final_url)
        
        # HTTP -> HTTPS (comum e bom para SEO)
        if parsed_orig.scheme == 'http' and parsed_final.scheme == 'https':
            if parsed_orig.netloc == parsed_final.netloc and parsed_orig.path == parsed_final.path:
                return 'HTTP_to_HTTPS'
        
        # Mudança de domínio
        if parsed_orig.netloc != parsed_final.netloc:
            # Subdomain changes
            if (parsed_orig.netloc.endswith(f".{parsed_final.netloc}") or 
                parsed_final.netloc.endswith(f".{parsed_orig.netloc}")):
                return 'Subdomain_Change'
            else:
                return 'Domain_Change'
        
        # Mudança de path
        if parsed_orig.path.lower() != parsed_final.path.lower():
            # Capitalização ou mudança de estrutura
            if parsed_orig.path.lower() == parsed_final.path.lower():
                return 'Capitalization_Change'
            else:
                return 'Path_Change'
        
        # Mudança apenas de query string
        if parsed_orig.query != parsed_final.query:
            return 'Query_String_Change'
        
        # Trailing slash
        if parsed_orig.path.rstrip('/') == parsed_final.path.rstrip('/'):
            return 'Trailing_Slash_Change'
        
        # WWW changes
        if (parsed_orig.netloc.startswith('www.') and not parsed_final.netloc.startswith('www.')) or \
           (not parsed_orig.netloc.startswith('www.') and parsed_final.netloc.startswith('www.')):
            return 'WWW_Change'
        
        return 'Other'
        
    except Exception:
        return 'Unknown'


def analyze_redirect_chain(original_url: str, redirect_chain: List[Dict], final_url: str) -> Dict:
    """
    Analisa uma cadeia completa de redirects
    
    Args:
        original_url: URL original
        redirect_chain: Lista de redirects intermediários
        final_url: URL final
        
    Returns:
        Dict com análise completa dos redirects
    """
    analysis = {
        'total_redirects': len(redirect_chain),
        'redirect_types': [],
        'status_codes': [],
        'domains_involved': set(),
        'has_www_redirect': False,
        'has_https_redirect': False,
        'has_trailing_slash_redirect': False,
        'final_classification': 'No_Redirect'
    }
    
    if not redirect_chain:
        return analysis
    
    # Analisa cada redirect na cadeia
    current_url = original_url
    
    for redirect in redirect_chain:
        next_url = redirect.get('location', '')
        status_code = redirect.get('status_code', 0)
        
        if next_url:
            redirect_type = classify_redirect_type(current_url, next_url)
            analysis['redirect_types'].append(redirect_type)
            analysis['status_codes'].append(status_code)
            
            # Adiciona domínios envolvidos
            analysis['domains_involved'].add(urlparse(current_url).netloc)
            analysis['domains_involved'].add(urlparse(next_url).netloc)
            
            # Detecta tipos específicos
            if redirect_type == 'HTTP_to_HTTPS':
                analysis['has_https_redirect'] = True
            elif redirect_type == 'WWW_Change':
                analysis['has_www_redirect'] = True
            elif redirect_type == 'Trailing_Slash_Change':
                analysis['has_trailing_slash_redirect'] = True
            
            current_url = next_url
    
    # Classificação final baseada no redirect original -> final
    if final_url:
        analysis['final_classification'] = classify_redirect_type(original_url, final_url)
        analysis['domains_involved'].add(urlparse(final_url).netloc)
    
    # Converte set para list para serialização
    analysis['domains_involved'] = list(analysis['domains_involved'])
    
    return analysis


def get_seo_redirect_recommendations(redirect_analysis: Dict) -> List[str]:
    """
    Gera recomendações SEO baseadas na análise de redirects
    
    Args:
        redirect_analysis: Resultado de analyze_redirect_chain()
        
    Returns:
        Lista de recomendações SEO
    """
    recommendations = []
    
    if redirect_analysis['total_redirects'] == 0:
        return recommendations
    
    # Muitos redirects
    if redirect_analysis['total_redirects'] > 3:
        recommendations.append(
            f"⚠️ Cadeia de redirects muito longa ({redirect_analysis['total_redirects']} redirects). "
            "Considere reduzir para máximo 3 redirects."
        )
    
    # Múltiplos domínios
    if len(redirect_analysis['domains_involved']) > 2:
        recommendations.append(
            "⚠️ Redirects envolvem múltiplos domínios. "
            "Verifique se isso é necessário para a estratégia SEO."
        )
    
    # Status codes problemáticos
    status_codes = redirect_analysis['status_codes']
    if 302 in status_codes and redirect_analysis['total_redirects'] > 1:
        recommendations.append(
            "⚠️ Redirects 302 (temporários) em cadeia. "
            "Considere usar 301 (permanente) para melhor SEO."
        )
    
    # Redirects positivos
    if redirect_analysis['has_https_redirect']:
        recommendations.append("✅ Redirect HTTP->HTTPS implementado corretamente.")
    
    if redirect_analysis['final_classification'] == 'HTTP_to_HTTPS':
        recommendations.append("✅ Redirect para HTTPS é benéfico para SEO.")
    
    # Redirects desnecessários
    if redirect_analysis['final_classification'] == 'Trailing_Slash_Change':
        recommendations.append(
            "💡 Considere configurar o servidor para evitar redirects de trailing slash."
        )
    
    if redirect_analysis['final_classification'] == 'WWW_Change':
        recommendations.append(
            "💡 Considere usar canonical URLs consistentes (com ou sem www)."
        )
    
    return recommendations


def is_redirect_seo_friendly(redirect_analysis: Dict) -> bool:
    """
    Determina se uma cadeia de redirects é SEO-friendly
    
    Args:
        redirect_analysis: Resultado de analyze_redirect_chain()
        
    Returns:
        True se é SEO-friendly, False caso contrário
    """
    # Sem redirects é sempre OK
    if redirect_analysis['total_redirects'] == 0:
        return True
    
    # Muito redirects é problemático
    if redirect_analysis['total_redirects'] > 5:
        return False
    
    # Múltiplos domínios podem ser problemáticos
    if len(redirect_analysis['domains_involved']) > 3:
        return False
    
    # Redirects 302 em cadeia são problemáticos
    status_codes = redirect_analysis['status_codes']
    if status_codes.count(302) > 2:
        return False
    
    # HTTP->HTTPS é sempre bom
    if redirect_analysis['final_classification'] == 'HTTP_to_HTTPS':
        return True
    
    # Mudanças de domínio precisam atenção
    if redirect_analysis['final_classification'] == 'Domain_Change':
        return redirect_analysis['total_redirects'] <= 2
    
    # Outros tipos são OK se não muitos redirects
    return redirect_analysis['total_redirects'] <= 3