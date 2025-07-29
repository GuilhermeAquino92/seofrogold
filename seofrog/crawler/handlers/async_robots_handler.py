"""
AsyncRobotsHandler
Handler assíncrono para robots.txt compatível com asyncio
"""

import aiohttp
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
import logging
from typing import Dict, Optional


class AsyncRobotsHandler:
    """
    Handler assíncrono para robots.txt
    Mantém cache de parsers por domínio e respeita regras de crawling
    """
    
    def __init__(self, user_agent: str = "SEOFrog/0.4 AsyncCrawler"):
        self.user_agent = user_agent
        self.parsers: Dict[str, RobotFileParser] = {}
        self.failed_domains: set = set()
        self.logger = logging.getLogger('AsyncRobotsHandler')
    
    async def can_fetch(self, url: str, session: Optional[aiohttp.ClientSession] = None) -> bool:
        """
        Verifica se URL pode ser crawleada de acordo com robots.txt
        
        Args:
            url: URL para verificar
            session: Sessão aiohttp existente (opcional)
            
        Returns:
            True se pode crawlear, False caso contrário
        """
        try:
            domain = urlparse(url).netloc
            
            # Se já falhou antes, assume que pode (fail-safe)
            if domain in self.failed_domains:
                return True
            
            # Se já tem parser cached, usa ele
            if domain in self.parsers:
                return self.parsers[domain].can_fetch(self.user_agent, url)
            
            # Tenta baixar e parsear robots.txt
            await self._fetch_and_parse_robots(domain, session)
            
            # Verifica novamente com o parser (se conseguiu baixar)
            if domain in self.parsers:
                return self.parsers[domain].can_fetch(self.user_agent, url)
            
            # Se não conseguiu baixar, assume que pode (fail-safe)
            return True
            
        except Exception as e:
            self.logger.debug(f"Erro verificando robots.txt para {url}: {e}")
            return True  # fail-safe: se der erro, permite crawl
    
    async def _fetch_and_parse_robots(self, domain: str, session: Optional[aiohttp.ClientSession] = None):
        """
        Baixa e parseia robots.txt para um domínio
        """
        robots_url = f"https://{domain}/robots.txt"
        
        try:
            # Usa sessão existente ou cria temporária
            close_session = False
            if session is None:
                session = aiohttp.ClientSession()
                close_session = True
            
            try:
                async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        
                        # Parseia usando RobotFileParser padrão
                        rp = RobotFileParser()
                        rp.set_url(robots_url)
                        rp.parse(content.splitlines())
                        
                        self.parsers[domain] = rp
                        self.logger.debug(f"Robots.txt carregado para {domain}")
                        
                    else:
                        self.logger.debug(f"Robots.txt não encontrado para {domain} (status {resp.status})")
                        self.failed_domains.add(domain)
                        
            finally:
                if close_session:
                    await session.close()
                    
        except Exception as e:
            self.logger.debug(f"Erro baixando robots.txt de {domain}: {e}")
            self.failed_domains.add(domain)
    
    def get_crawl_delay(self, url: str) -> Optional[float]:
        """
        Retorna delay de crawl especificado no robots.txt (se houver)
        
        Args:
            url: URL para verificar
            
        Returns:
            Delay em segundos ou None se não especificado
        """
        try:
            domain = urlparse(url).netloc
            
            if domain in self.parsers:
                parser = self.parsers[domain]
                delay = parser.crawl_delay(self.user_agent)
                if delay is not None:
                    return float(delay)
            
            return None
            
        except Exception:
            return None
    
    def get_sitemap_urls(self, domain: str) -> list:
        """
        Retorna URLs de sitemaps especificadas no robots.txt
        
        Args:
            domain: Domínio para verificar
            
        Returns:
            Lista de URLs de sitemaps
        """
        try:
            if domain in self.parsers:
                parser = self.parsers[domain]
                return list(parser.site_maps()) if hasattr(parser, 'site_maps') else []
            
            return []
            
        except Exception:
            return []
    
    def clear_cache(self):
        """Limpa cache de parsers"""
        self.parsers.clear()
        self.failed_domains.clear()
        self.logger.debug("Cache de robots.txt limpo")
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do handler"""
        return {
            'domains_parsed': len(self.parsers),
            'failed_domains': len(self.failed_domains),
            'user_agent': self.user_agent
        }