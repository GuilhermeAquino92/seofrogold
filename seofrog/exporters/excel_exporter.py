"""
seofrog/exporters/excel_exporter.py
Excel Exporter Enterprise do SEOFrog v0.2 - VERSÃO MODULAR COMPLETA
Usa todas as 12 sheets especializadas
"""

import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

# Imports de dependências opcionais
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

from seofrog.utils.logger import get_logger
from seofrog.core.exceptions import ExportException
from .excel_writer import ExcelWriter

# Imports de todas as sheets modulares
from .sheets.dados_completos import DadosCompletosSheet
from .sheets.resumo_executivo import ResumoExecutivoSheet
from .sheets.erros_http import ErrosHttpSheet
from .sheets.problemas_titulos import ProblemasTitulosSheet
from .sheets.problemas_meta import ProblemasMetaSheet
from .sheets.problemas_headings import ProblemasHeadingsSheet
from .sheets.h1_h2_ausentes import H1H2AusentesSheet
from .sheets.problemas_imagens import ProblemasImagensSheet
from .sheets.problemas_tecnicos import ProblemasTecnicosSheet
from .sheets.problemas_performance import ProblemasPerformanceSheet
from .sheets.mixed_content import MixedContentSheet
from .sheets.analise_tecnica import AnaliseTecnicaSheet

