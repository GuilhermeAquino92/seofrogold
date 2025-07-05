"""
seofrog/utils/redirect_cache.py
Cache inteligente para redirects HTTP - evita múltiplas chamadas para os mesmos links
FEATURE 2: Integra ao LinksParser._resolve_redirect() para performance
"""

import os
import shelve
import time
import hashlib
import threading
from typing import Dict, Tuple, Optional, Any
from urllib.parse import urlparse
from pathlib import Path
import requests

from seofrog.utils.logger import get_logger


class RedirectCache:
    """
    Cache persistente e thread-safe para redirects HTTP
    Usa shelve para armazenamento local e reduce latência em crawls grandes
    """
    
    def __init__(self, 
                 cache_dir: str = "seofrog_cache",
                 cache_filename: str = "redirects_cache.db",
                 ttl_hours: int = 24,
                 max_cache_size: int = 10000,
                 enable_compression: bool = True):
        """
        Inicializa cache de redirects
        
        Args:
            cache_dir: Diretório para armazenar cache
            cache_filename: Nome do arquivo de cache
            ttl_hours: TTL em horas para expirar entradas
            max_cache_size: Número máximo de entradas no cache
            enable_compression: Habilita compressão de URLs
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_path = self.cache_dir / cache_filename
        self.ttl_seconds = ttl_hours * 3600
        self.max_cache_size = max_cache_size
        self.enable_compression = enable_compression
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Estatísticas
        self._hits = 0
        self._misses = 0
        self._saves = 0
        self._errors = 0
        
        self.logger = get_logger('RedirectCache')
        
        # Inicialização e limpeza
        self._cleanup_expired_entries()
        
        self.logger.debug(f"✅ RedirectCache inicializado: {self.cache_path}")
    
    def get_or_fetch(self, url: str, 
                    timeout: int = 3,
                    headers: Optional[Dict[str, str]] = None) -> Tuple[str, int]:
        """
        Obtém redirect do cache ou faz HTTP request
        
        Args:
            url: URL para verificar redirect
            timeout: Timeout da requisição HTTP
            headers: Headers customizados para request
            
        Returns:
            Tuple (resolved_url, status_code)
        """
        # Normaliza URL para uso como chave
        cache_key = self._normalize_url_for_cache(url)
        
        # Tenta obter do cache
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            self._hits += 1
            resolved_url, status_code, _ = cached_result
            self.logger.debug(f"🎯 Cache HIT: {url} → {resolved_url} ({status_code})")
            return resolved_url, status_code
        
        # Cache miss - faz requisição HTTP
        self._misses += 1
        self.logger.debug(f"❌ Cache MISS: {url}")
        
        resolved_url, status_code = self._fetch_redirect(url, timeout, headers)
        
        # Salva no cache
        self._save_to_cache(cache_key, resolved_url, status_code)
        
        return resolved_url, status_code
    
    def _get_from_cache(self, cache_key: str) -> Optional[Tuple[str, int, float]]:
        """
        Obtém entrada do cache se não expirada
        
        Returns:
            Tuple (resolved_url, status_code, timestamp) ou None
        """
        try:
            with self._lock:
                with shelve.open(str(self.cache_path)) as cache:
                    if cache_key in cache:
                        resolved_url, status_code, timestamp = cache[cache_key]
                        
                        # Verifica TTL
                        if time.time() - timestamp < self.ttl_seconds:
                            return resolved_url, status_code, timestamp
                        else:
                            # Entrada expirada - remove
                            del cache[cache_key]
                            self.logger.debug(f"🕒 Cache expirado removido: {cache_key}")
                            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"❌ Erro lendo cache: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, resolved_url: str, status_code: int):
        """
        Salva resultado no cache com timestamp
        """
        try:
            with self._lock:
                with shelve.open(str(self.cache_path)) as cache:
                    # Verifica limite de tamanho
                    if len(cache) >= self.max_cache_size:
                        self._cleanup_oldest_entries(cache)
                    
                    # Salva com timestamp atual
                    cache[cache_key] = (resolved_url, status_code, time.time())
                    self._saves += 1
                    
                    self.logger.debug(f"💾 Saved to cache: {cache_key} → {resolved_url}")
                    
        except Exception as e:
            self._errors += 1
            self.logger.error(f"❌ Erro salvando cache: {e}")
    
    def _fetch_redirect(self, url: str, timeout: int, headers: Optional[Dict[str, str]]) -> Tuple[str, int]:
        """
        Faz requisição HTTP para resolver redirect
        """
        try:
            default_headers = {'User-Agent': 'SEOFrog/0.2 (+https://seofrog.com/bot)'}
            if headers:
                default_headers.update(headers)
            
            response = requests.head(
                url,
                allow_redirects=True,
                timeout=timeout,
                headers=default_headers
            )
            
            return response.url, response.status_code
            
        except requests.RequestException as e:
            self.logger.debug(f"❌ Erro HTTP {url}: {e}")
            return url, 0
    
    def _normalize_url_for_cache(self, url: str) -> str:
        """
        Normaliza URL para usar como chave do cache
        Remove parâmetros de tracking e normaliza formato
        """
        try:
            parsed = urlparse(url)
            
            # Remove parâmetros de tracking comuns
            base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            if self.enable_compression:
                # Usa hash MD5 para chaves muito longas
                if len(base_url) > 200:
                    return hashlib.md5(base_url.encode()).hexdigest()
            
            return base_url.lower()
            
        except Exception:
            # Fallback - usa URL original
            return url.lower()
    
    def _cleanup_expired_entries(self):
        """
        Remove entradas expiradas na inicialização
        """
        try:
            with self._lock:
                with shelve.open(str(self.cache_path)) as cache:
                    current_time = time.time()
                    expired_keys = []
                    
                    for key in cache:
                        try:
                            _, _, timestamp = cache[key]
                            if current_time - timestamp >= self.ttl_seconds:
                                expired_keys.append(key)
                        except (ValueError, TypeError):
                            # Entrada corrompida
                            expired_keys.append(key)
                    
                    # Remove entradas expiradas
                    for key in expired_keys:
                        del cache[key]
                    
                    if expired_keys:
                        self.logger.debug(f"🧹 Removidas {len(expired_keys)} entradas expiradas")
                        
        except Exception as e:
            self.logger.error(f"❌ Erro na limpeza de cache: {e}")
    
    def _cleanup_oldest_entries(self, cache, remove_count: int = None):
        """
        Remove entradas mais antigas quando cache atinge limite
        """
        if remove_count is None:
            remove_count = max(1, len(cache) // 10)  # Remove 10% das entradas
        
        try:
            # Ordena por timestamp (mais antigas primeiro)
            entries_with_time = []
            for key in cache:
                try:
                    _, _, timestamp = cache[key]
                    entries_with_time.append((timestamp, key))
                except (ValueError, TypeError):
                    # Entrada corrompida - marca para remoção
                    entries_with_time.append((0, key))
            
            entries_with_time.sort()
            
            # Remove as mais antigas
            removed = 0
            for _, key in entries_with_time:
                if removed >= remove_count:
                    break
                del cache[key]
                removed += 1
            
            self.logger.debug(f"🧹 Removidas {removed} entradas antigas por limite de tamanho")
            
        except Exception as e:
            self.logger.error(f"❌ Erro removendo entradas antigas: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache
        """
        with self._lock:
            try:
                with shelve.open(str(self.cache_path)) as cache:
                    cache_size = len(cache)
            except:
                cache_size = 0
            
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'cache_hits': self._hits,
                'cache_misses': self._misses,
                'hit_rate_percent': round(hit_rate, 2),
                'cache_size': cache_size,
                'saves': self._saves,
                'errors': self._errors,
                'ttl_hours': self.ttl_seconds / 3600,
                'cache_file': str(self.cache_path)
            }
    
    def clear_cache(self):
        """
        Limpa todo o cache
        """
        try:
            with self._lock:
                if self.cache_path.exists():
                    self.cache_path.unlink()
                
                # Reset estatísticas
                self._hits = 0
                self._misses = 0
                self._saves = 0
                self._errors = 0
                
                self.logger.info("🗑️ Cache de redirects limpo")
                
        except Exception as e:
            self.logger.error(f"❌ Erro limpando cache: {e}")
    
    def invalidate_url(self, url: str):
        """
        Invalida entrada específica do cache
        """
        cache_key = self._normalize_url_for_cache(url)
        
        try:
            with self._lock:
                with shelve.open(str(self.cache_path)) as cache:
                    if cache_key in cache:
                        del cache[cache_key]
                        self.logger.debug(f"🗑️ Cache invalidado: {url}")
                        
        except Exception as e:
            self.logger.error(f"❌ Erro invalidando cache: {e}")


