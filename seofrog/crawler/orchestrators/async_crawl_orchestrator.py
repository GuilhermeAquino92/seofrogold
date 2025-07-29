"""
Async Crawl Orchestrator
Orquestrador principal do crawling enterprise
"""

import asyncio
import time
from typing import Dict
from datetime import datetime
import logging

from ..engines.async_http_engine import AsyncHTTPEngine
from ..queues.url_queue import URLQueue
from ..savers.result_saver import ResultSaver
from ..parsers.modular_page_parser import ModularPageParser
from ..models.crawl_result import CrawlResult
from ...core.sitemap_handler import SitemapHandler
from ..handlers.async_robots_handler import AsyncRobotsHandler
from ..utils.redirect_classifier import classify_redirect_type, analyze_redirect_chain, get_seo_redirect_recommendations


class AsyncCrawlOrchestrator:
    """
    [TARGET] Orquestrador principal do crawling enterprise
    Coordena: Fetching + Parsing + Saving + Queue Management
    """
    
    def __init__(self, config, output_dir: str = "./crawl_output", 
                 max_workers: int = 20, max_depth: int = 6, max_urls: int = 20000):
        
        # Core components
        self.http_engine = AsyncHTTPEngine(config)
        self.url_queue = URLQueue(max_depth=max_depth, max_urls=max_urls)
        self.result_saver = ResultSaver(output_dir)
        self.page_parser = ModularPageParser()
        self.robots_handler = AsyncRobotsHandler(getattr(config, 'user_agent', 'SEOFrog/0.4 AsyncCrawler'))
        
        # Configuration
        self.max_workers = max_workers
        self.running = False
        self.start_time = None
        self.logger = logging.getLogger('AsyncCrawlOrchestrator')
        
        # Stats
        self.stats = {
            'pages_crawled': 0,
            'pages_failed': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def crawl_site(self, start_url: str) -> Dict:
        """
        [START] Inicia crawling completo do site
        Returns: Estatísticas finais do crawl
        """
        self.logger.info(f"[START] Iniciando crawl de {start_url}")
        self.start_time = time.time()
        self.stats['start_time'] = datetime.now().isoformat()
        self.running = True
        
        # Descoberta e adição de URLs do sitemap antes da URL inicial
        await self._discover_and_add_sitemap_urls(start_url)
        
        # Adiciona URL inicial
        await self.url_queue.add_url(start_url, depth=0)
        
        # Cria workers
        workers = []
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            workers.append(worker)
        
        # Aguarda conclusão
        try:
            await asyncio.gather(*workers, return_exceptions=True)
        except KeyboardInterrupt:
            self.logger.info("[STOP] Crawl interrompido pelo usuário")
        finally:
            await self._shutdown()
        
        return self.get_final_stats()
    
    async def _worker(self, worker_name: str):
        """
        [WORKER] Worker individual para processamento de URLs
        Ciclo: fetch -> parse -> save -> extract links -> repeat
        """
        consecutive_empty = 0
        while self.running:
            try:
                # Pega próxima URL
                url_data = await self.url_queue.get_url()
                if url_data is None:
                    consecutive_empty += 1
                    # Give more time for dynamic URL discovery
                    if consecutive_empty > 10:  # Increased patience
                        if await self.url_queue.is_empty():
                            # Final check - wait longer for potential new URLs
                            await asyncio.sleep(2.0)
                            if await self.url_queue.is_empty():
                                self.logger.debug(f"{worker_name}: Queue consistently empty after extended wait, stopping")
                                break
                        # Progressive backoff but with longer max wait
                        await asyncio.sleep(min(consecutive_empty * 0.3, 3.0))
                    else:
                        # Shorter initial delays to be more responsive
                        await asyncio.sleep(0.1)
                    continue
                else:
                    consecutive_empty = 0  # Reset contador
                
                url, depth = url_data
                self.logger.debug(f"{worker_name}: Processing {url} (depth {depth})")
                
                # Verifica robots.txt antes do fetch
                if not await self.robots_handler.can_fetch(url, self.http_engine.session):
                    self.logger.debug(f"{worker_name}: URL blocked by robots.txt: {url}")
                    continue
                
                # Fetch da página
                start_time = time.time()
                response, redirect_chain, error_info = await self.http_engine.fetch_url(url)
                load_time = time.time() - start_time
                
                if response:
                    # Parse da resposta usando parsers modulares
                    result = await self.page_parser.parse_response_async(response, url, depth)
                    result.load_time = load_time
                    
                    # Analisa redirects se houver
                    if redirect_chain:
                        redirect_analysis = analyze_redirect_chain(url, redirect_chain, str(response.url))
                        result.redirect_info = {
                            'type': classify_redirect_type(url, str(response.url)),
                            'chain_analysis': redirect_analysis,
                            'seo_recommendations': get_seo_redirect_recommendations(redirect_analysis),
                            'redirect_count': len(redirect_chain)
                        }
                        self.logger.debug(f"Redirect analysis for {url}: {result.redirect_info['type']}")
                    
                    # Salva resultado
                    await self.result_saver.add_result(result)
                    
                    # Extrai links para próximo nível
                    if depth < self.url_queue.max_depth:
                        await self._extract_and_queue_links(response, url, depth + 1)
                    
                    self.stats['pages_crawled'] += 1
                    
                    if self.stats['pages_crawled'] % 50 == 0:
                        self.logger.info(f"[PROGRESS] Progresso: {self.stats['pages_crawled']} páginas crawled")
                
                else:
                    # Falha no fetch
                    error_result = CrawlResult(
                        url=url,
                        status_code=0,
                        final_url=url,
                        depth=depth,
                        crawl_timestamp=datetime.now().isoformat(),
                        errors=[error_info.get('error', 'Unknown error')]
                    )
                    error_result.load_time = load_time
                    await self.result_saver.add_result(error_result)
                    self.stats['pages_failed'] += 1
                    self.logger.warning(f"{worker_name}: Failed to fetch {url}: {error_info}")
            
            except Exception as e:
                self.logger.error(f"[ERROR] Erro no worker {worker_name}: {e}")
                continue
    
    async def _extract_and_queue_links(self, response, base_url: str, next_depth: int):
        """Extrai links da página e adiciona à fila"""
        # Permite extração de links de páginas 3xx (redirects) e 200
        if response.status_code not in [200, 301, 302, 303, 307, 308] or not self._is_html_response(response):
            return
        
        try:
            import re
            from urllib.parse import urljoin, urlparse
            
            # Use the final URL (after redirects) to determine the domain
            final_url = str(response.url)
            base_domain = urlparse(final_url).netloc
            
            # Parse HTML usando BeautifulSoup para extração mais robusta
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'lxml')
            links = soup.find_all('a', href=True)
            
            links_added = 0
            for link in links:
                href = link.get('href', '').strip()
                
                # Skip certain types of links
                if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                    continue
                
                # Resolve URL relativa
                try:
                    absolute_url = urljoin(final_url, href)
                    parsed_url = urlparse(absolute_url)
                    
                    # Filtra apenas links do mesmo domínio
                    if parsed_url.netloc == base_domain:
                        # Verifica se é uma URL crawlable (sem extensões problemáticas)
                        if self._is_crawlable_url(absolute_url):
                            if await self.url_queue.add_url(absolute_url, next_depth):
                                links_added += 1
                            
                except Exception as e:
                    self.logger.debug(f"Error processing link {href}: {e}")
                    continue
            
            self.logger.debug(f"Added {links_added} links from {base_url} at depth {next_depth}")
        
        except Exception as e:
            self.logger.warning(f"[WARNING] Erro extraindo links de {base_url}: {e}")
    
    def _is_html_response(self, response) -> bool:
        """Verifica se a resposta é HTML"""
        # Try both lowercase and title case for compatibility
        content_type = response.headers.get('content-type', '') or response.headers.get('Content-Type', '')
        content_type = content_type.lower()
        return 'text/html' in content_type
    
    def _is_crawlable_url(self, url: str) -> bool:
        """Verifica se URL pode ser crawleada (baseado no crawler antigo)"""
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Extensões a ignorar (comuns em crawlers)
            ignore_extensions = {
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.zip', '.rar', '.tar', '.gz', '.exe', '.dmg', '.pkg',
                '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico',
                '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mp3', '.wav', '.ogg',
                '.css', '.js', '.xml', '.rss', '.json', '.txt'
            }
            
            # Verifica extensão
            for ext in ignore_extensions:
                if path.endswith(ext):
                    return False
            
            # URLs com query parameters problemáticas
            query = parsed.query.lower()
            if any(param in query for param in ['download=', 'file=', 'attachment=']):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _discover_and_add_sitemap_urls(self, start_url: str):
        """Descobre e adiciona URLs do sitemap ao queue"""
        try:
            from urllib.parse import urlparse
            domain = urlparse(start_url).netloc
            
            # Cria handler de sitemap
            sitemap_handler = SitemapHandler(domain, self.http_engine)
            
            # Descobre sitemaps
            sitemap_urls = sitemap_handler.discover_sitemaps()
            
            if not sitemap_urls:
                self.logger.debug(f"Nenhum sitemap encontrado para {domain}")
                return
            
            # Processa cada sitemap
            total_sitemap_urls = 0
            for sitemap_url in sitemap_urls:  # Remove limite de sitemaps
                try:
                    urls = sitemap_handler.parse_sitemap(sitemap_url)
                    
                    # Adiciona URLs do sitemap com depth 0 (prioridade alta)
                    for url in urls:  # Remove limite de URLs por sitemap
                        if await self.url_queue.add_url(url, depth=0):
                            total_sitemap_urls += 1
                    
                    self.logger.info(f"Adicionadas {len(urls)} URLs do sitemap {sitemap_url}")
                    
                except Exception as e:
                    self.logger.warning(f"Erro processando sitemap {sitemap_url}: {e}")
                    continue
            
            if total_sitemap_urls > 0:
                self.logger.info(f"Total de {total_sitemap_urls} URLs adicionadas dos sitemaps")
            
        except Exception as e:
            self.logger.warning(f"Erro na descoberta de sitemaps: {e}")
            # Não falha o crawl se sitemaps falharem
    
    async def _shutdown(self):
        """Shutdown graceful do crawler"""
        self.running = False
        self.stats['end_time'] = datetime.now().isoformat()
        
        self.logger.info("[SHUTDOWN] Iniciando shutdown...")
        
        # Finaliza salvamento
        await self.result_saver.finalize()
        
        # Fecha HTTP engine
        await self.http_engine.close()
        
        self.logger.info("[FINISHED] Crawl finalizado")
    
    def get_final_stats(self) -> Dict:
        """Estatísticas consolidadas finais"""
        total_time = time.time() - self.start_time if self.start_time else 0
        
        final_stats = {
            'crawl_summary': {
                'total_pages': self.stats['pages_crawled'],
                'failed_pages': self.stats['pages_failed'],
                'success_rate': (self.stats['pages_crawled'] / 
                               (self.stats['pages_crawled'] + self.stats['pages_failed']))
                               if (self.stats['pages_crawled'] + self.stats['pages_failed']) > 0 else 0,
                'total_time_seconds': total_time,
                'pages_per_second': self.stats['pages_crawled'] / total_time if total_time > 0 else 0
            },
            'queue_stats': self.url_queue.get_stats(),
            'http_engine_stats': self.http_engine.get_performance_stats(),
            'saver_stats': self.result_saver.get_stats(),
            'parser_stats': self.page_parser.get_stats(),
            'timestamps': {
                'start': self.stats['start_time'],
                'end': self.stats['end_time']
            }
        }
        
        return final_stats
    
    async def pause_crawl(self):
        """Pausa o crawl (para implementação futura)"""
        self.running = False
        self.logger.info("[PAUSE] Crawl pausado")
    
    async def resume_crawl(self):
        """Resume o crawl (para implementação futura)"""
        self.running = True
        self.logger.info("[RESUME] Crawl resumido")
    
    def get_current_stats(self) -> Dict:
        """Estatísticas em tempo real durante o crawl"""
        current_time = time.time()
        elapsed_time = current_time - self.start_time if self.start_time else 0
        
        return {
            'pages_crawled': self.stats['pages_crawled'],
            'pages_failed': self.stats['pages_failed'],
            'elapsed_time': elapsed_time,
            'pages_per_second': self.stats['pages_crawled'] / elapsed_time if elapsed_time > 0 else 0,
            'queue_size': self.url_queue.queue.qsize(),
            'is_running': self.running
        }