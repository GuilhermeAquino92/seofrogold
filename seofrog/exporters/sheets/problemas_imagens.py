"""
seofrog/exporters/sheets/problemas_imagens.py
Aba específica para problemas de imagens - BASEADO NO _create_image_problems_sheet() ORIGINAL
"""

import pandas as pd
from .base_sheet import BaseSheet

class ProblemasImagensSheet(BaseSheet):
    """
    Sheet com problemas de imagens (sem ALT, sem SRC, muitas imagens)
    Baseado exatamente no método _create_image_problems_sheet() original (versão completa)
    """
    
    def get_sheet_name(self) -> str:
        return 'Problemas Imagens'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba de problemas de imagens - IDÊNTICO ao método original
        """
        try:
            image_issues = []
            
            # URLs com imagens sem ALT (exatamente como no original)
            if 'images_without_alt' in df.columns:
                images_no_alt = df[df['images_without_alt'].fillna(0) > 0].copy()
                if not images_no_alt.empty:
                    images_no_alt['problema'] = 'Imagens sem ALT'
                    images_no_alt['criticidade'] = 'ALTO'
                    image_issues.append(images_no_alt)
            
            # URLs com imagens sem SRC (exatamente como no original)
            if 'images_without_src' in df.columns:
                images_no_src = df[df['images_without_src'].fillna(0) > 0].copy()
                if not images_no_src.empty:
                    images_no_src['problema'] = 'Imagens sem SRC'
                    images_no_src['criticidade'] = 'CRÍTICO'
                    image_issues.append(images_no_src)
            
            # URLs com muitas imagens (pode ser problemático) (exatamente como no original)
            if 'images_count' in df.columns:
                many_images = df[df['images_count'].fillna(0) > 50].copy()
                if not many_images.empty:
                    many_images['problema'] = 'Muitas imagens (>50)'
                    many_images['criticidade'] = 'MÉDIO'
                    image_issues.append(many_images)
            
            if image_issues:
                # Concatena todos os problemas (exatamente como no original)
                all_image_issues = pd.concat(image_issues, ignore_index=True)
                all_image_issues = all_image_issues.drop_duplicates(subset=['url'], keep='first')
                
                # Define colunas para exportar (exatamente como no original)
                cols = ['url', 'problema', 'criticidade', 'images_count', 'images_without_alt', 'images_without_src']
                available_cols = [col for col in cols if col in all_image_issues.columns]
                
                if available_cols:
                    all_image_issues[available_cols].to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                    self.logger.info(f"✅ {self.get_sheet_name()}: {len(all_image_issues)} problemas encontrados")
                else:
                    error_df = pd.DataFrame([['Colunas de imagens não encontradas']], columns=['Erro'])
                    error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            else:
                # Sucesso - nenhum problema encontrado (exatamente como no original)
                success_df = pd.DataFrame([['✅ Nenhum problema de imagem encontrado!']], columns=['Status'])
                success_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                self.logger.info(f"✅ {self.get_sheet_name()}: Nenhum problema encontrado")
                
        except Exception as e:
            self.logger.error(f"Erro criando aba de problemas de imagens: {e}")
            error_df = pd.DataFrame([[f'Erro: {str(e)}']], columns=['Erro'])
            error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)