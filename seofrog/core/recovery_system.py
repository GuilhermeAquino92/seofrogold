# seofrog/core/recovery_system.py
"""
Sistema de Recuperação e Persistência Anti-Perda
Previne perda de dados por falhas de conexão/erro
"""

import json
import pickle
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import pandas as pd
from threading import Timer, Lock

class CrawlerRecoverySystem:
    """Sistema de recuperação que salva progresso automaticamente"""
    
    def __init__(self, project_name: str, auto_save_interval: int = 300):
        self.project_name = project_name
        self.auto_save_interval = auto_save_interval  # 5 minutos
        self.data_lock = Lock()
        
        # Diretórios de recuperação
        self.recovery_dir = Path(f"recovery/{project_name}")
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
        
        # Estado do crawler
        self.crawl_data = []
        self.processed_urls = set()
        self.pending_urls = []
        self.start_time = datetime.now()
        self.last_save_time = datetime.now()
        
        # Timer para auto-save
        self.auto_save_timer = None
        self._start_auto_save()
        
    def _start_auto_save(self):
        """Inicia timer de auto-save"""
        if self.auto_save_timer:
            self.auto_save_timer.cancel()
        
        self.auto_save_timer = Timer(self.auto_save_interval, self._auto_save)
        self.auto_save_timer.daemon = True
        self.auto_save_timer.start()
    
    def _auto_save(self):
        """Auto-save periódico"""
        try:
            self.save_progress("auto_save")
            print(f"🔄 Auto-save: {len(self.crawl_data)} URLs processadas")
        except Exception as e:
            print(f"❌ Erro no auto-save: {e}")
        finally:
            self._start_auto_save()  # Reagenda próximo save
    
    def add_crawl_result(self, url: str, data: Dict[str, Any]):
        """Adiciona resultado do crawl"""
        with self.data_lock:
            self.crawl_data.append(data)
            self.processed_urls.add(url)
            
            # Save a cada 100 URLs processadas
            if len(self.crawl_data) % 100 == 0:
                self.save_progress("batch_100")
                print(f"💾 Checkpoint: {len(self.crawl_data)} URLs salvas")
    
    def update_pending_urls(self, urls: List[str]):
        """Atualiza lista de URLs pendentes"""
        with self.data_lock:
            self.pending_urls = [url for url in urls if url not in self.processed_urls]
    
    def save_progress(self, save_type: str = "manual"):
        """Salva progresso atual"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Estado completo
        state = {
            'project_name': self.project_name,
            'save_type': save_type,
            'timestamp': timestamp,
            'start_time': self.start_time.isoformat(),
            'crawl_data': self.crawl_data,
            'processed_urls': list(self.processed_urls),
            'pending_urls': self.pending_urls,
            'progress': {
                'processed': len(self.processed_urls),
                'pending': len(self.pending_urls),
                'total': len(self.processed_urls) + len(self.pending_urls)
            }
        }
        
        # Salva estado completo
        state_file = self.recovery_dir / f"state_{timestamp}.json"
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False, default=str)
        
        # Salva dados em formato CSV (fallback)
        if self.crawl_data:
            csv_file = self.recovery_dir / f"dados_parciais_{timestamp}.csv"
            df = pd.DataFrame(self.crawl_data)
            df.to_csv(csv_file, index=False, encoding='utf-8')
        
        # Mantém apenas últimos 5 saves
        self._cleanup_old_saves()
        
        self.last_save_time = datetime.now()
        return state_file
    
    def _cleanup_old_saves(self):
        """Remove saves antigos, mantém apenas os 5 mais recentes"""
        try:
            state_files = sorted(self.recovery_dir.glob("state_*.json"))
            csv_files = sorted(self.recovery_dir.glob("dados_parciais_*.csv"))
            
            # Remove files antigos
            for files_list in [state_files, csv_files]:
                if len(files_list) > 5:
                    for old_file in files_list[:-5]:
                        old_file.unlink()
        except Exception as e:
            print(f"⚠️ Erro limpando saves antigos: {e}")
    
    def load_last_state(self) -> Optional[Dict]:
        """Carrega último estado salvo"""
        try:
            state_files = sorted(self.recovery_dir.glob("state_*.json"))
            if not state_files:
                return None
            
            latest_state = state_files[-1]
            with open(latest_state, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Restaura estado
            self.crawl_data = state.get('crawl_data', [])
            self.processed_urls = set(state.get('processed_urls', []))
            self.pending_urls = state.get('pending_urls', [])
            
            print(f"🔄 Estado restaurado: {len(self.crawl_data)} URLs processadas")
            return state
            
        except Exception as e:
            print(f"❌ Erro carregando estado: {e}")
            return None
    
    def emergency_export(self, error_msg: str = "Erro desconhecido"):
        """Exportação de emergência em caso de erro crítico"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Dados de emergência
            emergency_data = {
                'error': error_msg,
                'timestamp': timestamp,
                'processed_count': len(self.crawl_data),
                'data': self.crawl_data
            }
            
            # CSV de emergência
            if self.crawl_data:
                emergency_csv = self.recovery_dir / f"EMERGENCY_EXPORT_{timestamp}.csv"
                df = pd.DataFrame(self.crawl_data)
                df.to_csv(emergency_csv, index=False, encoding='utf-8')
                print(f"🚨 EXPORTAÇÃO DE EMERGÊNCIA: {emergency_csv}")
                return emergency_csv
            
        except Exception as e:
            print(f"💥 FALHA NA EXPORTAÇÃO DE EMERGÊNCIA: {e}")
        
        return None
    
    def get_recovery_info(self) -> Dict:
        """Informações sobre possível recuperação"""
        state_files = list(self.recovery_dir.glob("state_*.json"))
        csv_files = list(self.recovery_dir.glob("dados_parciais_*.csv"))
        emergency_files = list(self.recovery_dir.glob("EMERGENCY_EXPORT_*.csv"))
        
        return {
            'has_recovery': len(state_files) > 0,
            'state_files': len(state_files),
            'csv_files': len(csv_files),
            'emergency_files': len(emergency_files),
            'latest_save': max(state_files).stat().st_mtime if state_files else None
        }
    
    def cleanup(self):
        """Limpeza final - cancela timers"""
        if self.auto_save_timer:
            self.auto_save_timer.cancel()


