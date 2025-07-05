"""
seofrog/utils/url_normalizer.py
Módulo para normalização padronizada de URLs - FEATURE 1 CRÍTICA
Resolve inconsistências em redirects, comparações e duplicatas
"""

import re
import urllib.parse as urlparse
from typing import Optional, Set, Dict, Any
from urllib.parse import unquote, quote
import idna  # Para domínios internacionais

from seofrog.utils.logger import get_logger

class URLNormalizer:
    """
    Normalizador de URLs enterprise com configurações flexíveis
    Garante consistência em comparações, redirects e deduplicação
    """
    
    def __init__(self, 
                 force_https: bool = True,
                 lowercase_domain: bool = True, 
                 remove_trailing_slash: bool = True,
                 preserve_utm_params: bool = True,
                 remove_default_ports: bool = True,
                 normalize_paths: bool = True):
        """
        Inicializa normalizador com configurações personalizáveis
        
        Args:
            force_https: Converte http:// para https://
            lowercase_domain: Converte domínio para minúsculas
            remove_trailing_slash: Remove / final (exceto root)
            preserve_utm_params: Preserva parâmetros UTM importantes
            remove_default_ports: Remove portas padrão (80, 443)
            normalize_paths: Normaliza paths (/./path → /path)
        """
        self.force_https = force_https
        self.lowercase_domain = lowercase_domain
        self.remove_trailing_slash = remove_trailing_slash
        self.preserve_utm_params = preserve_utm_params
        self.remove_default_ports = remove_default_ports
        self.normalize_paths = normalize_paths
        
        self.logger = get_logger('URLNormalizer')
        
        # Parâmetros importantes a preservar
        self.important_params = {
            # UTM parameters
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            # Social media
            'fbclid', 'gclid', 'msclkid', 'twclid',
            # E-commerce
            'ref', 'affiliate_id', 'partner_id',
            # Tracking
            'source', 'medium', 'campaign'
        } if preserve_utm_params else set()
        
        # Cache para URLs já normalizadas (performance)
        self._cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def normalize(self, url: str, strict: bool = True) -> str:
        """
        Normaliza URL aplicando todas as regras configuradas
        
        Args:
            url: URL para normalizar
            strict: Se True, aplica todas as regras. Se False, mais permissivo
            
        Returns:
            str: URL normalizada
            
        Example:
            >>> normalizer = URLNormalizer()
            >>> normalizer.normalize("HTTP://Site.COM/Page/?ref=abc&utm_source=google")
            'https://site.com/page?ref=abc&utm_source=google'
        """
        if not url or not isinstance(url, str):
            return ""
        
        # Cache lookup para performance
        cache_key = f"{url}|{strict}"
        if cache_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_key]
        
        self._cache_misses += 1
        
        try:
            # Etapa 1: Limpeza inicial
            normalized = self._initial_cleanup(url)
            
            # Etapa 2: Parse da URL
            parsed = urlparse.urlparse(normalized)
            
            # Etapa 3: Normalização por componente
            scheme = self._normalize_scheme(parsed.scheme, strict)
            netloc = self._normalize_netloc(parsed.netloc, strict)
            path = self._normalize_path(parsed.path, strict)
            query = self._normalize_query(parsed.query, strict)
            fragment = self._normalize_fragment(parsed.fragment, strict)
            
            # Etapa 4: Reconstrução
            normalized_url = urlparse.urlunparse((
                scheme, netloc, path, parsed.params, query, fragment
            ))
            
            # Cache resultado
            self._cache[cache_key] = normalized_url
            
            # Log debug se mudou significativamente
            if url != normalized_url:
                self.logger.debug(f"URL normalizada: {url} → {normalized_url}")
            
            return normalized_url
            
        except Exception as e:
            self.logger.warning(f"Erro normalizando URL '{url}': {e}")
            return url  # Retorna original em caso de erro
    
    def _initial_cleanup(self, url: str) -> str:
        """Limpeza inicial da URL"""
        # Remove espaços e caracteres invisíveis
        url = url.strip()
        
        # Remove caracteres de controle
        url = re.sub(r'[\x00-\x1f\x7f]', '', url)
        
        # Adiciona scheme se ausente
        if not url.startswith(('http://', 'https://', '//')):
            url = 'https://' + url
        
        # Corrige // scheme
        if url.startswith('//'):
            url = 'https:' + url
            
        return url
    
    def _normalize_scheme(self, scheme: str, strict: bool) -> str:
        """Normaliza o scheme (protocolo)"""
        scheme = scheme.lower()
        
        if self.force_https and scheme == 'http':
            return 'https'
        
        return scheme or 'https'
    
    def _normalize_netloc(self, netloc: str, strict: bool) -> str:
        """Normaliza netloc (domínio + porta)"""
        if not netloc:
            return netloc
        
        # Parse host e porta
        if ':' in netloc and not netloc.startswith('['):  # IPv6 tem []
            host, port = netloc.rsplit(':', 1)
        else:
            host, port = netloc, None
        
        # Normaliza host
        if self.lowercase_domain:
            host = host.lower()
        
        # Normaliza domínios internacionais (IDN)
        try:
            host = idna.encode(host).decode('ascii')
        except (idna.core.IDNAError, UnicodeError):
            # Se falhar, mantém original
            pass
        
        # Remove portas padrão
        if self.remove_default_ports and port:
            if (port == '80' and self.force_https is False) or \
               (port == '443' and self.force_https is True):
                port = None
        
        # Reconstrói netloc
        if port:
            return f"{host}:{port}"
        else:
            return host
    
    def _normalize_path(self, path: str, strict: bool) -> str:
        """Normaliza o path da URL"""
        if not path:
            return '/'
        
        if self.normalize_paths:
            # Resolve . e .. no path
            path = urlparse.urlunparse(('', '', path, '', '', '')).split('?')[0]
            
            # Remove // duplicados
            path = re.sub(r'/+', '/', path)
            
            # Decode e re-encode para normalizar encoding
            try:
                path = quote(unquote(path), safe='/:@!$&\'()*+,;=')
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass  # Mantém original se der erro
        
        # Remove trailing slash (exceto root)
        if self.remove_trailing_slash and len(path) > 1 and path.endswith('/'):
            path = path.rstrip('/')
        
        return path
    
    def _normalize_query(self, query: str, strict: bool) -> str:
        """Normaliza query parameters"""
        if not query:
            return ''
        
        try:
            # Parse parâmetros
            params = urlparse.parse_qsl(query, keep_blank_values=False)
            
            # Filtra parâmetros importantes se configurado
            if self.important_params:
                filtered_params = [
                    (key, value) for key, value in params 
                    if key.lower() in self.important_params
                ]
            else:
                filtered_params = params
            
            # Remove parâmetros vazios e ordena
            clean_params = [
                (key, value) for key, value in filtered_params 
                if value.strip()
            ]
            clean_params.sort()  # Ordem consistente
            
            # Reconstrói query string
            if clean_params:
                return urlparse.urlencode(clean_params)
            else:
                return ''
                
        except Exception as e:
            self.logger.debug(f"Erro normalizando query '{query}': {e}")
            return query
    
    def _normalize_fragment(self, fragment: str, strict: bool) -> str:
        """Normaliza fragment (#anchor)"""
        # Por padrão, remove fragments para SEO (não afetam server-side)
        return ''
    
    def are_equivalent(self, url1: str, url2: str) -> bool:
        """
        Verifica se duas URLs são equivalentes após normalização
        
        Args:
            url1, url2: URLs para comparar
            
        Returns:
            bool: True se equivalentes
            
        Example:
            >>> normalizer.are_equivalent("http://site.com/page/", "https://SITE.com/page")
            True
        """
        norm1 = self.normalize(url1)
        norm2 = self.normalize(url2)
        return norm1 == norm2
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache para monitoramento
        
        Returns:
            Dict com hits, misses, hit_rate, cache_size
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses, 
            'hit_rate_percent': round(hit_rate, 2),
            'cache_size': len(self._cache),
            'total_normalizations': total
        }
    
    def clear_cache(self):
        """Limpa o cache de URLs normalizadas"""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self.logger.debug("Cache de URLs limpo")


