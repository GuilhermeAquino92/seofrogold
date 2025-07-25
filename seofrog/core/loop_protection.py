# seofrog/core/loop_protection.py
"""
Sistema de Proteção Anti-Loop para Crawler
Previne loops infinitos e crawls eternos
"""

import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, urlencode
import threading
from typing import Dict, Set, List, Optional, Tuple
import hashlib

class LoopProtectionSystem:
    """Sistema de proteção contra loops infinitos"""
    
    def __init__(self, max_crawl_time_hours: int = 24):
        self.max_crawl_time = max_crawl_time_hours * 3600  # segundos
        self.start_time = time.time()
        
        # Proteções principais
        self.url_frequency = defaultdict(int)  # Quantas vezes cada URL foi vista
        self.pattern_frequency = defaultdict(int)  # Padrões de URL suspeitos
        self.recent_urls = deque(maxlen=1000)  # URLs recentes para detectar ciclos
        self.redirect_chains = defaultdict(list)  # Cadeias de redirect
        
        # Thresholds de segurança
        self.MAX_URL_FREQUENCY = 3
        self.MAX_PATTERN_FREQUENCY = 50
        self.MAX_REDIRECT_CHAIN = 10
        self.MAX_CYCLE_LENGTH = 10
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Estatísticas
        self.blocked_loops = 0
        self.blocked_patterns = 0
        self.blocked_timeouts = 0
        
        print(f"🛡️ Loop Protection ativo - Timeout: {max_crawl_time_hours}h")
    
    def check_url_safety(self, url: str, depth: int = 0) -> Tuple[bool, str]:
        """
        Verifica se URL é segura para crawl
        Returns: (is_safe, reason_if_blocked)
        """
        with self.lock:
            # 1. Timeout absoluto
            if time.time() - self.start_time > self.max_crawl_time:
                self.blocked_timeouts += 1
                return False, f"Timeout absoluto atingido ({self.max_crawl_time/3600:.1f}h)"
            
            # 2. Frequência de URL específica
            normalized_url = self._normalize_for_loop_detection(url)
            self.url_frequency[normalized_url] += 1
            
            if self.url_frequency[normalized_url] > self.MAX_URL_FREQUENCY:
                self.blocked_loops += 1
                return False, f"URL repetida {self.url_frequency[normalized_url]}x (max: {self.MAX_URL_FREQUENCY})"
            
            # 3. Padrões suspeitos
            pattern = self._extract_url_pattern(url)
            self.pattern_frequency[pattern] += 1
            
            if self.pattern_frequency[pattern] > self.MAX_PATTERN_FREQUENCY:
                self.blocked_patterns += 1
                return False, f"Padrão suspeito detectado: {pattern} ({self.pattern_frequency[pattern]}x)"
            
            # 4. Detecção de ciclos
            if self._detect_cycle(normalized_url):
                self.blocked_loops += 1
                return False, "Ciclo infinito detectado na sequência de URLs"
            
            # 5. Profundidade excessiva (proteção extra)
            if depth > 50:  # Muito profundo
                return False, f"Profundidade excessiva: {depth}"
            
            # URL é segura
            self.recent_urls.append(normalized_url)
            return True, "OK"
    
    def check_redirect_chain(self, original_url: str, redirect_chain: List[Dict]) -> bool:
        """Verifica se cadeia de redirects é suspeita"""
        if len(redirect_chain) > self.MAX_REDIRECT_CHAIN:
            return False
        
        # Verifica se há loops na cadeia de redirects
        urls_in_chain = [original_url]
        for redirect in redirect_chain:
            redirect_url = redirect.get('location', '')
            if redirect_url in urls_in_chain:
                return False  # Loop detectado
            urls_in_chain.append(redirect_url)
        
        return True
    
    def _normalize_for_loop_detection(self, url: str) -> str:
        """Normaliza URL para detecção de loops"""
        try:
            parsed = urlparse(url)
            
            # Remove parâmetros que geram URLs infinitas
            dangerous_params = {
                'page', 'offset', 'start', 'p', 'pg', 'pagenum',
                'session', 'sid', 'token', 'csrf', 'nonce',
                'timestamp', 'time', 'cache', 'v', 'version',
                'random', 'rand', 'r', '_', 'nocache'
            }
            
            if parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=False)
                safe_params = {k: v for k, v in params.items() 
                              if k.lower() not in dangerous_params}
                
                # Ordena parâmetros para normalização
                if safe_params:
                    query = urlencode(sorted(safe_params.items()), doseq=True)
                else:
                    query = ''
            else:
                query = ''
            
            # Remove trailing slash para normalização
            path = parsed.path.rstrip('/')
            
            normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
            if query:
                normalized += f"?{query}"
            
            return normalized.lower()
            
        except Exception:
            return url.lower()
    
    def _extract_url_pattern(self, url: str) -> str:
        """Extrai padrão da URL para detectar geradores automáticos"""
        try:
            parsed = urlparse(url)
            path = parsed.path
            
            # Substitui números por placeholders para detectar padrões
            import re
            
            # Padrões comuns que geram infinitas URLs
            patterns = [
                (r'/\d+/', '/[NUM]/'),  # /123/ -> /[NUM]/
                (r'\d{4}-\d{2}-\d{2}', '[DATE]'),  # 2023-01-01 -> [DATE]
                (r'page-\d+', 'page-[NUM]'),  # page-123 -> page-[NUM]
                (r'id=\d+', 'id=[NUM]'),  # id=123 -> id=[NUM]
                (r'\?p=\d+', '?p=[NUM]'),  # ?p=123 -> ?p=[NUM]
            ]
            
            pattern = path
            for regex, replacement in patterns:
                pattern = re.sub(regex, replacement, pattern)
            
            return f"{parsed.netloc}{pattern}"
            
        except Exception:
            return urlparse(url).netloc
    
    def _detect_cycle(self, url: str) -> bool:
        """Detecta ciclos na sequência recente de URLs"""
        if len(self.recent_urls) < self.MAX_CYCLE_LENGTH:
            return False
        
        # Verifica se a URL atual aparece muito recentemente
        recent_list = list(self.recent_urls)[-self.MAX_CYCLE_LENGTH:]
        
        return recent_list.count(url) >= 2
    
    def add_processing_time_limit(self, url: str, max_seconds: int = 300):
        """Adiciona limite de tempo por URL individual"""
        # Para URLs que demoram muito para processar
        start_time = time.time()
        
        def check_timeout():
            return time.time() - start_time > max_seconds
        
        return check_timeout
    
    def get_protection_stats(self) -> Dict:
        """Estatísticas das proteções ativas"""
        elapsed_hours = (time.time() - self.start_time) / 3600
        
        return {
            'protection_active': True,
            'elapsed_hours': round(elapsed_hours, 2),
            'max_hours': round(self.max_crawl_time / 3600, 1),
            'time_remaining_hours': round((self.max_crawl_time - (time.time() - self.start_time)) / 3600, 1),
            'blocked_loops': self.blocked_loops,
            'blocked_patterns': self.blocked_patterns,
            'blocked_timeouts': self.blocked_timeouts,
            'total_blocked': self.blocked_loops + self.blocked_patterns + self.blocked_timeouts,
            'unique_urls_seen': len(self.url_frequency),
            'unique_patterns_seen': len(self.pattern_frequency),
            'recent_urls_tracked': len(self.recent_urls)
        }
    
    def log_protection_summary(self, logger):
        """Log resumo das proteções"""
        stats = self.get_protection_stats()
        
        logger.info(f"🛡️ Loop Protection Stats:")
        logger.info(f"   ⏱️  Tempo: {stats['elapsed_hours']:.1f}h / {stats['max_hours']}h")
        logger.info(f"   🚫 Bloqueios: {stats['total_blocked']} total")
        logger.info(f"      🔄 Loops: {stats['blocked_loops']}")
        logger.info(f"      📋 Padrões: {stats['blocked_patterns']}")  
        logger.info(f"      ⏰ Timeouts: {stats['blocked_timeouts']}")
        logger.info(f"   📊 URLs únicas: {stats['unique_urls_seen']:,}")


