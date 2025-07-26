"""
Teste simples do crawler modular sem usar o CLI corrompido
"""

import asyncio
import sys
from pathlib import Path

# Adiciona o projeto ao path
sys.path.insert(0, str(Path(__file__).parent / "seofrog"))

from seofrog.crawler import create_crawler, CrawlerConfig

async def main():
    """Teste simples sem CLI"""
    print("Testando crawler modular diretamente...")
    
    try:
        # Configuração simples
        config = CrawlerConfig(
            max_urls=5,
            max_depth=2,
            max_workers=3,
            timeout=10,
            output_dir="./teste_direto",
            output_format="csv"
        )
        
        # Cria e executa crawler
        crawler = create_crawler(config=config)
        stats = await crawler.crawl_site('https://www.alastin.com.br/')
        
        print("SUCESSO!")
        print(f"Paginas crawled: {stats['crawl_summary']['total_pages']}")
        print(f"Tempo: {stats['crawl_summary']['total_time_seconds']:.2f}s")
        print(f"Arquivo: {stats['saver_stats']['output_file']}")
        
        return True
        
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    print("Teste concluido:", "OK" if success else "FALHOU")