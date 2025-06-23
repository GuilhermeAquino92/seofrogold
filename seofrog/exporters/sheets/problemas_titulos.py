"""
seofrog/exporters/sheets/problemas_titulos.py
Aba específica para problemas de títulos - BASEADO NO _create_title_problems_sheet() ORIGINAL
"""

import pandas as pd
from .base_sheet import BaseSheet

class ProblemasTitulosSheet(BaseSheet):
    """
    Sheet com problemas de títulos (ausentes, longos, curtos)
    Baseado exatamente no método _create_title_problems_sheet() original
    """
    
    def get_sheet_name(self) -> str:
        return 'Problemas Títulos'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba de problemas de títulos - IDÊNTICO ao método original
        """
        try:
            title_issues = []
            
            # URLs sem título (verificação segura - exatamente como no original)
            if 'title' in df.columns:
                no_title = df[df['title'].fillna('') == ''].copy()
                if not no_title.empty:
                    no_title['problema'] = 'Sem título'
                    title_issues.append(no_title)
            
            # Títulos muito longos (verificação segura - exatamente como no original)
            if 'title_length' in df.columns:
                long_titles = df[df['title_length'].fillna(0) > 60].copy()
                if not long_titles.empty:
                    long_titles['problema'] = 'Título muito longo (>60 chars)'
                    title_issues.append(long_titles)
            
            # Títulos muito curtos (exatamente como no original)
            if 'title_length' in df.columns:
                short_titles = df[df['title_length'].fillna(100) < 30].copy()
                if not short_titles.empty:
                    short_titles['problema'] = 'Título muito curto (<30 chars)'
                    title_issues.append(short_titles)
            
            if title_issues:
                # Concatena todos os problemas (exatamente como no original)
                all_title_issues = pd.concat(title_issues, ignore_index=True)
                all_title_issues = all_title_issues.drop_duplicates(subset=['url'], keep='first')
                
                # TODO: MELHORIA FUTURA (opcional para melhor UX):
                # all_title_issues.sort_values(by=['problema', 'title_length'], inplace=True)
                # Ordenaria por tipo de problema, depois por tamanho do título
                
                # Define colunas para exportar (exatamente como no original)
                cols = ['url', 'problema', 'title', 'title_length']
                available_cols = [col for col in cols if col in all_title_issues.columns]
                
                if available_cols:
                    all_title_issues[available_cols].to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                    self.logger.info(f"✅ {self.get_sheet_name()}: {len(all_title_issues)} problemas encontrados")
                else:
                    error_df = pd.DataFrame([['Colunas de título não encontradas']], columns=['Erro'])
                    error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            else:
                # Sucesso - nenhum problema encontrado (exatamente como no original)
                success_df = pd.DataFrame([['✅ Nenhum problema de título encontrado!']], columns=['Status'])
                success_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                self.logger.info(f"✅ {self.get_sheet_name()}: Nenhum problema encontrado")
                
        except Exception as e:
            self.logger.error(f"Erro criando aba de problemas de título: {e}")
            error_df = pd.DataFrame([[f'Erro: {str(e)}']], columns=['Erro'])
            error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)