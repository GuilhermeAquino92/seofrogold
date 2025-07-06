"""
seofrog/exporters/sheets/links_internos_redirect.py
Aba "Internal" - Links internos com redirects (igual Screaming Frog)
"""

import pandas as pd
from typing import List, Dict, Any
from .base_sheet import BaseSheet
from seofrog.utils.logger import get_logger

class LinksInternosRedirectSheet(BaseSheet):
    """
    Aba "Internal" - Links internos com redirects
    Formato igual ao Screaming Frog: Type, From, To, Anchor Text, etc.
    """
    
    def __init__(self):
        self.logger = get_logger('LinksInternosRedirectSheet')
    
    def get_sheet_name(self) -> str:
        return "Internal"
    
    def create_sheet(self, df: pd.DataFrame, writer) -> None:
        """
        Cria aba "Internal" com links internos que redirecionam
        """
        try:
            # Coleta dados de redirects
            redirects_data = self._collect_redirect_data(df)
            
            if not redirects_data:
                # Se não tem redirects, cria sheet vazia mas com headers
                empty_df = self._create_empty_dataframe()
                empty_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
                self.logger.info(f"📄 {self.get_sheet_name()}: 0 redirects (aba criada vazia)")
                return
            
            # Cria DataFrame dos redirects
            redirects_df = pd.DataFrame(redirects_data)
            
            # Ordenar por 'From' para organização
            redirects_df = redirects_df.sort_values('From', ascending=True)
            
            # Exporta para Excel
            redirects_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
            
            self.logger.info(f"✅ {self.get_sheet_name()}: {len(redirects_df)} redirects exportados")
            
        except Exception as e:
            self.logger.error(f"❌ Erro criando {self.get_sheet_name()}: {e}")
            # Fallback: cria sheet de erro
            error_df = pd.DataFrame([['Erro ao processar redirects', str(e)]], 
                                  columns=['Erro', 'Detalhes'])
            error_df.to_excel(writer, sheet_name=self.get_sheet_name(), index=False)
    
    def _collect_redirect_data(self, df: pd.DataFrame) -> List[Dict[str, str]]:
        """
        Coleta dados de redirects do DataFrame principal
        """
        redirects_data = []
        
        for _, row in df.iterrows():
            try:
                # Verifica se tem links_parser nos metadados
                if hasattr(row, 'links_parser') and row.links_parser:
                    # Usa método do LinksParser para pegar redirects
                    page_redirects = row.links_parser.get_redirects_only_for_export()
                    redirects_data.extend(page_redirects)
                
                # Método alternativo: verifica se URL original != final_url
                elif 'url' in row and 'final_url' in row:
                    if pd.notna(row['url']) and pd.notna(row['final_url']):
                        if str(row['url']).strip() != str(row['final_url']).strip():
                            redirect_item = {
                                'Type': 'Redirect',
                                'From': str(row['url']),
                                'To Original': str(row['final_url']),
                                'To Final': str(row['final_url']),
                                'Anchor': '',
                                'Alt Text': '',
                                'Follow': 'True',
                                'Target': '',
                                'Rel': '',
                                'Status Code': str(row.get('status_code', '')),
                                'Status': self._get_status_text(row.get('status_code', 0)),
                                'Redirected': 'True',
                                'Link Path': 'Redirect'
                            }
                            redirects_data.append(redirect_item)
                            
            except Exception as e:
                self.logger.debug(f"Erro processando linha para redirects: {e}")
                continue
        
        return redirects_data
    
    def _get_status_text(self, status_code: int) -> str:
        """
        Converte status code para texto descritivo
        """
        status_map = {
            301: 'Moved Permanently',
            302: 'Found', 
            303: 'See Other',
            307: 'Temporary Redirect',
            308: 'Permanent Redirect',
            200: 'OK',
            404: 'Not Found',
            500: 'Internal Server Error'
        }
        
        try:
            code = int(status_code)
            return status_map.get(code, f'HTTP {code}')
        except:
            return 'Unknown'
    
    def _create_empty_dataframe(self) -> pd.DataFrame:
        """
        Cria DataFrame vazio com headers padrão (igual Screaming Frog)
        """
        columns = [
            'Type',           # Hyperlink, Redirect, etc.
            'From',           # URL de origem
            'To Original',    # URL destino original
            'To Final',       # URL destino final (após redirects)
            'Anchor',         # Texto do anchor
            'Alt Text',       # Alt text (para imagens)
            'Follow',         # Follow/Nofollow
            'Target',         # Target do link (_blank, etc.)
            'Rel',            # Rel attribute
            'Status Code',    # Status HTTP
            'Status',         # Status texto
            'Redirected',     # True/False
            'Link Path'       # Caminho do link
        ]
        
        return pd.DataFrame(columns=columns)