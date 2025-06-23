"""
seofrog/exporters/sheets/erros_http.py
Aba específica para erros HTTP - BASEADO NO _create_status_problems_sheet() ORIGINAL
"""

import pandas as pd
from .base_sheet import BaseSheet

class ErrosHttpSheet(BaseSheet):
    """
    Sheet com problemas de status HTTP (diferentes de 200)
    Baseado exatamente no método _create_status_problems_sheet() original
    """
    
    def get_sheet_name(self) -> str:
        return 'Erros HTTP'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba de erros HTTP - IDÊNTICO ao método original
        """
        try:
            if 'status_code' not in df.columns:
                error_df = pd.DataFrame([['Coluna status_code não encontrada']], columns=['Erro'])
                error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                return
            
            # Filtra problemas de status de forma segura (exatamente como no original)
            status_problems = df[df['status_code'].fillna(0) != 200].copy()
            
            if not status_problems.empty:
                # Ordena por status code (exatamente como no original)
                status_problems = status_problems.sort_values('status_code')
                
                # Define colunas para exportar (exatamente como no original)
                cols = ['url', 'status_code', 'final_url', 'response_time']
                available_cols = [col for col in cols if col in status_problems.columns]
                
                if available_cols:
                    status_problems[available_cols].to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                    self.logger.info(f"✅ {self.get_sheet_name()}: {len(status_problems)} erros encontrados")
                else:
                    error_df = pd.DataFrame([['Colunas necessárias não encontradas']], columns=['Erro'])
                    error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            else:
                # Sucesso - nenhum erro encontrado (exatamente como no original)
                success_df = pd.DataFrame([['✅ Nenhum erro HTTP encontrado!']], columns=['Status'])
                success_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                self.logger.info(f"✅ {self.get_sheet_name()}: Nenhum erro HTTP encontrado")
                
        except Exception as e:
            self.logger.error(f"Erro criando aba de erros HTTP: {e}")
            error_df = pd.DataFrame([[f'Erro: {str(e)}']], columns=['Erro'])
            error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)