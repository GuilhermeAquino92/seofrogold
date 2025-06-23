"""
seofrog/exporters/sheets/h1_h2_ausentes.py
Aba específica para URLs sem H1 e/ou H2 - BASEADO NO _create_h1_h2_missing_sheet() ORIGINAL
"""

import pandas as pd
from .base_sheet import BaseSheet

class H1H2AusentesSheet(BaseSheet):
    """
    Sheet específica para URLs sem H1 e/ou H2 - análise focada nos mais críticos
    Baseado exatamente no método _create_h1_h2_missing_sheet() original (versão completa)
    """
    
    def get_sheet_name(self) -> str:
        return 'H1 H2 Ausentes'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba específica para H1/H2 ausentes - IDÊNTICO ao método original
        """
        try:
            h1_h2_issues = []
            
            # URLs sem H1 (crítico) - exatamente como no original
            if 'h1_count' in df.columns:
                no_h1 = df[df['h1_count'].fillna(0) == 0].copy()
                if not no_h1.empty:
                    no_h1['problema_h1_h2'] = 'Sem H1'
                    no_h1['criticidade'] = 'CRÍTICO'
                    no_h1['prioridade'] = 1
                    h1_h2_issues.append(no_h1)
            
            # URLs sem H2 (alto) - exatamente como no original
            if 'h2_count' in df.columns:
                no_h2 = df[df['h2_count'].fillna(0) == 0].copy()
                if not no_h2.empty:
                    no_h2['problema_h1_h2'] = 'Sem H2'
                    no_h2['criticidade'] = 'ALTO'
                    no_h2['prioridade'] = 2
                    h1_h2_issues.append(no_h2)
            
            # URLs sem H1 NEM H2 (crítico máximo) - exatamente como no original
            if 'h1_count' in df.columns and 'h2_count' in df.columns:
                no_h1_h2 = df[(df['h1_count'].fillna(0) == 0) & (df['h2_count'].fillna(0) == 0)].copy()
                if not no_h1_h2.empty:
                    no_h1_h2['problema_h1_h2'] = 'Sem H1 E sem H2'
                    no_h1_h2['criticidade'] = 'CRÍTICO MÁXIMO'
                    no_h1_h2['prioridade'] = 0
                    h1_h2_issues.append(no_h1_h2)
            
            if h1_h2_issues:
                # Concatena todos os problemas (exatamente como no original)
                all_h1_h2_issues = pd.concat(h1_h2_issues, ignore_index=True)
                all_h1_h2_issues = all_h1_h2_issues.drop_duplicates(subset=['url'], keep='first')
                
                # Ordena por prioridade (crítico máximo primeiro) - exatamente como no original
                if 'prioridade' in all_h1_h2_issues.columns:
                    all_h1_h2_issues = all_h1_h2_issues.sort_values('prioridade')
                
                # Define colunas para exportar (exatamente como no original)
                cols = ['url', 'problema_h1_h2', 'criticidade', 'h1_count', 'h2_count', 'h1_text']
                available_cols = [col for col in cols if col in all_h1_h2_issues.columns]
                
                if available_cols:
                    all_h1_h2_issues[available_cols].to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                    self.logger.info(f"✅ {self.get_sheet_name()}: {len(all_h1_h2_issues)} problemas encontrados")
                else:
                    error_df = pd.DataFrame([['Colunas H1/H2 não encontradas']], columns=['Erro'])
                    error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            else:
                # Sucesso - nenhum problema encontrado (exatamente como no original)
                success_df = pd.DataFrame([['✅ Estrutura de H1/H2 adequada!']], columns=['Status'])
                success_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                self.logger.info(f"✅ {self.get_sheet_name()}: Estrutura adequada")
                
        except Exception as e:
            self.logger.error(f"Erro criando aba H1/H2 ausentes: {e}")
            error_df = pd.DataFrame([[f'Erro: {str(e)}']], columns=['Erro'])
            error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)