# ==========================================
# INTEGRAÇÃO COM CRAWLER EXISTENTE
# ==========================================

def integrate_loop_protection(crawler_instance, max_hours: int = 12):
    """
    Integra proteção anti-loop em instância existente do crawler
    """
    # Adiciona sistema de proteção
    crawler_instance.loop_protection = LoopProtectionSystem(max_hours)
    
    # Salva método original
    original_crawl_url = crawler_instance.crawl_url
    original_discover_links = getattr(crawler_instance, '_discover_links', None)
    
    def protected_crawl_url(url: str, depth: int):
        """Versão protegida do crawl_url"""
        # Verifica segurança antes de processar
        is_safe, reason = crawler_instance.loop_protection.check_url_safety(url, depth)
        
        if not is_safe:
            crawler_instance.logger.debug(f"🚫 URL bloqueada: {url} - {reason}")
            return None
        
        # Processa normalmente se seguro
        return original_crawl_url(url, depth)
    
    def protected_discover_links(url: str, response, current_depth: int):
        """Versão protegida do _discover_links"""
        if original_discover_links is None:
            return
        
        # Verifica se ainda é seguro descobrir links
        stats = crawler_instance.loop_protection.get_protection_stats()
        
        # Para de descobrir links se já encontrou muitas URLs
        if stats['unique_urls_seen'] > 10000:
            crawler_instance.logger.info("🛑 Limite de descoberta atingido - parando busca de novos links")
            return
        
        return original_discover_links(url, response, current_depth)
    
    # Substitui métodos
    crawler_instance.crawl_url = protected_crawl_url
    if original_discover_links:
        crawler_instance._discover_links = protected_discover_links
    
    crawler_instance.logger.info("🛡️ Loop Protection integrado ao crawler")
    
    return crawler_instance


# ==========================================
# EXEMPLO DE USO
# ==========================================

if __name__ == "__main__":
    # Teste do sistema de proteção
    protection = LoopProtectionSystem(max_crawl_time_hours=1)
    
    # Simula URLs problemáticas
    test_urls = [
        "https://example.com/page/1",
        "https://example.com/page/2", 
        "https://example.com/page/1",  # Repetida
        "https://example.com/page/1",  # Repetida novamente
        "https://example.com/page/1",  # Repetida mais uma vez (deve bloquear)
    ]
    
    for url in test_urls:
        is_safe, reason = protection.check_url_safety(url)
        print(f"URL: {url}")
        print(f"  Segura: {is_safe}")
        print(f"  Razão: {reason}")
        print()
    
    # Mostra estatísticas
    stats = protection.get_protection_stats()
    print("📊 Estatísticas:")
    for key, value in stats.items():
        print(f"  {key}: {value}")