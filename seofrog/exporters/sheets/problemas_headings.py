"""
seofrog/exporters/sheets/problemas_headings.py
Aba específica para problemas de headings - BASEADO NO _create_heading_problems_sheet() ORIGINAL
"""

import pandas as pd
from .base_sheet import BaseSheet

class ProblemasHeadingsSheet(BaseSheet):
    """
    Sheet com problemas de headings (sem H1, múltiplos H1, sem H2)
    Baseado exatamente no método _create_heading_problems_sheet() original (versão completa)
    """
    
    def get_sheet_name(self) -> str:
        return 'Problemas Headings'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba de problemas de headings - IDÊNTICO ao método original
        """
        try:
            heading_issues = []
            
            # URLs sem H1 (exatamente como no original)
            if 'h1_count' in df.columns:
                no_h1 = df[df['h1_count'].fillna(0) == 0].copy()
                if not no_h1.empty:
                    no_h1['problema'] = 'Sem H1'
                    no_h1['criticidade'] = 'CRÍTICO'
                    heading_issues.append(no_h1)
            
            # URLs com múltiplos H1 (exatamente como no original)
            if 'h1_count' in df.columns:
                multiple_h1 = df[df['h1_count'].fillna(0) > 1].copy()
                if not multiple_h1.empty:
                    multiple_h1['problema'] = 'Múltiplos H1'
                    multiple_h1['criticidade'] = 'ALTO'
                    heading_issues.append(multiple_h1)
            
            # URLs sem estrutura de headings (sem H2) (exatamente como no original)
            if 'h2_count' in df.columns:
                no_h2 = df[df['h2_count'].fillna(0) == 0].copy()
                if not no_h2.empty:
                    no_h2['problema'] = 'Sem H2'
                    no_h2['criticidade'] = 'MÉDIO'
                    heading_issues.append(no_h2)
            
            if heading_issues:
                # Concatena todos os problemas (exatamente como no original)
                all_heading_issues = pd.concat(heading_issues, ignore_index=True)
                all_heading_issues = all_heading_issues.drop_duplicates(subset=['url'], keep='first')
                
                # Define colunas para exportar (exatamente como no original)
                cols = ['url', 'problema', 'criticidade', 'h1_count', 'h2_count', 'h3_count']
                available_cols = [col for col in cols if col in all_heading_issues.columns]
                
                if available_cols:
                    all_heading_issues[available_cols].to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                    self.logger.info(f"✅ {self.get_sheet_name()}: {len(all_heading_issues)} problemas encontrados")
                else:
                    error_df = pd.DataFrame([['Colunas de headings não encontradas']], columns=['Erro'])
                    error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            else:
                # Sucesso - nenhum problema encontrado (exatamente como no original)
                success_df = pd.DataFrame([['✅ Estrutura de headings adequada!']], columns=['Status'])
                success_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                self.logger.info(f"✅ {self.get_sheet_name()}: Estrutura adequada")
                
        except Exception as e:
            self.logger.error(f"Erro criando aba de problemas de headings: {e}")
            error_df = pd.DataFrame([[f'Erro: {str(e)}']], columns=['Erro'])
            error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)