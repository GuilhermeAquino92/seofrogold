"""
seofrog/core/crawler.py
Core Engine Principal do SEOFrog v0.2 Enterprise - ATUALIZADO PARA PARSERS MODULARES
🚀 VERSÃO CORRIGIDA: Detecta redirects corretamente
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
import chardet  # 🆕 Adicionado para detecção de encoding

from .config import CrawlConfig

from .exceptions import (
    CrawlException, NetworkException, ParseException, 
    MemoryException, URLException
)
from seofrog.utils.logger import get_logger, CrawlProgressLogger

# 🔥 PARSERS MODULARES - REMOVIDO SEOParser
from seofrog.parsers.meta_parser import MetaParser
from seofrog.parsers.technical_parser import TechnicalParser
from seofrog.parsers.social_parser import SocialParser
from seofrog.parsers.schema_parser import SchemaParser

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
    """Handler enterprise para sitemap.xml - VERSÃO CORRIGIDA"""
    
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
        """
        🔧 MÉTODO CORRIGIDO - Parseia sitemap com tratamento robusto para XML malformado
        """
        urls = []
        
        try:
            response, _, _ = self.http_engine.fetch_url(sitemap_url)
            if not response or response.status_code != 200:
                return urls
            
            # === CORREÇÃO PARA XML MALFORMADO ===
            
            # 1. Detecta encoding corretamente
            content = response.content
            
            # Detecta encoding via XML declaration ou chardet
            encoding = 'utf-8'  # default
            xml_declaration_match = re.search(rb'<\?xml[^>]+encoding=["\']([^"\']+)["\']', content[:200])
            if xml_declaration_match:
                declared_encoding = xml_declaration_match.group(1).decode('ascii', errors='ignore')
                if declared_encoding:
                    encoding = declared_encoding
                    self.logger.debug(f"Encoding detectado via XML declaration: {encoding}")
            else:
                # Usa chardet como fallback
                try:
                    detected = chardet.detect(content[:5000])
                    if detected and detected.get('confidence', 0) > 0.7:
                        encoding = detected['encoding']
                        self.logger.debug(f"Encoding detectado via chardet: {encoding} (conf: {detected.get('confidence', 0):.2f})")
                except Exception as e:
                    self.logger.debug(f"Erro no chardet: {e}")
                    pass
            
            # 2. Decodifica com tratamento de erro
            try:
                content_str = content.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                content_str = content.decode('utf-8', errors='replace')
                self.logger.debug(f"Fallback para UTF-8 com errors='replace' no sitemap {sitemap_url}")
            
            # 3. Remove caracteres inválidos para XML
            invalid_chars_pattern = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]')
            original_length = len(content_str)
            content_str = invalid_chars_pattern.sub('', content_str)
            
            if len(content_str) != original_length:
                chars_removed = original_length - len(content_str)
                self.logger.debug(f"Removidos {chars_removed} caracteres inválidos do XML")
            
            # 4. Remove BOMs se presentes
            content_str = content_str.lstrip('\ufeff\ufffe\u0000')
            
            # 5. Tenta parsing com múltiplas estratégias
            root = None
            parsing_method = None
            
            # Estratégia 1: Parsing direto
            try:
                root = ET.fromstring(content_str)
                parsing_method = "direct"
            except ET.ParseError as e:
                self.logger.debug(f"Parsing direto falhou: {e}")
            
            # Estratégia 2: Remove namespaces problemáticos
            if root is None:
                try:
                    cleaned_content = re.sub(r'xmlns[^=]*="[^"]*"', '', content_str)
                    cleaned_content = re.sub(r'xmlns[^=]*=\'[^\']*\'', '', cleaned_content)
                    cleaned_content = re.sub(r'<(/?)[\w]*:', r'<\1', cleaned_content)
                    root = ET.fromstring(cleaned_content)
                    parsing_method = "namespace_cleanup"
                except ET.ParseError as e:
                    self.logger.debug(f"Parsing com limpeza de namespace falhou: {e}")
            
            # Estratégia 3: Correções manuais para problemas comuns
            if root is None:
                try:
                    # Corrige & não escapados
                    fixed_content = re.sub(r'&(?![a-zA-Z]+;)', r'&amp;', content_str)
                    # Corrige < e > em atributos
                    fixed_content = re.sub(r'<([^>]*?)&([^>]*?)>', r'<\1&amp;\2>', fixed_content)
                    root = ET.fromstring(fixed_content)
                    parsing_method = "manual_fixes"
                except ET.ParseError as e:
                    self.logger.debug(f"Parsing com correções manuais falhou: {e}")
            
            # Estratégia 4: Extração por regex (fallback)
            if root is None:
                try:
                    self.logger.warning(f"XML malformado em {sitemap_url}, usando extração por regex")
                    
                    # Extrai URLs usando regex
                    url_pattern = r'<loc[^>]*>(https?://[^<]+)</loc>'
                    sitemap_pattern = r'<sitemap[^>]*>.*?<loc[^>]*>(https?://[^<]+)</loc>.*?</sitemap>'
                    
                    extracted_urls = re.findall(url_pattern, content_str, re.DOTALL | re.IGNORECASE)
                    extracted_sitemaps = re.findall(sitemap_pattern, content_str, re.DOTALL | re.IGNORECASE)
                    
                    # Adiciona URLs encontradas
                    for url in extracted_urls:
                        clean_url = url.strip()
                        if self._is_valid_url(clean_url):
                            urls.append(clean_url)
                    
                    # Processa sub-sitemaps recursivamente
                    for sub_sitemap_url in extracted_sitemaps[:5]:  # Máximo 5
                        try:
                            clean_sub_url = sub_sitemap_url.strip()
                            if self._is_valid_url(clean_sub_url):
                                sub_urls = self.parse_sitemap(clean_sub_url)
                                urls.extend(sub_urls)
                        except Exception as e:
                            self.logger.warning(f"Erro em sub-sitemap {sub_sitemap_url}: {e}")
                    
                    parsing_method = "regex_extraction"
                    
                    # Remove duplicatas e retorna
                    urls = list(dict.fromkeys(urls))  # Remove duplicatas preservando ordem
                    self.logger.info(f"Extraídas {len(urls)} URLs do sitemap {sitemap_url} (método: {parsing_method})")
                    return urls
                    
                except Exception as e:
                    self.logger.error(f"Todas as estratégias de parsing falharam para {sitemap_url}: {e}")
                    return urls
            
            # 6. Se conseguiu fazer parsing do XML, extrai URLs normalmente
            if root is not None:
                # Remove namespace para facilitar parsing
                for elem in root.iter():
                    if '}' in str(elem.tag):
                        elem.tag = elem.tag.split('}')[1]
                
                # Extrai URLs do sitemap
                for url_elem in root.findall('.//url'):
                    loc_elem = url_elem.find('loc')
                    if loc_elem is not None and loc_elem.text:
                        clean_url = loc_elem.text.strip()
                        if self._is_valid_url(clean_url):
                            urls.append(clean_url)
                
                # Se é sitemap index, processa sub-sitemaps
                for sitemap_elem in root.findall('.//sitemap'):
                    loc_elem = sitemap_elem.find('loc')
                    if loc_elem is not None and loc_elem.text:
                        try:
                            clean_sub_url = loc_elem.text.strip()
                            if self._is_valid_url(clean_sub_url):
                                sub_urls = self.parse_sitemap(clean_sub_url)
                                urls.extend(sub_urls)
                        except Exception as e:
                            self.logger.warning(f"Erro processando sub-sitemap: {e}")
                
                # Remove duplicatas
                urls = list(dict.fromkeys(urls))
                self.logger.info(f"Extraídas {len(urls)} URLs do sitemap {sitemap_url} (método: {parsing_method})")
            
        except Exception as e:
            self.logger.error(f"Erro parseando sitemap {sitemap_url}: {e}")
            # Log adicional para debug
            self.logger.debug(f"Detalhes do erro: {type(e).__name__}: {str(e)}")
        
        return urls
    
    def _is_valid_url(self, url: str) -> bool:
        """
        🆕 Valida se URL é válida
        """
        try:
            if not url or not isinstance(url, str):
                return False
            
            # Remove espaços
            url = url.strip()
            
            # Deve começar com http ou https
            if not url.startswith(('http://', 'https://')):
                return False
            
            # Parse básico
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
            
        except Exception:
            return False

class SEOFrog:
    """Engine principal do SEOFrog v0.2 Enterprise"""
    
    def __init__(self, config: CrawlConfig):
        self.config = config
        self.logger = get_logger('SEOFrog')
        
        # Inicializa componentes
        self.url_manager = None
        self.http_engine = HTTPEngine(config)
        
        # 🆕 PARSERS MODULARES
        self.meta_parser = MetaParser()
        self.technical_parser = TechnicalParser()
        self.social_parser = SocialParser()
        self.schema_parser = SchemaParser()
        
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
        """🚀 MÉTODO CORRIGIDO - Crawl com detecção correta de redirects"""
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
                    'crawl_timestamp': datetime.now().isoformat(),
                    'depth': depth
                }
            
            # 🚀 CORREÇÃO: Determina status code e URLs corretos ANTES do parser
            original_status_code = self._get_original_status_code(redirect_chain, response)
            final_url = self._get_final_url_from_chain(url, redirect_chain, response)
            
            # === DADOS BÁSICOS DA RESPOSTA ===
            data = {
                'url': url,
                'status_code': original_status_code,  # 🚀 USA STATUS ORIGINAL (301/302)
                'content_type': response.headers.get('content-type', ''),
                'content_length': len(response.content),
                'response_time': response.elapsed.total_seconds(),
                'final_url': final_url,               # 🚀 USA URL FINAL CORRETA
                'original_url': url,                  # 🚀 PRESERVA URL ORIGINAL
                'crawl_timestamp': datetime.now().isoformat(),
                'depth': depth
            }
            
            # Se não é HTML, retorna dados básicos
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                data['content_type_category'] = self._categorize_content_type(content_type)
                return data
            
            # === PARSE HTML COM PARSERS MODULARES ===
            soup = BeautifulSoup(response.content, 'lxml')
            
            # 🔥 PARSE MODULAR
            meta_data = self.meta_parser.parse(soup, url)
            technical_data = self.technical_parser.parse(soup, url)
            social_data = self.social_parser.parse(soup, url)
            schema_data = self.schema_parser.parse(soup, url)
            
            # Merge todos os dados
            data.update(meta_data)
            data.update(technical_data)
            data.update(social_data)
            data.update(schema_data)
            
            # 🚀 ADICIONA DADOS DETALHADOS DE REDIRECT
            if redirect_chain:
                data['redirect_chain_length'] = len(redirect_chain)
                data['redirect_chain_data'] = redirect_chain
                data['redirect_urls'] = [r['url'] for r in redirect_chain]
                data['has_redirect'] = True
                
                # Dados do primeiro redirect (mais importante para SEO)
                first_redirect = redirect_chain[0]
                data['redirect_status_code'] = first_redirect.get('status_code', original_status_code)
                data['redirect_location'] = first_redirect.get('location', final_url)
                
                # Classifica tipo de redirect
                data['redirect_type'] = self._classify_redirect_type(url, final_url)
                
                # Informações para análise SEO
                data['redirect_is_permanent'] = original_status_code in [301, 308]
                data['redirect_is_temporary'] = original_status_code in [302, 303, 307]
                
                self.logger.debug(f"Redirect detectado: {url} [{original_status_code}] → {final_url}")
            else:
                data['has_redirect'] = False
                data['redirect_type'] = 'None'
                data['redirect_chain_length'] = 0
            
            # Descobre novos links se dentro da profundidade
            if depth < self.config.max_depth and response.status_code == 200:
                self._discover_links(url, response, depth)
            
            # Delay entre requests
            if self.config.delay > 0:
                time.sleep(self.config.delay)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Erro crítico crawling {url}: {e}")
            return {
                'url': url,
                'status_code': 0,
                'error': str(e),
                'crawl_timestamp': datetime.now().isoformat(),
                'depth': depth
            }
    
    def _get_original_status_code(self, redirect_chain: List[Dict], final_response) -> int:
        """
        🚀 NOVO: Determina o status code que deve ser reportado
        """
        if redirect_chain:
            # Se houve redirects, retorna o status do PRIMEIRO redirect
            return redirect_chain[0].get('status_code', final_response.status_code)
        else:
            # Se não houve redirects, retorna o status final
            return final_response.status_code
    
    def _get_final_url_from_chain(self, original_url: str, redirect_chain: List[Dict], final_response) -> str:
        """
        🚀 NOVO: Determina a URL final correta
        """
        if redirect_chain:
            # Se houve redirects, a URL final é a do response final
            return final_response.url
        else:
            # Se não houve redirects, URL final = URL original
            return original_url
    
    def _classify_redirect_type(self, original_url: str, final_url: str) -> str:
        """
        🚀 NOVO: Classifica o tipo de redirect para análise SEO
        """
        try:
            parsed_orig = urlparse(original_url)
            parsed_final = urlparse(final_url)
            
            # HTTP -> HTTPS (comum e bom)
            if parsed_orig.scheme == 'http' and parsed_final.scheme == 'https':
                return 'HTTP_to_HTTPS'
            
            # HTTPS -> HTTP (problema grave!)
            if parsed_orig.scheme == 'https' and parsed_final.scheme == 'http':
                return 'HTTPS_to_HTTP'
            
            # Redirect de WWW
            if ('www.' in parsed_orig.netloc) != ('www.' in parsed_final.netloc):
                if 'www.' in parsed_orig.netloc:
                    return 'WWW_to_Non_WWW'
                else:
                    return 'Non_WWW_to_WWW'
            
            # Capitalização no path
            if (parsed_orig.netloc.lower() == parsed_final.netloc.lower() and 
                parsed_orig.path != parsed_final.path and 
                parsed_orig.path.lower() == parsed_final.path.lower()):
                return 'Capitalization_Fix'
            
            # Trailing slash
            if (parsed_orig.netloc == parsed_final.netloc and 
                parsed_orig.path.rstrip('/') == parsed_final.path.rstrip('/') and
                parsed_orig.path != parsed_final.path):
                return 'Trailing_Slash'
            
            # Query string changes
            if (parsed_orig.netloc == parsed_final.netloc and 
                parsed_orig.path == parsed_final.path and 
                parsed_orig.query != parsed_final.query):
                return 'Query_String_Change'
            
            # Path redirect (mudança de estrutura)
            if (parsed_orig.netloc == parsed_final.netloc and 
                parsed_orig.path != parsed_final.path):
                return 'Path_Change'
            
            # Domain redirect (mudança de domínio)
            if parsed_orig.netloc != parsed_final.netloc:
                return 'Domain_Change'
            
            return 'Other'
            
        except Exception:
            return 'Unknown'
    
    def _categorize_content_type(self, content_type: str) -> str:
        """🆕 Categoriza tipos de conteúdo não-HTML"""
        content_type = content_type.lower()
        
        if 'image/' in content_type:
            return 'image'
        elif 'application/pdf' in content_type:
            return 'pdf'
        elif 'video/' in content_type:
            return 'video'
        elif 'audio/' in content_type:
            return 'audio'
        elif 'application/' in content_type:
            return 'application'
        else:
            return 'other'
    
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