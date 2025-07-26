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
            'avg_response_time': 0.0
        }
        
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
                    
                    # Read content immediately while connection is open
                    try:
                        content = await response.read()
                        text = content.decode('utf-8', errors='ignore')
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
                                        final_text = final_content.decode('utf-8', errors='ignore')
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
                    
                    # Create final response object
                    final_response = SimpleResponse(
                        status=current_response.status,
                        url=current_response.url,
                        headers=current_response.headers,
                        text=final_text,
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
            'total_response_time': self.stats['total_response_time']
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
        self._text = text
        self.content = content
    
    @property
    def text(self):
        """Retorna o texto como atributo"""
        return self._text
        
    def __getattr__(self, name):
        # Fallback para compatibilidade
        if name == 'status':
            return self.status_code
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")