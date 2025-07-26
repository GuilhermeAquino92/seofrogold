import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "seofrog"))

from seofrog.crawler import quick_crawl

async def main():
    print("Iniciando teste simples do crawler modular...")
    
    try:
        stats = await quick_crawl(
            url='https://httpbin.org',
            max_pages=3,
            max_depth=1,
            output_dir='./resultado_teste'
        )
        
        print("✅ SUCESSO!")
        print(f"Páginas crawled: {stats['crawl_summary']['total_pages']}")
        print(f"Tempo: {stats['crawl_summary']['total_time_seconds']:.2f}s")
        print(f"Arquivo: {stats['saver_stats']['output_file']}")
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())