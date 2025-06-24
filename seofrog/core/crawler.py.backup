"""
seofrog/core/crawler.py
Core Engine Principal do SEOFrog v0.2 Enterprise
"""

import requests
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode, unquote
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import time
import re
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import Set, List, Dict, Optional, Tuple, Any
from datetime import datetime
import signal
import psutil
import os

from .config import CrawlConfig

from .exceptions import (
    CrawlException, NetworkException, ParseException, 
    MemoryException, URLException
)
from seofrog.utils.logger import get_logger, CrawlProgressLogger
from seofrog.parsers.seo_parser import SEOParser
from seofrog.exporters.csv_exporter import CSVExporter

class URLManager:
    """Gerenciador enterprise de URLs com normalização avançada"""
    
    def __init__(self, domain: str):
        self.domain = domain
        self.seen_urls: Set[str] = set()
        self.normalized_cache: Dict[str, str] = {}
        self.url_data: Dict[str, Dict] = {}
        self.lock = threading.Lock()
        self.logger = get_logger('URLManager')
        
    def normalize_url(self, url: str) -> str:
        """Normalização enterprise de URLs"""
        if url in self.normalized_cache:
            return self.normalized_cache[url]
            
        try:
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
                
            normalized = urlunparse((
                parsed.scheme or 'https',
                parsed.netloc,
                path,
                parsed.params,
                query,
                ''
            ))
            
            self.normalized_cache[url] = normalized
            return normalized
            
        except Exception as e:
            self.logger.warning(f"Erro normalizando URL {url}: {e}")
            self.normalized_cache[url] = url
            return url
    
    def is_duplicate(self, url: str) -> bool:
        """Thread-safe duplicate detection"""
        normalized = self.normalize_url(url)
        with self.lock:
            if normalized in self.seen_urls:
                return True
            self.seen_urls.add(normalized)
            return False
    
    def add_url_data(self, url: str, data: Dict):
        """Armazena dados da URL de forma thread-safe"""
        normalized = self.normalize_url(url)
        with self.lock:
            self.url_data[normalized] = data
    
    def get_stats(self) -> Dict:
        """Estatísticas do URL Manager"""
        with self.lock:
            return {
                'total_urls': len(self.seen_urls),
                'cache_size': len(self.normalized_cache),
                'data_entries': len(self.url_data)
            }

