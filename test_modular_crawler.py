"""
Teste do Crawler Modular
Script de teste para validar a modularização do crawler
"""

import asyncio
import logging
import sys
from pathlib import Path

# Adiciona o diretório do projeto ao path
sys.path.insert(0, str(Path(__file__).parent / "seofrog"))

from seofrog.crawler import CrawlerFactory, CrawlerConfig, create_crawler, quick_crawl


async def test_basic_functionality():
    """Teste básico da funcionalidade modular"""
    print("Teste 1: Funcionalidade Basica")
    print("-" * 50)
    
    try:
        # Teste 1: Factory pattern
        factory = CrawlerFactory()
        config = CrawlerConfig.default()
        crawler = factory.create_crawler(config=config, max_urls=5, max_depth=1)
        
        print("OK Factory pattern")
        
        # Teste 2: Função de conveniência
        quick_crawler = create_crawler(preset='fast', max_urls=3)
        print("OK Funcao create_crawler")
        
        # Teste 3: Configurações preset
        presets = factory.get_preset_configs()
        print(f"OK Presets disponiveis: {list(presets.keys())}")
        
        return True
        
    except Exception as e:
        print(f"ERRO no teste basico: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_quick_crawl():
    """Teste da função quick_crawl"""
    print("\nTeste 2: Quick Crawl")
    print("-" * 50)
    
    try:
        # Configura logging apenas para este teste
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
        
        # Teste com um site simples
        print("Iniciando quick crawl de httpbin.org...")
        
        stats = await quick_crawl(
            url='https://httpbin.org',
            max_pages=5,
            max_depth=1,
            output_dir='./test_output'
        )
        
        # Verifica se retornou estatísticas válidas
        if 'crawl_summary' in stats:
            summary = stats['crawl_summary']
            print(f"OK Paginas crawled: {summary['total_pages']}")
            print(f"OK Taxa de sucesso: {summary['success_rate']:.2%}")
            print(f"OK Tempo total: {summary['total_time_seconds']:.2f}s")
            return True
        else:
            print("ERRO Estatisticas invalidas retornadas")
            return False
            
    except Exception as e:
        print(f"ERRO no quick crawl: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_configuration_flexibility():
    """Teste da flexibilidade de configuração"""
    print("\nTeste 3: Flexibilidade de Configuracao")
    print("-" * 50)
    
    try:
        # Teste diferentes configurações
        configs = {
            'fast': CrawlerConfig.fast(),
            'safe': CrawlerConfig.safe(), 
            'deep': CrawlerConfig.deep(),
            'custom': CrawlerConfig(
                max_workers=2,
                max_depth=1,
                max_urls=3,
                timeout=5
            )
        }
        
        factory = CrawlerFactory()
        
        for name, config in configs.items():
            crawler = factory.create_crawler(config=config)
            print(f"OK Configuracao '{name}': workers={config.max_workers}, "
                  f"depth={config.max_depth}, max_urls={config.max_urls}")
        
        return True
        
    except Exception as e:
        print(f"ERRO no teste de configuracao: {e}")
        return False


async def main():
    """Função principal de teste"""
    print("TESTE DO CRAWLER MODULAR")
    print("=" * 60)
    
    tests = [
        test_basic_functionality,
        test_configuration_flexibility,
        test_quick_crawl  # Este por último pois faz crawl real
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            print(f"ERRO Teste falhou com excecao: {e}")
    
    print("\n" + "=" * 60)
    print(f"RESULTADO DOS TESTES: {passed}/{total} passaram")
    
    if passed == total:
        print("Todos os testes passaram! Modularizacao bem-sucedida.")
    else:
        print("Alguns testes falharam. Verifique os erros acima.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)