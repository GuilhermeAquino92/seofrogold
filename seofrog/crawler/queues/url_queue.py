"""
URL Queue Management
Gerenciador inteligente de fila de URLs
"""

import asyncio
from typing import Dict, Optional, Set, Tuple
import logging


class URLQueue:
    """
    📋 Gerenciador inteligente de fila de URLs
    Controla depth, duplicatas e priorização
    """
    
    def __init__(self, max_depth: int = 6, max_urls: int = 20000):
        self.queue = asyncio.Queue()
        self.seen_urls: Set[str] = set()
        self.processed_urls: Set[str] = set()
        self.max_depth = max_depth
        self.max_urls = max_urls
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger('URLQueue')
        
        # Stats
        self.urls_added = 0
        self.urls_processed = 0
        self.urls_skipped_depth = 0
        self.urls_skipped_duplicate = 0
        self.urls_by_depth: Dict[int, int] = {}
    
    async def add_url(self, url: str, depth: int = 0) -> bool:
        """
        Adiciona URL à fila com verificações
        Returns: True se adicionada, False se rejeitada
        """
        async with self.lock:
            # Normaliza URL
            normalized_url = self._normalize_url(url)
            
            # Verificações
            if depth > self.max_depth:
                self.urls_skipped_depth += 1
                self.logger.debug(f"URL skipped (depth {depth} > {self.max_depth}): {url}")
                return False
            
            if normalized_url in self.seen_urls:
                self.urls_skipped_duplicate += 1
                self.logger.debug(f"URL skipped (duplicate): {url}")
                return False
            
            if self.urls_added >= self.max_urls:
                self.logger.debug(f"URL skipped (max URLs {self.max_urls} reached): {url}")
                return False
            
            # Adiciona à fila
            self.seen_urls.add(normalized_url)
            await self.queue.put((normalized_url, depth))
            self.urls_added += 1
            
            # Track URLs by depth
            self.urls_by_depth[depth] = self.urls_by_depth.get(depth, 0) + 1
            
            self.logger.debug(f"URL added (depth {depth}): {url}")
            return True
    
    async def get_url(self) -> Optional[Tuple[str, int]]:
        """Pega próxima URL da fila"""
        try:
            url, depth = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            async with self.lock:
                self.processed_urls.add(url)
                self.urls_processed += 1
            self.logger.debug(f"URL retrieved (depth {depth}): {url}")
            return url, depth
        except asyncio.TimeoutError:
            return None
    
    def _normalize_url(self, url: str) -> str:
        """Normalização avançada de URL baseada no crawler_old"""
        try:
            from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, unquote
            
            # Decode percent encoding
            url = unquote(url)
            parsed = urlparse(url.lower().strip())
            
            # Remove fragment
            parsed = parsed._replace(fragment='')
            
            # Normaliza path
            path = parsed.path.rstrip('/')
            if not path or path == '':
                path = '/'
            
            # Remove trailing slashes exceto root
            if path != '/' and path.endswith('/'):
                path = path[:-1]
            
            # Normaliza query parameters
            if parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=False)
                
                # Remove parâmetros de tracking comuns
                tracking_params = {
                    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                    'gclid', 'fbclid', 'msclkid', 'twclid', '_ga', '_gl', 'ref', 'source',
                    'campaign_id', 'ad_id', 'adset_id', 'campaign_name'
                }
                
                filtered_params = {k: v for k, v in params.items() 
                                 if k.lower() not in tracking_params}
                
                # Ordena parâmetros para consistência
                if filtered_params:
                    sorted_params = sorted(filtered_params.items())
                    query = urlencode(sorted_params, doseq=True)
                else:
                    query = ''
            else:
                query = ''
            
            # Força HTTPS se não especificado
            scheme = parsed.scheme or 'https'
            
            # Reconstrói URL normalizada
            normalized = urlunparse((scheme, parsed.netloc, path, '', query, ''))
            
            return normalized
            
        except Exception as e:
            self.logger.debug(f"Erro normalizando URL {url}: {e}")
            return url.lower().strip()
    
    async def is_empty(self) -> bool:
        """Verifica se fila está vazia"""
        return self.queue.empty()
    
    async def size(self) -> int:
        """Retorna tamanho atual da fila"""
        return self.queue.qsize()
    
    def is_processed(self, url: str) -> bool:
        """Verifica se URL já foi processada"""
        normalized_url = self._normalize_url(url)
        return normalized_url in self.processed_urls
    
    def is_seen(self, url: str) -> bool:
        """Verifica se URL já foi vista"""
        normalized_url = self._normalize_url(url)
        return normalized_url in self.seen_urls
    
    def get_stats(self) -> Dict:
        """Estatísticas da fila"""
        return {
            'queue_size': self.queue.qsize(),
            'urls_added': self.urls_added,
            'urls_processed': self.urls_processed,
            'urls_seen': len(self.seen_urls),
            'skipped_depth': self.urls_skipped_depth,
            'skipped_duplicate': self.urls_skipped_duplicate,
            'max_depth': self.max_depth,
            'max_urls': self.max_urls,
            'urls_by_depth': dict(self.urls_by_depth)
        }
    
    async def clear(self):
        """Limpa a fila e reinicia contadores"""
        async with self.lock:
            # Limpa a fila
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            # Reinicia sets e contadores
            self.seen_urls.clear()
            self.processed_urls.clear()
            self.urls_added = 0
            self.urls_processed = 0
            self.urls_skipped_depth = 0
            self.urls_skipped_duplicate = 0
            self.urls_by_depth.clear()
            
        self.logger.info("URL queue cleared")
    
    def __len__(self) -> int:
        """Tamanho da fila (compatibilidade)"""
        return self.queue.qsize()
    
    def __bool__(self) -> bool:
        """True se fila não está vazia"""
        return not self.queue.empty()