class HTTPEngine:
    """Engine HTTP enterprise com retry inteligente e redirect handling"""
    
    def __init__(self, config: CrawlConfig):
        self.config = config
        self.session = requests.Session()
        
        # Desabilita verificação SSL para sites com problemas de certificado
        self.session.verify = False
        # Suprime warnings de SSL
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.session.headers.update({
            'User-Agent': config.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.logger = get_logger('HTTPEngine')
    
    def fetch_url(self, url: str) -> Tuple[Optional[requests.Response], List[str], Dict]:
        """Fetch URL com retry inteligente e tracking de redirects"""
        redirect_chain = []
        error_info = {}
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = self.session.get(
                    url,
                    timeout=self.config.timeout,
                    allow_redirects=False,
                    stream=True
                )
                
                # Handle redirects manualmente para tracking
                current_response = response
                redirect_count = 0
                
                while (current_response.status_code in [301, 302, 303, 307, 308] and 
                       redirect_count < self.config.max_redirects):
                    
                    redirect_chain.append({
                        'url': current_response.url,
                        'status_code': current_response.status_code,
                        'location': current_response.headers.get('location', '')
                    })
                    
                    if 'location' not in current_response.headers:
                        break
                        
                    next_url = urljoin(current_response.url, current_response.headers['location'])
                    
                    try:
                        current_response = self.session.get(
                            next_url,
                            timeout=self.config.timeout,
                            allow_redirects=False,
                            stream=True
                        )
                        redirect_count += 1
                    except Exception as e:
                        error_info['redirect_error'] = str(e)
                        break
                
                # Se chegou aqui, foi sucesso ou redirect final
                return current_response, redirect_chain, error_info
                
            except requests.exceptions.Timeout:
                error_info['error'] = 'timeout'
                self.logger.warning(f"Timeout em {url} (tentativa {attempt + 1})")
                
            except requests.exceptions.ConnectionError:
                error_info['error'] = 'connection_error'
                self.logger.warning(f"Erro de conexão em {url} (tentativa {attempt + 1})")
                
            except requests.exceptions.RequestException as e:
                error_info['error'] = str(e)
                self.logger.warning(f"Erro de request em {url}: {e}")
                
            # Backoff exponencial
            if attempt < self.config.retry_attempts - 1:
                sleep_time = self.config.retry_backoff ** attempt
                time.sleep(sleep_time)
        
        return None, redirect_chain, error_info

class RobotsHandler:
    """Handler enterprise para robots.txt"""
    
    def __init__(self, domain: str, user_agent: str):
        self.domain = domain
        self.user_agent = user_agent
        self.rp = RobotFileParser()
        self.rp.set_url(f"https://{domain}/robots.txt")
        self.loaded = False
        self.logger = get_logger('RobotsHandler')
        
    def load_robots(self) -> bool:
        """Carrega e parseia robots.txt"""
        try:
            # Cria contexto SSL que ignora verificação
            import ssl
            import urllib.request
            
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # Configura opener com contexto SSL
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
            urllib.request.install_opener(opener)
            
            self.rp.read()
            self.loaded = True
            self.logger.info(f"Robots.txt carregado para {self.domain}")
            return True
        except Exception as e:
            self.logger.warning(f"Erro carregando robots.txt para {self.domain}: {e}")
            self.loaded = False
            return False
    
    def can_fetch(self, url: str) -> bool:
        """Verifica se pode fazer fetch da URL"""
        if not self.loaded:
            return True  # Se não conseguiu carregar, permite
        
        try:
            return self.rp.can_fetch(self.user_agent, url)
        except Exception as e:
            self.logger.warning(f"Erro verificando robots.txt para {url}: {e}")
            return True

class SitemapHandler:
    """Handler enterprise para sitemap.xml"""
    
    def __init__(self, domain: str, http_engine: HTTPEngine):
        self.domain = domain
        self.http_engine = http_engine
        self.logger = get_logger('SitemapHandler')
    
    def discover_sitemaps(self) -> List[str]:
        """Descobre sitemaps do site"""
        sitemap_urls = [
            f"https://{self.domain}/sitemap.xml",
            f"https://{self.domain}/sitemap_index.xml",
            f"https://{self.domain}/sitemaps.xml",
            f"http://{self.domain}/sitemap.xml"
        ]
        
        valid_sitemaps = []
        
        for sitemap_url in sitemap_urls:
            response, _, _ = self.http_engine.fetch_url(sitemap_url)
            if response and response.status_code == 200:
                valid_sitemaps.append(sitemap_url)
                self.logger.info(f"Sitemap encontrado: {sitemap_url}")
        
        return valid_sitemaps
    
    def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Parseia sitemap e extrai URLs"""
        urls = []
        
        try:
            response, _, _ = self.http_engine.fetch_url(sitemap_url)
            if not response or response.status_code != 200:
                return urls
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Remove namespace para facilitar parsing
            for elem in root.iter():
                if '}' in str(elem.tag):
                    elem.tag = elem.tag.split('}')[1]
            
            # Extrai URLs do sitemap
            for url_elem in root.findall('.//url'):
                loc_elem = url_elem.find('loc')
                if loc_elem is not None and loc_elem.text:
                    urls.append(loc_elem.text.strip())
            
            # Se é sitemap index, processa sub-sitemaps
            for sitemap_elem in root.findall('.//sitemap'):
                loc_elem = sitemap_elem.find('loc')
                if loc_elem is not None and loc_elem.text:
                    sub_urls = self.parse_sitemap(loc_elem.text.strip())
                    urls.extend(sub_urls)
            
            self.logger.info(f"Extraídas {len(urls)} URLs do sitemap {sitemap_url}")
            
        except Exception as e:
            self.logger.error(f"Erro parseando sitemap {sitemap_url}: {e}")
        
        return urls

class SEOFrog:
    """Engine principal do SEOFrog v0.2 Enterprise"""
    
    def __init__(self, config: CrawlConfig):
        self.config = config
        self.logger = get_logger('SEOFrog')
        
        # Inicializa componentes
        self.url_manager = None
        self.http_engine = HTTPEngine(config)
        self.seo_parser = SEOParser()
        self.exporter = CSVExporter(config.output_dir)
        
        # Estado do crawl
        self.crawl_queue = deque()
        self.results = []
        self.crawled_count = 0
        self.start_time = None
        self.should_stop = False
        
        # Thread safety
        self.results_lock = threading.Lock()
        self.queue_lock = threading.Lock()
        
        # Progress logger
        self.progress_logger = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handler para sinais de interrupção"""
        self.logger.info("Sinal de interrupção recebido. Finalizando crawl...")
        self.should_stop = True
    
    def _check_memory_usage(self):
        """Verifica uso de memória e alerta se necessário"""
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.config.memory_limit_mb:
                self.logger.warning(f"Uso de memória alto: {memory_mb:.1f}MB (limite: {self.config.memory_limit_mb}MB)")
                
                if memory_mb > self.config.memory_limit_mb * 1.5:
                    raise MemoryException(
                        "Limite de memória excedido", 
                        memory_usage=int(memory_mb), 
                        limit=self.config.memory_limit_mb
                    )
        except psutil.NoSuchProcess:
            pass
    
    def add_seed_urls(self, start_url: str) -> List[str]:
        """Adiciona URLs seed do sitemap e URL inicial"""
        domain = urlparse(start_url).netloc
        self.url_manager = URLManager(domain)
        
        seed_urls = [start_url]
        
        # Tenta descobrir sitemap se configurado
        if self.config.respect_robots:
            sitemap_handler = SitemapHandler(domain, self.http_engine)
            sitemaps = sitemap_handler.discover_sitemaps()
            
            sitemap_count = 0
            for sitemap_url in sitemaps[:3]:  # Máximo 3 sitemaps
                sitemap_urls = sitemap_handler.parse_sitemap(sitemap_url)
                seed_urls.extend(sitemap_urls[:1000])  # Máximo 1000 URLs por sitemap
                sitemap_count += len(sitemap_urls)
                
                if sitemap_count > 5000:  # Limite total de URLs do sitemap
                    self.logger.info(f"Limite de URLs do sitemap atingido: {sitemap_count}")
                    break
        
        # Remove duplicatas e adiciona à queue
        unique_seeds = []
        for url in seed_urls:
            if not self.url_manager.is_duplicate(url):
                unique_seeds.append(url)
                self.crawl_queue.append((url, 0))  # (url, depth)
        
        self.logger.info(f"Adicionadas {len(unique_seeds)} URLs seed ({len(seed_urls)} total, {len(seed_urls) - len(unique_seeds)} duplicatas)")
        return unique_seeds
    
    def crawl_url(self, url: str, depth: int) -> Optional[Dict]:
        """Crawl de uma URL específica"""
        if self.should_stop:
            return None
            
        try:
            # Verifica robots.txt se configurado
            if self.config.respect_robots:
                domain = urlparse(url).netloc
                robots_handler = RobotsHandler(domain, self.config.user_agent)
                robots_handler.load_robots()
                
                if not robots_handler.can_fetch(url):
                    self.logger.debug(f"Bloqueado por robots.txt: {url}")
                    return None
            
            # Fetch da URL
            response, redirect_chain, error_info = self.http_engine.fetch_url(url)
            
            if response is None:
                self.logger.debug(f"Falha no fetch: {url} - {error_info}")
                return {
                    'url': url,
                    'status_code': 0,
                    'error': error_info.get('error', 'unknown'),
                    'crawl_timestamp': datetime.now().isoformat()
                }
            
            # Parse da página
            page_data = self.seo_parser.parse_page(url, response)
            
            # Adiciona dados de redirect se houver
            if redirect_chain:
                page_data['redirect_chain'] = len(redirect_chain)
                page_data['redirect_urls'] = [r['url'] for r in redirect_chain]
            
            # Descobre novos links se dentro da profundidade
            if depth < self.config.max_depth and response.status_code == 200:
                self._discover_links(url, response, depth)
            
            # Delay entre requests
            if self.config.delay > 0:
                time.sleep(self.config.delay)
            
            return page_data
            
        except Exception as e:
            self.logger.error(f"Erro crítico crawling {url}: {e}")
            return {
                'url': url,
                'status_code': 0,
                'error': str(e),
                'crawl_timestamp': datetime.now().isoformat()
            }
    
    def _discover_links(self, url: str, response: requests.Response, current_depth: int):
        """Descobre novos links para crawling"""
        try:
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                return
            
            soup = BeautifulSoup(response.content, 'lxml')
            links = soup.find_all('a', href=True)
            
            new_urls = []
            for link in links:
                href = link.get('href', '').strip()
                if not href or href.startswith('#'):
                    continue
                
                full_url = urljoin(url, href)
                parsed = urlparse(full_url)
                
                # Só URLs do mesmo domínio
                if parsed.netloc != urlparse(url).netloc:
                    continue
                
                # Verifica se é uma URL válida para crawl
                if self._is_crawlable_url(full_url) and not self.url_manager.is_duplicate(full_url):
                    new_urls.append(full_url)
            
            # Adiciona novas URLs à queue
            with self.queue_lock:
                for new_url in new_urls:
                    self.crawl_queue.append((new_url, current_depth + 1))
            
            if new_urls:
                self.logger.debug(f"Descobertas {len(new_urls)} novas URLs em {url}")
                
        except Exception as e:
            self.logger.warning(f"Erro descobrindo links em {url}: {e}")
    
    def _is_crawlable_url(self, url: str) -> bool:
        """Verifica se URL pode ser crawleada"""
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Extensões a ignorar baseadas na config
            ignore_extensions = set(self.config.ignore_extensions)
            
            if not self.config.crawl_images:
                ignore_extensions.update({'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'})
            
            if not self.config.crawl_css:
                ignore_extensions.add('.css')
                
            if not self.config.crawl_js:
                ignore_extensions.add('.js')
                
            if not self.config.crawl_pdf:
                ignore_extensions.add('.pdf')
            
            return not any(path.endswith(ext) for ext in ignore_extensions)
            
        except Exception:
            return False
    
    def crawl(self, start_url: str) -> List[Dict]:
        """Executa crawl completo do site"""
        self.start_time = datetime.now()
        self.logger.info(f"🚀 Iniciando SEOFrog v0.2 Enterprise crawl: {start_url}")
        self.logger.info(f"⚙️  Config: {self.config.max_urls:,} URLs max, depth {self.config.max_depth}, {self.config.max_workers} workers")
        
        # Setup progress logger
        self.progress_logger = CrawlProgressLogger(self.logger, log_interval=50)
        
        # Adiciona URLs seed
        try:
            seed_urls = self.add_seed_urls(start_url)
            if not seed_urls:
                raise CrawlException("Nenhuma URL seed encontrada", url=start_url)
        except Exception as e:
            self.logger.error(f"Erro adicionando seeds: {e}")
            return []
        
        # Crawl multi-threaded
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {}
            
            while (self.crawl_queue or futures) and self.crawled_count < self.config.max_urls and not self.should_stop:
                
                # Verifica memória periodicamente
                if self.crawled_count % 100 == 0:
                    self._check_memory_usage()
                
                # Submete novos jobs
                while (len(futures) < self.config.max_workers and 
                       self.crawl_queue and 
                       self.crawled_count < self.config.max_urls and
                       not self.should_stop):
                    
                    with self.queue_lock:
                        if not self.crawl_queue:
                            break
                        url, depth = self.crawl_queue.popleft()
                    
                    future = executor.submit(self.crawl_url, url, depth)
                    futures[future] = url
                    self.crawled_count += 1
                
                # Processa resultados completados
                if futures:
                    done_futures = [f for f in futures if f.done()]
                    
                    for future in done_futures:
                        url = futures.pop(future)
                        try:
                            result = future.result()
                            if result:
                                with self.results_lock:
                                    self.results.append(result)
                                
                                # Log progresso
                                if len(self.results) % 50 == 0:
                                    self.progress_logger.log_progress(
                                        len(self.results), 
                                        self.config.max_urls, 
                                        len(self.crawl_queue)
                                    )
                        
                        except Exception as e:
                            self.logger.error(f"Erro processando resultado de {url}: {e}")
                
                # Pequeno delay para evitar busy waiting
                time.sleep(0.1)
        
        # Finaliza crawl
        elapsed = (datetime.now() - self.start_time).total_seconds()
        success_count = len([r for r in self.results if r.get('status_code', 0) == 200])
        error_count = len(self.results) - success_count
        
        self.progress_logger.log_final_stats(len(self.results), success_count, error_count)
        self.logger.info(f"✅ SEOFrog crawl finalizado! {len(self.results)} URLs processadas em {elapsed:.1f}s")
        
        return self.results
    
    def export_results(self, format: str = 'xlsx', filename: str = None) -> str:
        """Exporta resultados do crawl"""
        if format.lower() == 'csv':
            return self.exporter.export_results(self.results, filename)
        elif format.lower() == 'xlsx':
            # Importa ExcelExporter
            from seofrog.exporters.excel_exporter import ExcelExporter
            excel_exporter = ExcelExporter(self.config.output_dir)
            return excel_exporter.export_results(self.results, filename)
        else:
            self.logger.warning(f"Formato {format} não suportado. Usando CSV.")
            return self.exporter.export_results(self.results, filename)
    
    def get_stats(self) -> Dict:
        """Estatísticas do crawl"""
        if not self.start_time:
            return {}
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        stats = {
            'total_urls_crawled': len(self.results),
            'elapsed_time': elapsed,
            'crawl_rate': len(self.results) / elapsed if elapsed > 0 else 0,
            'queue_size': len(self.crawl_queue),
            'config': {
                'max_urls': self.config.max_urls,
                'max_depth': self.config.max_depth,
                'max_workers': self.config.max_workers,
                'delay': self.config.delay
            }
        }
        
        if self.url_manager:
            stats['url_manager'] = self.url_manager.get_stats()
        
        # Status codes distribution
        status_codes = {}
        for result in self.results:
            status = result.get('status_code', 0)
            status_codes[status] = status_codes.get(status, 0) + 1
        stats['status_codes'] = status_codes
        
        return stats