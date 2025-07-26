#!/usr/bin/env python3
"""
SEOFrog v0.2 Enterprise - Main Entry Point com Sistema Anti-Perda
Versão modificada com proteção contra perda de dados
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import signal
import json
import pandas as pd

# Adiciona o diretório atual ao sys.path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from seofrog.cli import parse_cli_args
from seofrog.core.config import CrawlConfig, create_config_from_dict
from seofrog.core.crawler import SEOCrawler
from seofrog.exporters.csv_exporter import CSVExporter
from seofrog.exporters.excel_exporter import ExcelExporter
from seofrog.utils.logger import setup_logging, get_logger
from seofrog.utils.banner import print_banner
from seofrog.utils.validators import validate_system_requirements
from seofrog.exceptions import SEOFrogException, CrawlException, ConfigException


# ==========================================
# SISTEMA ANTI-PERDA INTEGRADO
# ==========================================

class CrawlRecoverySystem:
    """Sistema de recuperação integrado ao main"""
    
    def __init__(self, project_name: str = None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.project_name = project_name or f"crawl_{timestamp}"
        self.backup_dir = Path(f"recovery/{self.project_name}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.saved_results = []
        self.save_counter = 0
        self.start_time = datetime.now()
        self.logger = get_logger('Recovery')
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._emergency_handler)
        signal.signal(signal.SIGTERM, self._emergency_handler)
        
        self.logger.info(f"🛡️ Sistema Anti-Perda ativo: {self.backup_dir}")
    
    def add_result(self, result_data: dict):
        """Adiciona resultado e auto-save"""
        self.saved_results.append(result_data)
        self.save_counter += 1
        
        # Auto-save a cada 100 URLs
        if self.save_counter % 100 == 0:
            self._save_progress("auto_save")
            self.logger.info(f"💾 Auto-save: {self.save_counter} URLs processadas")
    
    def _save_progress(self, save_type: str = "manual"):
        """Salva progresso atual"""
        if not self.saved_results:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # CSV com dados
            csv_file = self.backup_dir / f"backup_{save_type}_{timestamp}.csv"
            df = pd.DataFrame(self.saved_results)
            df.to_csv(csv_file, index=False, encoding='utf-8')
            
            # JSON com estado
            state_file = self.backup_dir / f"state_{save_type}_{timestamp}.json"
            state = {
                'project_name': self.project_name,
                'save_type': save_type,
                'timestamp': timestamp,
                'start_time': self.start_time.isoformat(),
                'total_processed': len(self.saved_results),
                'last_url': self.saved_results[-1].get('url', 'N/A') if self.saved_results else None
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            # Limpa arquivos antigos (mantém 5 mais recentes)
            self._cleanup_old_files()
            
        except Exception as e:
            self.logger.error(f"❌ Erro salvando progresso: {e}")
    
    def _cleanup_old_files(self):
        """Remove arquivos antigos"""
        try:
            for pattern in ["backup_auto_save_*.csv", "state_auto_save_*.json"]:
                files = sorted(self.backup_dir.glob(pattern))
                if len(files) > 5:
                    for old_file in files[:-5]:
                        old_file.unlink()
        except Exception:
            pass
    
    def _emergency_handler(self, signum, frame):
        """Handler para emergências (Ctrl+C, kill)"""
        print(f"\n🚨 INTERRUPÇÃO DETECTADA! Salvando {len(self.saved_results)} resultados...")
        
        if self.saved_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            emergency_file = self.backup_dir / f"EMERGENCY_EXPORT_{timestamp}.csv"
            
            try:
                df = pd.DataFrame(self.saved_results)
                df.to_csv(emergency_file, index=False, encoding='utf-8')
                print(f"✅ DADOS SALVOS EM: {emergency_file}")
                print(f"📊 Total recuperado: {len(self.saved_results)} URLs")
            except Exception as e:
                print(f"💥 ERRO CRÍTICO NO SALVAMENTO: {e}")
        else:
            print("ℹ️  Nenhum dado para salvar")
        
        print("🛑 Encerrando...")
        sys.exit(0)
    
    def finalize(self):
        """Finalização com save completo"""
        if self.saved_results:
            self._save_progress("final")
            self.logger.info(f"✅ Crawl finalizado: {len(self.saved_results)} URLs processadas")
        return self.saved_results


# ==========================================
# HANDLERS COM RECOVERY INTEGRADO
# ==========================================

def handle_crawl_mode_with_recovery(url: str, config_dict: Dict) -> int:
    """Handler de crawl com sistema de recuperação integrado"""
    
    logger = get_logger('Main')
    
    try:
        # Cria configuração
        config = create_config_from_dict(config_dict)
        
        # Inicializa sistema de recuperação
        project_name = f"crawl_{url.replace('://', '_').replace('/', '_')}"
        recovery = CrawlRecoverySystem(project_name)
        
        # Inicializa crawler
        crawler = SEOCrawler(config)
        
        # ADICIONA PROTEÇÃO ANTI-LOOP
        from seofrog.core.loop_protection import integrate_loop_protection
        crawler = integrate_loop_protection(crawler, max_hours=12)
        
        logger.info(f"🚀 Iniciando crawl com proteção anti-perda + anti-loop: {url}")
        
        # Verifica se há crawl anterior para recuperar
        recovery_files = list(recovery.backup_dir.glob("EMERGENCY_EXPORT_*.csv"))
        if recovery_files:
            latest_recovery = max(recovery_files, key=lambda x: x.stat().st_mtime)
            response = input(f"\n🔄 Encontrado backup anterior: {latest_recovery.name}\nRecuperar dados? (y/n): ")
            
            if response.lower() == 'y':
                try:
                    recovered_df = pd.read_csv(latest_recovery)
                    logger.info(f"📁 Carregados {len(recovered_df)} resultados do backup")
                    for _, row in recovered_df.iterrows():
                        recovery.add_result(row.to_dict())
                    logger.info("✅ Backup recuperado com sucesso")
                except Exception as e:
                    logger.warning(f"⚠️ Erro recuperando backup: {e}")
        
        # Executa crawl
        results = crawler.crawl(url)
        
        # Adiciona resultados ao recovery system
        for result in results:
            recovery.add_result(result)
        
        # Finaliza recovery e obtém resultados completos
        final_results = recovery.finalize()
        
        if not final_results:
            logger.warning("⚠️ Nenhum resultado obtido")
            return 1
        
        # Exporta resultados
        export_format = config_dict.get('export_format', 'csv')
        
        if export_format == 'excel':
            exporter = ExcelExporter(config.output_dir)
            output_file = exporter.export_to_excel(final_results, url)
        else:
            exporter = CSVExporter(config.output_dir)
            output_file = exporter.export_crawl_data(final_results, url)
        
        # Estatísticas finais
        crawl_time = datetime.now() - recovery.start_time
        logger.info(f"✅ Crawl concluído em {crawl_time}")
        logger.info(f"📊 URLs processadas: {len(final_results):,}")
        logger.info(f"💾 Arquivo exportado: {output_file}")
        logger.info(f"🛡️ Backups salvos em: {recovery.backup_dir}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("⚠️ Crawl interrompido pelo usuário")
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


def handle_analyze_mode(analyze_file: str) -> int:
    """Handler para análise de arquivo existente (sem modificações)"""
    logger = get_logger('Main')
    
    try:
        from seofrog.analyzers.file_analyzer import FileAnalyzer
        
        analyzer = FileAnalyzer()
        result = analyzer.analyze_file(analyze_file)
        
        if result:
            logger.info(f"✅ Análise concluída: {result}")
            return 0
        else:
            logger.error("❌ Falha na análise do arquivo")
            return 1
            
    except ImportError as e:
        logger.error(f"❌ Erro de import: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Erro na análise: {e}")
        return 1


# ==========================================
# MAIN FUNCTION MODIFICADA
# ==========================================

def main() -> int:
    """Entry point principal do SEOFrog com sistema anti-perda"""
    
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
        
        # Se é crawl normal - USA VERSÃO COM RECOVERY
        if url:
            return handle_crawl_mode_with_recovery(url, config_dict)
        
        # Não deveria chegar aqui
        print("❌ Erro: Nenhuma ação válida especificada")
        return 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Operação interrompida pelo usuário")
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