# seofrog/core/enhanced_crawler.py  
"""
Crawler Enhanced com Sistema de Recuperação
"""

from .crawler import SEOCrawler
from .recovery_system import CrawlerRecoverySystem
import signal
import sys

class RecoverableCrawler(SEOCrawler):
    """Crawler com capacidade de recuperação"""
    
    def __init__(self, config, project_name: str = None):
        super().__init__(config)
        self.project_name = project_name or f"crawl_{datetime.now().strftime('%Y%m%d_%H%M')}"
        self.recovery_system = CrawlerRecoverySystem(self.project_name)
        
        # Handler para interrupções
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handler para Ctrl+C e kill"""
        print(f"\n🛑 Interrupção detectada (signal {signum})")
        self._safe_shutdown()
        sys.exit(0)
    
    def _safe_shutdown(self):
        """Shutdown seguro com save dos dados"""
        try:
            print("💾 Salvando progresso antes de sair...")
            self.recovery_system.save_progress("shutdown")
            
            # Exportação de emergência se houver dados
            if self.recovery_system.crawl_data:
                emergency_file = self.recovery_system.emergency_export("Interrupção manual")
                print(f"🚨 Dados salvos em: {emergency_file}")
                
        except Exception as e:
            print(f"❌ Erro no shutdown: {e}")
        finally:
            self.recovery_system.cleanup()
    
    def crawl_url(self, url: str, depth: int) -> Optional[Dict]:
        """Override com recovery system"""
        try:
            # Crawl normal
            result = super().crawl_url(url, depth)
            
            if result:
                # Adiciona ao recovery system
                self.recovery_system.add_crawl_result(url, result)
            
            return result
            
        except Exception as e:
            # Em caso de erro, tenta salvar dados parciais
            print(f"❌ Erro no crawl de {url}: {e}")
            
            # Exportação de emergência
            if self.recovery_system.crawl_data:
                self.recovery_system.emergency_export(f"Erro no crawl: {str(e)}")
            
            raise e
    
    def start_crawling(self, seed_urls: List[str]):
        """Inicia crawling com verificação de recuperação"""
        try:
            # Verifica se há estado anterior
            recovery_info = self.recovery_system.get_recovery_info()
            
            if recovery_info['has_recovery']:
                response = input(f"🔄 Encontrado save anterior. Recuperar? (y/n): ")
                if response.lower() == 'y':
                    state = self.recovery_system.load_last_state()
                    if state:
                        print(f"✅ Recuperado: {len(state['crawl_data'])} URLs já processadas")
                        # Filtra URLs já processadas
                        remaining_urls = [url for url in seed_urls if url not in self.recovery_system.processed_urls]
                        seed_urls = remaining_urls
            
            # Atualiza URLs pendentes
            self.recovery_system.update_pending_urls(seed_urls)
            
            # Inicia crawling normal
            return super().start_crawling(seed_urls)
            
        except KeyboardInterrupt:
            self._safe_shutdown()
        except Exception as e:
            print(f"💥 ERRO CRÍTICO: {e}")
            self.recovery_system.emergency_export(f"Erro crítico: {str(e)}")
            raise e


# Exemplo de uso simples:
if __name__ == "__main__":
    from seofrog.config import CrawlConfig
    
    config = CrawlConfig(
        max_pages=1000,
        timeout=30,
        retry_attempts=3
    )
    
    crawler = RecoverableCrawler(config, project_name="meu_site_crawl")
    
    seed_urls = ["https://example.com"]
    results = crawler.start_crawling(seed_urls)