# ==========================================
# FACTORY FUNCTIONS E PRESETS
# ==========================================

def create_seo_normalizer() -> URLNormalizer:
    """
    Cria normalizador otimizado para SEO
    Configuração para detectar duplicatas e redirects
    """
    return URLNormalizer(
        force_https=True,
        lowercase_domain=True,
        remove_trailing_slash=True,
        preserve_utm_params=True,
        remove_default_ports=True,
        normalize_paths=True
    )

def create_strict_normalizer() -> URLNormalizer:
    """
    Cria normalizador estrito para comparação exata
    Remove tudo exceto estrutura essencial
    """
    return URLNormalizer(
        force_https=True,
        lowercase_domain=True,
        remove_trailing_slash=True,
        preserve_utm_params=False,  # Remove todos os params
        remove_default_ports=True,
        normalize_paths=True
    )

def create_permissive_normalizer() -> URLNormalizer:
    """
    Cria normalizador permissivo que preserva mais informação
    Útil quando tracking é importante
    """
    return URLNormalizer(
        force_https=False,  # Preserva scheme original
        lowercase_domain=True,
        remove_trailing_slash=False,  # Preserva trailing slash
        preserve_utm_params=True,
        remove_default_ports=False,  # Preserva portas
        normalize_paths=True
    )

