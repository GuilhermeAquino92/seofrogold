"""
SEOFrog AsyncCrawlOrchestrator v0.3 - Enterprise Complete Crawler
🚀 Orquestrador completo: AsyncHTTPEngine + Parsing + Saving + Queue Management
"""

import asyncio
import time
import json
import sqlite3
from pathlib import Path
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set, Any, Callable
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import logging



@dataclass
class CrawlResult:
    """Resultado estruturado de um crawl individual"""
    url: str
    status_code: int
    final_url: str
    title: str = ""
    meta_description: str = ""
    h1_count: int = 0
    h2_count: int = 0
    internal_links: int = 0
    external_links: int = 0
    images_count: int = 0
    page_size: int = 0
    load_time: float = 0.0
    depth: int = 0
    crawl_timestamp: str = ""
    redirect_info: Dict = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.redirect_info is None:
            self.redirect_info = {}


class ResultSaver:
    """
    💾 Sistema de salvamento incremental com batching automático
    Previne perda de dados e otimiza I/O
    """
    
    def __init__(self, output_dir: str, batch_size: int = 100, format: str = "csv"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.batch_size = batch_size
        self.format = format
        self.buffer: List[CrawlResult] = []
        self.total_saved = 0
        self.lock = asyncio.Lock()
        
        # Arquivo principal
        self.main_file = self.output_dir / f"crawl_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self._init_csv_file()
    
    def _init_csv_file(self):
        """Inicializa arquivo CSV com headers"""
        if self.format == "csv":
            import csv
            with open(self.main_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Headers baseados em CrawlResult
                headers = [
                    'url', 'status_code', 'final_url', 'title', 'meta_description',
                    'h1_count', 'h2_count', 'internal_links', 'external_links',
                    'images_count', 'page_size', 'load_time', 'depth',
                    'crawl_timestamp', 'redirect_type', 'is_clean_redirect',
                    'is_external_redirect', 'errors'
                ]
                writer.writerow(headers)
    
    async def add_result(self, result: CrawlResult):
        """Adiciona resultado ao buffer e salva se necessário"""
        async with self.lock:
            self.buffer.append(result)
            
            if len(self.buffer) >= self.batch_size:
                await self._flush_buffer()
    
    async def _flush_buffer(self):
        """Salva buffer atual em disco"""
        if not self.buffer:
            return
        
        if self.format == "csv":
            await self._save_csv_batch()
        elif self.format == "json":
            await self._save_json_batch()
        
        self.total_saved += len(self.buffer)
        self.buffer.clear()
    
    async def _save_csv_batch(self):
        """Salva batch em CSV"""
        import csv
        
        # Executa I/O em thread pool para não bloquear event loop
        loop = asyncio.get_event_loop()
        
        def write_batch():
            with open(self.main_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for result in self.buffer:
                    row = [
                        result.url, result.status_code, result.final_url,
                        result.title, result.meta_description,
                        result.h1_count, result.h2_count,
                        result.internal_links, result.external_links,
                        result.images_count, result.page_size, result.load_time,
                        result.depth, result.crawl_timestamp,
                        result.redirect_info.get('type', ''),
                        result.redirect_info.get('is_clean', False),
                        result.redirect_info.get('is_external', False),
                        '; '.join(result.errors) if result.errors else ''
                    ]
                    writer.writerow(row)
        
        await loop.run_in_executor(None, write_batch)
    
    async def finalize(self):
        """Força salvamento final do buffer"""
        async with self.lock:
            if self.buffer:
                await self._flush_buffer()
    
    def get_stats(self) -> Dict:
        """Estatísticas do saver"""
        return {
            'total_saved': self.total_saved,
            'buffer_size': len(self.buffer),
            'output_file': str(self.main_file)
        }


class URLQueue:
    """
    📋 Gerenciador inteligente de fila de URLs
    Controla depth, duplicatas e priorização
    """
    
    def __init__(self, max_depth: int = 3, max_urls: int = 1000):
        self.queue = asyncio.Queue()
        self.seen_urls: Set[str] = set()
        self.processed_urls: Set[str] = set()
        self.max_depth = max_depth
        self.max_urls = max_urls
        self.lock = asyncio.Lock()
        
        # Stats
        self.urls_added = 0
        self.urls_processed = 0
        self.urls_skipped_depth = 0
        self.urls_skipped_duplicate = 0
    
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
                return False
            
            if normalized_url in self.seen_urls:
                self.urls_skipped_duplicate += 1
                return False
            
            if self.urls_added >= self.max_urls:
                return False
            
            # Adiciona à fila
            self.seen_urls.add(normalized_url)
            await self.queue.put((normalized_url, depth))
            self.urls_added += 1
            return True
    
    async def get_url(self) -> Optional[tuple]:
        """Pega próxima URL da fila"""
        try:
            url, depth = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            async with self.lock:
                self.processed_urls.add(url)
                self.urls_processed += 1
            return url, depth
        except asyncio.TimeoutError:
            return None
    
    def _normalize_url(self, url: str) -> str:
        """Normalização básica de URL"""
        # Remove fragment
        if '#' in url:
            url = url.split('#')[0]
        # Remove trailing slash duplicado
        if url.endswith('//'):
            url = url[:-1]
        return url.lower()
    
    async def is_empty(self) -> bool:
        """Verifica se fila está vazia"""
        return self.queue.empty()
    
    def get_stats(self) -> Dict:
        """Estatísticas da fila"""
        return {
            'queue_size': self.queue.qsize(),
            'urls_added': self.urls_added,
            'urls_processed': self.urls_processed,
            'urls_seen': len(self.seen_urls),
            'skipped_depth': self.urls_skipped_depth,
            'skipped_duplicate': self.urls_skipped_duplicate
        }


class SimplePageParser:
    """
    📄 Parser simples para extração básica de dados da página
    Substituto temporário até integração com parsers modulares existentes
    """
    
    def __init__(self):
        self.redirect_classifier = RedirectClassifier()
    
    def parse_response(self, response, original_url: str, depth: int) -> CrawlResult:
        """
        Parseia response HTTP para CrawlResult
        """
        from bs4 import BeautifulSoup
        
        result = CrawlResult(
            url=original_url,
            status_code=response.status_code,
            final_url=str(response.url),
            depth=depth,
            crawl_timestamp=datetime.now().isoformat()
        )
        
        # Parse do conteúdo HTML
        if response.status_code == 200 and 'text/html' in response.headers.get('content-type', ''):
            try:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Title
                title_tag = soup.find('title')
                result.title = title_tag.get_text().strip() if title_tag else ""
                
                # Meta description
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                result.meta_description = meta_desc.get('content', '') if meta_desc else ""
                
                # Headings
                result.h1_count = len(soup.find_all('h1'))
                result.h2_count = len(soup.find_all('h2'))
                
                # Links
                links = soup.find_all('a', href=True)
                domain = urlparse(original_url).netloc
                
                internal_links = 0
                external_links = 0
                
                for link in links:
                    href = link['href']
                    if href.startswith('http'):
                        if urlparse(href).netloc == domain:
                            internal_links += 1
                        else:
                            external_links += 1
                    elif href.startswith('/'):
                        internal_links += 1
                
                result.internal_links = internal_links
                result.external_links = external_links
                
                # Images
                result.images_count = len(soup.find_all('img'))
                
                # Page size
                result.page_size = len(response.content)
                
            except Exception as e:
                result.errors.append(f"Parse error: {str(e)}")
        
        # Classificação de redirect
        if original_url != str(response.url):
            # Simula chain de status codes (simplificado)
            status_chain = [response.status_code] if response.status_code != 200 else [301]
            result.redirect_info = self.redirect_classifier.classify_redirect(
                original_url, str(response.url), status_chain
            )
        
        return result


class AsyncCrawlOrchestrator:
    """
    🎯 Orquestrador principal do crawling enterprise
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
        
        # Stats
        self.stats = {
            'pages_crawled': 0,
            'pages_failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Logging
        self.logger = logging.getLogger('AsyncCrawlOrchestrator')
    
    async def crawl_site(self, start_url: str) -> Dict:
        """
        🚀 Inicia crawling completo do site
        Returns: Estatísticas finais do crawl
        """
        self.logger.info(f"🚀 Iniciando crawl de {start_url}")
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
            self.logger.info("⏹️  Crawl interrompido pelo usuário")
        finally:
            await self._shutdown()
        
        return self.get_final_stats()
    
    async def _worker(self, worker_name: str):
        """
        👷 Worker individual para processamento de URLs
        Ciclo: fetch → parse → save → extract links → repeat
        """
        while self.running:
            try:
                # Pega próxima URL
                url_data = await self.url_queue.get_url()
                if url_data is None:
                    # Timeout ou fila vazia
                    if await self.url_queue.is_empty():
                        break
                    continue
                
                url, depth = url_data
                
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
                        self.logger.info(f"📊 Progresso: {self.stats['pages_crawled']} páginas crawled")
                
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
                    await self.result_saver.add_result(error_result)
                    self.stats['pages_failed'] += 1
            
            except Exception as e:
                self.logger.error(f"❌ Erro no worker {worker_name}: {e}")
                continue
    
    async def _extract_and_queue_links(self, response, base_url: str, next_depth: int):
        """Extrai links da página e adiciona à fila"""
        if response.status_code != 200 or 'text/html' not in response.headers.get('content-type', ''):
            return
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            base_domain = urlparse(base_url).netloc
            
            # Extrai todos os links
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Resolve URL relativa
                absolute_url = urljoin(base_url, href)
                
                # Filtra apenas links do mesmo domínio
                if urlparse(absolute_url).netloc == base_domain:
                    await self.url_queue.add_url(absolute_url, next_depth)
        
        except Exception as e:
            self.logger.warning(f"⚠️  Erro extraindo links de {base_url}: {e}")
    
    async def _shutdown(self):
        """Shutdown graceful do crawler"""
        self.running = False
        self.stats['end_time'] = datetime.now().isoformat()
        
        # Finaliza salvamento
        await self.result_saver.finalize()
        
        # Fecha HTTP engine
        await self.http_engine.close()
        
        self.logger.info("🏁 Crawl finalizado")
    
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
            'timestamps': {
                'start': self.stats['start_time'],
                'end': self.stats['end_time']
            }
        }
        
        return final_stats


# 🧪 TESTE COMPLETO DO ORCHESTRATOR
async def test_orchestrator():
    """Teste completo do sistema de crawling"""
    from types import SimpleNamespace
    
    # Config básica
    config = SimpleNamespace(
        timeout=10,
        user_agent='SEOFrog/0.3 Orchestrator Test',
        retry_attempts=2
    )
    
    # Cria orchestrator
    orchestrator = AsyncCrawlOrchestrator(
        config=config,
        output_dir="./test_crawl_output",
        max_workers=3,
        max_depth=2,
        max_urls=20
    )
    
    # Configura logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("🚀 Iniciando teste completo do AsyncCrawlOrchestrator...")
    print("🎯 Target: httpbin.org (max 20 URLs, depth 2)")
    
    try:
        # Executa crawl
        final_stats = await orchestrator.crawl_site('https://httpbin.org')
        
        # Exibe resultados
        print("\n" + "="*60)
        print("📊 RELATÓRIO FINAL DO CRAWL")
        print("="*60)
        
        summary = final_stats['crawl_summary']
        print(f"✅ Páginas crawled: {summary['total_pages']}")
        print(f"❌ Páginas com falha: {summary['failed_pages']}")
        print(f"📈 Taxa de sucesso: {summary['success_rate']:.2%}")
        print(f"⏱️  Tempo total: {summary['total_time_seconds']:.2f}s")
        print(f"🚀 Velocidade: {summary['pages_per_second']:.2f} páginas/s")
        
        print(f"\n📁 Arquivo de saída: {final_stats['saver_stats']['output_file']}")
        
        # Stats detalhadas
        print(f"\n🔧 Queue Stats:")
        for key, value in final_stats['queue_stats'].items():
            print(f"  {key}: {value}")
        
        print(f"\n🌐 HTTP Engine Stats:")
        http_stats = final_stats['http_engine_stats']
        print(f"  Requests made: {http_stats['requests_made']}")
        print(f"  Avg response time: {http_stats['avg_response_time']:.3f}s")
        
    except Exception as e:
        print(f"💥 Erro durante teste: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Executa teste completo
    asyncio.run(test_orchestrator())
    
    