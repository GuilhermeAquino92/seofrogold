"""
seofrog/exporters/sheets/analise_tecnica.py
Aba específica para análise técnica completa - BASEADO NO _create_technical_sheet() ORIGINAL
"""

import pandas as pd
from .base_sheet import BaseSheet

class AnaliseTecnicaSheet(BaseSheet):
    """
    Sheet com análise técnica completa - aba final
    Baseado exatamente no método _create_technical_sheet() original
    """
    
    def get_sheet_name(self) -> str:
        return 'Análise Técnica'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba de análise técnica - IDÊNTICO ao método original
        """
        try:
            # Define colunas técnicas importantes (exatamente como no original)
            tech_columns = [
                'url', 'status_code', 'final_url', 'content_type',
                'canonical_url', 'canonical_is_self', 'meta_robots',
                'has_viewport', 'has_charset', 'has_favicon',
                'schema_total_count', 'og_tags_count', 'twitter_tags_count',
                'hreflang_count', 'response_time', 'content_length'
            ]
            
            # Filtra apenas colunas que existem no DataFrame (exatamente como no original)
            available_tech_cols = [col for col in tech_columns if col in df.columns]
            
            if available_tech_cols:
                tech_df = df[available_tech_cols].copy()
                
                # Adiciona análise técnica resumida (exatamente como no original)
                tech_df['analise_tecnica'] = tech_df.apply(self._generate_technical_analysis, axis=1)
                
                tech_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                self.logger.info(f"✅ {self.get_sheet_name()}: {len(tech_df)} URLs com análise técnica")
            else:
                error_df = pd.DataFrame([['Nenhuma coluna técnica encontrada']], columns=['Erro'])
                error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                self.logger.warning(f"❌ {self.get_sheet_name()}: Nenhuma coluna técnica encontrada")
                
        except Exception as e:
            self.logger.error(f"Erro criando aba técnica: {e}")
            error_df = pd.DataFrame([[f'Erro: {str(e)}']], columns=['Erro'])
            error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
    
    def _generate_technical_analysis(self, row) -> str:
        """
        Gera análise técnica resumida para cada URL - IDÊNTICO ao método original
        """
        try:
            issues = []
            
            # Verifica problemas técnicos (exatamente como no original)
            if row.get('status_code', 200) != 200:
                issues.append(f"Status {row.get('status_code')}")
            
            if not row.get('has_viewport', True):
                issues.append("Sem viewport")
            
            if not row.get('has_charset', True):
                issues.append("Sem charset")
            
            if not row.get('canonical_url', ''):
                issues.append("Sem canonical")
            
            if row.get('canonical_is_self', True) == False:
                issues.append("Canonical externa")
            
            if row.get('response_time', 0) > 3:
                issues.append("Lenta")
            
            if row.get('schema_total_count', 0) == 0:
                issues.append("Sem schema")
            
            if row.get('og_tags_count', 0) == 0:
                issues.append("Sem Open Graph")
            
            # Verifica Mixed Content (se disponível)
            if row.get('total_mixed_content_count', 0) > 0:
                if row.get('active_mixed_content_count', 0) > 0:
                    issues.append("Mixed Content CRÍTICO")
                else:
                    issues.append("Mixed Content")
            
            # Retorna resumo (exatamente como no original)
            if issues:
                return '; '.join(issues)
            else:
                return '✅ OK'
                
        except Exception:
            return 'Erro na análise'