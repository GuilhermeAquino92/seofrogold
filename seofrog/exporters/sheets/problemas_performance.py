"""
seofrog/exporters/sheets/problemas_performance.py
Aba específica para problemas de performance - BASEADO NO _create_performance_problems_sheet() ORIGINAL
"""

import pandas as pd
from .base_sheet import BaseSheet

class ProblemasPerformanceSheet(BaseSheet):
    """
    Sheet com problemas de performance (páginas lentas, pesadas)
    Baseado exatamente no método _create_performance_problems_sheet() original (versão completa)
    """
    
    def get_sheet_name(self) -> str:
        return 'Problemas Performance'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba de problemas de performance - IDÊNTICO ao método original
        """
        try:
            perf_issues = []
            
            # Páginas lentas (>3 segundos) (exatamente como no original)
            if 'response_time' in df.columns:
                slow_pages = df[df['response_time'].fillna(0) > 3].copy()
                if not slow_pages.empty:
                    slow_pages['problema'] = 'Página lenta (>3s)'
                    slow_pages['criticidade'] = 'ALTO'
                    perf_issues.append(slow_pages)
            
            # Páginas muito lentas (>5 segundos) (exatamente como no original)
            if 'response_time' in df.columns:
                very_slow_pages = df[df['response_time'].fillna(0) > 5].copy()
                if not very_slow_pages.empty:
                    very_slow_pages['problema'] = 'Página muito lenta (>5s)'
                    very_slow_pages['criticidade'] = 'CRÍTICO'
                    perf_issues.append(very_slow_pages)
            
            # Páginas pesadas (>1MB) (exatamente como no original)
            if 'content_length' in df.columns:
                heavy_pages = df[df['content_length'].fillna(0) > 1048576].copy()  # 1MB
                if not heavy_pages.empty:
                    heavy_pages['problema'] = 'Página pesada (>1MB)'
                    heavy_pages['criticidade'] = 'MÉDIO'
                    heavy_pages['content_length_mb'] = heavy_pages['content_length'] / 1048576
                    perf_issues.append(heavy_pages)
            
            if perf_issues:
                # Concatena todos os problemas (exatamente como no original)
                all_perf_issues = pd.concat(perf_issues, ignore_index=True)
                all_perf_issues = all_perf_issues.drop_duplicates(subset=['url'], keep='first')
                
                # Ordena por tempo de resposta (mais lento primeiro) (exatamente como no original)
                if 'response_time' in all_perf_issues.columns:
                    all_perf_issues = all_perf_issues.sort_values('response_time', ascending=False)
                
                # Define colunas para exportar (exatamente como no original)
                cols = ['url', 'problema', 'criticidade', 'response_time', 'content_length', 'content_length_mb']
                available_cols = [col for col in cols if col in all_perf_issues.columns]
                
                if available_cols:
                    all_perf_issues[available_cols].to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                    self.logger.info(f"✅ {self.get_sheet_name()}: {len(all_perf_issues)} problemas encontrados")
                else:
                    error_df = pd.DataFrame([['Colunas de performance não encontradas']], columns=['Erro'])
                    error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            else:
                # Sucesso - nenhum problema encontrado (exatamente como no original)
                success_df = pd.DataFrame([['✅ Nenhum problema de performance encontrado!']], columns=['Status'])
                success_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                self.logger.info(f"✅ {self.get_sheet_name()}: Nenhum problema encontrado")
                
        except Exception as e:
            self.logger.error(f"Erro criando aba de problemas de performance: {e}")
            error_df = pd.DataFrame([[f'Erro: {str(e)}']], columns=['Erro'])
            error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)