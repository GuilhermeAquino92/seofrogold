"""
seofrog/exporters/sheets/base_sheet.py
Classe base abstrata para todas as sheets especializadas
"""

import pandas as pd
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from seofrog.utils.logger import get_logger

class BaseSheet(ABC):
    """
    Classe base abstrata para todas as sheets especializadas
    Define interface comum e métodos utilitários
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    def get_sheet_name(self) -> str:
        """
        Retorna o nome da sheet para o Excel
        
        Returns:
            str: Nome da aba no Excel
        """
        pass
    
    @abstractmethod
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria a sheet com dados específicos
        
        Args:
            df: DataFrame com todos os dados do crawl
            writer: pd.ExcelWriter object
        """
        pass
    
    # ==========================================
    # MÉTODOS UTILITÁRIOS COMUNS
    # ==========================================
    
    def _safe_filter(self, df: pd.DataFrame, column: str, condition) -> pd.DataFrame:
        """
        Filtra DataFrame de forma segura, verificando se coluna existe
        
        Args:
            df: DataFrame para filtrar
            column: Nome da coluna
            condition: Condição de filtro
            
        Returns:
            DataFrame filtrado ou vazio se coluna não existir
        """
        if column not in df.columns:
            self.logger.warning(f"Coluna '{column}' não encontrada em {self.get_sheet_name()}")
            return pd.DataFrame()
        
        try:
            return df[condition].copy()
        except Exception as e:
            self.logger.warning(f"Erro filtrando {column} em {self.get_sheet_name()}: {e}")
            return pd.DataFrame()
    
    def _safe_get_column(self, df: pd.DataFrame, column: str, default_value=0):
        """
        Obtém coluna de forma segura com valor padrão
        
        Args:
            df: DataFrame
            column: Nome da coluna
            default_value: Valor padrão se coluna não existir
            
        Returns:
            pd.Series com a coluna ou valores padrão
        """
        if column in df.columns:
            return df[column].fillna(default_value)
        else:
            self.logger.debug(f"Coluna '{column}' não existe, usando valor padrão: {default_value}")
            return pd.Series([default_value] * len(df), name=column)
    
    def _create_error_sheet(self, writer, error_msg: str):
        """
        Cria aba de erro padronizada
        
        Args:
            writer: pd.ExcelWriter
            error_msg: Mensagem de erro
        """
        try:
            error_df = pd.DataFrame([[error_msg]], columns=['Erro'])
            error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            self.logger.error(f"❌ {self.get_sheet_name()}: {error_msg}")
        except Exception as e:
            self.logger.error(f"Erro criando sheet de erro para {self.get_sheet_name()}: {e}")
    
    def _create_success_sheet(self, writer, success_msg: str):
        """
        Cria aba de sucesso padronizada
        
        Args:
            writer: pd.ExcelWriter
            success_msg: Mensagem de sucesso
        """
        try:
            success_df = pd.DataFrame([[success_msg]], columns=['Status'])
            success_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            self.logger.info(f"✅ {self.get_sheet_name()}: {success_msg}")
        except Exception as e:
            self.logger.error(f"Erro criando sheet de sucesso para {self.get_sheet_name()}: {e}")
    
    def _export_dataframe(self, df: pd.DataFrame, writer, columns: List[str] = None):
        """
        Exporta DataFrame para Excel de forma segura
        
        Args:
            df: DataFrame para exportar
            writer: pd.ExcelWriter
            columns: Lista de colunas específicas (opcional)
        """
        try:
            if df.empty:
                self._create_success_sheet(writer, f"✅ Nenhum problema encontrado!")
                return
            
            # Filtra colunas se especificado
            if columns:
                available_cols = [col for col in columns if col in df.columns]
                if available_cols:
                    df = df[available_cols]
                else:
                    self._create_error_sheet(writer, 'Colunas necessárias não encontradas')
                    return
            
            # Exporta DataFrame
            df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            self.logger.info(f"✅ {self.get_sheet_name()}: {len(df)} registros exportados")
            
        except Exception as e:
            self.logger.error(f"Erro exportando DataFrame para {self.get_sheet_name()}: {e}")
            self._create_error_sheet(writer, f'Erro na exportação: {str(e)}')
    
    def _export_consolidated_issues(self, issues: List[Dict], writer):
        """
        Exporta lista consolidada de problemas
        Método comum para sheets que detectam múltiplos tipos de problemas
        
        Args:
            issues: Lista de dicionários com problemas
            writer: pd.ExcelWriter
        """
        if not issues:
            self._create_success_sheet(writer, '✅ Nenhum problema encontrado!')
            return
        
        try:
            # Converte para DataFrame
            issues_df = pd.DataFrame(issues)
            
            # Ordena por criticidade se a coluna existir
            if 'criticidade' in issues_df.columns:
                criticality_order = {'CRÍTICO MÁXIMO': 0, 'CRÍTICO': 1, 'ALTO': 2, 'MÉDIO': 3, 'BAIXO': 4}
                issues_df['_sort_order'] = issues_df['criticidade'].map(criticality_order).fillna(5)
                issues_df = issues_df.sort_values('_sort_order').drop('_sort_order', axis=1)
            
            # Remove duplicatas baseado na URL se possível
            if 'url' in issues_df.columns:
                initial_count = len(issues_df)
                issues_df = issues_df.drop_duplicates(subset=['url'], keep='first')
                removed_count = initial_count - len(issues_df)
                if removed_count > 0:
                    self.logger.debug(f"Removidas {removed_count} duplicatas em {self.get_sheet_name()}")
            
            # Exporta
            issues_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            self.logger.info(f"✅ {self.get_sheet_name()}: {len(issues_df)} problemas encontrados")
            
        except Exception as e:
            self.logger.error(f"Erro exportando problemas consolidados para {self.get_sheet_name()}: {e}")
            self._create_error_sheet(writer, f'Erro consolidando problemas: {str(e)}')
    
    def _get_url_info(self, row: pd.Series) -> Dict[str, Any]:
        """
        Extrai informações básicas da URL para sheets de problemas
        
        Args:
            row: Linha do DataFrame
            
        Returns:
            Dict com informações básicas da URL
        """
        return {
            'url': row.get('url', ''),
            'final_url': row.get('final_url', ''),
            'status_code': row.get('status_code', ''),
            'title': row.get('title', ''),
            'response_time': row.get('response_time', ''),
            'crawl_timestamp': row.get('crawl_timestamp', '')
        }
    
    def _detect_page_type(self, row: pd.Series) -> str:
        """
        Detecta o tipo da página baseado na URL
        Útil para sheets que precisam categorizar páginas
        
        Args:
            row: Linha do DataFrame
            
        Returns:
            str: Tipo da página detectado
        """
        url = str(row.get('url', '')).lower()
        
        # Páginas específicas
        if url.endswith('/') and url.count('/') <= 3:
            return 'Homepage'
        elif '/blog/' in url or '/artigo/' in url or '/post/' in url:
            return 'Blog/Artigo'
        elif '/produto/' in url or '/product/' in url:
            return 'Produto'
        elif '/categoria/' in url or '/category/' in url:
            return 'Categoria'
        elif '/sobre' in url or '/about' in url:
            return 'Institucional'
        elif '/contato' in url or '/contact' in url:
            return 'Contato'
        elif '/busca' in url or '/search' in url:
            return 'Busca'
        else:
            return 'Conteúdo'
    
    def _calculate_percentage(self, value: int, total: int) -> str:
        """
        Calcula porcentagem de forma segura
        
        Args:
            value: Valor
            total: Total
            
        Returns:
            str: Porcentagem formatada
        """
        if total == 0:
            return '0.0%'
        return f"{(value / total * 100):.1f}%"