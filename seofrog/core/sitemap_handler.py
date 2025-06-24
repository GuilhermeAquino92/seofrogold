"""
seofrog/core/sitemap_handler.py
SitemapHandler robusto para lidar com XML malformado e problemas de encoding
"""

import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import re
import chardet
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import gzip
import io

from seofrog.utils.logger import get_logger
from seofrog.core.exceptions import ParseException

class RobustSitemapHandler:
    """
    Handler enterprise robusto para sitemap.xml
    Lida com XML malformado, encoding incorreto, e outros problemas comuns
    """
    
    def __init__(self, domain: str, http_engine=None, timeout: int = 10):
        self.domain = domain
        self.http_engine = http_engine
        self.timeout = timeout
        self.logger = get_logger('SitemapHandler')
        
        # Configurações de parsing
        self.max_urls_per_sitemap = 50000  # Google limit
        self.max_sitemaps_to_process = 10
        self.max_recursion_depth = 3
        
        # Padrões para limpeza de XML
        self.invalid_xml_chars_pattern = re.compile(
            r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]'  # Caracteres de controle inválidos
        )
        
        # Namespaces comuns em sitemaps
        self.common_namespaces = {
            'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'image': 'http://www.google.com/schemas/sitemap-image/1.1',
            'video': 'http://www.google.com/schemas/sitemap-video/1.1',
            'news': 'http://www.google.com/schemas/sitemap-news/0.9',
            'mobile': 'http://www.google.com/schemas/sitemap-mobile/1.0'
        }
    
    def discover_sitemaps(self) -> List[Dict[str, Any]]:
        """
        Descobre sitemaps do site com informações detalhadas
        
        Returns:
            Lista de dicts com informações dos sitemaps encontrados
        """
        sitemap_candidates = [
            f"https://{self.domain}/sitemap.xml",
            f"https://{self.domain}/sitemap_index.xml",
            f"https://{self.domain}/sitemaps.xml",
            f"https://{self.domain}/sitemap-index.xml",
            f"https://{self.domain}/wp-sitemap.xml",  # WordPress
            f"https://{self.domain}/sitemap.xml.gz",
            f"http://{self.domain}/sitemap.xml",  # Fallback HTTP
        ]
        
        discovered_sitemaps = []
        
        for sitemap_url in sitemap_candidates:
            try:
                sitemap_info = self._analyze_sitemap_url(sitemap_url)
                if sitemap_info['accessible']:
                    discovered_sitemaps.append(sitemap_info)
                    self.logger.info(f"Sitemap descoberto: {sitemap_url} "
                                   f"({sitemap_info['content_type']}, "
                                   f"{sitemap_info['size_kb']}KB)")
                    
                    # Para sitemap_index, processa apenas o primeiro encontrado
                    if 'index' in sitemap_url.lower():
                        break
                        
            except Exception as e:
                self.logger.debug(f"Erro verificando {sitemap_url}: {e}")
                continue
        
        # Tenta descobrir sitemaps via robots.txt
        robots_sitemaps = self._discover_sitemaps_from_robots()
        for robots_sitemap in robots_sitemaps:
            if not any(s['url'] == robots_sitemap for s in discovered_sitemaps):
                try:
                    sitemap_info = self._analyze_sitemap_url(robots_sitemap)
                    if sitemap_info['accessible']:
                        discovered_sitemaps.append(sitemap_info)
                        self.logger.info(f"Sitemap do robots.txt: {robots_sitemap}")
                except Exception as e:
                    self.logger.debug(f"Erro com sitemap do robots.txt {robots_sitemap}: {e}")
        
        return discovered_sitemaps[:self.max_sitemaps_to_process]
    
    def _analyze_sitemap_url(self, sitemap_url: str) -> Dict[str, Any]:
        """
        Analisa uma URL de sitemap sem fazer parsing completo
        """
        sitemap_info = {
            'url': sitemap_url,
            'accessible': False,
            'status_code': None,
            'content_type': None,
            'size_kb': 0,
            'is_compressed': False,
            'encoding': None,
            'last_modified': None,
            'error': None
        }
        
        try:
            if self.http_engine:
                response, _, _ = self.http_engine.fetch_url(sitemap_url)
            else:
                response = requests.get(sitemap_url, timeout=self.timeout, 
                                      allow_redirects=True, stream=True)
            
            if response and response.status_code == 200:
                sitemap_info['accessible'] = True
                sitemap_info['status_code'] = response.status_code
                sitemap_info['content_type'] = response.headers.get('content-type', '')
                sitemap_info['size_kb'] = round(len(response.content) / 1024, 2)
                sitemap_info['is_compressed'] = sitemap_url.endswith('.gz') or \
                                               'gzip' in response.headers.get('content-encoding', '')
                sitemap_info['last_modified'] = response.headers.get('last-modified')
                
                # Detecta encoding
                encoding = self._detect_encoding(response.content)
                sitemap_info['encoding'] = encoding
                
            else:
                sitemap_info['status_code'] = response.status_code if response else None
                sitemap_info['error'] = f"HTTP {response.status_code}" if response else "No response"
                
        except Exception as e:
            sitemap_info['error'] = str(e)
        
        return sitemap_info
    
    def _discover_sitemaps_from_robots(self) -> List[str]:
        """
        Descobre sitemaps listados no robots.txt
        """
        robots_sitemaps = []
        
        try:
            robots_url = f"https://{self.domain}/robots.txt"
            
            if self.http_engine:
                response, _, _ = self.http_engine.fetch_url(robots_url)
            else:
                response = requests.get(robots_url, timeout=self.timeout)
            
            if response and response.status_code == 200:
                robots_content = response.text
                
                # Procura por linhas "Sitemap:"
                sitemap_lines = re.findall(r'^Sitemap:\s*(.+)$', robots_content, re.MULTILINE | re.IGNORECASE)
                
                for sitemap_url in sitemap_lines:
                    sitemap_url = sitemap_url.strip()
                    if sitemap_url:
                        robots_sitemaps.append(sitemap_url)
                        
        except Exception as e:
            self.logger.debug(f"Erro lendo robots.txt: {e}")
        
        return robots_sitemaps
    
    def parse_sitemap(self, sitemap_url: str, depth: int = 0) -> Dict[str, Any]:
        """
        Parseia sitemap com tratamento robusto de erros
        
        Args:
            sitemap_url: URL do sitemap
            depth: Nível de recursão (para sitemap index)
            
        Returns:
            Dict com URLs extraídas e metadados
        """
        result = {
            'sitemap_url': sitemap_url,
            'urls': [],
            'sub_sitemaps': [],
            'parsing_success': False,
            'parsing_method': None,
            'error': None,
            'stats': {
                'url_count': 0,
                'sub_sitemap_count': 0,
                'parse_time_ms': 0,
                'encoding_detected': None,
                'xml_cleaned': False
            }
        }
        
        if depth > self.max_recursion_depth:
            result['error'] = f"Máxima profundidade de recursão atingida: {depth}"
            return result
        
        start_time = datetime.now()
        
        try:
            # 1. Download do sitemap
            response = self._download_sitemap(sitemap_url)
            if not response:
                result['error'] = "Falha no download do sitemap"
                return result
            
            # 2. Processamento do conteúdo
            content = self._process_sitemap_content(response, result['stats'])
            if not content:
                result['error'] = "Falha no processamento do conteúdo"
                return result
            
            # 3. Tentativas de parsing com diferentes estratégias
            parsed_data = self._parse_xml_with_fallbacks(content, result['stats'])
            if not parsed_data:
                result['error'] = "Falha no parsing XML com todas as estratégias"
                return result
            
            # 4. Extração de URLs e sub-sitemaps
            urls, sub_sitemaps = self._extract_urls_from_xml(parsed_data)
            
            result['urls'] = urls[:self.max_urls_per_sitemap]
            result['sub_sitemaps'] = sub_sitemaps
            result['parsing_success'] = True
            result['stats']['url_count'] = len(urls)
            result['stats']['sub_sitemap_count'] = len(sub_sitemaps)
            
            # 5. Processa sub-sitemaps recursivamente (apenas se for sitemap index)
            if sub_sitemaps and depth < self.max_recursion_depth:
                for sub_sitemap_url in sub_sitemaps[:5]:  # Máximo 5 sub-sitemaps
                    try:
                        sub_result = self.parse_sitemap(sub_sitemap_url, depth + 1)
                        if sub_result['parsing_success']:
                            result['urls'].extend(sub_result['urls'])
                            self.logger.debug(f"Sub-sitemap processado: {sub_sitemap_url} "
                                            f"({len(sub_result['urls'])} URLs)")
                    except Exception as e:
                        self.logger.warning(f"Erro processando sub-sitemap {sub_sitemap_url}: {e}")
            
            # Remove duplicatas
            result['urls'] = list(dict.fromkeys(result['urls']))  # Preserva ordem
            result['stats']['url_count'] = len(result['urls'])
            
            parse_time = (datetime.now() - start_time).total_seconds() * 1000
            result['stats']['parse_time_ms'] = round(parse_time, 2)
            
            self.logger.info(f"Sitemap parseado com sucesso: {sitemap_url} "
                           f"({len(result['urls'])} URLs em {parse_time:.1f}ms)")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Erro parseando sitemap {sitemap_url}: {e}")
        
        return result
    
    def _download_sitemap(self, sitemap_url: str) -> Optional[requests.Response]:
        """
        Download do sitemap com tratamento de compressão
        """
        try:
            if self.http_engine:
                response, _, _ = self.http_engine.fetch_url(sitemap_url)
            else:
                headers = {
                    'User-Agent': 'SEOFrog/1.0 (+https://seofrog.com/bot)',
                    'Accept': 'application/xml,text/xml,*/*',
                    'Accept-Encoding': 'gzip, deflate'
                }
                response = requests.get(sitemap_url, timeout=self.timeout, 
                                      headers=headers, allow_redirects=True)
            
            if not response or response.status_code != 200:
                return None
            
            return response
            
        except Exception as e:
            self.logger.error(f"Erro no download do sitemap {sitemap_url}: {e}")
            return None
    
    def _process_sitemap_content(self, response: requests.Response, stats: Dict) -> Optional[str]:
        """
        Processa o conteúdo do sitemap (descompressão, encoding, limpeza)
        """
        try:
            content = response.content
            
            # 1. Descompressão se necessário
            if response.url.endswith('.gz') or 'gzip' in response.headers.get('content-encoding', ''):
                try:
                    content = gzip.decompress(content)
                except Exception as e:
                    self.logger.debug(f"Erro na descompressão: {e}")
                    pass
            
            # 2. Detecção de encoding
            encoding = self._detect_encoding(content)
            stats['encoding_detected'] = encoding
            
            # 3. Decodificação para string
            try:
                content_str = content.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                # Fallback para encoding padrão
                content_str = content.decode('utf-8', errors='replace')
                stats['encoding_detected'] = 'utf-8 (fallback)'
            
            # 4. Limpeza de caracteres inválidos
            original_length = len(content_str)
            content_str = self._clean_xml_content(content_str)
            
            if len(content_str) != original_length:
                stats['xml_cleaned'] = True
                self.logger.debug(f"Caracteres inválidos removidos: {original_length - len(content_str)}")
            
            return content_str
            
        except Exception as e:
            self.logger.error(f"Erro processando conteúdo: {e}")
            return None
    
    def _detect_encoding(self, content: bytes) -> str:
        """
        Detecta encoding do conteúdo XML
        """
        # 1. Tenta detectar via XML declaration
        xml_declaration_match = re.search(rb'<\?xml[^>]+encoding=["\']([^"\']+)["\']', content[:200])
        if xml_declaration_match:
            declared_encoding = xml_declaration_match.group(1).decode('ascii', errors='ignore')
            if declared_encoding:
                return declared_encoding
        
        # 2. Usa chardet para detecção automática
        try:
            detected = chardet.detect(content[:10000])  # Analisa primeiros 10KB
            if detected and detected.get('confidence', 0) > 0.7:
                return detected['encoding']
        except Exception:
            pass
        
        # 3. Fallback para UTF-8
        return 'utf-8'
    
    def _clean_xml_content(self, content: str) -> str:
        """
        Remove caracteres inválidos do XML
        """
        # Remove caracteres de controle inválidos
        content = self.invalid_xml_chars_pattern.sub('', content)
        
        # Corrige algumas entidades HTML comuns que podem estar incorretas
        html_entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&apos;': "'",
        }
        
        for entity, replacement in html_entities.items():
            content = content.replace(entity, replacement)
        
        # Remove BOMs
        content = content.lstrip('\ufeff\ufffe\u0000')
        
        return content.strip()
    
    def _parse_xml_with_fallbacks(self, content: str, stats: Dict) -> Optional[ET.Element]:
        """
        Tenta fazer parsing do XML com múltiplas estratégias de fallback
        """
        parsing_strategies = [
            ('direct', self._parse_xml_direct),
            ('namespace_cleanup', self._parse_xml_with_namespace_cleanup),
            ('regex_extraction', self._parse_xml_with_regex_cleanup),
            ('manual_fix', self._parse_xml_with_manual_fixes),
        ]
        
        for strategy_name, strategy_func in parsing_strategies:
            try:
                result = strategy_func(content)
                if result is not None:
                    stats['parsing_method'] = strategy_name
                    self.logger.debug(f"XML parseado com estratégia: {strategy_name}")
                    return result
            except Exception as e:
                self.logger.debug(f"Estratégia {strategy_name} falhou: {e}")
                continue
        
        return None
    
    def _parse_xml_direct(self, content: str) -> Optional[ET.Element]:
        """
        Parsing direto do XML
        """
        return ET.fromstring(content)
    
    def _parse_xml_with_namespace_cleanup(self, content: str) -> Optional[ET.Element]:
        """
        Remove namespaces problemáticos antes do parsing
        """
        # Remove declarações de namespace problemáticas
        content = re.sub(r'xmlns[^=]*="[^"]*"', '', content)
        content = re.sub(r'xmlns[^=]*=\'[^\']*\'', '', content)
        
        # Remove prefixos de namespace das tags
        content = re.sub(r'<(/?)[\w]*:', r'<\1', content)
        
        return ET.fromstring(content)
    
    def _parse_xml_with_regex_cleanup(self, content: str) -> Optional[ET.Element]:
        """
        Usa regex para extrair e reconstruir XML válido
        """
        # Extrai URLs usando regex como fallback
        url_pattern = r'<loc[^>]*>(https?://[^<]+)</loc>'
        sitemap_pattern = r'<sitemap[^>]*>.*?<loc[^>]*>(https?://[^<]+)</loc>.*?</sitemap>'
        
        urls = re.findall(url_pattern, content, re.DOTALL | re.IGNORECASE)
        sitemaps = re.findall(sitemap_pattern, content, re.DOTALL | re.IGNORECASE)
        
        # Reconstrói XML simples
        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset>']
        
        for url in urls:
            xml_parts.append(f'<url><loc>{url}</loc></url>')
        
        for sitemap_url in sitemaps:
            xml_parts.append(f'<sitemap><loc>{sitemap_url}</loc></sitemap>')
        
        xml_parts.append('</urlset>')
        
        reconstructed_xml = '\n'.join(xml_parts)
        return ET.fromstring(reconstructed_xml)
    
    def _parse_xml_with_manual_fixes(self, content: str) -> Optional[ET.Element]:
        """
        Aplica correções manuais para problemas comuns
        """
        # Corrige tags não fechadas comuns
        fixes = [
            (r'<url>([^<]*)<loc>', r'<url><loc>'),
            (r'</loc>([^<]*)</url>', r'</loc></url>'),
            (r'&(?![a-zA-Z]+;)', r'&amp;'),  # Fixa & não escapados
            (r'<([^>]*?)&([^>]*?)>', r'<\1&amp;\2>'),  # & em atributos
        ]
        
        for pattern, replacement in fixes:
            content = re.sub(pattern, replacement, content)
        
        return ET.fromstring(content)
    
    def _extract_urls_from_xml(self, root: ET.Element) -> Tuple[List[str], List[str]]:
        """
        Extrai URLs e sub-sitemaps do XML parseado
        """
        urls = []
        sub_sitemaps = []
        
        # Remove namespaces das tags para facilitar busca
        for elem in root.iter():
            if '}' in str(elem.tag):
                elem.tag = elem.tag.split('}')[1]
        
        # Extrai URLs principais
        for url_elem in root.findall('.//url'):
            loc_elem = url_elem.find('loc')
            if loc_elem is not None and loc_elem.text:
                url = loc_elem.text.strip()
                if self._is_valid_url(url):
                    urls.append(url)
        
        # Extrai sub-sitemaps (sitemap index)
        for sitemap_elem in root.findall('.//sitemap'):
            loc_elem = sitemap_elem.find('loc')
            if loc_elem is not None and loc_elem.text:
                sitemap_url = loc_elem.text.strip()
                if self._is_valid_url(sitemap_url):
                    sub_sitemaps.append(sitemap_url)
        
        return urls, sub_sitemaps
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Valida se URL é válida
        """
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False
    
    def get_sitemap_stats(self, sitemap_results: List[Dict]) -> Dict[str, Any]:
        """
        Gera estatísticas dos sitemaps processados
        """
        total_urls = 0
        successful_parses = 0
        total_sitemaps = len(sitemap_results)
        parsing_methods = {}
        encodings = {}
        total_parse_time = 0
        
        for result in sitemap_results:
            if result['parsing_success']:
                successful_parses += 1
                total_urls += result['stats']['url_count']
                total_parse_time += result['stats']['parse_time_ms']
                
                method = result['stats']['parsing_method']
                parsing_methods[method] = parsing_methods.get(method, 0) + 1
                
                encoding = result['stats']['encoding_detected']
                if encoding:
                    encodings[encoding] = encodings.get(encoding, 0) + 1
        
        return {
            'total_sitemaps_processed': total_sitemaps,
            'successful_parses': successful_parses,
            'success_rate': (successful_parses / total_sitemaps * 100) if total_sitemaps > 0 else 0,
            'total_urls_extracted': total_urls,
            'average_urls_per_sitemap': total_urls / successful_parses if successful_parses > 0 else 0,
            'total_parse_time_ms': total_parse_time,
            'average_parse_time_ms': total_parse_time / successful_parses if successful_parses > 0 else 0,
            'parsing_methods_used': parsing_methods,
            'encodings_detected': encodings,
            'sitemaps_with_errors': [r for r in sitemap_results if not r['parsing_success']]
        }

# ==========================================
# FUNÇÃO DE COMPATIBILIDADE COM CÓDIGO EXISTENTE
# ==========================================

class SitemapHandler:
    """
    Wrapper de compatibilidade para manter interface existente
    """
    
    def __init__(self, domain: str, http_engine=None):
        self.robust_handler = RobustSitemapHandler(domain, http_engine)
        self.logger = get_logger('SitemapHandler')
    
    def discover_sitemaps(self) -> List[str]:
        """Mantém interface existente"""
        sitemaps_info = self.robust_handler.discover_sitemaps()
        return [s['url'] for s in sitemaps_info if s['accessible']]
    
    def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Mantém interface existente"""
        result = self.robust_handler.parse_sitemap(sitemap_url)
        
        if result['parsing_success']:
            self.logger.info(f"Extraídas {len(result['urls'])} URLs do sitemap {sitemap_url}")
            return result['urls']
        else:
            self.logger.error(f"Erro parseando sitemap {sitemap_url}: {result['error']}")
            return []

