"""
seofrog/services/redirect_service.py
Serviço Unificado para Gerenciar Status Codes e Redirects
🔄 Substitui múltiplas implementações dispersas por uma única fonte de verdade
"""

import threading
import time
from typing import Dict, Tuple, Optional, Any, List
from urllib.parse import urlparse
from pathlib import Path
import requests
from dataclasses import dataclass, field
from enum import Enum

from seofrog.utils.logger import get_logger


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
    response_time: float
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


class RedirectService:
    """
    🔄 Serviço Unificado para Status Codes e Redirects
    
    BENEFÍCIOS:
    - ✅ Única fonte de verdade para status codes
    - ✅ Cache compartilhado entre parsers  
    - ✅ Logging centralizado e estatísticas
    - ✅ Fácil para testes unitários
    - ✅ Análise SEO automática de redirects
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Implementa Singleton pattern"""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, 
                 cache_size: int = 10000,
                 ttl_hours: int = 24,
                 timeout: int = 3,
                 user_agent: str = "SEOFrog/0.2 (+https://seofrog.com/bot)"):
        
        # Evita re-inicialização do singleton
        if hasattr(self, '_initialized'):
            return
            
        self.cache_size = cache_size
        self.ttl_seconds = ttl_hours * 3600
        self.timeout = timeout
        self.user_agent = user_agent
        
        # Cache in-memory thread-safe
        self._cache: Dict[str, Tuple[RedirectInfo, float]] = {}
        self._cache_lock = threading.RLock()
        
        # Estatísticas
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'requests_made': 0,
            'errors': 0,
            'redirects_found': 0,
            'problematic_redirects': 0
        }
        
        self.logger = get_logger('RedirectService')
        self._initialized = True
        
        self.logger.info(f"🔄 RedirectService inicializado (cache: {cache_size}, TTL: {ttl_hours}h)")
    
    def get_status_info(self, url: str, force_refresh: bool = False) -> RedirectInfo:
        """
        🎯 MÉTODO PRINCIPAL - Obtém informações completas de status/redirect
        
        Args:
            url: URL para verificar
            force_refresh: Ignora cache e força nova requisição
            
        Returns:
            RedirectInfo: Informações completas sobre o status/redirect
        """
        cache_key = self._normalize_url(url)
        
        # Verifica cache primeiro (se não forçando refresh)
        if not force_refresh:
            cached_info = self._get_from_cache(cache_key)
            if cached_info:
                self.stats['cache_hits'] += 1
                self.logger.debug(f"🎯 Cache HIT: {url}")
                return cached_info
        
        # Cache miss - faz requisição
        self.stats['cache_misses'] += 1
        self.logger.debug(f"❌ Cache MISS: {url}")
        
        redirect_info = self._fetch_redirect_info(url)
        
        # Salva no cache
        self._save_to_cache(cache_key, redirect_info)
        
        # Atualiza estatísticas
        if redirect_info.is_redirect:
            self.stats['redirects_found'] += 1
            if redirect_info.has_issues:
                self.stats['problematic_redirects'] += 1
        
        return redirect_info
    
    def get_status_code(self, url: str) -> int:
        """
        🔍 Método simplificado para obter apenas status code
        Compatibilidade com código existente
        """
        info = self.get_status_info(url)
        return info.status_code
    
    def get_final_url(self, url: str) -> str:
        """
        🔗 Método simplificado para obter URL final após redirects
        """
        info = self.get_status_info(url)
        return info.final_url
    
    def check_multiple_urls(self, urls: List[str], max_workers: int = 10) -> Dict[str, RedirectInfo]:
        """
        📊 Verifica múltiplas URLs em paralelo
        Útil para LinksParser processar muitos links
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submete todos os jobs
            future_to_url = {
                executor.submit(self.get_status_info, url): url 
                for url in urls
            }
            
            # Coleta resultados
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    results[url] = future.result()
                except Exception as e:
                    self.logger.error(f"Erro verificando {url}: {e}")
                    self.stats['errors'] += 1
                    # Cria RedirectInfo de erro
                    results[url] = RedirectInfo(
                        original_url=url,
                        final_url=url,
                        status_code=0,
                        redirect_type=RedirectType.SELF_REDIRECT,  # Placeholder
                        chain_length=0,
                        response_time=0.0
                    )
        
        return results
    
    def _fetch_redirect_info(self, url: str) -> RedirectInfo:
        """
        🌐 Faz requisição HTTP e analisa redirects
        """
        start_time = time.time()
        
        try:
            self.stats['requests_made'] += 1
            
            # Faz HEAD request primeiro (mais eficiente)
            headers = {'User-Agent': self.user_agent}
            response = requests.head(
                url, 
                allow_redirects=True, 
                timeout=self.timeout,
                headers=headers
            )
            
            # Se HEAD falhou com 405/403, tenta GET
            if response.status_code in (405, 403, 429):
                response = requests.get(
                    url, 
                    allow_redirects=True, 
                    timeout=self.timeout,
                    headers=headers,
                    stream=True  # Não baixa o body completo
                )
                response.close()
            
            response_time = time.time() - start_time
            
            # Analisa tipo de redirect
            redirect_type = self._classify_redirect(url, response.url)
            
            # Calcula chain length (aproximado)
            chain_length = len(response.history)
            
            return RedirectInfo(
                original_url=url,
                final_url=response.url,
                status_code=response.status_code,
                redirect_type=redirect_type,
                chain_length=chain_length,
                response_time=response_time
            )
            
        except requests.exceptions.Timeout:
            self.logger.warning(f"⏰ Timeout verificando {url}")
            self.stats['errors'] += 1
            return self._create_error_info(url, 0, "Timeout")
            
        except requests.exceptions.ConnectionError:
            self.logger.warning(f"🔌 Connection error verificando {url}")
            self.stats['errors'] += 1
            return self._create_error_info(url, 0, "Connection Error")
            
        except Exception as e:
            self.logger.error(f"❌ Erro verificando {url}: {e}")
            self.stats['errors'] += 1
            return self._create_error_info(url, 0, f"Error: {type(e).__name__}")
    
    def _classify_redirect(self, original_url: str, final_url: str) -> RedirectType:
        """
        🔍 Classifica tipo de redirect para análise SEO
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
    
    def _create_error_info(self, url: str, status_code: int, error_type: str) -> RedirectInfo:
        """Cria RedirectInfo para casos de erro"""
        return RedirectInfo(
            original_url=url,
            final_url=url,
            status_code=status_code,
            redirect_type=RedirectType.SELF_REDIRECT,  # Placeholder
            chain_length=0,
            response_time=0.0
        )
    
    def _normalize_url(self, url: str) -> str:
        """Normaliza URL para uso como chave de cache"""
        return url.lower().strip().rstrip('/')
    
    def _get_from_cache(self, cache_key: str) -> Optional[RedirectInfo]:
        """Obtém entrada do cache se não expirada"""
        with self._cache_lock:
            if cache_key in self._cache:
                redirect_info, timestamp = self._cache[cache_key]
                
                # Verifica TTL
                if time.time() - timestamp < self.ttl_seconds:
                    return redirect_info
                else:
                    # Remove entrada expirada
                    del self._cache[cache_key]
        
        return None
    
    def _save_to_cache(self, cache_key: str, redirect_info: RedirectInfo):
        """Salva no cache com timestamp"""
        with self._cache_lock:
            # Limpa cache se muito grande
            if len(self._cache) >= self.cache_size:
                self._cleanup_cache()
            
            self._cache[cache_key] = (redirect_info, time.time())
    
    def _cleanup_cache(self):
        """Remove 25% das entradas mais antigas"""
        if not self._cache:
            return
            
        # Ordena por timestamp e remove as mais antigas
        sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
        remove_count = len(sorted_items) // 4  # Remove 25%
        
        for i in range(remove_count):
            cache_key = sorted_items[i][0]
            del self._cache[cache_key]
        
        self.logger.debug(f"🧹 Cache cleanup: removidas {remove_count} entradas antigas")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        📊 Retorna estatísticas detalhadas do serviço
        """
        total_requests = self.stats['cache_hits'] + self.stats['cache_misses']
        hit_rate = (self.stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            'cache_size': len(self._cache),
            'hit_rate_percent': round(hit_rate, 1),
            'total_requests': total_requests
        }
    
    def log_statistics(self):
        """📝 Log estatísticas formatadas"""
        stats = self.get_statistics()
        
        self.logger.info(
            f"📊 RedirectService Stats: "
            f"{stats['cache_hits']} hits, "
            f"{stats['cache_misses']} misses, "
            f"{stats['hit_rate_percent']}% hit rate, "
            f"{stats['redirects_found']} redirects found"
        )
        
        if stats['problematic_redirects'] > 0:
            self.logger.warning(
                f"⚠️ Problematic redirects found: {stats['problematic_redirects']}"
            )
    
    def flush_cache(self):
        """🧹 Limpa todo o cache"""
        with self._cache_lock:
            self._cache.clear()
        self.logger.info("🧹 Cache totalmente limpo")
    
    def reset_statistics(self):
        """📊 Reseta estatísticas"""
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'requests_made': 0,
            'errors': 0,
            'redirects_found': 0,
            'problematic_redirects': 0
        }
        self.logger.info("📊 Estatísticas resetadas")


# ==========================================
# FACTORY FUNCTION E INTEGRAÇÃO
# ==========================================

def get_redirect_service(**kwargs) -> RedirectService:
    """
    🏭 Factory function para obter instância do RedirectService
    Garante singleton pattern
    """
    return RedirectService(**kwargs)


# ==========================================
# EXEMPLO DE USO
# ==========================================

if __name__ == "__main__":
    # Testa o RedirectService
    service = get_redirect_service()
    
    test_urls = [
        "http://google.com",
        "https://httpbin.org/redirect/2",
        "https://httpbin.org/status/404"
    ]
    
    print("🧪 Testando RedirectService...")
    
    for url in test_urls:
        info = service.get_status_info(url)
        print(f"  {url}")
        print(f"    → {info.final_url} ({info.status_code})")
        print(f"    → Type: {info.redirect_type.value}")
        print(f"    → SEO Impact: {info.seo_impact}")
        if info.has_issues:
            print(f"    → ⚠️ Issues detected!")
        print()
    
    # Estatísticas
    service.log_statistics()