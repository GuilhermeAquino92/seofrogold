"""
Async HTTP Engine for crawler
Motor HTTP assíncrono baseado em aiohttp
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin
import aiohttp
import logging


class AsyncHTTPEngine:
    """
    Engine HTTP assíncrono enterprise com retry inteligente e redirect handling
    Baseado no HTTPEngine sincrónico mas usando aiohttp
    """
    
    def __init__(self, config):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger('AsyncHTTPEngine')
        
        # Performance stats
        self.stats = {
            'requests_made': 0,
            'requests_failed': 0,
            'total_response_time': 0.0,
            'avg_response_time': 0.0,
            'throttle_events': 0,
            'adaptive_delays': 0
        }
        
        # Throttling adaptativo
        self.domain_stats = {}  # stats por domínio
        self.last_request_time = {}  # último request por domínio
        self.adaptive_delay = 0.1  # delay base em segundos
        
        # SSL context desativado para sites com problemas de certificado
        import ssl
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    async def _ensure_session(self):
        """Garante que a sessão aiohttp está criada"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                ssl=self.ssl_context,
                limit=100,
                limit_per_host=30,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            headers = {
                'User-Agent': getattr(self.config, 'user_agent', 'SEOFrog/0.4 AsyncCrawler'),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers,
                trust_env=True
            )
    
    async def fetch_url(self, url: str) -> Tuple[Optional[Any], List[Dict], Dict]:
        """
        Fetch URL com retry inteligente e tracking de redirects
        Returns: (response, redirect_chain, error_info)
        """
        await self._ensure_session()
        
        # Throttling adaptativo por domínio
        await self._apply_adaptive_throttling(url)
        
        redirect_chain = []
        error_info = {}
        
        retry_attempts = getattr(self.config, 'retry_attempts', 3)
        retry_backoff = getattr(self.config, 'retry_backoff', 2)
        max_redirects = getattr(self.config, 'max_redirects', 10)
        
        for attempt in range(retry_attempts):
            start_time = time.time()
            
            try:
                async with self.session.get(url, allow_redirects=False) as response:
                    response_time = time.time() - start_time
                    self._update_stats(response_time, success=True)
                    
                    # Atualiza throttling adaptativo
                    self._update_adaptive_throttling(url, response_time, response.status)
                    
                    # Read content immediately while connection is open
                    try:
                        content = await response.read()
                        text = content.decode('utf-8', errors='replace')
                    except Exception as read_error:
                        self.logger.error(f"Error reading initial response: {read_error}")
                        content = b""
                        text = ""
                    
                    # Handle redirects manualmente para tracking
                    current_response = response
                    current_url = url
                    redirect_count = 0
                    final_content = content
                    final_text = text
                    
                    while (current_response.status in [301, 302, 303, 307, 308] and 
                           redirect_count < max_redirects):
                        
                        redirect_chain.append({
                            'url': str(current_response.url),
                            'status_code': current_response.status,
                            'location': current_response.headers.get('location', '')
                        })
                        
                        if 'location' not in current_response.headers:
                            break
                            
                        next_url = urljoin(str(current_response.url), current_response.headers['location'])
                        
                        try:
                            async with self.session.get(next_url, allow_redirects=False) as next_response:
                                current_response = next_response
                                redirect_count += 1
                                
                                # Read content for final response
                                if next_response.status == 200:
                                    try:
                                        final_content = await next_response.read()
                                        final_text = final_content.decode('utf-8', errors='replace')
                                    except Exception as read_error:
                                        self.logger.error(f"Error reading redirect response: {read_error}")
                                        final_content = b""
                                        final_text = ""
                                else:
                                    final_content = b""
                                    final_text = ""
                        except Exception as e:
                            error_info['redirect_error'] = str(e)
                            break
                    
                    # Create final response object with safe text encoding
                    try:
                        # Garante que o texto é decodificado corretamente
                        if isinstance(final_text, bytes):
                            safe_text = final_text.decode('utf-8', errors='replace')
                        else:
                            safe_text = str(final_text).encode('utf-8', errors='replace').decode('utf-8')
                    except (UnicodeDecodeError, UnicodeEncodeError, AttributeError):
                        safe_text = ""
                    
                    final_response = SimpleResponse(
                        status=current_response.status,
                        url=current_response.url,
                        headers=current_response.headers,
                        text=safe_text,
                        content=final_content
                    )
                    
                    return final_response, redirect_chain, error_info
                    
            except asyncio.TimeoutError:
                error_info['error'] = 'timeout'
                self.logger.warning(f"Timeout em {url} (tentativa {attempt + 1})")
                self._update_stats(time.time() - start_time, success=False)
                
            except aiohttp.ClientConnectorError:
                error_info['error'] = 'connection_error'
                self.logger.warning(f"Erro de conexão em {url} (tentativa {attempt + 1})")
                self._update_stats(time.time() - start_time, success=False)
                
            except Exception as e:
                error_info['error'] = str(e)
                self.logger.warning(f"Erro de request em {url}: {e}")
                self._update_stats(time.time() - start_time, success=False)
                
            # Backoff exponencial
            if attempt < retry_attempts - 1:
                sleep_time = retry_backoff ** attempt
                await asyncio.sleep(sleep_time)
        
        return None, redirect_chain, error_info
    
    async def _apply_adaptive_throttling(self, url: str):
        """Aplica throttling adaptativo baseado no domínio e histórico"""
        from urllib.parse import urlparse
        
        domain = urlparse(url).netloc
        current_time = time.time()
        
        # Inicializa stats do domínio se necessário
        if domain not in self.domain_stats:
            self.domain_stats[domain] = {
                'response_times': [],
                'error_count': 0,
                'total_requests': 0,
                'throttle_level': 1.0
            }
        
        domain_stat = self.domain_stats[domain]
        
        # Calcula delay baseado no último request
        if domain in self.last_request_time:
            time_since_last = current_time - self.last_request_time[domain]
            required_delay = self.adaptive_delay * domain_stat['throttle_level']
            
            if time_since_last < required_delay:
                sleep_time = required_delay - time_since_last
                await asyncio.sleep(sleep_time)
                self.stats['adaptive_delays'] += 1
        
        self.last_request_time[domain] = current_time
    
    def _update_adaptive_throttling(self, url: str, response_time: float, status_code: int):
        """Atualiza parâmetros de throttling baseado na resposta"""
        from urllib.parse import urlparse
        
        domain = urlparse(url).netloc
        if domain not in self.domain_stats:
            return
        
        domain_stat = self.domain_stats[domain]
        domain_stat['total_requests'] += 1
        domain_stat['response_times'].append(response_time)
        
        # Mantém apenas os últimos 50 tempos de resposta
        if len(domain_stat['response_times']) > 50:
            domain_stat['response_times'] = domain_stat['response_times'][-50:]
        
        # Ajusta throttle_level baseado no status code
        if status_code == 429:  # Too Many Requests
            domain_stat['throttle_level'] *= 2.0  # Dobra o delay
            domain_stat['error_count'] += 1
            self.stats['throttle_events'] += 1
            self.logger.warning(f"Rate limit detected for {domain}, increasing throttle to {domain_stat['throttle_level']:.2f}x")
            
        elif status_code == 503:  # Service Unavailable
            domain_stat['throttle_level'] *= 1.5  # Aumenta 50% o delay
            domain_stat['error_count'] += 1
            self.stats['throttle_events'] += 1
            self.logger.warning(f"Service unavailable for {domain}, throttling to {domain_stat['throttle_level']:.2f}x")
            
        elif 200 <= status_code < 300:  # Success
            # Diminui gradualmente o throttle se sucessos consecutivos
            if domain_stat['error_count'] == 0 and domain_stat['total_requests'] % 10 == 0:
                domain_stat['throttle_level'] = max(0.5, domain_stat['throttle_level'] * 0.9)
            domain_stat['error_count'] = max(0, domain_stat['error_count'] - 1)
        else:
            domain_stat['error_count'] += 1
        
        # Calcula EMA (média exponencial) do tempo de resposta
        if len(domain_stat['response_times']) >= 5:
            recent_avg = sum(domain_stat['response_times'][-5:]) / 5
            if recent_avg > 2.0:  # Se média dos últimos 5 requests > 2s
                domain_stat['throttle_level'] = min(5.0, domain_stat['throttle_level'] * 1.2)
                self.logger.debug(f"Slow responses detected for {domain}, adjusting throttle to {domain_stat['throttle_level']:.2f}x")
        
        # Limita throttle_level
        domain_stat['throttle_level'] = max(0.1, min(10.0, domain_stat['throttle_level']))
    
    def _update_stats(self, response_time: float, success: bool):
        """Atualiza estatísticas de performance"""
        self.stats['requests_made'] += 1
        if not success:
            self.stats['requests_failed'] += 1
        
        self.stats['total_response_time'] += response_time
        self.stats['avg_response_time'] = (
            self.stats['total_response_time'] / self.stats['requests_made']
        )
    
    async def close(self):
        """Fecha a sessão HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def get_performance_stats(self) -> Dict:
        """Retorna estatísticas de performance"""
        return {
            'requests_made': self.stats['requests_made'],
            'requests_failed': self.stats['requests_failed'],
            'success_rate': (
                (self.stats['requests_made'] - self.stats['requests_failed']) / 
                self.stats['requests_made']
            ) if self.stats['requests_made'] > 0 else 0,
            'avg_response_time': self.stats['avg_response_time'],
            'total_response_time': self.stats['total_response_time'],
            'throttle_events': self.stats['throttle_events'],
            'adaptive_delays': self.stats['adaptive_delays'],
            'domains_tracked': len(self.domain_stats),
            'domain_throttle_levels': {
                domain: stats['throttle_level'] 
                for domain, stats in self.domain_stats.items()
            }
        }


class SimpleResponse:
    """
    Classe simples para compatibilidade com a interface esperada
    Simula um objeto response com atributos essenciais
    """
    
    def __init__(self, status: int, url: str, headers: Dict, text: str, content: bytes):
        self.status_code = status
        self.url = str(url)
        self.headers = dict(headers)
        
        # Garante que text é uma string UTF-8 válida
        try:
            if isinstance(text, bytes):
                self._text = text.decode('utf-8', errors='replace')
            elif isinstance(text, str):
                # Re-encode/decode para garantir UTF-8 válido
                self._text = text.encode('utf-8', errors='replace').decode('utf-8')
            else:
                self._text = str(text)
        except (UnicodeDecodeError, UnicodeEncodeError, AttributeError):
            self._text = ""
            
        self.content = content if isinstance(content, bytes) else b""
        
        # Detecta encoding do content
        try:
            import chardet
            
            # Primeiro tenta detectar via content-type header
            content_type = headers.get('content-type', '').lower()
            if 'charset=' in content_type:
                declared_encoding = content_type.split('charset=')[1].split(';')[0].strip()
                if declared_encoding and declared_encoding not in ['ascii']:
                    self.encoding = declared_encoding
                else:
                    self.encoding = 'utf-8'
            else:
                # Fallback para detecção automática
                detected = chardet.detect(content[:10000])
                detected_encoding = detected.get('encoding', 'utf-8') if detected else 'utf-8'
                
                # Força UTF-8 se detectar ASCII (muito restritivo)
                if detected_encoding and detected_encoding.lower() == 'ascii':
                    self.encoding = 'utf-8'
                else:
                    self.encoding = detected_encoding or 'utf-8'
                    
        except Exception:
            self.encoding = 'utf-8'
    
    @property
    def text(self):
        """Retorna o texto como atributo"""
        return self._text
    
    def decode(self, encoding=None, errors='strict'):
        """Método decode para compatibilidade com parsers"""
        try:
            # Se encoding não especificado, usa o detectado ou UTF-8
            if not encoding:
                encoding = getattr(self, 'encoding', 'utf-8')
            
            # Se encoding é problemático, usa UTF-8
            if encoding and encoding.lower() in ['ascii', 'us-ascii']:
                encoding = 'utf-8'
                
            return self.content.decode(encoding, errors)
        except (UnicodeDecodeError, LookupError, UnicodeEncodeError, AttributeError):
            # Múltiplos fallbacks
            fallback_encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for fallback_encoding in fallback_encodings:
                try:
                    return self.content.decode(fallback_encoding, 'replace')
                except (UnicodeDecodeError, LookupError):
                    continue
            
            # Último recurso: força UTF-8 com replace
            return self.content.decode('utf-8', errors='replace')
    
    def get_encoding(self):
        """Retorna encoding detectado"""
        return self.encoding
        
    def __getattr__(self, name):
        # Fallback para compatibilidade
        if name == 'status':
            return self.status_code
        elif name == 'apparent_encoding':
            return self.encoding
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")