# ==========================================
# FUNÇÕES DE CONVENIÊNCIA
# ==========================================

# Instância global padrão (thread-safe)
_default_normalizer = None

def normalize_url(url: str, strict: bool = False) -> str:
    """
    Função de conveniência para normalização rápida
    
    Args:
        url: URL para normalizar
        strict: Se True, usa normalizador estrito
        
    Returns:
        str: URL normalizada
        
    Example:
        >>> from seofrog.utils.url_normalizer import normalize_url
        >>> normalize_url("HTTP://Site.com/page/?ref=abc")
        'https://site.com/page?ref=abc'
    """
    global _default_normalizer
    
    if _default_normalizer is None:
        _default_normalizer = create_strict_normalizer() if strict else create_seo_normalizer()
    
    return _default_normalizer.normalize(url, strict=strict)

def urls_are_equivalent(url1: str, url2: str) -> bool:
    """
    Função de conveniência para comparação de URLs
    
    Example:
        >>> urls_are_equivalent("http://site.com/page/", "https://SITE.com/page")
        True
    """
    global _default_normalizer
    
    if _default_normalizer is None:
        _default_normalizer = create_seo_normalizer()
    
    return _default_normalizer.are_equivalent(url1, url2)

# ==========================================
# TESTES INTEGRADOS
# ==========================================

def run_normalization_tests():
    """
    Executa testes básicos de normalização
    Útil para verificar se module está funcionando
    """
    normalizer = create_seo_normalizer()
    
    test_cases = [
        ("HTTP://SITE.COM/PAGE/", "https://site.com/page"),
        ("https://site.com:443/page", "https://site.com/page"),
        ("http://site.com/page?utm_source=google&junk=123", "https://site.com/page?utm_source=google"),
        ("https://site.com/page/../other", "https://site.com/other"),
        ("https://site.com//page///", "https://site.com/page"),
    ]
    
    print("🧪 Executando testes de normalização:")
    for i, (input_url, expected) in enumerate(test_cases, 1):
        result = normalizer.normalize(input_url)
        status = "✅" if result == expected else "❌"
        print(f"  {i}. {status} {input_url} → {result}")
        if result != expected:
            print(f"      Esperado: {expected}")
    
    # Mostra estatísticas do cache
    stats = normalizer.get_cache_stats()
    print(f"\n📊 Cache stats: {stats}")

if __name__ == "__main__":
    run_normalization_tests()