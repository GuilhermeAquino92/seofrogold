"""
seofrog/exporters/sheets/resumo_executivo.py
Aba específica para resumo executivo - BASEADO NO _create_summary_sheet() ORIGINAL
"""

import pandas as pd
from .base_sheet import BaseSheet

class ResumoExecutivoSheet(BaseSheet):
    """
    Sheet com resumo executivo e KPIs principais
    Baseado exatamente no método _create_summary_sheet() original
    """
    
    def get_sheet_name(self) -> str:
        return 'Resumo Executivo'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba de resumo executivo - IDÊNTICO ao método original
        """
        try:
            summary_data = []
            total_urls = len(df)
            
            if total_urls == 0:
                self._create_error_sheet(writer, 'Nenhum dado para resumir')
                return
            
            summary_data.append(['Métrica', 'Valor', 'Percentual'])
            summary_data.append(['Total de URLs', total_urls, '100%'])
            
            # Status codes (exatamente como no original)
            if 'status_code' in df.columns:
                try:
                    status_counts = df['status_code'].value_counts()
                    for status, count in status_counts.head(10).items():  # Limita a 10 mais comuns
                        percentage = f"{count/total_urls*100:.1f}%"
                        summary_data.append([f'Status {status}', count, percentage])
                except Exception as e:
                    self.logger.warning(f"Erro processando status codes: {e}")
            
            # Problemas SEO básicos (exatamente como no original)
            self._add_seo_problems_to_summary(df, summary_data, total_urls)
            
            # Cria DataFrame do resumo
            if len(summary_data) > 1:
                summary_df = pd.DataFrame(summary_data[1:], columns=summary_data[0])
                summary_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                self.logger.info(f"✅ {self.get_sheet_name()}: {len(summary_df)} métricas")
            else:
                self._create_error_sheet(writer, 'Erro na criação do resumo')
                
        except Exception as e:
            self.logger.error(f"Erro criando resumo: {e}")
            self._create_error_sheet(writer, f'Erro: {str(e)}')
    
    def _add_seo_problems_to_summary(self, df: pd.DataFrame, summary_data: list, total_urls: int):
        """
        Adiciona problemas SEO ao resumo de forma segura - IDÊNTICO ao original
        """
        try:
            # Títulos
            if 'title' in df.columns:
                no_title = len(df[df['title'].fillna('') == ''])
                if no_title > 0:
                    summary_data.append(['URLs sem título', no_title, f"{no_title/total_urls*100:.1f}%"])
            
            # Meta descriptions
            if 'meta_description' in df.columns:
                no_meta = len(df[df['meta_description'].fillna('') == ''])
                if no_meta > 0:
                    summary_data.append(['URLs sem meta description', no_meta, f"{no_meta/total_urls*100:.1f}%"])
            
            # H1s
            if 'h1_count' in df.columns:
                no_h1 = len(df[df['h1_count'].fillna(0) == 0])
                if no_h1 > 0:
                    summary_data.append(['URLs sem H1', no_h1, f"{no_h1/total_urls*100:.1f}%"])
            
            # H2s
            if 'h2_count' in df.columns:
                no_h2 = len(df[df['h2_count'].fillna(0) == 0])
                if no_h2 > 0:
                    summary_data.append(['URLs sem H2', no_h2, f"{no_h2/total_urls*100:.1f}%"])
                    
        except Exception as e:
            self.logger.warning(f"Erro adicionando problemas SEO ao resumo: {e}")