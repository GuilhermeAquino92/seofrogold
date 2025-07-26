"""
Modular Crawler Interface
Interface principal do sistema de crawler modular
"""

import asyncio
from typing import Dict, Any, Optional
import logging

from .crawler_factory import CrawlerFactory, CrawlerConfig, CrawlerType


class ModularCrawler:
    """
    🎯 Interface principal do sistema de crawler modular
    
    Fornece uma API unificada para diferentes tipos de crawler,
    mantendo compatibilidade com a versão anterior.
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        self.config = config or CrawlerConfig.default()
        self.factory = CrawlerFactory()
        self.logger = logging.getLogger('ModularCrawler')
        self.current_crawler = None
    
    async def crawl_site(self, 
                        start_url: str,
                        crawler_type: str = CrawlerType.ASYNC) -> Dict[str, Any]:
        """
        Executa crawl completo de um site
        
        Args:
            start_url: URL inicial para o crawl
            crawler_type: Tipo de crawler a usar
            
        Returns:
            Estatísticas finais do crawl
        """
        self.logger.info(f"Starting modular crawl of {start_url}")
        
        # Cria crawler específico
        self.current_crawler = self.factory.create_crawler(
            crawler_type=crawler_type,
            config=self.config
        )
        
        try:
            # Executa crawl
            stats = await self.current_crawler.crawl_site(start_url)
            self.logger.info("Crawl completed successfully")
            return stats
            
        except Exception as e:
            self.logger.error(f"Crawl failed: {e}")
            raise
    
    async def crawl_multiple_sites(self, 
                                  urls: list,
                                  crawler_type: str = CrawlerType.ASYNC) -> Dict[str, Dict]:
        """
        Executa crawl de múltiplos sites
        
        Args:
            urls: Lista de URLs para crawl
            crawler_type: Tipo de crawler a usar
            
        Returns:
            Dict com estatísticas para cada site
        """
        results = {}
        
        for url in urls:
            self.logger.info(f"Starting crawl of {url}")
            try:
                result = await self.crawl_site(url, crawler_type)
                results[url] = result
            except Exception as e:
                self.logger.error(f"Failed to crawl {url}: {e}")
                results[url] = {'error': str(e)}
        
        return results
    
    def get_current_stats(self) -> Optional[Dict]:
        """Retorna estatísticas do crawl atual"""
        if self.current_crawler and hasattr(self.current_crawler, 'get_current_stats'):
            return self.current_crawler.get_current_stats()
        return None
    
    async def pause_current_crawl(self):
        """Pausa o crawl atual"""
        if self.current_crawler and hasattr(self.current_crawler, 'pause_crawl'):
            await self.current_crawler.pause_crawl()
    
    async def resume_current_crawl(self):
        """Resume o crawl atual"""
        if self.current_crawler and hasattr(self.current_crawler, 'resume_crawl'):
            await self.current_crawler.resume_crawl()
    
    def update_config(self, **kwargs):
        """Atualiza configuração do crawler"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self.logger.info(f"Config updated: {key} = {value}")
    
    @classmethod
    def with_preset(cls, preset: str) -> 'ModularCrawler':
        """
        Cria crawler com configuração preset
        
        Args:
            preset: Nome do preset ('default', 'fast', 'deep', 'safe')
        """
        presets = CrawlerFactory.get_preset_configs()
        config = presets.get(preset, CrawlerConfig.default())
        return cls(config)
    
    @classmethod
    def quick_setup(cls, max_pages: int = 100, max_depth: int = 2) -> 'ModularCrawler':
        """Setup rápido para crawls simples"""
        config = CrawlerConfig.fast()
        config.max_urls = max_pages
        config.max_depth = max_depth
        return cls(config)


# Função de compatibilidade com versão anterior
async def test_orchestrator():
    """Teste de compatibilidade com a função original"""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("🚀 Testando ModularCrawler...")
    print("🎯 Target: httpbin.org (max 20 URLs, depth 2)")
    
    try:
        # Cria crawler modular
        crawler = ModularCrawler.quick_setup(max_pages=20, max_depth=2)
        
        # Executa crawl
        final_stats = await crawler.crawl_site('https://httpbin.org')
        
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
        
    except Exception as e:
        print(f"💥 Erro durante teste: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Executa teste
    asyncio.run(test_orchestrator())