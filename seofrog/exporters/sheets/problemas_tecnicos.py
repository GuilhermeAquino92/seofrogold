"""
seofrog/exporters/sheets/problemas_tecnicos.py
Aba específica para problemas técnicos - BASEADO NO _create_technical_problems_sheet() ORIGINAL
"""

import pandas as pd
from .base_sheet import BaseSheet

class ProblemasTecnicosSheet(BaseSheet):
    """
    Sheet com problemas técnicos (canonical, viewport, charset, etc.)
    Baseado exatamente no método _create_technical_problems_sheet() original (versão completa)
    """
    
    def get_sheet_name(self) -> str:
        return 'Problemas Técnicos'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba de problemas técnicos - IDÊNTICO ao método original
        """
        try:
            technical_issues = []
            
            # URLs sem canonical (exatamente como no original)
            if 'canonical_url' in df.columns:
                no_canonical = df[df['canonical_url'].fillna('') == ''].copy()
                if not no_canonical.empty:
                    no_canonical['problema'] = 'Sem canonical'
                    no_canonical['criticidade'] = 'MÉDIO'
                    technical_issues.append(no_canonical)
            
            # URLs sem viewport (exatamente como no original)
            if 'has_viewport' in df.columns:
                no_viewport = df[df['has_viewport'].fillna(False) == False].copy()
                if not no_viewport.empty:
                    no_viewport['problema'] = 'Sem viewport'
                    no_viewport['criticidade'] = 'ALTO'
                    technical_issues.append(no_viewport)
            
            # URLs sem charset (exatamente como no original)
            if 'has_charset' in df.columns:
                no_charset = df[df['has_charset'].fillna(False) == False].copy()
                if not no_charset.empty:
                    no_charset['problema'] = 'Sem charset'
                    no_charset['criticidade'] = 'MÉDIO'
                    technical_issues.append(no_charset)
            
            # URLs com canonical não-self (exatamente como no original)
            if 'canonical_is_self' in df.columns:
                canonical_not_self = df[df['canonical_is_self'].fillna(True) == False].copy()
                if not canonical_not_self.empty:
                    canonical_not_self['problema'] = 'Canonical aponta para outra URL'
                    canonical_not_self['criticidade'] = 'BAIXO'
                    technical_issues.append(canonical_not_self)
            
            if technical_issues:
                # Concatena todos os problemas (exatamente como no original)
                all_tech_issues = pd.concat(technical_issues, ignore_index=True)
                all_tech_issues = all_tech_issues.drop_duplicates(subset=['url'], keep='first')
                
                # Define colunas para exportar (exatamente como no original)
                cols = ['url', 'problema', 'criticidade', 'canonical_url', 'has_viewport', 'has_charset']
                available_cols = [col for col in cols if col in all_tech_issues.columns]
                
                if available_cols:
                    all_tech_issues[available_cols].to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                    self.logger.info(f"✅ {self.get_sheet_name()}: {len(all_tech_issues)} problemas encontrados")
                else:
                    error_df = pd.DataFrame([['Colunas técnicas não encontradas']], columns=['Erro'])
                    error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            else:
                # Sucesso - nenhum problema encontrado (exatamente como no original)
                success_df = pd.DataFrame([['✅ Nenhum problema técnico encontrado!']], columns=['Status'])
                success_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                self.logger.info(f"✅ {self.get_sheet_name()}: Nenhum problema encontrado")
                
        except Exception as e:
            self.logger.error(f"Erro criando aba de problemas técnicos: {e}")
            error_df = pd.DataFrame([[f'Erro: {str(e)}']], columns=['Erro'])
            error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)