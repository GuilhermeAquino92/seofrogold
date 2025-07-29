"""
seofrog/exporters/excel_exporter.py
Excel Exporter Enterprise do SEOFrog v0.2 - VERSÃO LIMPA E CORRETA
Usa arquitetura modular com 13 sheets especializadas
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
from .sheets.links_internos_redirect import LinksInternosRedirectSheet  # 🆕 Aba "Internal"

class ExcelExporter:
    """
    Exportador Excel Enterprise - VERSÃO MODULAR LIMPA
    Usa arquitetura modular com 13 sheets especializadas
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
        
        # Define ordem das sheets (arquitetura modular)
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
            LinksInternosRedirectSheet, # 12. 🆕 Aba "Internal" (links com redirects)
            AnaliseTecnicaSheet,        # 13. Análise técnica final
        ]
    
    def export_results(self, crawl_data: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        """
        Exporta dados para Excel usando arquitetura modular
        
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
            self.logger.info(f"Iniciando export modular: {len(df)} URLs")
            
            # Exporta usando arquitetura modular
            engine = 'openpyxl' if OPENPYXL_AVAILABLE else 'xlsxwriter'
            
            try:
                with pd.ExcelWriter(filepath, engine=engine) as writer:
                    
                    # === CRIA TODAS AS SHEETS MODULARES ===
                    self._create_all_modular_sheets(df, writer)
                    
                    # === FORMATAÇÃO (só com openpyxl) ===
                    if OPENPYXL_AVAILABLE and engine == 'openpyxl':
                        try:
                            self.writer.format_workbook(writer)
                        except Exception as format_error:
                            safe_error = str(format_error).encode('utf-8', errors='replace').decode('utf-8')
                            self.logger.warning(f"Erro na formatação: {safe_error}")
                            
            except Exception as write_error:
                safe_error = str(write_error).encode('utf-8', errors='replace').decode('utf-8')
                self.logger.error(f"Erro escrevendo Excel: {safe_error}")
                # Fallback: cria arquivo básico
                self._create_simple_fallback_excel(df, filepath)
            
            # Sanitização automática de campos antes de finalizar
            df = self._sanitize_dataframe_fields(df)
            
            # Log estatísticas finais
            self._log_export_stats(df, filepath)
            return filepath
            
        except Exception as e:
            safe_error = str(e).encode('utf-8', errors='replace').decode('utf-8')
            error_msg = f"Erro no export modular: {safe_error}"
            self.logger.error(error_msg)
            raise ExportException(error_msg)
    
    def _create_all_modular_sheets(self, df: pd.DataFrame, writer):
        """
        Cria todas as sheets usando arquitetura modular
        """
        self.logger.info(f"Criando {len(self.ALL_SHEETS)} sheets modulares...")
        
        sheets_created = 0
        sheets_failed = 0
        
        for i, sheet_class in enumerate(self.ALL_SHEETS, 1):
            try:
                # Instancia a sheet
                sheet_instance = sheet_class()
                sheet_name = sheet_instance.get_sheet_name()
                
                # Limita nome da sheet a 31 caracteres (limite Excel)
                safe_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
                
                # Cria a sheet
                sheet_instance.create_sheet(df, writer)
                
                sheets_created += 1
        
                self.logger.debug(f"OK [{i:2d}/13] {safe_sheet_name}")
                
            except Exception as e:
                sheets_failed += 1
                sheet_name = getattr(sheet_class, '__name__', 'Unknown')
                safe_error = str(e).encode('utf-8', errors='replace').decode('utf-8')[:100]
                self.logger.warning(f"WARN [{i:2d}/13] {sheet_name}: {safe_error}")
                
                # Se muitos erros, para de tentar
                if sheets_failed > 5:
                    self.logger.error("ERRO: Muitos erros nas sheets - abortando criacao modular")
                    break
        
        # Log final
        if sheets_failed == 0:
            self.logger.info(f"Todas as {sheets_created} sheets criadas com sucesso!")
        else:
            self.logger.warning(f"WARN: {sheets_created} sheets criadas, {sheets_failed} falharam")
    
    def _log_export_stats(self, df: pd.DataFrame, filepath: str):
        """
        Log estatísticas finais do export
        """
        file_size = os.path.getsize(filepath) / 1024 / 1024  # MB
        
        self.logger.info(f"Export Excel concluido!")
        self.logger.info(f"Arquivo: {filepath}")
        self.logger.info(f"URLs: {len(df):,}")
        self.logger.info(f"Sheets: {len(self.ALL_SHEETS)}")
        self.logger.info(f"Tamanho: {file_size:.2f} MB")
        
        # Estatísticas básicas dos dados
        self._log_basic_stats(df)
    
    def _log_basic_stats(self, df: pd.DataFrame):
        """
        Loga estatísticas básicas dos dados
        """
        try:
            total_urls = len(df)
            
            # Status codes
            if 'status_code' in df.columns:
                status_counts = df['status_code'].value_counts()
                self.logger.info(f"Status codes: {dict(status_counts.head(3))}")
                
                errors = len(df[df['status_code'] != 200])
                if errors > 0:
                    self.logger.info(f"URLs com erro: {errors} ({errors/total_urls*100:.1f}%)")
            
            # Redirects
            if 'final_url' in df.columns:
                redirects = len(df[df['url'] != df['final_url']])
                if redirects > 0:
                    self.logger.info(f"Redirects: {redirects} ({redirects/total_urls*100:.1f}%)")
            
            # SEO básico
            if 'title' in df.columns:
                no_titles = len(df[df['title'].fillna('').str.strip() == ''])
                if no_titles > 0:
                    self.logger.info(f"Sem titulo: {no_titles} ({no_titles/total_urls*100:.1f}%)")
            
            if 'h1_count' in df.columns:
                no_h1 = len(df[df['h1_count'].fillna(0) == 0])
                if no_h1 > 0:
                    self.logger.info(f"Sem H1: {no_h1} ({no_h1/total_urls*100:.1f}%)")
                    
        except Exception as e:
            safe_error = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.debug(f"Erro calculando estatísticas básicas: {safe_error}")
    
    def _sanitize_dataframe_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sanitização automática de campos para prevenir problemas de encoding
        Aplica proteção UTF-8 em todos os campos string
        """
        try:
            self.logger.debug("Aplicando sanitização automática de campos...")
            
            # Faz uma cópia para não modificar o original
            sanitized_df = df.copy()
            
            # Aplica sanitização em colunas string
            for column in sanitized_df.columns:
                if sanitized_df[column].dtype == 'object':  # String columns
                    sanitized_df[column] = sanitized_df[column].astype(str).apply(
                        lambda x: x.encode('utf-8', errors='replace').decode('utf-8') if pd.notna(x) else x
                    )
            
            self.logger.debug(f"Sanitização aplicada em {len(sanitized_df.columns)} colunas")
            return sanitized_df
            
        except Exception as e:
            safe_error = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.warning(f"Erro na sanitização automática: {safe_error}")
            return df  # Retorna original se falhar
    
    def _create_simple_fallback_excel(self, df: pd.DataFrame, filepath: str):
        """
        Cria um arquivo Excel simples como fallback
        """
        try:
            self.logger.info("Criando arquivo Excel simples como fallback...")
            
            # Usa xlsxwriter que é mais confiável
            with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
                # Sheet principal com dados básicos
                basic_columns = []
                for col in ['url', 'status_code', 'final_url', 'title', 'meta_description', 
                           'h1_count', 'h2_count', 'load_time', 'page_size', 'depth']:
                    if col in df.columns:
                        basic_columns.append(col)
                
                if basic_columns:
                    df[basic_columns].to_excel(writer, sheet_name='Dados_Completos', index=False)
                else:
                    df.to_excel(writer, sheet_name='Dados_Completos', index=False)
                
                # Sheet de resumo
                if 'status_code' in df.columns:
                    resumo_data = {
                        'Total_URLs': [len(df)],
                        'Status_200': [len(df[df['status_code'] == 200])],
                        'Erros_4xx_5xx': [len(df[df['status_code'] >= 400])],
                        'Com_Titulo': [len(df[df['title'].notna() & (df['title'].str.strip() != '')])],
                        'Sem_Titulo': [len(df[df['title'].isna() | (df['title'].str.strip() == '')])],
                    }
                    resumo_df = pd.DataFrame(resumo_data)
                    resumo_df.to_excel(writer, sheet_name='Resumo', index=False)
                
            self.logger.info("Arquivo Excel simples criado com sucesso")
            
        except Exception as e:
            safe_error = str(e).encode('utf-8', errors='replace').decode('utf-8')
            self.logger.error(f"Falha no fallback Excel: {safe_error}")
            # Último recurso: salva como CSV
            csv_path = filepath.replace('.xlsx', '_fallback.csv')
            df.to_csv(csv_path, index=False, encoding='utf-8')
            self.logger.info(f"Salvo como CSV: {csv_path}")
            raise ExportException(f"Não foi possível criar Excel, salvo como CSV: {csv_path}")


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