"""
Crawler Factory
Factory pattern para criação de crawlers modulares
"""

from typing import Dict, Any, Optional
from types import SimpleNamespace
import logging

from ..orchestrators.async_crawl_orchestrator import AsyncCrawlOrchestrator


class CrawlerConfig:
    """Configuração para o crawler"""
    
    def __init__(self, 
                 timeout: int = 10,
                 user_agent: str = "SEOFrog/0.4 Modular Crawler",
                 retry_attempts: int = 3,
                 retry_backoff: int = 2,
                 max_redirects: int = 10,
                 max_workers: int = 10,
                 max_depth: int = 3,
                 max_urls: int = 1000,
                 output_dir: str = "./crawl_output",
                 output_format: str = "csv"):
        
        self.timeout = timeout
        self.user_agent = user_agent
        self.retry_attempts = retry_attempts
        self.retry_backoff = retry_backoff
        self.max_redirects = max_redirects
        self.max_workers = max_workers
        self.max_depth = max_depth
        self.max_urls = max_urls
        self.output_dir = output_dir
        self.output_format = output_format
    
    @classmethod
    def default(cls) -> 'CrawlerConfig':
        """Configuração padrão"""
        return cls()
    
    @classmethod
    def fast(cls) -> 'CrawlerConfig':
        """Configuração para crawling rápido"""
        return cls(
            max_workers=20,
            timeout=5,
            max_depth=2,
            max_urls=500
        )
    
    @classmethod
    def deep(cls) -> 'CrawlerConfig':
        """Configuração para crawling profundo"""
        return cls(
            max_workers=5,
            timeout=15,
            max_depth=5,
            max_urls=5000
        )
    
    @classmethod
    def safe(cls) -> 'CrawlerConfig':
        """Configuração conservadora"""
        return cls(
            max_workers=3,
            timeout=20,
            retry_attempts=5,
            max_depth=3,
            max_urls=1000
        )


class CrawlerType:
    """Tipos de crawler disponíveis"""
    ASYNC = "async"
    # Futuros tipos podem ser adicionados aqui
    # SYNC = "sync"
    # DISTRIBUTED = "distributed"


class CrawlerFactory:
    """
    🏭 Factory para criação de crawlers modulares
    
    Centraliza a criação e configuração de diferentes tipos de crawler,
    permitindo fácil extensão e personalização.
    """
    
    def __init__(self):
        self.logger = logging.getLogger('CrawlerFactory')
    
    def create_crawler(self, 
                      crawler_type: str = CrawlerType.ASYNC,
                      config: Optional[CrawlerConfig] = None,
                      **kwargs) -> AsyncCrawlOrchestrator:
        """
        Cria um crawler do tipo especificado
        
        Args:
            crawler_type: Tipo de crawler (CrawlerType.ASYNC, etc.)
            config: Configuração do crawler
            **kwargs: Parâmetros adicionais que sobrescrevem a config
            
        Returns:
            Instância do crawler configurado
        """
        if config is None:
            config = CrawlerConfig.default()
        
        # Override config with kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        self.logger.info(f"Creating {crawler_type} crawler with config: "
                        f"workers={config.max_workers}, depth={config.max_depth}, "
                        f"max_urls={config.max_urls}")
        
        if crawler_type == CrawlerType.ASYNC:
            return self._create_async_crawler(config)
        else:
            raise ValueError(f"Unsupported crawler type: {crawler_type}")
    
    def _create_async_crawler(self, config: CrawlerConfig) -> AsyncCrawlOrchestrator:
        """Cria crawler assíncrono"""
        # Converte CrawlerConfig para formato esperado pelo AsyncHTTPEngine
        engine_config = SimpleNamespace(
            timeout=config.timeout,
            user_agent=config.user_agent,
            retry_attempts=config.retry_attempts,
            retry_backoff=config.retry_backoff,
            max_redirects=config.max_redirects
        )
        
        return AsyncCrawlOrchestrator(
            config=engine_config,
            output_dir=config.output_dir,
            max_workers=config.max_workers,
            max_depth=config.max_depth,
            max_urls=config.max_urls
        )
    
    @staticmethod
    def get_available_types() -> list:
        """Retorna tipos de crawler disponíveis"""
        return [CrawlerType.ASYNC]
    
    @staticmethod
    def get_preset_configs() -> Dict[str, CrawlerConfig]:
        """Retorna configurações pré-definidas"""
        return {
            'default': CrawlerConfig.default(),
            'fast': CrawlerConfig.fast(),
            'deep': CrawlerConfig.deep(),
            'safe': CrawlerConfig.safe()
        }


# Função de conveniência para criação rápida
def create_crawler(url: str = None, 
                  preset: str = 'default',
                  crawler_type: str = CrawlerType.ASYNC,
                  config: Optional[CrawlerConfig] = None,
                  **kwargs) -> AsyncCrawlOrchestrator:
    """
    Função de conveniência para criar crawler rapidamente
    
    Args:
        url: URL inicial para crawl (opcional)
        preset: Preset de configuração ('default', 'fast', 'deep', 'safe')
        crawler_type: Tipo de crawler
        config: Configuração customizada (sobrescreve preset)
        **kwargs: Parâmetros adicionais
        
    Returns:
        Crawler configurado
    """
    factory = CrawlerFactory()
    
    # Se config foi fornecida, usa ela, senão usa preset
    if config is None:
        presets = factory.get_preset_configs()
        config = presets.get(preset, CrawlerConfig.default())
    
    return factory.create_crawler(crawler_type=crawler_type, config=config, **kwargs)


# Função para crawler básico com configuração mínima
async def quick_crawl(url: str, 
                     max_pages: int = 100,
                     max_depth: int = 2,
                     output_dir: str = "./quick_crawl") -> Dict[str, Any]:
    """
    Crawl rápido com configuração mínima
    
    Args:
        url: URL para crawl
        max_pages: Máximo de páginas
        max_depth: Profundidade máxima
        output_dir: Diretório de saída
        
    Returns:
        Estatísticas do crawl
    """
    crawler = create_crawler(
        preset='fast',
        max_urls=max_pages,
        max_depth=max_depth,
        output_dir=output_dir
    )
    
    return await crawler.crawl_site(url)