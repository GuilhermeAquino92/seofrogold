"""
Result Saver System
Sistema de salvamento incremental com batching automático
"""

import asyncio
import csv
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import logging

from ..models.crawl_result import CrawlResult


class ResultSaver:
    """
    [DISK] Sistema de salvamento incremental com batching automático
    Previne perda de dados e otimiza I/O
    """
    
    def __init__(self, output_dir: str, batch_size: int = 100, format: str = "csv"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.batch_size = batch_size
        self.format = format
        self.buffer: List[CrawlResult] = []
        self.total_saved = 0
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger('ResultSaver')
        
        # Arquivo principal
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.main_file = self.output_dir / f"crawl_results_{timestamp}.{format}"
        self._init_file()
    
    def _init_file(self):
        """Inicializa arquivo com headers"""
        if self.format == "csv":
            self._init_csv_file()
        elif self.format == "json":
            self._init_json_file()
    
    def _init_csv_file(self):
        """Inicializa arquivo CSV com headers"""
        with open(self.main_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Headers baseados em CrawlResult
            headers = [
                'url', 'status_code', 'final_url', 'title', 'meta_description',
                'h1_count', 'h2_count', 'internal_links', 'external_links',
                'images_count', 'page_size', 'load_time', 'depth',
                'crawl_timestamp', 'redirect_type', 'is_clean_redirect',
                'is_external_redirect', 'errors'
            ]
            writer.writerow(headers)
        self.logger.info(f"CSV file initialized: {self.main_file}")
    
    def _init_json_file(self):
        """Inicializa arquivo JSON"""
        with open(self.main_file, 'w', encoding='utf-8') as f:
            f.write('[\n')  # Inicia array JSON
        self.logger.info(f"JSON file initialized: {self.main_file}")
    
    async def add_result(self, result: CrawlResult):
        """Adiciona resultado ao buffer e salva se necessário"""
        async with self.lock:
            self.buffer.append(result)
            self.logger.debug(f"Result added to buffer: {result.url}")
            
            if len(self.buffer) >= self.batch_size:
                await self._flush_buffer()
    
    async def _flush_buffer(self):
        """Salva buffer atual em disco"""
        if not self.buffer:
            return
        
        buffer_size = len(self.buffer)
        self.logger.info(f"Flushing {buffer_size} results to disk")
        
        try:
            if self.format == "csv":
                await self._save_csv_batch()
            elif self.format == "json":
                await self._save_json_batch()
            
            self.total_saved += buffer_size
            self.buffer.clear()
            self.logger.info(f"Successfully saved {buffer_size} results. Total: {self.total_saved}")
            
        except Exception as e:
            safe_error = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.error(f"Error flushing buffer: {safe_error}")
            raise
    
    async def _save_csv_batch(self):
        """Salva batch em CSV"""
        # Executa I/O em thread pool para não bloquear event loop
        loop = asyncio.get_event_loop()
        
        def write_batch():
            with open(self.main_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for result in self.buffer:
                    # Sanitização automática de campos string
                    safe_title = self._sanitize_field(result.title)
                    safe_meta_desc = self._sanitize_field(result.meta_description)
                    safe_errors = '; '.join(result.errors) if result.errors else ''
                    safe_errors = self._sanitize_field(safe_errors)
                    
                    row = [
                        result.url, result.status_code, result.final_url,
                        safe_title, safe_meta_desc,
                        result.h1_count, result.h2_count,
                        result.internal_links, result.external_links,
                        result.images_count, result.page_size, result.load_time,
                        result.depth, result.crawl_timestamp,
                        result.redirect_info.get('type', ''),
                        result.redirect_info.get('is_clean', False),
                        result.redirect_info.get('is_external', False),
                        safe_errors
                    ]
                    writer.writerow(row)
        
        await loop.run_in_executor(None, write_batch)
    
    async def _save_json_batch(self):
        """Salva batch em JSON"""
        loop = asyncio.get_event_loop()
        
        def write_batch():
            with open(self.main_file, 'a', encoding='utf-8') as f:
                for i, result in enumerate(self.buffer):
                    # Adiciona vírgula se não é o primeiro resultado total
                    if self.total_saved > 0 or i > 0:
                        f.write(',\n')
                    
                    # Sanitiza dados antes de salvar como JSON
                    result_dict = result.to_dict()
                    sanitized_dict = self._sanitize_dict_fields(result_dict)
                    json.dump(sanitized_dict, f, ensure_ascii=False, indent=2)
        
        await loop.run_in_executor(None, write_batch)
    
    async def finalize(self):
        """Força salvamento final do buffer"""
        async with self.lock:
            if self.buffer:
                self.logger.info("Finalizing - flushing remaining buffer")
                await self._flush_buffer()
            
            # Finaliza arquivo JSON
            if self.format == "json":
                await self._finalize_json()
            
            self.logger.info(f"Finalization complete. Total results saved: {self.total_saved}")
    
    async def _finalize_json(self):
        """Finaliza arquivo JSON fechando o array"""
        loop = asyncio.get_event_loop()
        
        def close_json():
            with open(self.main_file, 'a', encoding='utf-8') as f:
                f.write('\n]')  # Fecha array JSON
        
        await loop.run_in_executor(None, close_json)
    
    def get_stats(self) -> Dict:
        """Estatísticas do saver"""
        return {
            'total_saved': self.total_saved,
            'buffer_size': len(self.buffer),
            'batch_size': self.batch_size,
            'output_file': str(self.main_file),
            'format': self.format
        }
    
    async def export_to_excel(self, excel_path: str = None) -> str:
        """Exporta resultados para Excel (se disponível)"""
        if excel_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            excel_path = str(self.output_dir / f"crawl_results_{timestamp}.xlsx")
        
        try:
            import pandas as pd
            
            # Força flush do buffer antes de exportar
            async with self.lock:
                if self.buffer:
                    await self._flush_buffer()
            
            if self.format == "csv":
                # Lê CSV e converte para Excel
                loop = asyncio.get_event_loop()
                
                def convert_to_excel():
                    df = pd.read_csv(self.main_file)
                    df.to_excel(excel_path, index=False, engine='openpyxl')
                
                await loop.run_in_executor(None, convert_to_excel)
                
            self.logger.info(f"Results exported to Excel: {excel_path}")
            return excel_path
            
        except ImportError:
            self.logger.warning("pandas or openpyxl not available - Excel export skipped")
            return ""
        except Exception as e:
            safe_error = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.error(f"Error exporting to Excel: {safe_error}")
            raise
    
    def _sanitize_field(self, field) -> str:
        """
        Sanitiza campo string para prevenir problemas de encoding
        Aplicação da melhoria sugerida em implementar.txt
        """
        if field is None:
            return ''
        try:
            return str(field).encode('utf-8', errors='replace').decode('utf-8')
        except Exception:
            return str(field) if field else ''
    
    def _sanitize_dict_fields(self, data: Dict) -> Dict:
        """
        Sanitiza todos os campos string de um dicionário recursivamente
        """
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self._sanitize_field(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict_fields(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_field(item) if isinstance(item, str) else item for item in value]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def __len__(self) -> int:
        """Retorna total de resultados salvos + buffer"""
        return self.total_saved + len(self.buffer)