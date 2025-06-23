"""
seofrog/utils/logger.py
Sistema de logging enterprise do SEOFrog
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

class SEOFrogFormatter(logging.Formatter):
    """Formatter customizado para SEOFrog"""
    
    # Cores para console
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors
        super().__init__()
    
    def format(self, record):
        # Timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Level com cor se habilitado
        level = record.levelname
        if self.use_colors and level in self.COLORS:
            level = f"{self.COLORS[level]}{level:<8}{self.COLORS['RESET']}"
        else:
            level = f"{level:<8}"
        
        # Logger name truncado
        logger_name = record.name
        if len(logger_name) > 20:
            logger_name = logger_name[:17] + "..."
        logger_name = f"{logger_name:<20}"
        
        # Thread info se disponível
        thread_info = ""
        if hasattr(record, 'thread') and record.thread:
            thread_info = f"[T{record.thread}] "
        
        # Message
        message = record.getMessage()
        
        # Exception info se houver
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return f"{timestamp} | {level} | {logger_name} | {thread_info}{message}"

class PerformanceFilter(logging.Filter):
    """Filtro para logs de performance"""
    
    def filter(self, record):
        # Adiciona informações de performance se disponível
        if hasattr(record, 'url_count'):
            record.msg = f"[{record.url_count} URLs] {record.msg}"
        
        if hasattr(record, 'rate'):
            record.msg = f"{record.msg} ({record.rate:.1f} URLs/s)"
        
        return True

def setup_logging(
    level: str = "INFO",
    output_dir: str = "seofrog_output",
    log_filename: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configura sistema de logging enterprise
    
    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        output_dir: Diretório para arquivos de log
        log_filename: Nome customizado do arquivo (default: auto-gerado)
        max_file_size: Tamanho máximo do arquivo antes de rotacionar
        backup_count: Número de backups a manter
    
    Returns:
        Logger configurado
    """
    
    # Cria diretório se não existir
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Remove handlers existentes
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Determina filename se não fornecido
    if not log_filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"seofrog_{timestamp}.log"
    
    log_filepath = os.path.join(output_dir, log_filename)
    
    # === FILE HANDLER com rotação ===
    file_handler = logging.handlers.RotatingFileHandler(
        log_filepath,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, level.upper()))
    file_handler.setFormatter(SEOFrogFormatter(use_colors=False))
    file_handler.addFilter(PerformanceFilter())
    
    # === CONSOLE HANDLER ===
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # Console sempre INFO ou superior
    console_handler.setFormatter(SEOFrogFormatter(use_colors=True))
    
    # === ERROR HANDLER (arquivo separado) ===
    error_filepath = os.path.join(output_dir, f"seofrog_errors_{datetime.now().strftime('%Y%m%d')}.log")
    error_handler = logging.FileHandler(error_filepath, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(SEOFrogFormatter(use_colors=False))
    
    # === ROOT LOGGER CONFIG ===
    root_logger.setLevel(logging.DEBUG)  # Captura tudo, handlers filtram
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(error_handler)
    
    # === LOGGER PRINCIPAL ===
    main_logger = logging.getLogger('SEOFrog')
    main_logger.info(f"🚀 SEOFrog logging iniciado")
    main_logger.info(f"📁 Log file: {log_filepath}")
    main_logger.info(f"📊 Log level: {level}")
    main_logger.info(f"❌ Error log: {error_filepath}")
    
    return main_logger

def get_logger(name: str) -> logging.Logger:
    """Retorna logger para módulo específico"""
    return logging.getLogger(f'SEOFrog.{name}')

class CrawlProgressLogger:
    """Logger especializado para progresso de crawl"""
    
    def __init__(self, logger: logging.Logger, log_interval: int = 50):
        self.logger = logger
        self.log_interval = log_interval
        self.start_time = datetime.now()
        self.last_count = 0
        self.last_time = self.start_time
    
    def log_progress(self, current_count: int, total_target: int, queue_size: int = 0):
        """Log de progresso com estatísticas"""
        
        if current_count % self.log_interval == 0 or current_count == 1:
            now = datetime.now()
            
            # Calcula estatísticas
            elapsed = (now - self.start_time).total_seconds()
            rate = current_count / elapsed if elapsed > 0 else 0
            
            # Rate desde último log
            interval_elapsed = (now - self.last_time).total_seconds()
            interval_rate = (current_count - self.last_count) / interval_elapsed if interval_elapsed > 0 else 0
            
            # Estimativa de tempo restante
            if rate > 0:
                remaining_urls = total_target - current_count
                eta_seconds = remaining_urls / rate
                eta_formatted = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
            else:
                eta_formatted = "N/A"
            
            # Percentual
            percentage = (current_count / total_target * 100) if total_target > 0 else 0
            
            # Log com informações extras
            self.logger.info(
                f"📊 Progresso: {current_count:,}/{total_target:,} URLs ({percentage:.1f}%) | "
                f"Queue: {queue_size:,} | Rate: {rate:.1f} URLs/s (atual: {interval_rate:.1f}) | "
                f"ETA: {eta_formatted}",
                extra={'url_count': current_count, 'rate': rate}
            )
            
            self.last_count = current_count
            self.last_time = now
    
    def log_final_stats(self, total_crawled: int, success_count: int, error_count: int):
        """Log de estatísticas finais"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        avg_rate = total_crawled / elapsed if elapsed > 0 else 0
        success_rate = (success_count / total_crawled * 100) if total_crawled > 0 else 0
        
        self.logger.info(
            f"✅ Crawl finalizado! {total_crawled:,} URLs em {elapsed:.1f}s "
            f"(avg: {avg_rate:.1f} URLs/s) | Sucesso: {success_rate:.1f}% | "
            f"Erros: {error_count:,}"
        )

# === CONTEXT MANAGERS ===

class LogContext:
    """Context manager para logs temporários"""
    
    def __init__(self, logger: logging.Logger, context_name: str):
        self.logger = logger
        self.context_name = context_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"🔄 Iniciando {self.context_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.debug(f"✅ {self.context_name} concluído em {elapsed:.2f}s")
        else:
            self.logger.error(f"❌ {self.context_name} falhou em {elapsed:.2f}s: {exc_val}")

# === DECORATORS ===

def log_execution_time(logger: Optional[logging.Logger] = None):
    """Decorator para logar tempo de execução de funções"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            func_logger = logger or get_logger(func.__module__)
            
            try:
                result = func(*args, **kwargs)
                elapsed = (datetime.now() - start_time).total_seconds()
                func_logger.debug(f"⚡ {func.__name__} executado em {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = (datetime.now() - start_time).total_seconds()
                func_logger.error(f"❌ {func.__name__} falhou em {elapsed:.3f}s: {e}")
                raise
        
        return wrapper
    return decorator