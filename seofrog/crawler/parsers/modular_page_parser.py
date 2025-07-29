"""
ModularPageParser
Parser modular que reutiliza os parsers do crawler_old
"""

import asyncio
import sys
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup
import logging

# Força UTF-8 no sistema
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

from ...parsers.meta_parser import MetaParser
from ...parsers.headings_parser import HeadingsParser
from ...parsers.technical_parser import TechnicalParser
from ...parsers.social_parser import SocialParser
from ...parsers.schema_parser import SchemaParser
from ...parsers.images_parser import ImagesParser
from ...parsers.security_parser import SecurityParser
from ...parsers.content_parser import ContentParser
from ..models.crawl_result import CrawlResult


class ModularPageParser:
    """
    Parser modular que usa os parsers existentes do crawler_old
    Mantém compatibilidade com async mas executa parsing síncrono
    """
    
    def __init__(self):
        self.logger = logging.getLogger('ModularPageParser')
        
        # Inicializa parsers modulares
        self.meta_parser = MetaParser()
        self.headings_parser = HeadingsParser()
        self.technical_parser = TechnicalParser()
        self.social_parser = SocialParser()
        self.schema_parser = SchemaParser()
        self.images_parser = ImagesParser()
        self.security_parser = SecurityParser()
        self.content_parser = ContentParser()
        
        # Stats
        self.stats = {
            'pages_parsed': 0,
            'parse_errors': 0,
            'avg_parse_time': 0.0,
            'total_parse_time': 0.0,
            'total_links_extracted': 0,
            'pages_with_links': 0
        }
    
    def parse_response(self, response, url: str, depth: int) -> CrawlResult:
        """
        Parseia response usando parsers modulares (método síncrono)
        
        Args:
            response: Response object do HTTP engine
            url: URL da página
            depth: Profundidade do crawl
            
        Returns:
            CrawlResult com dados parseados
        """
        start_time = datetime.now()
        
        try:
            # Cria BeautifulSoup com texto seguro
            try:
                safe_text = response.text.encode('utf-8', errors='replace').decode('utf-8')
                soup = BeautifulSoup(safe_text, 'lxml')
            except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
                soup = BeautifulSoup(str(response.text), 'lxml')
            
            # Cria resultado base
            result = CrawlResult(
                url=url,
                status_code=response.status_code,
                final_url=str(response.url),
                depth=depth,
                crawl_timestamp=start_time.isoformat()
            )
            
            # Aplica parsers modulares
            self._apply_meta_parser(result, soup)
            self._apply_headings_parser(result, soup)
            self._apply_technical_parser(result, soup, response)
            self._apply_social_parser(result, soup)
            self._apply_schema_parser(result, soup)
            self._apply_content_parser(result, soup)
            self._apply_images_parser(result, soup, result.word_count)
            self._apply_security_parser(result, soup, response)
            
            # Atualiza stats
            parse_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(parse_time, success=True)
            
            return result
            
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            safe_url = str(url).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.error(f"Erro parseando {safe_url}: {error_msg}")
            self._update_stats(0, success=False)
            
            # Retorna resultado básico em caso de erro
            return CrawlResult(
                url=url,
                status_code=response.status_code if response else 0,
                final_url=str(response.url) if response else url,
                depth=depth,
                crawl_timestamp=start_time.isoformat(),
                errors=[str(e)]
            )
    
    async def parse_response_async(self, response, url: str, depth: int) -> CrawlResult:
        """
        Versão assíncrona que executa parsing em thread separada
        
        Args:
            response: Response object do HTTP engine
            url: URL da página
            depth: Profundidade do crawl
            
        Returns:
            CrawlResult com dados parseados
        """
        return await asyncio.to_thread(self.parse_response, response, url, depth)
    
    def _apply_meta_parser(self, result: CrawlResult, soup: BeautifulSoup):
        """Aplica MetaParser"""
        try:
            meta_data = self.meta_parser.parse(soup)
            result.title = meta_data.get('title')
            result.meta_description = meta_data.get('description')
            result.meta_keywords = meta_data.get('keywords')
            result.canonical_url = meta_data.get('canonical')
            result.robots_meta = meta_data.get('robots')
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.debug(f"Erro no MetaParser: {error_msg}")
    
    def _apply_headings_parser(self, result: CrawlResult, soup: BeautifulSoup):
        """Aplica HeadingsParser"""
        try:
            headings_data = self.headings_parser.parse(soup)
            result.h1 = headings_data.get('h1')
            result.headings = headings_data.get('all_headings', [])
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.debug(f"Erro no HeadingsParser: {error_msg}")
    
    def _apply_technical_parser(self, result: CrawlResult, soup: BeautifulSoup, response):
        """Aplica TechnicalParser"""
        try:
            # Extrai URL do response para passar corretamente ao TechnicalParser
            url = str(response.url) if hasattr(response, 'url') else None
            
            technical_data = self.technical_parser.parse(soup, url)
            result.charset = technical_data.get('charset')
            result.content_type = technical_data.get('content_type')
            result.server = technical_data.get('server')
            result.response_headers = technical_data.get('headers', {})
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.debug(f"Erro no TechnicalParser: {error_msg}")
    
    def _apply_social_parser(self, result: CrawlResult, soup: BeautifulSoup):
        """Aplica SocialParser"""
        try:
            social_data = self.social_parser.parse(soup)
            result.og_data = social_data.get('og', {})
            result.twitter_data = social_data.get('twitter', {})
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.debug(f"Erro no SocialParser: {error_msg}")
    
    def _apply_schema_parser(self, result: CrawlResult, soup: BeautifulSoup):
        """Aplica SchemaParser"""
        try:
            schema_data = self.schema_parser.parse(soup)
            result.schema_org = schema_data.get('schemas', [])
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.debug(f"Erro no SchemaParser: {error_msg}")
    
    def _apply_images_parser(self, result: CrawlResult, soup: BeautifulSoup, word_count: int):
        """Aplica ImagesParser"""
        try:
            # Garante que word_count é um int válido
            safe_word_count = int(word_count) if isinstance(word_count, (int, str)) and str(word_count).isdigit() else 0
            images_data = self.images_parser.parse(soup, safe_word_count)
            result.images = images_data.get('images', [])
            result.image_count = len(result.images)
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.debug(f"Erro no ImagesParser: {error_msg}")
    
    def _apply_security_parser(self, result: CrawlResult, soup: BeautifulSoup, response):
        """Aplica SecurityParser"""
        try:
            # Extrai URL e headers do response para passar corretamente ao SecurityParser
            url = str(response.url) if hasattr(response, 'url') else None
            response_headers = getattr(response, 'headers', {})
            
            security_data = self.security_parser.parse(soup, url, response_headers)
            result.security_headers = security_data.get('headers', {})
            result.mixed_content = security_data.get('mixed_content', [])
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.debug(f"Erro no SecurityParser: {error_msg}")
    
    def _apply_content_parser(self, result: CrawlResult, soup: BeautifulSoup):
        """Aplica ContentParser"""
        try:
            content_data = self.content_parser.parse(soup)
            result.word_count = content_data.get('word_count', 0)
            result.text_content = content_data.get('text_content', '')[:1000]  # Limita a 1000 chars
            result.links_internal = content_data.get('links_internal', [])
            result.links_external = content_data.get('links_external', [])
            
            # Log link extraction stats for debugging
            total_links = len(result.links_internal) + len(result.links_external)
            if total_links > 0:
                self.stats['pages_with_links'] += 1
                self.stats['total_links_extracted'] += total_links
                self.logger.debug(f"Links extracted from {result.url}: {len(result.links_internal)} internal, {len(result.links_external)} external")
            else:
                self.logger.debug(f"No links found in {result.url}")
                
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.debug(f"Erro no ContentParser: {error_msg}")
    
    def _update_stats(self, parse_time: float, success: bool):
        """Atualiza estatísticas de parsing"""
        self.stats['pages_parsed'] += 1
        if not success:
            self.stats['parse_errors'] += 1
        
        self.stats['total_parse_time'] += parse_time
        self.stats['avg_parse_time'] = (
            self.stats['total_parse_time'] / self.stats['pages_parsed']
        )
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do parser"""
        return {
            'pages_parsed': self.stats['pages_parsed'],
            'parse_errors': self.stats['parse_errors'],
            'success_rate': (
                (self.stats['pages_parsed'] - self.stats['parse_errors']) / 
                self.stats['pages_parsed']
            ) if self.stats['pages_parsed'] > 0 else 0,
            'avg_parse_time': self.stats['avg_parse_time'],
            'total_parse_time': self.stats['total_parse_time'],
            'total_links_extracted': self.stats['total_links_extracted'],
            'pages_with_links': self.stats['pages_with_links'],
            'avg_links_per_page': (
                self.stats['total_links_extracted'] / self.stats['pages_with_links']
            ) if self.stats['pages_with_links'] > 0 else 0
        }