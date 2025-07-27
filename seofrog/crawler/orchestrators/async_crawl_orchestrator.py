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
from ..parsers.simple_page_parser import SimplePageParser
from ..models.crawl_result import CrawlResult


class AsyncCrawlOrchestrator:
    """
    [TARGET] Orquestrador principal do crawling enterprise
    Coordena: Fetching + Parsing + Saving + Queue Management
    """
    
    def __init__(self, config, output_dir: str = "./crawl_output", 
                 max_workers: int = 10, max_depth: int = 3, max_urls: int = 1000):
        
        # Core components
        self.http_engine = AsyncHTTPEngine(config)
        self.url_queue = URLQueue(max_depth=max_depth, max_urls=max_urls)
        self.result_saver = ResultSaver(output_dir)
        self.page_parser = SimplePageParser()
        
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
        while self.running:
            try:
                # Pega próxima URL
                url_data = await self.url_queue.get_url()
                if url_data is None:
                    # Timeout ou fila vazia
                    if await self.url_queue.is_empty():
                        self.logger.debug(f"{worker_name}: Queue empty, stopping")
                        break
                    continue
                
                url, depth = url_data
                self.logger.debug(f"{worker_name}: Processing {url} (depth {depth})")
                
                # Fetch da página
                start_time = time.time()
                response, redirect_chain, error_info = await self.http_engine.fetch_url(url)
                load_time = time.time() - start_time
                
                if response:
                    # Parse da resposta
                    result = self.page_parser.parse_response(response, url, depth)
                    result.load_time = load_time
                    
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
        if response.status_code != 200 or not self._is_html_response(response):
            return
        
        try:
            import re
            from urllib.parse import urljoin, urlparse
            
            # Use the final URL (after redirects) to determine the domain
            final_url = str(response.url)
            base_domain = urlparse(final_url).netloc
            
            # Extrai todos os links usando regex
            href_pattern = r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>'
            hrefs = re.findall(href_pattern, response.text, re.IGNORECASE)
            
            links_added = 0
            for href in hrefs:
                href = href.strip()
                
                # Skip certain types of links
                if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                    continue
                
                # Resolve URL relativa
                try:
                    absolute_url = urljoin(final_url, href)
                    
                    # Filtra apenas links do mesmo domínio
                    if urlparse(absolute_url).netloc == base_domain:
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