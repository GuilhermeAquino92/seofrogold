"""
seofrog/exporters/sheets/links_internos_redirect.py
Aba "Internal" - Links internos com redirects (igual Screaming Frog)
🔧 VERSÃO CORRIGIDA: Acessa dados corretos com Anchor Text e Link Path
"""

import pandas as pd
from typing import List, Dict, Any
from .base_sheet import BaseSheet
from seofrog.utils.logger import get_logger

class LinksInternosRedirectSheet(BaseSheet):
    """
    Aba "Internal" - Links internos com redirects
    Formato igual ao Screaming Frog: Type, From, To, Anchor Text, etc.
    🔧 CORRIGIDO: Agora acessa dados corretos do LinksParser
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
        🔧 VERSÃO CORRIGIDA - Acessa dados de redirects da coluna correta
        Agora pega os dados do LinksParser com Anchor Text e Link Path
        """
        redirects_data = []
        
        for _, row in df.iterrows():
            try:
                # 🆕 CORREÇÃO: Acessa dados do LinksParser via coluna 'internal_redirects_for_this_url'
                if 'internal_redirects_for_this_url' in row and pd.notna(row['internal_redirects_for_this_url']):
                    internal_redirects = row['internal_redirects_for_this_url']
                    
                    # Se é uma lista de dicts (dados do LinksParser)
                    if isinstance(internal_redirects, list):
                        for redirect_data in internal_redirects:
                            if isinstance(redirect_data, dict):
                                # 🎯 AQUI ESTÃO OS DADOS COM ANCHOR TEXT E LINK PATH!
                                redirect_export = {
                                    'Type': 'Redirect',  # Sempre redirect nesta aba
                                    'From': str(redirect_data.get('from_url', '')),
                                    'To Original': str(redirect_data.get('to_original', '')),
                                    'To Final': str(redirect_data.get('to_final', '')),
                                    'Anchor': str(redirect_data.get('anchor_text', '')),  # ✅ "Consulte as condições"!
                                    'Alt Text': str(redirect_data.get('alt_text', '')),
                                    'Follow': str(redirect_data.get('follow', True)),
                                    'Target': str(redirect_data.get('target', '')),
                                    'Rel': str(redirect_data.get('rel', '')),
                                    'Status Code': str(redirect_data.get('status_code', '')),
                                    'Status': self._get_status_text(redirect_data.get('status_code', 0)),
                                    'Redirected': 'True',
                                    'Link Path': str(redirect_data.get('link_path', ''))  # ✅ XPath completo!
                                }
                                redirects_data.append(redirect_export)
                
                # 🆕 FALLBACK: Mantém método alternativo apenas para redirects do sistema (HTTP→HTTPS)
                elif 'url' in row and 'final_url' in row:
                    if pd.notna(row['url']) and pd.notna(row['final_url']):
                        if str(row['url']).strip() != str(row['final_url']).strip():
                            # Só adiciona se não é um redirect de link interno já processado
                            redirect_item = {
                                'Type': 'Redirect',
                                'From': str(row['url']),
                                'To Original': str(row['final_url']),
                                'To Final': str(row['final_url']),
                                'Anchor': '',  # Redirects automáticos não têm anchor
                                'Alt Text': '',
                                'Follow': 'True',
                                'Target': '',
                                'Rel': '',
                                'Status Code': str(row.get('status_code', '')),
                                'Status': self._get_status_text(row.get('status_code', 0)),
                                'Redirected': 'True',
                                'Link Path': 'System Redirect'
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