# ==========================================
# FACTORY FUNCTIONS E HELPERS
# ==========================================

def create_redirect_cache(cache_dir: str = "seofrog_cache", 
                         ttl_hours: int = 24) -> RedirectCache:
    """
    Factory function para criar cache com configurações padrão
    """
    return RedirectCache(
        cache_dir=cache_dir,
        ttl_hours=ttl_hours,
        max_cache_size=10000
    )


def create_memory_cache(ttl_hours: int = 1) -> RedirectCache:
    """
    Cria cache em memória para sessões curtas
    """
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="seofrog_cache_")
    
    return RedirectCache(
        cache_dir=temp_dir,
        ttl_hours=ttl_hours,
        max_cache_size=1000
    )


# ==========================================
# INTEGRATION HELPER - LinksParser
# ==========================================

class CachedLinksParserMixin:
    """
    Mixin para integrar cache no LinksParser existente
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Inicializa cache
        self.redirect_cache = create_redirect_cache()
        
        self.logger.info(f"✅ RedirectCache integrado ao LinksParser")
    
    def _resolve_redirect_cached(self, url: str) -> tuple:
        """
        Versão com cache do _resolve_redirect original
        Drop-in replacement para LinksParser._resolve_redirect
        """
        try:
            resolved_url, status_code = self.redirect_cache.get_or_fetch(
                url, 
                timeout=getattr(self, 'redirect_timeout', 3),
                headers={'User-Agent': 'SEOFrog/0.2 (+https://seofrog.com/bot)'}
            )
            
            return resolved_url, status_code
            
        except Exception as e:
            self.logger.debug(f"Erro resolvendo redirect {url}: {e}")
            return url, 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Expõe estatísticas do cache
        """
        return self.redirect_cache.get_stats()
    
    def log_cache_summary(self):
        """
        Log resumo das estatísticas do cache
        """
        stats = self.get_cache_stats()
        
        self.logger.info(
            f"📊 Cache Stats: "
            f"{stats['cache_hits']} hits, "
            f"{stats['cache_misses']} misses, "
            f"{stats['hit_rate_percent']}% hit rate, "
            f"{stats['cache_size']} entries"
        )


# ==========================================
# EXEMPLO DE USO DIRETO
# ==========================================

if __name__ == "__main__":
    # Exemplo de uso direto
    cache = create_redirect_cache()
    
    # Teste com URLs
    test_urls = [
        "http://example.com",
        "https://google.com",
        "https://httpbin.org/redirect/1"
    ]
    
    print("🧪 Testando RedirectCache...")
    
    for url in test_urls:
        resolved, status = cache.get_or_fetch(url)
        print(f"  {url} → {resolved} ({status})")
    
    # Estatísticas
    stats = cache.get_stats()
    print(f"\n📊 Cache Stats: {stats}")