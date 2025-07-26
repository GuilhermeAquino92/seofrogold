"""
Teste CLI do crawler modular
Script simples para testar o crawler via CLI
"""

import asyncio
import sys
from pathlib import Path

# Adiciona o diretório do projeto ao path
sys.path.insert(0, str(Path(__file__).parent / "seofrog"))

# Import das dependências necessárias
from seofrog.crawler import create_crawler, CrawlerConfig


async def test_cli_crawler():
    """Testa o crawler com configuração similar ao CLI"""
    
    # Simula argumentos do CLI
    url = "https://httpbin.org"
    max_urls = 5
    max_depth = 2
    output_dir = "./test_cli_output"
    
    print(f"Testando crawl de {url}")
    print(f"Configuracao: max_urls={max_urls}, max_depth={max_depth}")
    print(f"Output: {output_dir}")
    print("-" * 60)
    
    try:
        # Cria configuração baseada nos parâmetros CLI
        config = CrawlerConfig(
            max_urls=max_urls,
            max_depth=max_depth,
            max_workers=5,
            timeout=10,
            output_dir=output_dir,
            output_format="csv"
        )
        
        # Cria crawler
        crawler = create_crawler(config=config)
        
        print("OK Crawler criado com sucesso")
        
        # Executa crawl
        stats = await crawler.crawl_site(url)
        
        # Mostra resultados
        print("\n" + "="*60)
        print("RESULTADOS DO CRAWL:")
        print("="*60)
        
        summary = stats['crawl_summary']
        print(f"URLs processadas: {summary['total_pages']}")
        print(f"URLs com falha: {summary['failed_pages']}")
        print(f"Taxa de sucesso: {summary['success_rate']:.1%}")
        print(f"Tempo total: {summary['total_time_seconds']:.2f}s")
        print(f"Velocidade: {summary['pages_per_second']:.2f} paginas/s")
        
        print(f"\nArquivo gerado: {stats['saver_stats']['output_file']}")
        
        # Mostra estatísticas detalhadas
        print(f"\nEstatisticas da fila:")
        queue_stats = stats['queue_stats']
        print(f"   - URLs adicionadas: {queue_stats['urls_added']}")
        print(f"   - URLs processadas: {queue_stats['urls_processed']}")
        print(f"   - Rejeitadas (profundidade): {queue_stats['skipped_depth']}")
        print(f"   - Rejeitadas (duplicatas): {queue_stats['skipped_duplicate']}")
        
        print(f"\nEstatisticas HTTP:")
        http_stats = stats['http_engine_stats']
        print(f"   - Requests feitos: {http_stats['requests_made']}")
        print(f"   - Requests falharam: {http_stats['requests_failed']}")
        print(f"   - Tempo médio resposta: {http_stats['avg_response_time']:.3f}s")
        
        print("\nTeste concluido com sucesso!")
        return True
        
    except Exception as e:
        print(f"\nERRO durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Função principal"""
    print("TESTE CLI CRAWLER MODULAR")
    print("=" * 60)
    
    # Executa teste assíncrono
    success = asyncio.run(test_cli_crawler())
    
    if success:
        print("\nTodos os testes passaram!")
        print("O crawler modular esta funcionando corretamente.")
        print("Use: from seofrog.crawler import create_crawler")
    else:
        print("\nTeste falhou!")
        print("Verifique os erros acima.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())