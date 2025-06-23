#!/usr/bin/env python3
"""
seofrog/main.py
Entry Point Principal do SEOFrog v0.2 Enterprise - VERSÃO CORRIGIDA
"""

import sys
import os
from pathlib import Path
from typing import Optional

# Add seofrog to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from .cli import parse_cli_args, get_config_for_seofrog
from seofrog.utils.logger import setup_logging, get_logger, CrawlProgressLogger
from seofrog.core.exceptions import SEOFrogException, ConfigException
from seofrog.analyzers.seo_analyzer import analyze_crawl_results

def print_banner():
    """Banner do SEOFrog"""
    banner = """
🐸 =====================================================
   SEOFrog v0.2 Enterprise 
   Professional Screaming Frog Clone
   Enterprise-grade web crawler for SEO analysis
🐸 =====================================================
"""
    print(banner)

def validate_system_requirements():
    """Valida requisitos do sistema"""
    try:
        import platform
        import psutil
        
        # Verifica Python version
        if sys.version_info < (3, 9):
            raise SystemError("SEOFrog requer Python 3.9 ou superior")
        
        # Verifica memória disponível
        memory_gb = psutil.virtual_memory().total / (1024**3)
        if memory_gb < 1:
            print("⚠️  Aviso: Sistema com menos de 1GB RAM - performance pode ser limitada")
        
        # Verifica espaço em disco
        disk_free_gb = psutil.disk_usage('.').free / (1024**3)
        if disk_free_gb < 0.5:
            print("⚠️  Aviso: Menos de 500MB de espaço livre - exports podem falhar")
            
    except ImportError:
        print("⚠️  Aviso: psutil não disponível - não foi possível verificar recursos do sistema")
    except Exception as e:
        print(f"⚠️  Aviso: Erro verificando sistema: {e}")

def handle_analyze_mode(analyze_file: str) -> int:
    """Handle do modo de análise"""
    logger = get_logger('Analyzer')
    
    try:
        if not os.path.exists(analyze_file):
            logger.error(f"❌ Arquivo não encontrado: {analyze_file}")
            return 1
        
        logger.info(f"📊 Analisando arquivo: {analyze_file}")
        analyze_crawl_results(analyze_file)
        logger.info("✅ Análise concluída")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erro na análise: {e}")
        return 1

def handle_crawl_mode(url: str, config_dict: dict) -> int:
    """Handle do modo de crawl"""
    
    # Inicializa logger primeiro
    logger = get_logger('Main')
    
    try:
        # Converte dict para CrawlConfig
        config = get_config_for_seofrog(config_dict)
        
        logger.info(f"🎯 Iniciando crawl: {url}")
        logger.info(f"📊 Configuração: {config.max_urls:,} URLs, {config.max_depth} depth, {config.max_workers} workers")
        
        # Importa e executa core engine
        from seofrog.core.crawler import SEOFrog
        
        seofrog = SEOFrog(config)
        results = seofrog.crawl(url)
        
        if not results:
            logger.error("❌ Nenhum resultado obtido")
            return 1
        
        # Mostra estatísticas
        stats = seofrog.get_stats()
        print(f"\n📊 ESTATÍSTICAS DO CRAWL:")
        print(f"   URLs processadas: {stats['total_urls_crawled']:,}")
        print(f"   Tempo total: {stats['elapsed_time']:.1f}s")
        print(f"   Taxa de crawl: {stats['crawl_rate']:.1f} URLs/s")
        
        # Status codes distribution
        status_codes = stats.get('status_codes', {})
        print(f"\n📈 DISTRIBUIÇÃO DE STATUS CODES:")
        for status, count in sorted(status_codes.items()):
            print(f"   {status}: {count:,} URLs")
        
        # Se não for stats-only, faz export
        if not config_dict.get('stats_only', False):
            # Define formato (xlsx por padrão)
            export_format = config_dict.get('format', 'xlsx')
            
            output_file = seofrog.export_results(
                format=export_format,
                filename=config_dict.get('filename')
            )
            if output_file:
                print(f"\n💾 Resultados exportados: {output_file}")
                
                # Export adicional de issues (sempre CSV para simplicidade)
                try:
                    issues_file = seofrog.exporter.export_issues_only(results)
                    print(f"⚠️  Issues exportados: {issues_file}")
                except Exception as e:
                    logger.warning(f"Não foi possível exportar issues: {e}")
                    
            else:
                logger.error("❌ Erro na exportação")
                return 1
        
        print(f"\n✅ SEOFrog crawl finalizado com sucesso!")
        return 0
        
    except ImportError as e:
        logger.error(f"❌ Erro de import: {e}")
        logger.error("💡 Instale as dependências: pip install beautifulsoup4 lxml pandas requests")
        return 1
    except ConfigException as e:
        logger.error(f"❌ Erro de configuração: {e}")
        return 1
    except SEOFrogException as e:
        logger.error(f"❌ Erro SEOFrog: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {e}")
        return 1

def main() -> int:
    """Entry point principal do SEOFrog"""
    
    try:
        # Banner e validações
        print_banner()
        validate_system_requirements()
        
        # Parse argumentos CLI
        url, config_dict = parse_cli_args()
        
        # Setup logging baseado na configuração
        log_level = config_dict.get('log_level', 'INFO')
        output_dir = config_dict.get('output_dir', 'seofrog_output')
        setup_logging(level=log_level, output_dir=output_dir)
        
        # Se é análise de arquivo existente
        if config_dict.get('analyze_file'):
            return handle_analyze_mode(config_dict['analyze_file'])
        
        # Se é crawl normal
        if url:
            return handle_crawl_mode(url, config_dict)
        
        # Não deveria chegar aqui
        print("❌ Erro: Nenhuma ação válida especificada")
        return 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Operação interrompida pelo usuário")
        return 0
    except SystemExit as e:
        return e.code if hasattr(e, 'code') else 0
    except Exception as e:
        print(f"\n❌ Erro crítico no main: {e}")
        return 1

def cli_entry_point():
    """Entry point para console script"""
    sys.exit(main())

if __name__ == "__main__":
    sys.exit(main())