# ==========================================
# EXEMPLO DE USO E TESTE
# ==========================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Uso: python sitemap_handler.py <domain>")
        print("Exemplo: python sitemap_handler.py cafelor.com.br")
        sys.exit(1)
    
    domain = sys.argv[1]
    
    print(f"🗺️  Testando SitemapHandler Robusto para: {domain}")
    print("=" * 60)
    
    # Testa o handler robusto
    handler = RobustSitemapHandler(domain)
    
    # 1. Descoberta de sitemaps
    print("1. Descobrindo sitemaps...")
    discovered = handler.discover_sitemaps()
    
    if not discovered:
        print("❌ Nenhum sitemap descoberto")
        sys.exit(1)
    
    print(f"✅ {len(discovered)} sitemap(s) descoberto(s):")
    for sitemap in discovered:
        print(f"   📄 {sitemap['url']}")
        print(f"      Status: {sitemap['status_code']}")
        print(f"      Tamanho: {sitemap['size_kb']}KB")
        print(f"      Encoding: {sitemap['encoding']}")
        print(f"      Comprimido: {sitemap['is_compressed']}")
    
    # 2. Parse dos sitemaps
    print("\n2. Parseando sitemaps...")
    all_results = []
    
    for sitemap in discovered[:3]:  # Testa apenas os primeiros 3
        print(f"\n   Parseando: {sitemap['url']}")
        result = handler.parse_sitemap(sitemap['url'])
        all_results.append(result)
        
        if result['parsing_success']:
            print(f"   ✅ Sucesso: {len(result['urls'])} URLs extraídas")
            print(f"      Método: {result['stats']['parsing_method']}")
            print(f"      Tempo: {result['stats']['parse_time_ms']}ms")
            print(f"      Encoding: {result['stats']['encoding_detected']}")
            print(f"      XML limpo: {result['stats']['xml_cleaned']}")
            
            # Mostra algumas URLs de exemplo
            if result['urls']:
                print(f"      Exemplos de URLs:")
                for url in result['urls'][:3]:
                    print(f"        - {url}")
                if len(result['urls']) > 3:
                    print(f"        ... e mais {len(result['urls']) - 3}")
        else:
            print(f"   ❌ Falha: {result['error']}")
    
    # 3. Estatísticas finais
    print("\n3. Estatísticas Finais:")
    stats = handler.get_sitemap_stats(all_results)
    
    print(f"   📊 Sitemaps processados: {stats['total_sitemaps_processed']}")
    print(f"   ✅ Sucessos: {stats['successful_parses']} ({stats['success_rate']:.1f}%)")
    print(f"   🔗 Total de URLs: {stats['total_urls_extracted']}")
    print(f"   ⏱️  Tempo total: {stats['total_parse_time_ms']:.1f}ms")
    
    if stats['parsing_methods_used']:
        print(f"   🔧 Métodos de parsing usados:")
        for method, count in stats['parsing_methods_used'].items():
            print(f"      - {method}: {count}")
    
    if stats['encodings_detected']:
        print(f"   📝 Encodings detectados:")
        for encoding, count in stats['encodings_detected'].items():
            print(f"      - {encoding}: {count}")
    
    if stats['sitemaps_with_errors']:
        print(f"\n❌ Sitemaps com erros:")
        for error_result in stats['sitemaps_with_errors']:
            print(f"   - {error_result['sitemap_url']}: {error_result['error']}")
    
    print("\n" + "=" * 60)
    print("✅ Teste do SitemapHandler Robusto concluído!")