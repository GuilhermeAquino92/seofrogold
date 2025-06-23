"""
seofrog/exporters/sheets/problemas_meta.py
Aba específica para problemas de meta description - BASEADO NO _create_meta_problems_sheet() ORIGINAL
"""

import pandas as pd
from .base_sheet import BaseSheet

class ProblemasMetaSheet(BaseSheet):
    """
    Sheet com problemas de meta description (ausentes, longas, curtas)
    Baseado exatamente no método _create_meta_problems_sheet() original (versão completa)
    """
    
    def get_sheet_name(self) -> str:
        return 'Problemas Meta'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba de problemas de meta description - IDÊNTICO ao método original
        """
        try:
            meta_issues = []
            
            # URLs sem meta description (exatamente como no original)
            if 'meta_description' in df.columns:
                no_meta = df[df['meta_description'].fillna('') == ''].copy()
                if not no_meta.empty:
                    no_meta['problema'] = 'Sem meta description'
                    meta_issues.append(no_meta)
            
            # Meta descriptions muito longas (exatamente como no original)
            if 'meta_description_length' in df.columns:
                long_meta = df[df['meta_description_length'].fillna(0) > 160].copy()
                if not long_meta.empty:
                    long_meta['problema'] = 'Meta description muito longa (>160 chars)'
                    meta_issues.append(long_meta)
            
            # Meta descriptions muito curtas (exatamente como no original)
            if 'meta_description_length' in df.columns:
                short_meta = df[df['meta_description_length'].fillna(200) < 120].copy()
                if not short_meta.empty and 'meta_description' in df.columns:
                    # Só considera curta se não estiver vazia (lógica original)
                    short_meta_filtered = short_meta[short_meta['meta_description'].fillna('') != ''].copy()
                    if not short_meta_filtered.empty:
                        short_meta_filtered['problema'] = 'Meta description muito curta (<120 chars)'
                        meta_issues.append(short_meta_filtered)
            
            if meta_issues:
                # Concatena todos os problemas (exatamente como no original)
                all_meta_issues = pd.concat(meta_issues, ignore_index=True)
                all_meta_issues = all_meta_issues.drop_duplicates(subset=['url'], keep='first')
                
                # Define colunas para exportar (exatamente como no original)
                cols = ['url', 'problema', 'meta_description', 'meta_description_length']
                available_cols = [col for col in cols if col in all_meta_issues.columns]
                
                if available_cols:
                    all_meta_issues[available_cols].to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                    self.logger.info(f"✅ {self.get_sheet_name()}: {len(all_meta_issues)} problemas encontrados")
                else:
                    error_df = pd.DataFrame([['Colunas de meta não encontradas']], columns=['Erro'])
                    error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            else:
                # Sucesso - nenhum problema encontrado (exatamente como no original)
                success_df = pd.DataFrame([['✅ Nenhum problema de meta description!']], columns=['Status'])
                success_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                self.logger.info(f"✅ {self.get_sheet_name()}: Nenhum problema encontrado")
                
        except Exception as e:
            self.logger.error(f"Erro criando aba de problemas de meta: {e}")
            error_df = pd.DataFrame([[f'Erro: {str(e)}']], columns=['Erro'])
            error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)