class ExcelExporter:
    """
    Exportador Excel Enterprise - VERSÃO MODULAR COMPLETA
    Usa arquitetura modular com 12 sheets especializadas
    """
    
    def __init__(self, output_dir: str = "seofrog_output"):
        self.output_dir = output_dir
        self.logger = get_logger('ExcelExporter')
        self.writer = ExcelWriter()
        
        # Cria diretório se não existir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Verifica dependências
        if not OPENPYXL_AVAILABLE:
            self.logger.warning("openpyxl não disponível. Install: pip install openpyxl")
        
        # Define ordem das sheets (mesma ordem do original)
        self.ALL_SHEETS = [
            DadosCompletosSheet,        # 1. Dados principais
            ResumoExecutivoSheet,       # 2. KPIs e estatísticas
            ErrosHttpSheet,             # 3. Status HTTP != 200
            ProblemasTitulosSheet,      # 4. Títulos problemáticos  
            ProblemasMetaSheet,         # 5. Meta descriptions problemáticas
            ProblemasHeadingsSheet,     # 6. Problemas de headings gerais
            H1H2AusentesSheet,          # 7. H1/H2 ausentes (crítico)
            ProblemasImagensSheet,      # 8. Imagens sem ALT/SRC
            ProblemasTecnicosSheet,     # 9. Canonical, viewport, charset
            ProblemasPerformanceSheet,  # 10. Páginas lentas/pesadas
            MixedContentSheet,          # 11. Problemas HTTPS/HTTP
            AnaliseTecnicaSheet,        # 12. Análise técnica final
        ]
    
    def export_results(self, crawl_data: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        Exporta dados para Excel usando arquitetura modular completa
        
        Args:
            crawl_data: Lista de dicionários com dados crawleados
            filename: Nome do arquivo (opcional)
            
        Returns:
            str: Caminho do arquivo gerado
        """
        try:
            if not crawl_data:
                raise ExportException("Nenhum dado para exportar")
            
            # Gera filename se não fornecido
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"seofrog_crawl_{timestamp}.xlsx"
            
            filepath = os.path.join(self.output_dir, filename)
            
            # Converte para DataFrame
            df = pd.DataFrame(crawl_data)
            if df.empty:
                raise ExportException("DataFrame vazio após conversão")
            
            # Log início do processo
            self.logger.info(f"🚀 Iniciando export modular: {len(df)} URLs")
            
            # Exporta usando arquitetura modular
            engine = 'openpyxl' if OPENPYXL_AVAILABLE else 'xlsxwriter'
            with pd.ExcelWriter(filepath, engine=engine) as writer:
                
                # === CRIA TODAS AS SHEETS MODULARES ===
                self._create_all_modular_sheets(df, writer)
                
                # === FORMATAÇÃO ===
                if OPENPYXL_AVAILABLE:
                    self.writer.format_workbook(writer)
            
            # Log estatísticas finais
            self._log_export_stats(df, filepath)
            return filepath
            
        except Exception as e:
            error_msg = f"Erro no export modular: {e}"
            self.logger.error(error_msg)
            raise ExportException(error_msg)
    
    def _create_all_modular_sheets(self, df: pd.DataFrame, writer):
        """
        Cria todas as sheets usando arquitetura modular
        """
        self.logger.info(f"📊 Criando {len(self.ALL_SHEETS)} sheets modulares...")
        
        sheets_created = 0
        sheets_failed = 0
        
        for i, sheet_class in enumerate(self.ALL_SHEETS, 1):
            try:
                # Instancia a sheet
                sheet_instance = sheet_class()
                sheet_name = sheet_instance.get_sheet_name()
                
                # Cria a sheet
                sheet_instance.create_sheet(df, writer)
                
                sheets_created += 1
                self.logger.debug(f"✅ [{i:2d}/12] {sheet_name}")
                
            except Exception as e:
                sheets_failed += 1
                sheet_name = getattr(sheet_class, '__name__', 'Unknown')
                self.logger.error(f"❌ [{i:2d}/12] {sheet_name}: {e}")
                
                # Cria sheet de erro como fallback
                try:
                    error_df = pd.DataFrame([[f'Erro criando {sheet_name}: {str(e)}']], columns=['Erro'])
                    error_df.to_excel(writer, sheet_name=f'Erro_{i}', index=False)
                except:
                    pass  # Se nem o fallback funcionar, continua
        
        # Log final
        if sheets_failed == 0:
            self.logger.info(f"🎉 Todas as {sheets_created} sheets criadas com sucesso!")
        else:
            self.logger.warning(f"⚠️ {sheets_created} sheets criadas, {sheets_failed} falharam")
    
    def _log_export_stats(self, df: pd.DataFrame, filepath: str):
        """
        Loga estatísticas detalhadas do export
        """
        total_rows = len(df)
        total_columns = len(df.columns)
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        
        self.logger.info(f"✅ Excel modular exportado: {filepath}")
        self.logger.info(f"📊 {total_rows:,} URLs × {total_columns} colunas ({file_size_mb:.1f} MB)")
        self.logger.info(f"🗂️ {len(self.ALL_SHEETS)} sheets especializadas")
        
        # Estatísticas por categoria
        self._log_category_stats(df)
    
    def _log_category_stats(self, df: pd.DataFrame):
        """
        Loga estatísticas por categoria de problemas
        """
        try:
            total_urls = len(df)
            
            # Status codes
            if 'status_code' in df.columns:
                errors = len(df[df['status_code'] != 200])
                if errors > 0:
                    self.logger.info(f"🚨 {errors} URLs com erros HTTP ({errors/total_urls*100:.1f}%)")
            
            # SEO crítico
            if 'title' in df.columns:
                no_titles = len(df[df['title'].fillna('') == ''])
                if no_titles > 0:
                    self.logger.info(f"📝 {no_titles} URLs sem título ({no_titles/total_urls*100:.1f}%)")
            
            if 'h1_count' in df.columns:
                no_h1 = len(df[df['h1_count'].fillna(0) == 0])
                if no_h1 > 0:
                    self.logger.info(f"🚨 {no_h1} URLs sem H1 ({no_h1/total_urls*100:.1f}%)")
            
            # Performance
            if 'response_time' in df.columns:
                slow_pages = len(df[df['response_time'].fillna(0) > 3])
                if slow_pages > 0:
                    self.logger.info(f"⚡ {slow_pages} páginas lentas ({slow_pages/total_urls*100:.1f}%)")
            
            # Mixed Content
            if 'total_mixed_content_count' in df.columns:
                mixed_content = len(df[df['total_mixed_content_count'].fillna(0) > 0])
                if mixed_content > 0:
                    self.logger.info(f"🔒 {mixed_content} URLs com Mixed Content ({mixed_content/total_urls*100:.1f}%)")
            
        except Exception as e:
            self.logger.debug(f"Erro calculando estatísticas: {e}")


# ==========================================
# FUNÇÃO AUXILIAR PARA USO EXTERNO
# ==========================================

def export_to_excel(crawl_data: List[Dict[str, Any]], 
                   output_dir: str = "seofrog_output", 
                   filename: Optional[str] = None) -> str:
    """
    Função auxiliar para exportar dados para Excel usando arquitetura modular
    
    Args:
        crawl_data: Lista de dicionários com dados do crawl
        output_dir: Diretório de saída
        filename: Nome do arquivo (opcional)
    
    Returns:
        Caminho do arquivo gerado
        
    Example:
        >>> data = [{'url': 'example.com', 'title': 'Test', 'status_code': 200}]
        >>> filepath = export_to_excel(data)
        >>> print(f"Excel gerado: {filepath}")
    """
    exporter = ExcelExporter(output_dir)
    return exporter.export_results(crawl_data, filename)


# ==========================================
# COMPATIBILIDADE COM VERSÃO ANTERIOR
# ==========================================

# Para manter compatibilidade com código existente que espera métodos específicos
class LegacyExcelExporter(ExcelExporter):
    """
    Wrapper para compatibilidade com versão anterior
    Mantém interface antiga mas usa arquitetura modular internamente
    """
    
    def export_data(self, data: List[Dict], domain: str, format_type: str = 'xlsx') -> str:
        """Método legacy - redireciona para nova arquitetura"""
        if format_type.lower() != 'xlsx':
            raise ValueError("LegacyExcelExporter só suporta formato xlsx")
        
        filename = f"seofrog_{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return self.export_results(data, filename)