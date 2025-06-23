"""
seofrog/exporters/sheets/dados_completos.py
Aba específica para dados completos - todos os dados em formato tabular
"""

import pandas as pd
from .base_sheet import BaseSheet

class DadosCompletosSheet(BaseSheet):
    """
    Sheet com todos os dados completos do crawl
    Responsável por organizar, ordenar e limpar os dados
    """
    
    def get_sheet_name(self) -> str:
        return 'Dados Completos'
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria a aba de dados completos com ordenação otimizada
        """
        try:
            # Prepara DataFrame
            df_processed = self._prepare_dataframe(df)
            
            # Reordena colunas por importância
            df_ordered = self._reorder_columns(df_processed)
            
            # Exporta para Excel
            df_ordered.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            
            self.logger.info(f"✅ {self.get_sheet_name()}: {len(df_ordered)} linhas × {len(df_ordered.columns)} colunas")
            
        except Exception as e:
            self.logger.error(f"Erro criando aba dados completos: {e}")
            # Fallback: exporta DataFrame original
            df.fillna('').to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
    
    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara DataFrame: limpa dados, adiciona colunas obrigatórias
        """
        df_clean = df.copy()
        
        # Adiciona colunas obrigatórias se não existirem
        required_columns = [
            'url', 'status_code', 'title', 'meta_description',
            'h1_count', 'h2_count', 'response_time', 'crawl_timestamp'
        ]
        
        for col in required_columns:
            if col not in df_clean.columns:
                df_clean[col] = ''
                self.logger.debug(f"Adicionada coluna obrigatória: {col}")
        
        # Preenche valores nulos
        df_clean = df_clean.fillna('')
        
        # Remove duplicatas baseado na URL
        if 'url' in df_clean.columns:
            initial_count = len(df_clean)
            df_clean = df_clean.drop_duplicates(subset=['url'], keep='first')
            removed_count = initial_count - len(df_clean)
            if removed_count > 0:
                self.logger.info(f"🔄 Removidas {removed_count} URLs duplicadas")
        
        return df_clean
    
    def _reorder_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Reordena colunas por ordem de importância/relevância
        """
        # Definição da ordem de prioridade das colunas
        priority_columns = [
            # === INFORMAÇÕES BÁSICAS ===
            'url',
            'final_url', 
            'status_code',
            
            # === SEO BÁSICO ===
            'title',
            'title_length',
            'title_words',
            'meta_description',
            'meta_description_length',
            'meta_keywords',
            
            # === ESTRUTURA DE HEADINGS ===
            'h1_count',
            'h1_text',
            'h1_length',
            'h2_count',
            'h3_count',
            'h4_count',
            'h5_count',
            'h6_count',
            
            # === LINKS ===
            'internal_links_count',
            'external_links_count',
            'total_links_count',
            
            # === IMAGENS ===
            'images_count',
            'images_without_alt',
            'images_without_src',
            
            # === CONTEÚDO ===
            'word_count',
            'character_count',
            'text_ratio',
            
            # === SEO TÉCNICO ===
            'canonical_url',
            'canonical_is_self',
            'meta_robots',
            'has_viewport',
            'has_charset',
            'has_favicon',
            
            # === STRUCTURED DATA ===
            'schema_total_count',
            'og_tags_count',
            'twitter_tags_count',
            
            # === PERFORMANCE ===
            'response_time',
            'content_length',
            'content_type',
            
            # === METADADOS ===
            'crawl_timestamp',
            'crawl_depth'
        ]
        
        # Separa colunas disponíveis vs extras
        available_columns = [col for col in priority_columns if col in df.columns]
        extra_columns = [col for col in df.columns if col not in priority_columns]
        
        # Ordem final: prioridade + extras ordenadas alfabeticamente
        final_columns = available_columns + sorted(extra_columns)
        
        self.logger.debug(f"Colunas reordenadas: {len(available_columns)} prioritárias + {len(extra_columns)} extras")
        
        return df[final_columns]