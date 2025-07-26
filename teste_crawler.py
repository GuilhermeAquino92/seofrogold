"""
Teste Rápido do Crawler Modular
Como usar o crawler modularizado
"""

import asyncio
import sys
from pathlib import Path

# Adiciona o projeto ao path
sys.path.insert(0, str(Path(__file__).parent / "seofrog"))

from seofrog.crawler import create_crawler, quick_crawl, CrawlerConfig


async def exemplo_basico():
    """Exemplo básico de uso"""
    print("=== EXEMPLO BÁSICO ===")
    
    # Crawl rápido de 3 páginas
    stats = await quick_crawl(
        url='https://httpbin.org',
        max_pages=3,
        max_depth=1
    )
    
    print(f"Páginas crawled: {stats['crawl_summary']['total_pages']}")
    print(f"Arquivo: {stats['saver_stats']['output_file']}")


async def exemplo_avancado():
    """Exemplo com configuração personalizada"""
    print("\n=== EXEMPLO AVANÇADO ===")
    
    # Configuração personalizada
    config = CrawlerConfig(
        max_urls=10,
        max_depth=2,
        max_workers=5,
        timeout=15,
        output_dir="./meu_crawl",
        user_agent="MeuBot/1.0"
    )
    
    # Cria crawler
    crawler = create_crawler(config=config)
    
    # Executa crawl
    stats = await crawler.crawl_site('https://httpbin.org')
    
    print(f"Páginas crawled: {stats['crawl_summary']['total_pages']}")
    print(f"Tempo: {stats['crawl_summary']['total_time_seconds']:.2f}s")
    print(f"Arquivo: {stats['saver_stats']['output_file']}")


async def exemplo_presets():
    """Exemplo usando presets"""
    print("\n=== EXEMPLO COM PRESETS ===")
    
    # Teste com preset 'fast'
    crawler = create_crawler(preset='fast', max_urls=5)
    stats = await crawler.crawl_site('https://httpbin.org')
    
    print(f"Preset 'fast': {stats['crawl_summary']['total_pages']} páginas")


async def main():
    """Executa todos os exemplos"""
    print("TESTE DO CRAWLER MODULAR")
    print("=" * 50)
    
    try:
        await exemplo_basico()
        await exemplo_avancado() 
        await exemplo_presets()
        
        print("\n✅ Todos os testes funcionaram!")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Para testar, simplesmente execute:
    # python teste_crawler.py
    asyncio.run(main())